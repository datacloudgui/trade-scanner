# Etapa 5A — TimeframeSpec + SymbolData (lógica y tests sintéticos)

**Estado:** en progreso (T1 ✅ · T2 ✅ · falta T3 — ver [etapa-05a-checkpoint.md](etapa-05a-checkpoint.md))
**Depende de:** Etapa 4 (UniverseSpec entrega tickers por estrategia)
**Estimado:** 4–6 horas
**Contexto:** primera mitad de la antigua Etapa 5, fraccionada el 2026-06-11 (análisis en [etapa-05.md](etapa-05.md)). La integración en `main.py`, los datos de muestra y la validación manual de precisión son **Etapa 5B**.

---

## Objetivo

Al cerrar la etapa existen `core/timeframes.py` y `core/symbol_data.py`: el primero es un registro declarativo de timeframes con la fórmula de warmup generalizada (PLAN §4) y un planificador con presupuesto; el segundo construye, por símbolo, **solo** los consolidators e indicadores de la unión de timeframes declarados, con un único punto de entrada de datos que funciona igual en warmup (barras diarias históricas) y en runtime (barras minute). Todo verificado por tests con TradeBars sintéticos dentro de Docker — esta etapa no toca `main.py` ni necesita datos reales.

A partir de aquí, Etapa 5B puede integrar el warmup real sabiendo que la lógica de consolidación, registro y profundidad es correcta.

---

## Decisiones de diseño

### D1 — Registro declarativo de timeframes (no if/elif)

Cada timeframe es una entrada en un registro; la fórmula de warmup es una sola y opera sobre los atributos del spec. Añadir un marco futuro (ej. 5m/15m/30m como marcos principales) = añadir una entrada, **cero ediciones a fórmulas o a `SymbolData`**.

```python
@dataclass(frozen=True)
class TimeframeSpec:
    code: str                # "D" | "W" | "M"  (futuros: "5T", "15T", "30T")
    source_resolution: str   # "daily" | "minute" — string propio; el mapeo a Resolution de LEAN vive en symbol_data
    bars_per_period: int     # barras fuente por barra consolidada: D=1, W=5, M=21 (5T=5, 30T=30 en minutos)
    buffer_bars: int         # colchón por barra parcial inicial + feriados: D=5, W=10, M=21

    def warmup_bars(self, period: int) -> int:
        return period * self.bars_per_period + self.buffer_bars

    def make_consolidator(self):
        """Import perezoso de AlgorithmImports aquí dentro — el módulo se importa sin CLR."""

TIMEFRAMES: dict[str, TimeframeSpec] = {"D": ..., "W": ..., "M": ...}
```

Profundidades que la fórmula debe reproducir (verificadas por test):

| Timeframe | SMA 8 | SMA 20 | SMA 200 |
|---|---|---|---|
| D (`n+5`) | 13 | 25 | 205 |
| W (`n×5+10`) | 50 | 110 | 1.010 |
| M (`n×21+21`) | 189 | 441 | 4.221 |

`timeframes.py` sigue el patrón de `universe.py`: **sin imports de `AlgorithmImports` a nivel de módulo** (solo dentro de `make_consolidator`). Los tests de fórmula y planificación corren sin tocar el CLR; los de consolidators sí (Docker, como siempre).

### D2 — `plan_warmup()` con presupuesto: SMA 200 condicional en el marco mayor

Decisión de producto (2026-06-11): SMA 200 es **must en los dos marcos menores** y **activable en el marco mayor según proveedor de datos**. El mecanismo es un presupuesto por resolución fuente, no un hardcodeo de "D y W sí, M no":

```python
@dataclass(frozen=True)
class PlannedSeries:
    tf: str
    period: int
    warmup_bars: int

@dataclass(frozen=True)
class WarmupPlan:
    depth_by_resolution: dict[str, int]   # ej. {"daily": 1010} — max de las series incluidas
    included: list[PlannedSeries]
    excluded: list[PlannedSeries]         # series cuyo warmup_bars excede el presupuesto

def plan_warmup(
    requirements: dict[str, set[int]],          # unión por símbolo: {"D": {8,20,200}, "W": {8,20,200}, "M": {8,20,200}}
    budget: dict[str, int] | None = None,       # ej. {"daily": 1200} — None = sin límite
) -> WarmupPlan: ...
```

- Con `budget={"daily": 1200}`: `W:200` (1.010) entra; `M:200` (4.221) queda en `excluded` → el llamador (main.py, 5B) loguea warning y no crea esa SMA. Con un proveedor de historia profunda, subir el presupuesto en config activa `M:200` sin tocar código.
- Función pura → test sin LEAN. El presupuesto vivirá en `environments` de `strategies.json` (cableado en 5B); aquí solo se implementa y testea la función.

### D3 — SMAs cableadas al evento del consolidator (compatibilidad QC cloud verificada)

Acordado el 2026-06-11 (condicionado por el usuario a no romper compatibilidad cloud): `SymbolData` **no recibe la instancia del algorithm**. Cada SMA se suscribe al evento `data_consolidated` de su consolidator y se actualiza con `sma.update(bar.end_time, bar.close)`.

**Por qué no rompe la portabilidad:** `TradeBarConsolidator`, el evento `DataConsolidated` y `IndicatorBase.update` son APIs del engine (assemblies `QuantConnect.Common`/`QuantConnect.Indicators`), idénticas en local y en QC cloud. `register_indicator` es un wrapper de conveniencia de `QCAlgorithm` que hace exactamente este cableado por dentro. Lo único que sí requiere el algorithm — conectar el consolidator raíz al flujo de datos de la suscripción (`self.subscription_manager.add_consolidator`) — queda en `main.py` (L5, Etapa 5B), también API estándar en cloud. La portabilidad se re-verifica formalmente en Etapa 9.

Esto es una excepción acordada a la mención literal de `register_indicator` en CLAUDE.md/PLAN §1.6: se mantiene el espíritu de la regla (indicadores + consolidators de LEAN, cero resampling con pandas) con el mecanismo nativo subyacente.

### D4 — Un punto de entrada de datos; cadena minute→daily→W/M

El riesgo más fino de la antigua Etapa 5: el warmup empuja barras **diarias** de `self.history`, pero en runtime llegan barras **minute**. Diseño:

```
update(bar) ──► consolidator diario (timedelta(days=1))
                   │  data_consolidated (barra diaria)
                   ├──► SMA D:8, D:20, D:200
                   ├──► consolidator W (Calendar.WEEKLY) ──► SMA W:n
                   └──► consolidator M (Calendar.MONTHLY) ──► SMA M:n
```

- `SymbolData.update(bar)` es el único punto de entrada: acepta tanto la barra minute de runtime como la barra diaria histórica del warmup (el `TradeBarConsolidator` agrega cualquier barra contenida en su periodo; una barra diaria completa el periodo y emite).
- W y M se **encadenan** a la salida del consolidator diario — nunca consumen minutos directamente. Una sola ruta de verdad para construir barras semanales/mensuales.
- El test de equivalencia (T3.9) alimenta el mismo día con minutos sintéticos y con su barra diaria equivalente, y exige barras W idénticas por ambas rutas. Esto des-riesga 5B antes de empezarla.
- `working_bar` = `working_data` del consolidator diario (barra parcial del día en curso cuando entran minutos).

---

## Tareas

> **Esfuerzo Fable por tarea** (se ajusta con `/model`): base `high` — punto dulce calidad/costo para trabajo spec-driven con criterios verificables. `xhigh` reservado para las partes que razonan sobre semántica de LEAN no documentada (consolidators, cadena de alimentación). `max` solo si una sesión queda genuinamente atascada. Tareas mecánicas (checkboxes, commits) pueden bajar a `medium`.

### T1 — `core/timeframes.py`: registro + fórmula + plan · esfuerzo Fable: `high`

Nuevo archivo según D1 y D2: `TimeframeSpec`, `TIMEFRAMES` (D/W/M), `warmup_bars`, `plan_warmup`, `WarmupPlan`, `PlannedSeries`.

**Notas técnicas:**
- `Calendar` no expone variante diaria en Python: el consolidator de D es `TradeBarConsolidator(timedelta(days=1))`; W y M usan `Calendar.WEEKLY` / `Calendar.MONTHLY`.
- `source_resolution` como string propio (`"daily"`/`"minute"`) mantiene el módulo libre de CLR; `symbol_data.py` (o main.py en 5B) mapea a `Resolution.DAILY`/`Resolution.MINUTE`.
- Validación de entrada: timeframe desconocido en `requirements` → `KeyError`/`ValueError` con mensaje que nombra el código (no silencioso), consistente con el manejo de errores de `UniverseSpec`.

**Criterio de aceptación:**
- `warmup_bars` reproduce la tabla D1 exacta para D/W/M × {8, 20, 200}.
- `plan_warmup({"D": {8,20,200}, "W": {8,20,200}, "M": {8,20,200}}, budget={"daily": 1200})` → `depth_by_resolution == {"daily": 1010}`, `M:200` en `excluded`, el resto en `included`.
- Sin presupuesto (`budget=None`) → `depth_by_resolution == {"daily": 4221}` y nada excluido.
- `import core.timeframes` funciona sin `AlgorithmImports` cargado (test puede correr antes de cualquier import LEAN).

### T2 — `core/symbol_data.py`: `SymbolData` · esfuerzo Fable: `xhigh`

Nuevo archivo según D3 y D4.

**Interfaz:**
```python
class SymbolData:
    def __init__(self, symbol, requirements: dict[str, set[int]]):
        """requirements = unión de (tf → periodos) de todas las estrategias que usan el símbolo.
        Construye SOLO los consolidators y SMAs declarados. Valida contra TIMEFRAMES."""

    def update(self, bar) -> None:
        """Único punto de entrada: barra minute (runtime) o diaria (warmup histórico)."""

    def scan(self, time) -> None:
        """Flush de barras con periodo vencido (añadido en T2 — ver consideración 3 corregida)."""

    @property
    def daily_consolidator(self): ...   # main.py (5B) lo conecta a la suscripción minute

    @property
    def working_bar(self): ...          # OHLC parcial del día en curso (working_data) o None

    def sma(self, tf: str, period: int): ...   # KeyError con mensaje claro si no fue declarada

    def is_ready(self, tf: str | None = None, period: int | None = None) -> bool:
        """Sin args: todas las SMAs declaradas calientes. Con args: una serie concreta."""
```

**Notas técnicas:**
- Importa **tipos** de `AlgorithmImports` (`TradeBarConsolidator`, `Calendar`, `SimpleMovingAverage`) — eso es L2 legítimo. Lo prohibido es referenciar la **instancia** de `QCAlgorithm` (D3); verificable por grep.
- Suscripción a eventos: `consolidator.data_consolidated += handler`. El handler de D, además de actualizar las SMAs D, empuja la barra consolidada a los consolidators W/M (cadena D4). Cuidado con capturas en lambdas dentro de loops (cerrar sobre la variable con default arg).
- Si un timeframe se declara sin periodos (set vacío), no se crea nada para él.
- `is_ready()` agregado existe para que 5B/Etapa 7 excluyan símbolos fríos del scan; aquí solo se expone.

**Criterio de aceptación:**
- Con `{"D": {8,20}, "W": {20}}`: no existe consolidator M ni SMA `W:8` (introspección por test — unión exacta, nada de más).
- Tras `update()` con barras diarias suficientes, `is_ready()` es `True`; con barras insuficientes, `False` sin excepciones.
- `working_bar` devuelve el OHLC parcial correcto a mitad de día con barras minute, y `None`/vacío antes de la primera barra.

### T3 — Tests unitarios con TradeBars sintéticos (en Docker) · esfuerzo Fable: `high` (↑ `xhigh` en T3.9)

Nuevos `tests/test_timeframes.py` y `tests/test_symbol_data.py`. Los TradeBars se construyen a mano con valores cuya aritmética se documenta en comentario (convención de Etapa 2). Gotcha transversal: el `TradeBarConsolidator` emite la barra consolidada **al recibir una barra que cruza el límite del periodo** — los tests deben empujar una barra posterior (o usar `scan(time)`) para forzar el flush de la última barra.

- **T3.1 — fórmula:** tabla D1 completa (D/W/M × 8/20/200).
- **T3.2 — extensibilidad:** registrar en el test un `TimeframeSpec("30T", "minute", 30, 60)` sintético y obtener `warmup_bars(200) == 6060` **sin tocar código de la fórmula**; `plan_warmup` lo agrupa bajo `"minute"` separado de `"daily"`.
- **T3.3 — plan con presupuesto:** caso del criterio T1 (M:200 excluida con budget 1200; sin budget nada se excluye).
- **T3.4 — semana cierra viernes:** 2 semanas de barras diarias (lun–vie) → exactamente 2 barras W con OHLCV verificable a mano (`Calendar.WEEKLY` agrupa lunes→domingo).
- **T3.5 — mes calendario:** 2 meses de barras diarias → 2 barras M correctas.
- **T3.6 — SMA a mano:** SMA(3) semanal sobre closes conocidos (ej. semanas que cierran 10, 20, 30 → SMA 20.0).
- **T3.7 — primera barra parcial:** historia que arranca un miércoles → la primera barra W es parcial; verificar que tras `buffer_bars` adicionales la SMA coincide con el cálculo a mano que ignora la semana incompleta (justifica el buffer de D1).
- **T3.8 — unión exacta:** criterio de T2.
- **T3.9 — equivalencia de rutas (des-riesga 5B):** mismos días alimentados como (a) barras diarias directas y (b) barras minute sintéticas (bastan ~3 por día: open/mid/close) → las barras W emitidas y los valores de SMA finales son idénticos por ambas rutas.
- **T3.10 — working bar:** con barras minute de medio día, `working_bar` tiene open de la primera, high/low agregados y close de la última.
- **T3.11 — readiness:** `is_ready("W", 20)` falso con 19 barras W, verdadero con 20; `is_ready()` agregado refleja la serie más lenta.

**Criterio de aceptación:** `bash scripts/run_tests.sh` verde con los 11 casos (más los tests previos del repo).

---

## Scope

✅ Entra en esta etapa:
- `core/timeframes.py` completo (D1 + D2)
- `core/symbol_data.py` completo (D3 + D4)
- `tests/test_timeframes.py` + `tests/test_symbol_data.py` (T3.1–T3.11)
- Exportar desde `core/__init__.py`

❌ No entra (todo es **Etapa 5B** salvo indicación):
- **Integración en `main.py`** — crear SymbolData por símbolo del universo, `self.history` batch, conexión del consolidator diario a la suscripción, logs de warmup.
- **Datos de muestra multi-símbolo** (`seed_sample_data.sh`) y cualquier backtest como evidencia — esta etapa se verifica solo con `run_tests.sh`.
- **`DataNormalizationMode.SPLIT_ADJUSTED`** en `add_equity` — decisión ya tomada (cuadra con el default de TradingView/IBKR), se aplica donde se suscriben símbolos (5B).
- **Cambio de `strategies.json` prod** a `D:[8,20,200]`, `W:[8,20,200]` — acordado para 5B, donde su efecto (warmup real) es observable.
- **Archivo de validación + validación manual del usuario** (tolerancia ≤0,25%, fixture de regresión) — 5B.
- **Cableado del presupuesto a `environments`** — `plan_warmup` lo acepta como argumento; leerlo de config es 5B.
- **Features, Rules, exclusión de símbolos fríos del scan** — Etapas 6–7.
- **Consolidators intradía reales** (5m/15m/30m) — solo se prueba que el registro los admite (T3.2).

---

## Consideraciones técnicas específicas al stack

1. **Emisión del consolidator es perezosa:** la barra W/M se emite cuando llega data que cruza el límite del periodo, no al completarse el periodo en tiempo de reloj. En tests → trailing bar o `scan()`. En producción esto es correcto y deseado (las SMAs W/M se actualizan con la primera barra de la semana/mes siguiente — gotcha ya documentado en CLAUDE.md: indicadores estables intradía).
2. **`end_time` de la barra consolidada cae al inicio del periodo siguiente** (`Calendar.WEEKLY` lunes→domingo, cierre efectivo viernes; `Calendar.MONTHLY` mes calendario). Los asserts de los tests fijan estas convenciones por escrito; el archivo de validación de 5B reportará `bar_end_time` tal cual.
3. **Barras diarias dentro del consolidator `timedelta(days=1)` — CORREGIDO (hallazgo T2, 2026-06-11):** la suposición original ("una barra diaria completa exactamente el periodo y emite") es **falsa**: la emisión es perezosa incluso con barras diarias exactas — la barra queda en `working_data` hasta que llega una barra posterior o un `scan(time)` (verificado en Docker: 3 barras diarias → SMA(3) con solo 2 muestras). El lag se **encadena** a W/M: la barra W de la semana 1 exige que una barra diaria de la semana 2 sea *emitida*, no solo pusheada. Consecuencias: (a) `SymbolData` expone `scan(time)` — flush del diario primero y luego de los encadenados; `scan` solo emite si el periodo venció, es seguro a mitad de semana/mes; (b) el warmup de 5B debe cerrar con `scan(end_time de la última barra)` o las SMAs quedan un periodo frías; (c) `buffer_bars` absorbe el +1 en producción. T3.9 mantiene su rol (equivalencia daily directo vs minute encadenado) y T3.x usa trailing bar o `scan()`.
4. **Actualización de SMA desde el handler:** `sma.update(bar.end_time, bar.close)` (o `IndicatorDataPoint`). Usar `end_time`, no `time` — con `time` la SMA queda desplazada un periodo.
5. **Lambdas en loops:** al suscribir handlers para varias SMAs/consolidators en un loop, capturar la variable con argumento por defecto (`lambda s, bar, sma=sma: ...`) o usar funciones parciales — el bug clásico de closure compartido produciría todas las SMAs actualizando la última serie.
6. **`timeframes.py` importable sin CLR** (import perezoso en `make_consolidator`): los tests de fórmula/plan no pagan el arranque de pythonnet y el módulo queda usable desde scripts del host, como `universe.py`. Los tests de `symbol_data.py` sí corren en Docker (receta de Etapa 2).
7. **`buffer_bars` es parte del contrato, no un detalle:** absorbe la primera barra parcial (T3.7) y la varianza por feriados (una semana con feriado aporta 4 barras diarias, no 5). Si en 5B la validación manual muestra SMAs W/M "casi correctas", lo primero a revisar es si el buffer expulsó la barra parcial inicial de la ventana.

---

## Done when (medible)

- [ ] `bash scripts/run_tests.sh` verde con T3.1–T3.11 (más los tests previos del repo)
- [ ] Solo se crean los consolidators/indicadores de la unión de timeframes declarados (T3.8)
- [ ] Profundidad de warmup derivada por fórmula generalizada; timeframe nuevo sin tocar la fórmula (T3.1–T3.2)
- [ ] `plan_warmup()` excluye series sobre presupuesto y reporta profundidad por resolución (T3.3)
- [ ] Equivalencia de rutas daily directo vs minute encadenado (T3.9)
- [ ] `grep -n "QCAlgorithm" trade-scanner/core/symbol_data.py` → sin resultados; `import core.timeframes` funciona sin CLR
- [ ] PLAN.md: checkboxes de Etapa 5A marcados y Estado a `completada`
- [ ] Commit `[Etapa 5A] ...`

---

## Preguntas abiertas

- [ ] **Convención de códigos intradía futuros:** propuesta `"5T"`, `"15T"`, `"30T"` (estilo pandas, evita colisión de `"M"` mes vs minuto). Solo afecta a T3.2 en esta etapa; se ratifica cuando se implementen de verdad.
- [ ] **¿`plan_warmup` por símbolo o global?** En 5B la unión de requirements será idéntica para casi todos los símbolos (mismas estrategias) — un plan global por conjunto de estrategias basta y simplifica el log. Decidir en 5B; la función actual es agnóstica (recibe requirements y devuelve plan).
- [x] **¿Cableado manual o `register_indicator`?** Resuelto 2026-06-11: cableado manual, condicionado a compatibilidad QC cloud — verificada (D3).
- [x] **¿Config SMA 200 en prod ahora o en 5B?** Resuelto 2026-06-11: en 5B.
