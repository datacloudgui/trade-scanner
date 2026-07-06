OpenAI Codex v0.139.0
--------
workdir: /Users/guille/Documents/quant/trade-scanner
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: detailed
session id: 019ee2cd-56f0-7270-a057-047d2a0b19d2
--------
user
Revisa exhaustivamente SOLO la Etapa 4 del proyecto, siguiendo la metodología y los criterios de AGENTS.md. Usa el documento .claude/fase-1-desarrollo-local/etapa-04.md como definición del alcance y los criterios de aceptación (Done when) de esta etapa, y PLAN.md/SPECS.md como fuentes de verdad del diseño. Traza objetivo->codigo->test para cada criterio de la etapa, verifica la API de LEAN y la corrección funcional de las funciones tocadas y que se relacionen en la etapa (dependencias de etapas previas) en esta etapa. Reporta hallazgos con archivo:linea, severidad y sugerencia. No modifiques archivos.
**Planning file operations**

I want to begin by looking at the present working directory (pwd) and searching through files with "rg." I think I should also consider staging documents, planning, and checking the specifications. To streamline this, I could use multi-tool parallel for independent readings since I don't need any chained commands at this point. Also, starting the commentary seems like the right move. This should help keep things organized!
codex
Voy a revisar en modo solo lectura, empezando por el alcance de Etapa 4 y las fuentes de verdad (`PLAN.md`/`SPECS.md`). Después trazaré los archivos y tests que implementan esa etapa contra cada criterio.
  → Leer alcance Etapa 4 y documentos de diseño aplicables
  • Mapear archivos y dependencias tocadas por Etapa 4
  • Auditar implementación, API LEAN y corrección funcional
  • Auditar tests y trazabilidad objetivo-código-test
  • Redactar hallazgos y resumen ejecutivo
exec
/bin/zsh -lc pwd in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
/Users/guille/Documents/quant/trade-scanner

exec
/bin/zsh -lc 'rg --files' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
CLAUDE.md
SPECS.md
PLAN.md
revision-quality-20260618.md
lean.json
review-report-clean.md
README.md
AGENTS.md
LICENSE
revisiones/20260619-205134/etapa-02-log.md
revisiones/20260619-205134/etapa-02-informe.md
revisiones/20260619-205134/etapa-04-log.md
revisiones/20260619-205134/etapa-01-log.md
revisiones/20260619-205134/etapa-03-informe.md
revisiones/20260619-205134/etapa-03-log.md
revisiones/20260619-205134/etapa-01-informe.md
trade-scanner/main.py
config/notifications.json
universes/sample_dev.csv
config/strategies.json
trade-scanner/config.json
scripts/seed_sample_data.sh
scripts/run_review.sh
scripts/seed_object_store.sh
scripts/notify_email.py
scripts/run_tests.sh
scripts/explore_universe.py
scripts/stooq_to_lean.py
trade-scanner/tests/test_sma_regression.py
trade-scanner/tests/test_strategies.py
trade-scanner/tests/test_pipeline.py
trade-scanner/tests/test_symbol_data.py
trade-scanner/tests/test_rules.py
trade-scanner/tests/test_timeframes.py
trade-scanner/tests/test_universe.py
trade-scanner/strategies/base.py
trade-scanner/strategies/market_close.py
trade-scanner/strategies/swing_eod.py
trade-scanner/strategies/__init__.py
docs/DEVLOG.md
docs/ROADMAP.md
trade-scanner/core/__init__.py
trade-scanner/core/timeframes.py
trade-scanner/core/rules.py
trade-scanner/tests/test_pythonnet_bridge.py
trade-scanner/tests/test_email_render.py
trade-scanner/tests/test_t5_stooq_crosscheck.py
trade-scanner/tests/test_features.py
trade-scanner/tests/test_output.py
trade-scanner/tests/__init__.py
trade-scanner/tests/test_notify_email.py
trade-scanner/core/output.py
trade-scanner/core/email_render.py
trade-scanner/core/symbol_data.py
trade-scanner/core/pipeline.py
trade-scanner/core/universe.py
trade-scanner/core/features.py
trade-scanner/tests/fixtures/envelope_sample.json
docs/conceptos/buckets-y-simetria-largo-corto.md
docs/conceptos/factory-vs-composicion.md

exec
/bin/zsh -lc "sed -n '1,240p' .claude/fase-1-desarrollo-local/etapa-04.md" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "sed -n '1,260p' PLAN.md" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "sed -n '1,260p' SPECS.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# SPECS — Screener de Acciones sobre LEAN

**Versión:** 0.1 (V1) · **Fecha:** 2026-06-19 · **Estado:** en desarrollo — Etapas 1–5A y 6 completadas; 6B en cierre (capa de reglas rediseñada — ADR-005: snapshot único + reglas como filtros puros); 5B en progreso; 7 completada (pipeline end-to-end + composición declarativa + minute subscription + schedule); **8 completada** (T1–T7, 2026-06-19: `OutputSink` con salida por entorno aislada — envelope por estrategia base persistido CSV/JSON + correo híbrido render-puro-compartido/canal-por-config + script host `notify_email.py` dry-run; backtest dev verificado. Envío real Gmail + `qc_notify` cloud live diferidos a Etapa 9). El backtest a escala ≥3 meses se difiere a Etapa 9 por límite de datos minute — decisión usuario.

---

## 1. Contexto

**Problema.** Los traders manejan un universo de ideas (tickers) demasiado amplio para revisar manualmente. Necesitan filtrarlo con criterios técnicos (y a futuro fundamentales) de forma sistemática, repetible y programada, en los momentos del día que cada estrategia exige.

**Solución.** Un screener construido sobre el motor LEAN que carga un universo desde CSV, mantiene indicadores precisos en tres marcos de tiempo (día, semana, mes), valida reglas por estrategia en horarios programados, y entrega una watchlist con evidencia de por qué cada ticker pasó los filtros.

**Usuario.** Traders discrecionales que operan una o más estrategias (swing, earnings, etc.) y usan el screener como primer filtro antes de su análisis manual. El screener **no decide ni ejecuta**: propone candidatos.

---

## 2. Stack tecnológico

| Componente | Elección |
|---|---|
| Engine | LEAN open source (Python 3.11) |
| Lenguaje | Python |
| IDE / Dev | VSCode + LEAN CLI (local desde día uno) |
| Python host | pyenv + Python 3.11; virtualenv `.venv` por proyecto |
| Contenerización | Docker Desktop; imagen oficial `quantconnect/lean` para engine y tests |
| Ejecución | `lean backtest` / `lean live` vía CLI |
| Datos Fase 1 | Alpaca free (IEX, 15 min delay, 100 calls/min) |
| Datos backtest | Flexible: `lean data download` (Alpaca u otro provider soportado) |
| Notificación | `NotificationManager` (QC cloud) / archivo + sink local |

**Principio rector:** el código solo habla con la API de `QCAlgorithm`. La fuente de datos, el broker y el entorno son configuración externa (`lean.json` / parámetros), nunca lógica.

---

## 3. Arquitectura por capas

```
┌─────────────────────────────────────────────────────────┐
│ L6 · EJECUCIÓN                                          │
│   lean backtest | lean live (Docker quantconnect/lean)  │
│   Fase 1: local · Fase 2: VPS · portable a QC cloud     │
├─────────────────────────────────────────────────────────┤
│ L5 · ORQUESTACIÓN (main.py — QCAlgorithm)               │
│   initialize → carga config → carga universos →         │
│   crea SymbolData + warmup → registra ScheduledEvents   │
│   Un solo nodo, todas las estrategias por schedule      │
├─────────────────────────────────────────────────────────┤
│ L4 · ESTRATEGIAS (ScanPipeline)                         │
│   universo asignado + lista de Rules + schedule         │
│   V1: swing_eod (fin de día) · market_close (15:30 ET)  │
├─────────────────────────────────────────────────────────┤
│ L3 · FEATURES / PRIMITIVAS (LEAN-nativas, reutilizables)│
│   Cómputos reutilizables sobre SymbolData               │
│   Features: posición vs SMA(n) por timeframe,           │
│   extensión vs SMA(8), pullback, % cambio, barra        │
│   parcial del día (working bar)                         │
├─────────────────────────────────────────────────────────┤
│ L2 · DATOS DERIVADOS (SymbolData)                       │
│   SymbolData: consolidators D/W/M + indicadores         │
│   TradeBarConsolidator diario · Calendar.WEEKLY ·       │
│   Calendar.MONTHLY · working_bar                        │
│   Warmup derivado de timeframes declarados (PLAN §4)    │
├─────────────────────────────────────────────────────────┤
│ L1 · DATOS Y CONFIG EXTERNA                             │
│   lean.json (provider: Alpaca | QC cloud | otro)        │
│   CSV de universo(s) vía ObjectStore (portable)         │
│   Parámetros de estrategia (umbrales, horarios)         │
└─────────────────────────────────────────────────────────┘
```

**Reglas entre capas:**
- L3 y L4 nunca consultan la fuente de datos directamente: consumen el estado de `SymbolData`, que el engine mantiene actualizado.
- L4 no calcula indicadores: solo evalúa predicados (Rules) sobre features ya computadas. El scan es lectura, no cómputo.
- L5 es el único lugar con `self.schedule`, `self.history`, `self.add_equity`, `self.notify`.

---

## 4. Entidades core

| Entidad | Responsabilidad | Notas de implementación |
|---|---|---|
| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro declarativo sobre columnas normalizadas (ej. `"avg_vol_5d > 1e6 and price > 5"`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore. Footer strip (`^[A-Z]{1,5}$`). Alias normalizados (`COLUMN_ALIASES`). Filtro vía `df.query()`. Tope duro 200 post-filtro. Sin imports de `AlgorithmImports` (testeable con mock). Claves: `universes/swing_advances.csv`, `universes/swing_declines.csv`. |
| `SymbolData` | Estado técnico de un símbolo: consolidators D/W/M, indicadores registrados, barra parcial del día. | Patrón idiomático LEAN. SMAs vía `register_indicator` sobre cada consolidator. Warmup en construcción. |
| `Feature` | Cómputo reutilizable y nombrado sobre `SymbolData`. Ej.: `position_vs_sma(n, timeframe)`, `extension_pct(n)`, `is_pullback()`, `day_change_pct()`. | Funciones/propiedades puras de lectura. Compartidas por todas las estrategias. |
| `Rule` | Filtro puro sobre el snapshot de posición precio↔SMA (no recalcula): pasa/no-pasa + evidencia. Ej.: `AboveSMA(20, ["D","W","M"])`, `NotExtended(8, "D")`. Largos/cortos por mirror del set de buckets desde `direction` (sin duplicar reglas). | `evaluate(snapshot)` — sin `sd` ni thresholds. `buckets_allowed` desde config (validado en construcción). `NotExtended` excluye el bucket extremo; el corte es el `bucket_thresholds.extended` único de la estrategia, no un umbral por-regla (ADR-005). |
| `ScanPipeline` | Una estrategia: `UniverseSpec` + lista de `Rules` + `ScheduleSpec`. Ejecuta el scan y produce `ScanResult`. | V1: `swing_eod`, `market_close`. |
| `ScheduleSpec` | Cuándo corre cada pipeline. Ej.: `swing_eod` → tras el cierre; `market_close` → 30 min antes del cierre. | Implementado con `self.schedule.on(date_rules, time_rules)` sobre el calendario del mercado. |
| `ScanResult` | Watchlist: lista de candidatos con evidencia por regla (valores de SMAs, % extensión, % cambio, timestamp `as_of`, flag `partial_bar`). | Serializable a CSV/JSON. |
| `OutputSink` | Persistencia + notificación según entorno (Etapa 8). Unidad = **envelope por estrategia base·scan** (long+short en uno, D8.2). SIEMPRE escribe archivo (CSV+JSON+`latest.json` en `results/<base>/` vía ObjectStore); la notificación es condicional. | Dispatch por **tabla de canales leída de `config/notifications.json`** (`file`/`qc_notify`/`host_email`, D8.4), no por ramas `if env ==`. El correo se parte en **render puro compartido** (`core/email_render.py`) + **transporte por entorno**: cloud → `self.notify.email`; local/VPS → script host `scripts/notify_email.py` (Gmail, fuera del algoritmo). Gate de vida suprime correo en backtest. Suscriptores por estrategia base vía `JsonSubscriberSource` (swappable a DB, D8.5). |

---

## 5. Decisiones técnicas consolidadas

1. **Barras y SMAs de semana y mes se calculan dentro de LEAN** con la mejor configuración del framework: `TradeBarConsolidator(Calendar.WEEKLY)` y `Calendar.MONTHLY`, con los indicadores registrados sobre el consolidator. Nada de resampling manual con pandas.
2. **Warmup explícito y verificable.** Al crear cada `SymbolData`, se pide la historia necesaria (`self.history`) y se empuja a los consolidators. La profundidad se deriva dinámicamente de los timeframes declarados (ver fórmula en PLAN.md §4): `D:n → n+5` barras diarias; `W:n → n×5+10`; `M:n → n×21+21`. Ej.: `M:[20]` → ~441 barras. El número no es fijo.
3. **SMAs estables intradía.** Los indicadores W/M solo se actualizan al cierre de su barra (comportamiento natural del consolidator). En el scan intradía, el precio actual se compara contra medias del último cierre.
4. **Barra parcial del día en el scan intradía.** Suscripción en `Resolution.MINUTE`; el OHLC en curso del día se lee del `working_bar` del consolidator diario (mecanismo LEAN-nativo, agnóstico de la fuente). El `ScanResult` la marca como `partial_bar=True` con su `as_of`.
5. **Un nodo, múltiples estrategias.** Un solo algoritmo registra todos los `ScheduledEvents`. Las estrategias comparten los `SymbolData` de los símbolos que tengan en común (un símbolo = un `SymbolData`, aunque esté en varios universos).
6. **Fuente de datos = configuración.** Cambiar Alpaca ↔ QC cloud ↔ otro provider solo toca `lean.json` (y credenciales). El algoritmo no contiene referencias a la fuente.
7. **Portabilidad local/cloud.** Solo API `QCAlgorithm`, universos y config de estrategias (`config/strategies.json`) vía ObjectStore. `self.get_parameter` solo para escalares sueltos (ej. `env`) — no para la config anidada de estrategias, que no es portable a la UI plana de parámetros de cloud (ver PLAN.md §4). Nota D-E4: los parámetros escalares del algoritmo se definen en `trade-scanner/config.json["parameters"]`, no en `lean.json`. El mismo proyecto debe correr en LEAN CLI local y en QC cloud sin cambios de código.
8. **Solo escaneo en V1.** Cero órdenes. El diseño deja el punto de extensión: un `ScanResult` validado por expertos podrá alimentar un módulo de ejecución futuro sin reestructurar las capas (L4 produce candidatos; un futuro L4.5 los consumiría).

---

## 6. Alcance V1

1. Cargar universo principal desde **archivo CSV**, aplicar un **filtro simple** sobre sus columnas y extraer los tickers (máx ~200). Soporte para variantes de universo por estrategia.
2. Conexión a datos **live o backtest** con **Alpaca o QuantConnect cloud**, configurable **solo modificando `lean.json`**.
3. **Programación por horas del día**: ej. *Swing* al final del día; *Cierre de mercado* 30 min antes del cierre. Todas las estrategias en un mismo nodo vía schedule.
4. **Features reutilizables** entre estrategias (ej. detección de posición respecto a SMA), implementadas con indicadores y consolidators de LEAN.
5. **Filtro técnico en tres marcos de tiempo** (día, semana, mes) sobre el universo.
6. **Archivo de salida + notificación según el ambiente**: `NotificationManager` en QC cloud; archivo/log en local.

### Estrategia de referencia V1 (refinada)

**`swing_eod`** — corre tras el cierre:
1. Universo: CSV swing (≤200), filtro simple de liquidez/precio del propio CSV.
2. Ranking interno: top N por `day_change_pct` (gainers; losers vía la variante `*_short` con `direction: short`).
3. Snapshot único: posición precio↔SMA(8/20) en D/W/M, calculada **una vez** por símbolo·scan y clasificada en 7 buckets con los `bucket_thresholds` de la estrategia.
4. Regla: precio sobre SMA20 en D, W y M (`AboveSMA(20, [D,W,M])` — filtro de buckets `above_*`; para shorts, mirror a `below_*`).
5. Regla: NO extendida (`NotExtended(8, D)` — excluye el bucket `extended_above`, cuyo corte es `bucket_thresholds.extended`, default 10% **a calibrar**; sin umbral por-regla).
6. Salida: watchlist con evidencia (proyección del snapshot).

**`market_close`** — corre 15:30 ET (mismas reglas que swing_eod):
- Usa la barra parcial del día (working bar) como precio/OHLC actual.
- SMAs del último cierre (decisión 3). Resultado marcado provisional.

---

## 7. Fases

**FASE 1 — Desarrollo local ($0/mes)**
- LEAN CLI + VSCode en máquina local, Docker.
- Datos: Alpaca free (100 calls/min, IEX, 15 min delay).
- Backtest + paper trading local (paper solo valida el flujo de datos live; no ejecuta órdenes).

**FASE 2 — Validación en servidor (~$25/mes)**
- LEAN self-hosted en VPS cloud, mismo proyecto sin cambios de código.
- Datos: Alpaca free (igual que Fase 1).
- Paper trading live en servidor; salida y notificación operando de forma desatendida.

---

## 8. Fuera de alcance (V1)

- **Definición/descubrimiento del universo inicial**: solo se filtra un CSV provisto. La fuente del CSV de "best market movers" está **A DEFINIR** (ver §11).
- **Ejecución de órdenes**: ninguna orden, ni paper. Se habilitará tras validación con expertos.
- Datos fundamentales, earnings calendar, scoring/ranking avanzado, persistencia histórica de scans (candidatos a V2).

---

## 9. Restricciones

- Desarrollo local de algoritmos con **LEAN CLI** exclusivamente.
- El código **solo habla con la API de `QCAlgorithm`** (sin SDKs de brokers/datos embebidos).
- **Portable** a QuantConnect cloud o local sin cambios.
- **Todas las estrategias corren en un mismo nodo** con schedule.
- **Flexibilidad en fuentes de datos**: la fuente es configuración externa (`lean.json`).
- Universo fijo en primeras versiones, con `refresh_universe()` como punto de extensión.

---

## 10. DONE WHEN (criterios de aceptación)

El V1 está terminado cuando, en un mismo proyecto LEAN:

1. **Carga y warmup precisos.** `lean backtest` carga el universo desde CSV (≤200 símbolos), construye los `SymbolData` y completa el warmup; las SMA20 D/W/M de una muestra de símbolos **cuadran contra valores de referencia** (test de validación contra plataforma de charting acordada).
2. **Filtrado correcto.** Las reglas de `swing_eod` producen una watchlist reproducible en backtest sobre fechas conocidas, con evidencia por candidato.
3. **Schedule operativo.** `swing_eod` y `market_close` disparan a sus horas configuradas (verificado en backtest por timestamps y en `lean live` paper local).
4. **Barra parcial funcional.** El scan de `market_close` reporta OHLC del día en curso vía working bar, marcado `partial_bar=True`.
5. **Fuente intercambiable.** Cambiar entre datos Alpaca y QC cloud requiere tocar únicamente `lean.json`/credenciales.
6. **Salida por entorno.** En local se genera archivo CSV/JSON; en QC cloud se dispara `NotificationManager`. Sin ramas de negocio por entorno.

---

## 11. Pendientes y riesgos

**Pendientes de definición (bloquean calibración, no el desarrollo):**
- Fuente del CSV de universo "best market movers" (≤200).
- Calibración de `bucket_thresholds` (`near/mild/extended`); el corte "extendida" es `extended` (% sobre la SMA), un solo set por estrategia (ADR-005). Alternativa con ATR a futuro.
- Definición operativa de *pullback* (feature prevista, sin regla en V1 hasta definirla).
- Reglas específicas para *top losers*.
- Plataforma de referencia para validar SMAs W/M (convención de semana de `Calendar.WEEKLY`: lunes→domingo, cierre efectivo viernes).

**Riesgos conocidos:**
- **Alpaca free = IEX**: volumen muy subestimado (usar volumen relativo, no absoluto, en filtros) y 15 min de delay (el scan de 15:30 ve ~15:15; documentado en `as_of`).
- **Rate limit 100 calls/min**: warmup de 200 símbolos debe ir en batch/escalonado; el scan en sí no consume API (lee estado).
- **Memoria/CPU con 200 símbolos en `Resolution.MINUTE`**: viable en un nodo, pero medir en Fase 1 antes del VPS.
- **Equivalencia de barras W/M** con la plataforma del trader: validar antes de confiar en los filtros (criterio DONE #1).

 succeeded in 0ms:
# Etapa 4 — UniverseSpec

**Estado:** pendiente
**Depende de:** Etapa 3 (contratos ratificados, CSVs sembrados en ObjectStore)
**Estimado:** 3–5 horas

---

## Objetivo

Al cerrar la etapa existe `core/universe.py` con la clase `UniverseSpec` que lee un CSV desde ObjectStore, aplica footer strip, normaliza alias de columnas, evalúa el filtro declarativo y devuelve la lista de tickers con tope duro de 200. `main.py` integra la carga y loguea el universo por estrategia. Los tests unitarios (dentro de Docker) cubren filtro, tope y CSV malformado.

A partir de aquí, Etapa 5 puede crear `SymbolData` sabiendo exactamente qué tickers mantendrá.

---

## Decisión de diseño: P3 — `UniverseSpec` no conoce `direction`

> **Contexto:** el campo `direction` existe en cada estrategia (`"long"` / `"short"`) y en `ScanResult`. La pregunta era si `UniverseSpec` necesita conocerlo.

**Decisión: no. `UniverseSpec` es agnóstico a la dirección.**

Razonamiento:

| Lo que `UniverseSpec` hace | Lo que NO le corresponde |
|---|---|
| Leer CSV por clave ObjectStore | Saber para qué estrategia se usa |
| Strip footer, rename alias, aplicar filtro | Propagar `direction` al resultado |
| Devolver `list[str]` de tickers | Construir `ScanResult` |

La "señal de dirección" en los datos **ya está codificada en la clave del universo**: `swing_advances` = longs, `swing_declines` = shorts. `UniverseSpec` no repite esa información.

El campo `direction` vive en la config de la estrategia (`strategy_config["direction"]`). El pipeline (Etapa 7) lo lee de ahí y lo estampa en cada `ScanResult`. `UniverseSpec` nunca lo necesita.

```
strategies.json
 └── swing_eod
       ├── universe: "swing_advances"   → UniverseSpec("universes/swing_advances.csv", ...)
       ├── direction: "long"            → propaga el Pipeline al ScanResult (Etapa 7)
       └── universe_filter: "..."

Un UniverseSpec instanciado con "swing_declines" funciona igual de bien para una
estrategia short — la clase no sabe, ni necesita saber, para quién trabaja.
```

**Consecuencia práctica:** `swing_eod` y `market_close` comparten la misma clave `swing_advances`. En V1, cada uno llama `load()` por separado (el CSV es pequeño; la optimización de caché va en Etapa 7 si se decide necesaria).

---

## Tareas

### T1 — `core/universe.py`: clase `UniverseSpec`

Nuevo archivo. La clase recibe los parámetros de la estrategia en el constructor y ejecuta la carga contra el ObjectStore cuando `main.py` llama `load()`.

**Interfaz:**
```python
class UniverseSpec:
    def __init__(
        self,
        universe_key: str,      # "universes/swing_advances.csv"
        filter_expr: str,       # "avg_vol_5d > 1e6 and price > 5"
        max_tickers: int = 200,
    ): ...

    def load(self, object_store) -> list[str]:
        """Lee, parsea, filtra y devuelve lista de tickers (≤ max_tickers).
        object_store: cualquier objeto con .read(key: str) -> str
        """
```

**Pipeline interno de `load()`:**

1. `raw_csv = object_store.read(self.universe_key)` — devuelve string.
2. Parsear con `csv.DictReader` o `pandas.read_csv(io.StringIO(raw_csv))`.
3. **Footer strip:** descartar filas donde `Symbol` no matchee `^[A-Z]{1,5}$` (cubre el footer de Barchart y cualquier ticker inválido).
4. **Alias rename:** renombrar columnas según el mapa del contrato §5 PLAN.md (ej. `"Symbol" → "ticker"`, `"5D Avg Vol" → "avg_vol_5d"`, `"Latest" → "price"`, `"5D %Chg" → "pct_chg_5d"`, `"%Change" → "pct_chg_1d"`).
5. **Parsing de tipos:** strip `+`/`%` en columnas de porcentaje y dividir por 100; convertir numéricas a `float`.
6. **Filtro declarativo:** `df.query(self.filter_expr)` sobre los alias normalizados.
7. **Ordenar:** `df.sort_values("ticker")` — orden alfabético garantiza reproducibilidad entre runs con el mismo CSV.
8. **Tope duro:** si `len(result) > self.max_tickers`, truncar a `max_tickers` y loguear warning (con `print` o logger; sin dependencia de LEAN aquí).
9. Devolver `list(df["ticker"].values)`.

**Criterio de aceptación:**
- Con un CSV real (de `storage/universes/`) y `max_tickers=200`: devuelve ≤200 tickers, todos strings `^[A-Z]{1,5}$`.
- Con `filter_expr="avg_vol_5d > 1e6 and price > 5"`: devuelve los mismos conteos verificados en Etapa 3 (~74 advances, ~68 declines).
- El footer no aparece en la salida.
- `load()` es reproducible: misma entrada → mismo resultado.

**Notas técnicas:**
- `object_store` puede ser `self.object_store` de LEAN o cualquier mock con `.read(key)`. No importar nada de `AlgorithmImports` en `universe.py` — solo stdlib + pandas. Esto mantiene el módulo testeable sin LEAN y abre la puerta a scripts de exploración futuros.
- El alias map puede ser un diccionario de módulo (constante), no un parámetro externo. No necesita venir de `strategies.json`.
- Columnas extra en el CSV futuro se ignoran silenciosamente (el contrato §5 lo especifica).
- `refresh_universe()` **no-op documentado:** la instancia carga el universo en `initialize()` y no se refresca en runtime V1. Si en el futuro se necesita refresh diario, se sobreescribe este método; el pipeline lo llama antes del scan.

---

### T2 — `main.py`: integrar `UniverseSpec` y loguear universo por estrategia

Ampliar el `initialize()` del skeleton de Etapa 2 para instanciar y cargar cada universo antes de registrar los `ScheduledEvents`.

**Cambios en `main.py`:**

```python
# Leer ambiente y parámetros del bloque environments
env = self.get_parameter("env", "prod")
env_cfg = strategies_config["environments"][env]
top_n = env_cfg["top_n"]
max_universe = env_cfg["max_universe"]

# Por cada estrategia, cargar su universo
for name, cfg in strategies_config["strategies"].items():
    universe_key = f"universes/{cfg['universe']}.csv"
    spec = UniverseSpec(
        universe_key=universe_key,
        filter_expr=cfg["universe_filter"],
        max_tickers=max_universe,
    )
    tickers = spec.load(self.object_store)
    self.log(f"[{name}] universe loaded: {len(tickers)} tickers "
             f"(env={env}, max={max_universe}, key={universe_key})")
```

Los tickers aún no se usan para crear `SymbolData` — eso es Etapa 5. Solo se cargan y loguean.

**Criterio de aceptación:**
- `lean backtest "trade-scanner"` loguea 4 líneas `"[<strategy>] universe loaded: N tickers ..."` durante `initialize()`.
- Los conteos N son coherentes con los del filtro (ej. ~74 para longs, ~68 para shorts con filtro de Etapa 3).
- `env=dev` en `lean.json` → `max_universe=10` → log muestra `10 tickers` para ambos universos.
- El backtest continúa sin errores y los `ScheduledEvents` siguen disparando como en Etapa 3.

---

### T3 — Tests unitarios de `core/universe.py` (dentro de Docker)

Nuevos tests en `trade-scanner/tests/`. Los tests no usan `AlgorithmImports` — usan un mock mínimo de ObjectStore.

**Fixture base:**
```python
class MockObjectStore:
    def __init__(self, csv_content: str):
        self._content = csv_content
    def read(self, key: str) -> str:
        return self._content
```

**Test T3.1 — filtro funciona con alias normalizados:**
- CSV sintético con 5 filas: 3 pasan `avg_vol_5d > 1e6 and price > 5`, 2 no.
- Verificar que `load()` devuelve exactamente los 3 tickers esperados.

**Test T3.2 — tope duro:**
- CSV sintético con 10 filas que pasan el filtro, `max_tickers=5`.
- Verificar que `load()` devuelve exactamente 5 tickers.

**Test T3.3 — footer strip:**
- CSV con 3 filas válidas + 1 fila de footer (ej. `Symbol = "Downloaded from Barchart.com as of..."`).
- Verificar que `load()` devuelve 3 tickers y el footer no aparece.

**Test T3.4 — columna faltante lanza error claro:**
- CSV sin la columna `avg_vol_5d` (nombre original `5D Avg Vol`).
- Verificar que `load()` lanza `KeyError` o `ValueError` con mensaje que identifica la columna ausente (no silencioso).

**Test T3.5 — ObjectStore key no existe:**
- `MockObjectStore.read()` lanza `KeyError` (simula clave no encontrada).
- Verificar que la excepción se propaga sin transformar (no se swallow).

**Criterio de aceptación:**
```bash
bash scripts/run_tests.sh
```
Muestra `5 passed` (o más si ya hay tests de etapas anteriores).

---

## Scope

✅ Entra en esta etapa:
- `core/universe.py` con clase `UniverseSpec` completa (load, footer strip, alias, filtro, tope)
- Integración mínima en `main.py`: leer `env_cfg`, instanciar `UniverseSpec` por estrategia, loguear conteos
- Tests T3.1–T3.5 en `tests/test_universe.py`
- Actualizar `core/__init__.py` para exportar `UniverseSpec`

❌ No entra en esta etapa:
- **`SymbolData` ni `add_equity` por ticker** — Etapa 5. Los tickers se cargan pero no se usan para crear símbolos LEAN.
- **Ranking / top_n filtering** — Etapa 7. `top_n` se lee y loguea, pero no se aplica al cargar el universo; `UniverseSpec` solo aplica el filtro declarativo + tope de seguridad.
- **Refresh del universo en runtime** — `refresh_universe()` se deja como no-op documentado; se implementará si se necesita en Fase 2.
- **Propagación de `direction` en `UniverseSpec`** — ver decisión P3 arriba. `direction` viaja por el pipeline en Etapa 7.
- **Reglas específicas de short** — Etapa 6.
- **Caché de universo compartido entre estrategias** — optimización para Etapa 7 si se mide que es necesario.
- **Descarga automática de CSVs de Barchart** — fuera de scope V1.

---

## Consideraciones técnicas específicas al stack

1. **`df.query()` vs. `eval()`:** usar `df.query(filter_expr)` (pandas). Es más seguro para strings de filtro sin ejecutar código Python arbitrario sobre el namespace global. El `filter_expr` viene de `strategies.json` (fuente controlada, no input de usuario en runtime), así que el riesgo es bajo, pero `query()` es más expresivo y portable.

2. **`universe.py` sin imports de LEAN:** mantener el archivo libre de `AlgorithmImports`. Esto permite correrlo en el host Python (scripts, tests rápidos) y facilita los tests con mocks simples. `main.py` pasa `self.object_store` directamente; `UniverseSpec` solo necesita que tenga `.read(key) -> str`.

3. **El ObjectStore de LEAN devuelve string:** `self.object_store.read(key)` devuelve `str`. Se convierte con `io.StringIO(raw_csv)` antes de pasarlo a `pandas.read_csv()`. No usar rutas de archivo absolutas — el ObjectStore es el único canal portable local↔cloud.

4. **Parsing de porcentajes:** `5D %Chg` y `%Change` son strings como `"+14.32%"` o `"-2.10%"`. Aplicar `str.strip().lstrip('+').rstrip('%')` antes de `float()`. Dividir por 100. Si el CSV algún día llega sin el `%`, la división por 100 produce valores incorrectos — considerar validación de rango (>10 o <-10 post-conversión → warning).

5. **Alias map como constante de módulo:** definir en `universe.py` un `dict` `COLUMN_ALIASES = {"Symbol": "ticker", "5D Avg Vol": "avg_vol_5d", ...}`. Si en el futuro Barchart cambia un nombre de columna, hay un solo lugar para corregirlo. El alias map es el contrato §5 de PLAN.md — no duplicar en `strategies.json`.

6. **`max_tickers` vs. `top_n`:** son conceptos distintos.
   - `max_tickers` = tope duro de seguridad en la carga del universo (≤200). Viene de `env_cfg["max_universe"]`.
   - `top_n` = cuántos candidatos se emiten en el watchlist final, luego del ranking. Viene de `env_cfg["top_n"]`. No se aplica aquí.
   El tope `max_tickers` protege de CSVs inesperadamente grandes; `top_n` controla el output del scan.

7. **4 estrategias → potencialmente 2 cargas únicas:** `swing_eod` y `market_close` usan la misma clave + filtro. En V1 se llama `load()` dos veces — el CSV tiene ~200 filas y la operación es O(n) sobre datos pequeños. Sin caché en esta etapa. Si el perfilado de Etapa 7 muestra que es un cuello de botella (improbable), se añade caché allí.

8. **`env=dev` en `lean.json` → `max_universe=10`:** en backtest de desarrollo, solo se cargan 10 tickers por estrategia. Los primeros 10 del DataFrame post-filtro (sin orden garantizado por pandas, pero determinista en la misma sesión). Esto acelera backtests y reduce el warmup de Etapa 5.

---

## Done when

- [ ] `core/universe.py` existe y exporta `UniverseSpec`
- [ ] `lean backtest "trade-scanner"` loguea `universe loaded: N tickers` para cada una de las 4 estrategias durante `initialize()`, sin errores
- [ ] Con `env=dev` en `lean.json`: log muestra `max=10` y `10 tickers` (o menos si el CSV tiene menos de 10 post-filtro)
- [ ] `bash scripts/run_tests.sh` muestra los 5 tests de `test_universe.py` verdes (filtro, tope, footer strip, columna faltante, key no existe)
- [ ] `UniverseSpec` no importa nada de `AlgorithmImports` (verificado por `grep -n "AlgorithmImports" core/universe.py` → sin resultados)
- [ ] Commit `[Etapa 4] ...`

---

## Preguntas abiertas

- [ ] **¿El filtro `df.query()` es suficiente o necesitamos expresiones más complejas?** El filtro actual (`avg_vol_5d > 1e6 and price > 5`) es sencillo y cabe en pandas `query()`. Si en el futuro se necesitan funciones (ej. `pct_chg_5d.abs() > 0.05`), `query()` lo soporta con `@variable` y funciones de pandas. No es un bloqueante para V1.
- [ ] **¿Loguear los tickers individuales o solo el conteo?** Por ahora solo el conteo (privacidad + verbosidad). Si se necesita auditoría del universo exacto cargado, se puede añadir como log de debug en Etapa 8 (OutputSink).
- [x] **¿Ordenar los tickers antes del tope?** Resuelto: ordenar por `ticker` (alfabético) antes del tope. Garantiza que dos backtests dev con el mismo CSV usen exactamente los mismos 2 tickers.

 succeeded in 0ms:
# PLAN — Screener de Acciones sobre LEAN

Archivo principal de trabajo. Complementa a `SPECS.md` (contexto de producto). Ante conflicto, gana este archivo.

**Qué se construye:** screener multi-estrategia sobre LEAN. Carga universos desde CSV (≤200 tickers), mantiene indicadores en los marcos de tiempo que cada estrategia declare, evalúa reglas en horarios programados y emite watchlist con evidencia. **Solo escanea: cero órdenes en V1.**

---

## 1. Reglas no negociables

1. El código solo habla con la API de `QCAlgorithm`. Sin SDKs de brokers/datos embebidos.
2. Portable local ↔ QuantConnect cloud sin cambios de código: fuente de datos y broker viven en `lean.json`; config de negocio y archivos (universos, `strategies.json`) vía ObjectStore. `self.get_parameter` solo para escalares sueltos si hiciera falta — no para la config anidada de estrategias (ver §4).
3. Un solo algoritmo/nodo ejecuta TODAS las estrategias vía `self.schedule.on(...)`.
4. **Los marcos de tiempo NO son fijos: cada estrategia declara los suyos.** Los consolidators creados y la profundidad del warmup se derivan de esas declaraciones (ver §4).
5. Desarrollo solo con LEAN CLI (`lean backtest` / `lean live`), engine en Docker `quantconnect/lean`.
6. Indicadores y barras W/M/etc. siempre con consolidators e indicadores de LEAN (`Calendar.WEEKLY`, `Calendar.MONTHLY`, `register_indicator`). Prohibido resampling manual con pandas en el algoritmo.
7. Parámetros de estrategias (umbrales, horarios, timeframes, archivo de universo) en `config/strategies.json` (ObjectStore), nunca hardcodeados ni en `config.json` del proyecto (ver §4).

## 2. Capas y restricciones entre capas

```
L6 Ejecución      lean backtest | lean live (Docker quantconnect/lean) — boundary de runtime/deploy
L5 Orquestación   main.py (QCAlgorithm): config → universos → SymbolData+warmup → schedule → OutputSink
L4 Estrategias    ScanPipeline = universo + Rules + ScheduleSpec → ScanResult
L3 Features       cómputos reutilizables sobre SymbolData (posición vs SMA(n,tf), extensión, % día)
L2 Datos derivados SymbolData: consolidators por timeframe + indicadores + working bar + warmup
L1 Config externa lean.json · CSVs en ObjectStore · parámetros
```

- L3/L4 **nunca** consultan datos: leen estado de `SymbolData`. El scan es lectura, no cómputo.
- L4 no calcula indicadores; solo evalúa predicados (Rules) y arma evidencia.
- Solo L5 usa `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify`.
- Un símbolo = un `SymbolData` compartido entre estrategias (unión de sus timeframes requeridos).

## 3. Árbol de directorios

```
trade-scanner/              # lean init aquí (workspace)
├── lean.json                    # provider de datos/broker: ÚNICO lugar que cambia entre fuentes
├── data/                        # data folder LEAN (gestionado por CLI; no versionar contenido pesado)
├── storage/                     # ObjectStore local REAL del CLI (montado en /Storage); copia
│                                #   sembrada y gitignoreada — fuente versionada vive en config/
├── trade-scanner/               # lean project-create "trade-scanner" --language python
│   ├── main.py                  # L5: única clase QCAlgorithm
│   ├── config.json              # archivo de proyecto LEAN (algorithm-language, etc.) — NO config de negocio
│   ├── research.ipynb           # exploración (generado por CLI)
│   ├── core/                    # paquete: incluye __init__.py (portable local↔cloud)
│   │   ├── timeframes.py        # TimeframeSpec: "D"|"W"|"M" → consolidator + barras de warmup necesarias
│   │   ├── symbol_data.py       # SymbolData (L2)
│   │   ├── features.py          # Features (L3)
│   │   ├── rules.py             # Rules componibles con evidencia (L4)
│   │   ├── pipeline.py          # ScanPipeline, ScanResult (L4)
│   │   ├── universe.py          # UniverseSpec: CSV ObjectStore + filtro simple + refresh_universe() no-op
│   │   └── output.py            # OutputSink: CSV/JSON local | NotificationManager cloud (selección por entorno)
│   ├── strategies/              # paquete: incluye __init__.py
│   │   ├── base.py              # StrategyConfig: declara timeframes requeridos, rules, schedule, universo
│   │   ├── swing_eod.py
│   │   └── market_close.py
│   └── tests/                   # pytest con TradeBars sintéticos (correr dentro de imagen LEAN)
├── config/                      # config de negocio versionada (se siembra a ObjectStore)
│   └── strategies.json          # estrategias, timeframes, umbrales, horarios, top_n (ver §4)
├── universes/                   # CSVs fuente versionados (se siembran a ObjectStore con script)
│   └── swing.csv
├── data/equity/usa/             # sample data libre (SPY 2013) p/ que el reloj del backtest avance — ver Etapa 2
├── scripts/
│   ├── explore_universe.py      # perfilado del CSV de entrada (Etapa 3)
│   ├── seed_object_store.sh     # copia config/*.json + universes/*.csv → storage/
│   ├── seed_sample_data.sh      # baja sample data libre del repo público LEAN → data/ (Etapa 2)
│   └── run_tests.sh             # pytest dentro de la imagen quantconnect/lean
└── README.md
```

## 4. Diseño clave: timeframes por estrategia

Cada estrategia declara qué necesita; el orquestador construye lo mínimo. La config de estrategias vive en un **JSON en ObjectStore** (`config/strategies.json`), leído por `main.py` vía `self.object_store` + `json.loads` — **no** en `config.json` del proyecto ni vía `self.get_parameter`:

```json
// config/strategies.json  (sembrado a ObjectStore; versionado en config/ del repo)
{
  "bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 },
  "strategies": {
    "swing_eod":    { "universe": "swing", "direction": "long", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "after_close", "top_n": 50 },
    "market_close": { "universe": "swing", "direction": "long", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "before_close_30m", "top_n": 50 }
  }
}
```

- **Umbrales de posición (Etapa 6/6B):** los cortes `near/mild/extended` viven en `bucket_thresholds` (global + override opcional por estrategia), **un solo set por estrategia** compartido por todas sus rules. El antiguo `max_extension_pct` por estrategia quedó **retirado** (ADR-005): "no extendido" = excluir el bucket extremo, cuyo corte es el `extended` único. Ver [ADR-005](.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).

- **Por qué ObjectStore y no `get_parameter`:** `self.get_parameter` solo devuelve strings planos y no expresa el mapa anidado `timeframes`; la UI de parámetros de QC cloud es plana. ObjectStore es el único mecanismo portable local↔cloud que soporta estructura anidada y mantiene la config fuera del código (mismo canal que los universos CSV). El `config.json` del proyecto queda como archivo de LEAN + parámetros escalares sueltos (`env`, etc.) — **no** config de negocio anidada.
- **D-E4 — `get_parameter` lee de `config.json`, no de `lean.json`:** `self.get_parameter("env")` lee desde `trade-scanner/config.json["parameters"]`. El campo `"parameters"` en `lean.json` (raíz del workspace) es para el engine LEAN y es ignorado por `get_parameter`. Parámetros escalares del algoritmo → `trade-scanner/config.json["parameters"]`. Config de negocio anidada → ObjectStore.
- `timeframes` = mapa timeframe → periodos de SMA requeridos.
- Por símbolo, L5 calcula la **unión** de timeframes/periodos de todas las estrategias que lo incluyen y crea solo esos consolidators/indicadores.
- **Warmup derivado**: barras diarias necesarias = `max` sobre lo declarado. Regla: `D:n → n+5` barras; `W:n → n*5+10`; `M:n → n*21+21`. Ej.: `M:[20]` → ~441 barras diarias. Nada de "504 fijo".
- `working_bar` del consolidator diario expone el OHLC parcial del día en curso para scans intradía (suscripción `Resolution.MINUTE`).
- SMAs estables intradía: los indicadores solo se actualizan al cierre de su barra; el scan intradía compara precio actual (working bar) vs medias del último cierre.

## 5. Contratos de datos (definitivos — ratificados en Etapa 3)

### Contrato de entrada: CSV Barchart

Fuente: Barchart.com, exportado manualmente. Formato de nombre: `5-day-all-us-exchanges-percent-change-{tipo}-{MM-DD-YYYY}.csv`.
Claves ObjectStore: `universes/swing_advances.csv` (advances/longs) y `universes/swing_declines.csv` (declines/shorts).

| Campo original | Alias normalizado | Tipo   | Notas de parsing                            |
|----------------|-------------------|--------|---------------------------------------------|
| `Symbol`       | `ticker`          | string | Validar `^[A-Z]{1,5}$`; footer → descartar  |
| `Name`         | `name`            | string | Informativo; no usado en reglas             |
| `5D %Chg`      | `pct_chg_5d`      | float  | Strip `+`/`%`; dividir / 100               |
| `Latest`       | `price`           | float  | Precio de cierre del último día del período |
| `Change`       | `chg_1d`          | float  | Cambio absoluto 1D                          |
| `%Change`      | `pct_chg_1d`      | float  | Strip `+`/`%`; dividir / 100               |
| `5D Chg`       | `chg_5d`          | float  | Cambio absoluto 5D                          |
| `5D High`      | `high_5d`         | float  | Máximo del período                          |
| `5D Low`       | `low_5d`          | float  | Mínimo del período                          |
| `5D Avg Vol`   | `avg_vol_5d`      | float  | Ya numérico (sin comas)                     |
| `Time`         | `date`            | string | Fecha de exportación (`YYYY-MM-DD`)         |

Reglas de parsing:
- Footer strip: fila con `Symbol` no coincidente con `^[A-Z]{1,5}$` → descartar siempre.
- Columnas extra futuras: ignoradas si no están en el alias map.
- Filtro declarativo usa **alias normalizados**: `"avg_vol_5d > 1e6 and price > 5"`.
- Normalización (rename de columnas) ocurre en `UniverseSpec` (Etapa 4); el CSV en ObjectStore se guarda tal cual (con footer incluido).
- Tope duro: 200 tickers post-filtro.

### Contrato de salida: `ScanResult`

Una fila/objeto por candidato; serializa a CSV y JSON.

| Campo                   | Tipo CSV        | Tipo JSON        | Descripción                                                      |
|-------------------------|-----------------|------------------|------------------------------------------------------------------|
| `strategy`              | string          | string           | Nombre de la estrategia (ej. `swing_eod`)                       |
| `as_of`                 | ISO 8601 UTC    | ISO 8601 UTC     | Timestamp del scan                                               |
| `ticker`                | string          | string           | Símbolo (de `Symbol` del CSV)                                   |
| `direction`             | `long`/`short`  | string           | Dirección de la estrategia                                       |
| `partial_bar`           | `True`/`False`  | bool             | `True` si el precio viene del working bar (intraday)            |
| `price`                 | float           | float            | Precio usado: close o working_bar.close                         |
| `time_frames_evaluated` | `D,W,M`         | `["D","W","M"]`  | Timeframes evaluados por esta estrategia                        |
| `sma_evidence`          | JSON string     | object           | `{tf: {period: {value, distance_pct, bucket}}}` — proyección del snapshot único (Etapa 6/6B); ver ejemplo |
| `passed_rules`          | pipe-separated  | array of string  | Reglas que pasaron (ej. `AboveSMA20\|NotExtended`)               |
| `rules_passed_count`    | int             | int              | Conteo de reglas que pasaron; usado como score de ranking        |

Ejemplo `sma_evidence` — proyección del snapshot único (Etapa 6B), no un recompute; `distance_pct` y `bucket` se añadieron en Etapa 6 y `distance_pct` es fracción, no porcentaje:
```json
{
  "D": {"20": {"value": 150.20, "distance_pct": 0.0231, "bucket": "above_mild"}},
  "W": {"20": {"value": 148.50, "distance_pct": 0.0352, "bucket": "above_strong"}},
  "M": {"20": {"value": 145.00, "distance_pct": 0.0586, "bucket": "above_strong"}}
}
```

## 6. Estrategia de referencia

**`swing_eod`** (tras el cierre): universo `swing` filtrado → top N por `day_change_pct` → regla `AboveSMA(20, D∧W∧M)` → regla `NotExtended(8, D)` → ScanResult.
**`market_close`** (15:30 ET): mismas reglas; precio/OHLC desde working bar; resultado marcado `partial_bar=True`.
Variante shorts (`*_short`): universo `swing_declines`, `direction: short` → las mismas reglas con `side="below"` por mirror (ADR-005): `AboveSMA` filtra `below_*`, `NotExtended` excluye `extended_below`. Sin reglas nuevas.

> **Reglas (Etapa 6/6B):** una sola evaluación de posición precio↔SMA por símbolo·scan (snapshot único); las rules son filtros puros sobre buckets ya asignados. `NotExtended` no lleva umbral propio: excluye el bucket extremo, cuyo corte es el `bucket_thresholds.extended` único de la estrategia. Largos/cortos: mirror del set de buckets desde `direction`. Ver [ADR-005](.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).

---

## 7. FASE 1 — Etapas (spec-driven; no avanzar a una etapa sin cerrar el Done when de la anterior)

## Etapa 0 — Entorno de desarrollo
**Estado:** pendiente
**Objetivo:** máquina lista para correr LEAN CLI (válido para cualquier PC)
**Depende de:** nada
**Alcance:**
- Instalar Docker Desktop; verificar con `docker run hello-world`.
- Instalar pyenv; instalar Python 3.11 (`pyenv install 3.11.9`); fijar versión local en el repo (`pyenv local 3.11.9` → genera `.python-version`).
- Crear virtualenv del proyecto (`python -m venv .venv`); añadir `.venv/` a `.gitignore`.
- Instalar LEAN CLI dentro del venv: `pip install lean`; verificar `lean --version`.
**Done when:**
- [ ] `docker run hello-world` pasa sin errores
- [ ] `python --version` dentro del venv muestra `3.11.x`
- [ ] `lean --version` pasa sin errores
- [ ] `.venv/` en `.gitignore`; `.python-version` en el repo

## Etapa 1 — Workspace LEAN, cuentas y credenciales
**Estado:** completada
**Objetivo:** entorno local LEAN corriendo en Docker con credenciales listas
**Depende de:** Etapa 0
**Alcance:**
- Alpaca paper (API key/secret) en `.env` (gitignoreado); `lean login` QC no requerido para Fase 1.
- `lean.json` generado desde template público de LEAN (sin `lean init` — requiere QC pago); `organization-id` placeholder para satisfacer check del CLI.
- Smoke test: `lean project-create "trade-scanner" --language python` y `lean backtest "trade-scanner"`.
**Done when:**
- [x] `lean backtest "trade-scanner"` corre en Docker sin errores con el algoritmo de ejemplo
- [x] Credenciales Alpaca en `.env` (gitignoreado); `lean.json` sin valores reales
- [x] `lean.json`, `.gitignore` y proyecto commiteados con `[Etapa 1] ...`

## Etapa 2 — Esqueleto del proyecto (walking skeleton)
**Estado:** completada
**Objetivo:** plumbing end-to-end validado temprano: paquetes importables, carga de config desde ObjectStore, un ScheduledEvent por estrategia disparando a su hora real, y pytest verde dentro de la imagen LEAN. Sin lógica de negocio (eso son Etapas 4+).
**Depende de:** Etapa 1

> **Hallazgo que define el alcance (verificado en log de Etapa 1):** un backtest **sin datos no avanza el reloj** — el motor procesa "1 data point" y dispara `On End Of Algorithm` de inmediato; los `ScheduledEvents` nunca corren. Doc QC: *"in backtests, the algorithm clock only advances when new data arrives."* Por eso esta etapa siembra sample data libre y ancla las time-rules a un símbolo de referencia. Además, la config de negocio NO va en `config.json`/`get_parameter` (no portable a cloud para estructura anidada) sino en JSON en ObjectStore (ver §4).

**Alcance:**
- **Estructura mínima (no stubs muertos):** crear `core/`, `strategies/`, `tests/` como paquetes con `__init__.py`, y solo los archivos que esta etapa ejercita. Cada etapa posterior añade su módulo. `config/`, `universes/`, `scripts/` en la raíz del workspace (fuera del proyecto pusheable).
- **`scripts/seed_sample_data.sh`:** baja la sample data libre de SPY (~2013, `Resolution.MINUTE`) del repo público de LEAN a `data/equity/usa/` (sin auth QC — ver ADR-002). Hace avanzar el reloj del backtest.
- **`config/strategies.json` + seed a ObjectStore:** estructura mínima de §4 (dos estrategias con `schedule` y `universe`; resto de campos pueden ir vacíos/placeholder en esta etapa). `scripts/seed_object_store.sh` lo copia a `storage/config/` (el ObjectStore real del CLI; **no** `data/object-store/`). Key de lectura: `config/strategies.json`.
- **`main.py` esqueleto (L5):** `add_equity("SPY", Resolution.MINUTE)` como ancla de calendario; lee `config/strategies.json` vía `self.object_store` + `json.loads`; mapea los strings de schedule (`after_close` → `time_rules.after_market_close(SPY, …)`, `before_close_30m` → `time_rules.before_market_close(SPY, 30)`, `date_rules.every_day(SPY)`); registra un `ScheduledEvent` por estrategia que solo loguea `"scan <nombre> @ <hora>"`.
- **`scripts/run_tests.sh`:** pytest dentro de `quantconnect/lean` (montando el proyecto). El test no es trivial: **importa `AlgorithmImports` y construye un objeto LEAN** (p. ej. un `TradeBar`) — así de-riesga que el puente pythonnet funciona en Docker, que es el verdadero unknown.

**Done when:**
- [x] `lean backtest` recorre la ventana con sample data y loguea cada `scan <estrategia> @ <hora>` a la hora correcta según el calendario del mercado (after_close, before_close_30m) — verificado por timestamps en el log, no asumido
- [x] `main.py` carga `strategies.json` desde ObjectStore (no desde `config.json` ni `get_parameter`); cero config de negocio hardcodeada
- [x] `scripts/run_tests.sh` corre pytest dentro de la imagen LEAN con un test verde que importa `AlgorithmImports` y construye un objeto LEAN
- [x] `core/`, `strategies/`, `tests/` son paquetes importables (`__init__.py`); el árbol coincide con §3 para los archivos creados en esta etapa
- [x] Commit `[Etapa 2] ...`; sample data (`data/equity/`) gitignoreada

> **Cierre (commit `[Etapa 2]`):** `market_close` dispara 15:30 y `swing_eod` 16:01 (verificado en log); config leída de `storage/config/strategies.json`; `run_tests.sh` verde (`1 passed`). Hallazgos y decisiones reversibles en [.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md).

## Etapa 3 — Exploración y contrato del archivo de entrada
**Estado:** completada
**Objetivo:** CSV de universo real perfilado, contratos fijados y CSV sembrado en ObjectStore
**Depende de:** Etapa 2
**Alcance:**
- `scripts/explore_universe.py` sobre el CSV real: columnas, tipos, nulos, duplicados, tickers inválidos/no-US, rangos de price y volumen, conteo post-filtro.
- Confirmar o ajustar los contratos de datos borrador con base en lo observado; actualizar este archivo.
- `config/strategies.json`: sección `environments`, 4 estrategias con `direction`, `main_timeframe`, `timeframes`, `universe_filter`, `max_extension_pct` *(esta última retirada luego en 6B/T5 — ADR-005, redundante con `bucket_thresholds.extended`)*.
- `lean.json`: agregar `"parameters": {"env": "dev"}`.
- `scripts/seed_object_store.sh`: soporte para CSVs datados + archivo a `processed/`.

**Contratos de datos:** ver §5 (ratificados en esta etapa — el borrador quedó reemplazado por las tablas definitivas).

**Done when:**
- [x] `python scripts/explore_universe.py <path>` produce reporte completo para ambos CSVs sin errores
- [x] Reporte revisado y aprobado (hallazgos sin sorpresas que rompan el contrato)
- [x] PLAN.md §5 actualizado: contrato de entrada definitivo (alias map, parsing, footer, dos claves)
- [x] PLAN.md §5 actualizado: contrato de salida `ScanResult` definitivo (campos, tipos, ejemplo)
- [x] `config/strategies.json` tiene `environments` + 4 estrategias con `direction` y `universe_filter` correcto
- [x] `lean.json` tiene `"parameters": {"env": "dev"}`
- [x] `bash scripts/seed_object_store.sh` siembra `strategies.json` + `swing_advances.csv` + `swing_declines.csv`; mueve fuentes a `processed/`
- [x] `storage/universes/swing_advances.csv` y `swing_declines.csv` existen con ~200 filas; archivos movidos a `data/object-store/processed/`
- [x] `lean backtest "trade-scanner"` corre sin errores; las 4 estrategias loguearon a sus horas (15:30 y 16:01)

> **Cierre (commit `[Etapa 3]`):** perfilado confirma contrato sin sorpresas (200 datos + 1 footer, 11 columnas, mediana vol ~995K); filtro combinado `avg_vol_5d > 1M AND price > 5` deja 74 advances / 68 declines. Contratos definitivos en §5. 4 estrategias en `strategies.json` (2 long + 2 short placeholder) + `environments` dev/prod. `seed_object_store.sh` actualizado con glob datado y archivo a `processed/`. Backtest confirma las 4 estrategias disparando. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md).

## Etapa 4 — UniverseSpec
**Estado:** completada
**Objetivo:** carga de universos por estrategia desde ObjectStore con filtro declarativo
**Depende de:** Etapa 3
**Alcance:**
- `core/universe.py`: lee CSV desde `self.object_store`, aplica `universe_filter` declarativo, valida tope 200, expone símbolos por estrategia (variantes por clave de universo), `refresh_universe()` no-op documentado.
- Tests: filtro, tope, CSV malformado.
**Done when:**
- [x] Backtest loguea el universo cargado por estrategia con su conteo (≤200)
- [x] Tests de filtro, tope y CSV malformado verdes

> **Cierre (commit `[Etapa 4]`):** `core/universe.py` implementado con `COLUMN_ALIASES`, footer strip (`^[A-Z]{1,5}$`), filtro declarativo vía `df.query()`, orden alfabético y tope duro. Sin imports de `AlgorithmImports`. `main.py` integrado: 4 líneas `universe loaded: N tickers (env=..., max=..., key=...)` en `initialize()`; conteos 74 advances / 68 declines en prod, 2 en dev. 6 tests verdes en Docker (`bash scripts/run_tests.sh`). **Hallazgo D-E4:** `self.get_parameter()` lee parámetros escalares desde `trade-scanner/config.json["parameters"]`, NO desde `lean.json["parameters"]` (el campo en `lean.json` es configuración del engine, no del algoritmo). El parámetro `env` vive en `trade-scanner/config.json`. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes-md](.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes-md).

## Etapa 5A — TimeframeSpec + SymbolData (lógica y tests sintéticos)
**Estado:** completada
**Objetivo:** consolidators e indicadores construidos dinámicamente según los timeframes declarados, con fórmula de warmup generalizada (registro extensible, no D/W/M hardcodeado) y plan de warmup con presupuesto — verificable 100% por tests en Docker
**Depende de:** Etapa 4
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-05a.md](.claude/fase-1-desarrollo-local/etapa-05a.md)

codex
Ya tengo el alcance exacto: Etapa 4 se limita a `UniverseSpec`, su integración mínima en `main.py`, exportación, y tests de universo. Ahora voy a leer las decisiones congeladas y los archivos concretos para validar que la etapa no se desvió hacia etapas posteriores.
  ✓ Leer alcance Etapa 4 y documentos de diseño aplicables
  → Mapear archivos y dependencias tocadas por Etapa 4
  • Auditar implementación, API LEAN y corrección funcional
  • Auditar tests y trazabilidad objetivo-código-test
  • Redactar hallazgos y resumen ejecutivo
exec
/bin/zsh -lc 'find docs -type f | sort' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
docs/DEVLOG.md
docs/ROADMAP.md
docs/conceptos/buckets-y-simetria-largo-corto.md
docs/conceptos/factory-vs-composicion.md

exec
/bin/zsh -lc 'find .claude -type f | sort' in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'nl -ba trade-scanner/core/universe.py' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
.claude/decisions/ADR-001-python-version.md
.claude/decisions/ADR-002-qc-module-auth-constraint.md
.claude/decisions/ADR-003-stooq-como-fuente-de-datos.md
.claude/decisions/ADR-004-cadencia-evaluacion-intradia.md
.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md
.claude/fase-1-desarrollo-local/etapa-00.md
.claude/fase-1-desarrollo-local/etapa-01.md
.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-02.md
.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-03.md
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-04.md
.claude/fase-1-desarrollo-local/etapa-05.md
.claude/fase-1-desarrollo-local/etapa-05a-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05a.md
.claude/fase-1-desarrollo-local/etapa-05b-checkpoint.md
.claude/fase-1-desarrollo-local/etapa-05b-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05b-t5-2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05b-t5-3-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05b-t5-checkpoint.md
.claude/fase-1-desarrollo-local/etapa-05b-t6-1-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05b-t6-2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-05b.md
.claude/fase-1-desarrollo-local/etapa-06-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06.md
.claude/fase-1-desarrollo-local/etapa-06b-t1-1-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t1-2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t3-1-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t3-2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t4-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t5-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t6-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b-t7-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-06b.md
.claude/fase-1-desarrollo-local/etapa-07-t1-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07-t2-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07-t3-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07-t4-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07-t5-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-07.md
.claude/fase-1-desarrollo-local/etapa-08-decisiones-y-pendientes.md
.claude/fase-1-desarrollo-local/etapa-08.md
.claude/fase-1-desarrollo-local/etapa-09.md
.claude/settings.local.json

 succeeded in 0ms:
     1	"""UniverseSpec: lee un CSV desde ObjectStore y devuelve la lista filtrada de tickers.
     2	
     3	Sin imports de AlgorithmImports — testeable con cualquier mock que tenga .read(key) -> str.
     4	"""
     5	import io
     6	import re
     7	
     8	import pandas as pd
     9	
    10	COLUMN_ALIASES: dict[str, str] = {
    11	    "Symbol": "ticker",
    12	    "5D Avg Vol": "avg_vol_5d",
    13	    "Latest": "price",
    14	    "5D %Chg": "pct_chg_5d",
    15	    "%Change": "pct_chg_1d",
    16	}
    17	
    18	_TICKER_RE = r"^[A-Z]{1,5}$"
    19	_PCT_COLUMNS = {"pct_chg_5d", "pct_chg_1d"}
    20	_REQUIRED_COLUMNS = {"avg_vol_5d", "price"}
    21	
    22	
    23	def _parse_pct(val: str) -> float:
    24	    return float(str(val).strip().lstrip("+").rstrip("%")) / 100.0
    25	
    26	
    27	class UniverseSpec:
    28	    def __init__(
    29	        self,
    30	        universe_key: str,
    31	        filter_expr: str,
    32	        max_tickers: int = 200,
    33	    ) -> None:
    34	        self.universe_key = universe_key
    35	        self.filter_expr = filter_expr
    36	        self.max_tickers = max_tickers
    37	
    38	    def load(self, object_store) -> list[str]:
    39	        """Lee, parsea, filtra y devuelve lista de tickers (≤ max_tickers).
    40	
    41	        object_store: cualquier objeto con .read(key: str) -> str
    42	        """
    43	        raw_csv = object_store.read(self.universe_key)
    44	        df = pd.read_csv(io.StringIO(raw_csv))
    45	
    46	        # Footer strip: descartar filas cuyo Symbol no sea un ticker válido
    47	        df = df[df["Symbol"].astype(str).str.match(_TICKER_RE)].copy()
    48	
    49	        # Alias rename: Symbol→ticker, 5D Avg Vol→avg_vol_5d, etc.
    50	        df = df.rename(columns=COLUMN_ALIASES)
    51	
    52	        # Verificar columnas requeridas por el filtro declarativo
    53	        for col in _REQUIRED_COLUMNS:
    54	            if col not in df.columns:
    55	                raise KeyError(
    56	                    f"Required column missing after rename: '{col}' "
    57	                    f"(check COLUMN_ALIASES and source CSV headers)"
    58	                )
    59	
    60	        # Parsear porcentajes: "+14.32%" → 0.1432
    61	        for col in _PCT_COLUMNS:
    62	            if col in df.columns:
    63	                df[col] = df[col].apply(_parse_pct)
    64	
    65	        # Convertir numéricas
    66	        df["avg_vol_5d"] = pd.to_numeric(df["avg_vol_5d"], errors="raise")
    67	        df["price"] = pd.to_numeric(df["price"], errors="raise")
    68	
    69	        # Filtro declarativo sobre alias normalizados
    70	        df = df.query(self.filter_expr)
    71	
    72	        # Orden alfabético: garantiza reproducibilidad entre runs con el mismo CSV
    73	        df = df.sort_values("ticker")
    74	
    75	        # Tope duro de seguridad
    76	        if len(df) > self.max_tickers:
    77	            print(
    78	                f"[UniverseSpec] WARNING: truncating {self.universe_key} "
    79	                f"from {len(df)} to {self.max_tickers} tickers"
    80	            )
    81	            df = df.iloc[: self.max_tickers]
    82	
    83	        return list(df["ticker"].values)
    84	
    85	    def refresh_universe(self) -> None:
    86	        """No-op en V1. Sobrescribir en Fase 2 para refresh intradiario."""

exec
/bin/zsh -lc 'nl -ba trade-scanner/core/__init__.py' in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'nl -ba trade-scanner/tests/test_universe.py' in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'nl -ba trade-scanner/main.py' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	"""Núcleo del screener: features, rules, SymbolData, pipeline y output (L2–L4)."""
     2	
     3	from core.symbol_data import SymbolData
     4	from core.timeframes import TIMEFRAMES, PlannedSeries, TimeframeSpec, WarmupPlan, plan_warmup
     5	from core.universe import UniverseSpec
     6	
     7	__all__ = [
     8	    "TIMEFRAMES",
     9	    "PlannedSeries",
    10	    "SymbolData",
    11	    "TimeframeSpec",
    12	    "UniverseSpec",
    13	    "WarmupPlan",
    14	    "plan_warmup",
    15	]

 succeeded in 0ms:
     1	"""Tests unitarios de UniverseSpec.
     2	
     3	No usan AlgorithmImports — corren dentro de Docker pero sin el CLR path.
     4	Fixture base: MockObjectStore retorna CSV sintético construido en el test.
     5	"""
     6	import pytest
     7	
     8	from core.universe import UniverseSpec
     9	
    10	_HEADER = 'Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low","5D Avg Vol",Time'
    11	
    12	
    13	def _row(symbol: str, price: float, vol: float, pct5d: str = "+5.00%", pct1d: str = "+1.00%") -> str:
    14	    return f"{symbol},Test Corp,{pct5d},{price},0.5,{pct1d},0.5,{price},{price},{vol:.0f},2026-06-05"
    15	
    16	
    17	def _csv(*rows: str) -> str:
    18	    return "\n".join([_HEADER] + list(rows))
    19	
    20	
    21	class MockObjectStore:
    22	    def __init__(self, csv_content: str):
    23	        self._content = csv_content
    24	
    25	    def read(self, key: str) -> str:
    26	        return self._content
    27	
    28	
    29	class RaisingObjectStore:
    30	    def read(self, key: str) -> str:
    31	        raise KeyError(f"Object with path '{key}' was not found in the Object Store")
    32	
    33	
    34	FILTER = "avg_vol_5d > 1e6 and price > 5"
    35	
    36	
    37	# T3.1 — El filtro funciona con alias normalizados
    38	def test_filter_returns_matching_tickers():
    39	    csv = _csv(
    40	        _row("AAA", price=10.0, vol=2_000_000),   # pasa: vol > 1e6 AND price > 5
    41	        _row("BBB", price=10.0, vol=500_000),       # falla: vol ≤ 1e6
    42	        _row("CCC", price=3.0,  vol=2_000_000),     # falla: price ≤ 5
    43	        _row("DDD", price=15.0, vol=3_000_000),     # pasa
    44	        _row("EEE", price=20.0, vol=4_000_000),     # pasa
    45	    )
    46	    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    47	    assert sorted(result) == ["AAA", "DDD", "EEE"]
    48	    assert len(result) == 3
    49	
    50	
    51	# T3.2 — Tope duro trunca correctamente
    52	def test_hard_cap_truncates_to_max_tickers():
    53	    rows = [_row(sym, price=10.0, vol=2_000_000)
    54	            for sym in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ"]]
    55	    csv = _csv(*rows)
    56	    result = UniverseSpec("k", FILTER, max_tickers=5).load(MockObjectStore(csv))
    57	    assert len(result) == 5
    58	    # Orden alfabético garantiza los primeros 5 después del sort
    59	    assert result == ["AAA", "BBB", "CCC", "DDD", "EEE"]
    60	
    61	
    62	# T3.3 — Footer strip elimina filas inválidas
    63	def test_footer_strip_excludes_non_ticker_rows():
    64	    csv = _csv(
    65	        _row("AAA", price=10.0, vol=2_000_000),
    66	        _row("BBB", price=10.0, vol=2_000_000),
    67	        _row("CCC", price=10.0, vol=2_000_000),
    68	        '"Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT"',
    69	    )
    70	    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    71	    assert len(result) == 3
    72	    assert "Downloaded" not in " ".join(result)
    73	
    74	
    75	# T3.4 — Columna requerida faltante lanza error con mensaje claro
    76	def test_missing_required_column_raises_key_error():
    77	    # CSV sin la columna "5D Avg Vol" → avg_vol_5d no aparece tras el rename
    78	    header_no_vol = 'Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low",Time'
    79	    row = "AAA,Test Corp,+5.00%,10.0,0.5,+1.00%,0.5,10.0,10.0,2026-06-05"
    80	    csv = header_no_vol + "\n" + row
    81	    with pytest.raises(KeyError, match="avg_vol_5d"):
    82	        UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    83	
    84	
    85	# T3.5 — KeyError de ObjectStore se propaga sin transformar
    86	def test_object_store_key_not_found_propagates():
    87	    with pytest.raises(KeyError):
    88	        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())

 succeeded in 0ms:
     1	# region imports
     2	from AlgorithmImports import *
     3	
     4	import json
     5	from collections import deque
     6	from time import perf_counter
     7	
     8	import core
     9	from core.features import SIDE_BY_DIRECTION, resolve_bucket_thresholds
    10	from core.output import JsonSubscriberSource, OutputSink
    11	from core.pipeline import ScanPipeline
    12	from core.symbol_data import SymbolData
    13	from core.timeframes import TIMEFRAMES, plan_warmup
    14	from core.universe import UniverseSpec
    15	import strategies
    16	# endregion
    17	
    18	
    19	class Tradescanner(QCAlgorithm):
    20	    """Orquestación L5 (Etapa 5B): config desde ObjectStore, universo efectivo por
    21	    entorno, un SymbolData por símbolo suscrito a DAILY con su consolidator cableado
    22	    a la suscripción (T2.1), warmup engine-managed con gate opcional contra la ruta
    23	    manual (T2.2, D4; flag validate_warmup). Features y rules (Etapas 6+) llegan después."""
    24	
    25	    def initialize(self):
    26	        # Ventana 2013-10 (Etapa 7/T5): única con datos minute (SPY sample del repo LEAN).
    27	        # SPY ejercita el working_bar; AAPL/IBM/FB no tienen minute aquí → caen al fallback
    28	        # close("D") (C2). SPY M:200 no calienta del todo (~3970 barras pre-2013 < 4221) pero
    29	        # M:200 no la referencia ninguna rule. FB (IPO 2012) tiene M:20 frío → gate B lo excluye.
    30	        self.set_start_date(2013, 10, 7)
    31	        self.set_end_date(2013, 10, 11)
    32	        self.set_cash(100000)
    33	
    34	        # Config de negocio desde ObjectStore (key = ruta relativa bajo storage/).
    35	        raw = self.object_store.read("config/strategies.json")
    36	        full_config = json.loads(raw)
    37	
    38	        env = self.get_parameter("env", "prod")
    39	        env_cfg = full_config["environments"][env]
    40	        top_n = env_cfg["top_n"]
    41	        max_universe = env_cfg["max_universe"]
    42	        strategies_config = full_config["strategies"]
    43	
    44	        # Universo efectivo: el override de environment (harness dev, D2) fuerza el
    45	        # universo de TODAS las estrategias; sin override cada una usa el suyo (prod).
    46	        universe_override = env_cfg.get("universe")
    47	        tickers: set[str] = set()
    48	        for name, cfg in strategies_config.items():
    49	            universe_key = f"universes/{universe_override or cfg['universe']}.csv"
    50	            spec = UniverseSpec(
    51	                universe_key=universe_key,
    52	                filter_expr=cfg["universe_filter"],
    53	                max_tickers=max_universe,
    54	            )
    55	            loaded = spec.load(self.object_store)
    56	            tickers.update(loaded)
    57	            self.log(
    58	                f"[{name}] universe loaded: {len(loaded)} tickers "
    59	                f"(env={env}, max={max_universe}, key={universe_key})"
    60	            )
    61	
    62	        # Plan de warmup global (R4: requirements idénticos entre símbolos → un solo
    63	        # plan). Las series sobre presupuesto NO se construyen: warning por cada una.
    64	        budget = env_cfg.get("warmup_budget")
    65	        plan = plan_warmup(self._build_requirements(env_cfg, strategies_config), budget)
    66	        for series in plan.excluded:
    67	            res = TIMEFRAMES[series.tf].source_resolution
    68	            self.log(
    69	                f"WARNING [warmup] serie {series.tf}:{series.period} excluida del plan: "
    70	                f"necesita {series.warmup_bars} barras ({res}), presupuesto {budget.get(res)}"
    71	            )
    72	        self._requirements: dict[str, set[int]] = {}
    73	        for series in plan.included:
    74	            self._requirements.setdefault(series.tf, set()).add(series.period)
    75	
    76	        # T2.1 — suscripción DAILY + SymbolData + wiring consolidator→suscripción.
    77	        # El wiring va SIEMPRE antes del warmup (consideración #8): set_warm_up
    78	        # stremea la historia por la suscripción y los consolidators ya cuelgan de ella.
    79	        self.symbol_data: dict[Symbol, SymbolData] = {}
    80	        self._daily_received: dict[Symbol, int] = {}
    81	        self._daily_consolidated: dict[Symbol, int] = {}
    82	        for ticker in sorted(tickers):
    83	            # MINUTE (T5.1): habilita el working_bar intradía del consolidator diario. El
    84	            # warmup sigue siendo DAILY (set_warm_up más abajo); resolución de suscripción ⟂
    85	            # resolución de warmup (5A T3.9). El consolidator diario se cabla a esta suscripción.
    86	            symbol = self.add_equity(
    87	                ticker,
    88	                Resolution.MINUTE,
    89	                data_normalization_mode=DataNormalizationMode.SPLIT_ADJUSTED,
    90	            ).symbol
    91	            sd = SymbolData(symbol, self._requirements)
    92	            self.subscription_manager.add_consolidator(symbol, sd.daily_consolidator)
    93	            # Contadores de evidencia del criterio 1:1 de T2.1 (se loguean al final).
    94	            self._daily_received[symbol] = 0
    95	            self._daily_consolidated[symbol] = 0
    96	            sd.daily_consolidator.data_consolidated += (
    97	                lambda _sender, bar, s=symbol: self._count_consolidated(s)
    98	            )
    99	            self.symbol_data[symbol] = sd
   100	            declared = ", ".join(f"{tf}:{p}" for tf, p in sorted(sd.declared))
   101	            self.log(f"[{ticker}] SymbolData listo (series: {declared})")
   102	
   103	        # T3 — recorder de validación (flag sma_validation, pensado para dev): captura
   104	        # los últimos K=5 puntos (barra consolidada, SMA) por serie; el archivo se
   105	        # escribe al cerrar el warmup (on_warmup_finished, tras el flush).
   106	        self._validation_rows: dict[tuple[Symbol, str, int], deque] = {}
   107	        if env_cfg.get("sma_validation", False):
   108	            for symbol, sd in self.symbol_data.items():
   109	                for tf in sorted(sd.timeframes):
   110	                    periods = tuple(sorted(p for t, p in sd.declared if t == tf))
   111	                    if not periods:
   112	                        continue  # la raíz D existe aunque no declare series
   113	                    for period in periods:
   114	                        self._validation_rows[(symbol, tf, period)] = deque(maxlen=5)
   115	                    sd.consolidator(tf).data_consolidated += (
   116	                        lambda _s, bar, sym=symbol, t=tf, ps=periods:
   117	                            self._record_validation(sym, t, ps, bar)
   118	                    )
   119	
   120	        # Ancla de calendario para las time-rules: SPY del universo si está suscrito;
   121	        # si no (prod), suscripción propia. Provee data (avanza el reloj) y market hours.
   122	        spy = next((s for s in self.symbol_data if s.value == "SPY"), None)
   123	        self.spy = spy or self.add_equity("SPY", Resolution.DAILY).symbol
   124	
   125	        # Un ScanPipeline por estrategia/variante (config=datos × strategies/=composición),
   126	        # resuelto en initialize() (D7.1): direction→side en un solo punto (D7.3), thresholds y
   127	        # rules ya construidas. El schedule ya NO es por variante: lo registra el grupo (T5.2).
   128	        self.pipelines: dict[str, ScanPipeline] = {}
   129	        self._probe_done = False  # probe de emisión A.3: solo en el primer scan real
   130	        for name, cfg in strategies_config.items():
   131	            composition = strategies.STRATEGIES.get(name)
   132	            if composition is None:
   133	                self.log(f"[{name}] sin StrategyConfig en STRATEGIES: omitida del scan")
   134	                continue
   135	            side = SIDE_BY_DIRECTION[cfg["direction"]]
   136	            self.pipelines[name] = ScanPipeline(
   137	                strategy_name=name,
   138	                direction=cfg["direction"],
   139	                side=side,
   140	                rules=composition.build_rules(side),
   141	                series=composition.series(side),
   142	                thresholds=resolve_bucket_thresholds(full_config, name),
   143	                top_n=top_n,
   144	                partial_bar=composition.partial_bar,
   145	            )
   146	
   147	        # T5.1 — OutputSink (Etapa 8): L5 es el único que toca object_store/notify/live_mode/
   148	        # schedule, así que aquí se construye el sink y se enchufa la config de notificación. El
   149	        # switch local/cloud vive SOLO en OutputSink (D8.4): main.py no decide canal por entorno.
   150	        self._env = env
   151	        notif_cfg = json.loads(self.object_store.read("config/notifications.json"))
   152	        self.output = OutputSink(
   153	            self.object_store,
   154	            self.notify,
   155	            self.live_mode,
   156	            notif_cfg,
   157	            JsonSubscriberSource(notif_cfg),
   158	            self.log,
   159	        )
   160	
   161	        # T5.2 — un ScheduledEvent por estrategia BASE (D8.7), no por variante: el grupo corre sus
   162	        # pipelines miembro (long/short) y emite UNA vez. Invariante D8.7 validado aquí (miembros
   163	        # comparten schedule y partial_bar) → config inconsistente = error explícito en initialize().
   164	        for base, members in notif_cfg["notification_groups"].items():
   165	            active = [m for m in members if m in self.pipelines]
   166	            if not active:
   167	                self.log(f"[{base}] grupo sin pipelines activos: omitido del schedule")
   168	                continue
   169	            schedules = {strategies_config[m]["schedule"] for m in active}
   170	            if len(schedules) > 1:
   171	                raise ValueError(
   172	                    f"grupo '{base}' (D8.7): miembros con schedule distinto {schedules}"
   173	                )
   174	            partial_bars = {self.pipelines[m].partial_bar for m in active}
   175	            if len(partial_bars) > 1:
   176	                raise ValueError(
   177	                    f"grupo '{base}' (D8.7): miembros con partial_bar distinto {partial_bars}"
   178	                )
   179	            time_rule = self._time_rule_for(schedules.pop())
   180	            if time_rule is None:
   181	                self.log(f"[{base}] schedule desconocido: grupo omitido")
   182	                continue
   183	            self.schedule.on(
   184	                self.date_rules.every_day(self.spy),
   185	                time_rule,
   186	                lambda base=base, active=tuple(active): self._scan_group(base, active),
   187	            )
   188	            self.log(f"[{base}] schedule registrado: miembros {list(active)}")
   189	
   190	        # T2.2 — Estrategia A (D4): warmup engine-managed (adoptada: gate 9/9 series
   191	        # exactas vs ruta manual, 2026-06-11). El gate de cross-check queda detrás del
   192	        # flag validate_warmup del environment — apagado por defecto: duplica el warmup.
   193	        self._gate_enabled = bool(env_cfg.get("validate_warmup", False))
   194	        self._warmup_depth = plan.depth_by_resolution.get("daily", 0)
   195	        driver = max(plan.included, key=lambda s: s.warmup_bars, default=None)
   196	        per_tf_max: dict[str, int] = {}
   197	        for series in plan.included:
   198	            per_tf_max[series.tf] = max(per_tf_max.get(series.tf, 0), series.warmup_bars)
   199	        detail = ", ".join(f"{tf}:{max(self._requirements[tf])}→{bars}"
   200	                           for tf, bars in sorted(per_tf_max.items()))
   201	        if self._warmup_depth:
   202	            self.set_warm_up(self._warmup_depth, Resolution.DAILY)
   203	            self.log(
   204	                f"[warmup] plan(daily): depth={self._warmup_depth} "
   205	                f"(driver {driver.tf}:{driver.period}) | {detail}"
   206	            )
   207	        self._warmup_t0 = perf_counter()
   208	
   209	    def on_data(self, data: Slice):
   210	        """Instrumentación 1:1 (cuenta SIEMPRE, warmup incluido) + guard de warmup:
   211	        nada de scans/escritura con data histórica (T2.2)."""
   212	        for symbol in self.symbol_data:
   213	            if data.bars.contains_key(symbol):
   214	                self._daily_received[symbol] += 1
   215	        if self.is_warming_up:
   216	            return
   217	        # Lógica de runtime (Etapas 6+) va debajo de este guard.
   218	
   219	    def on_warmup_finished(self):
   220	        """Cierre del warmup (T2.2/T2.3): flush de la emisión perezosa, evidencia de
   221	        duración/ready/estrategia, y gate opcional de cross-check vs ruta manual (D4)."""
   222	        elapsed = perf_counter() - self._warmup_t0
   223	        streamed = sum(self._daily_received.values())
   224	
   225	        # Hallazgo #1 de 5A aplica también a la ruta engine EN ESTE INSTANTE: la última
   226	        # barra diaria del warmup sigue retenida (working) hasta la próxima barra o un
   227	        # scan. Sin este flush, las SMAs quedan un periodo frías justo cuando T3 va a
   228	        # escribir el archivo de validación.
   229	        held = sum(1 for sd in self.symbol_data.values() if sd.working_bar is not None)
   230	        for sd in self.symbol_data.values():
   231	            sd.scan(self.time)
   232	        self.log(
   233	            f"[warmup] set_warm_up({self._warmup_depth}, DAILY) completado: {streamed} "
   234	            f"barras stremeadas en {elapsed:.2f}s; flush scan({self.time}) emitió "
   235	            f"{held} working bar(s) retenidas"
   236	        )
   237	
   238	        ready = sum(1 for sd in self.symbol_data.values() if sd.is_ready())
   239	        self.log(f"[warmup] ready: {ready}/{len(self.symbol_data)} símbolos")
   240	        for symbol, sd in self.symbol_data.items():
   241	            if not sd.is_ready():
   242	                cold = [f"{tf}:{p}" for tf, p in sorted(sd.declared)
   243	                        if not sd.is_ready(tf, p)]
   244	                self.log(f"WARNING [warmup] {symbol.value} series frías: {', '.join(cold)}")
   245	
   246	        gate = "ON" if self._gate_enabled else "OFF (flag validate_warmup)"
   247	        self.log(
   248	            f"[warmup] estrategia: set_warm_up engine-managed (A, adoptada en T2.2 "
   249	            f"con gate 9/9 exactas); gate cross-check {gate}"
   250	        )
   251	        if self._gate_enabled and self._warmup_depth:
   252	            self._run_warmup_gate()
   253	
   254	        if self._validation_rows:
   255	            self._write_validation_file()
   256	
   257	    def _run_warmup_gate(self) -> None:
   258	        """Gate D4 (bajo flag validate_warmup): la ruta manual de 5A — history[TradeBar] tipado en UNA
   259	        llamada batch + update por barra + scan de cierre — sobre SymbolData sombra
   260	        debe reproducir EXACTAMENTE las SMAs que dejó set_warm_up. Coinciden → A
   261	        adoptado; divergen → WARNING con detalle (causa de rollback)."""
   262	        symbols = list(self.symbol_data)
   263	        shadows = {s: SymbolData(s, self._requirements) for s in symbols}
   264	        history = self.history[TradeBar](symbols, self._warmup_depth, Resolution.DAILY)
   265	        rows = 0
   266	        for trade_bars in history:
   267	            for bar in trade_bars.values():
   268	                shadows[bar.symbol].update(bar)
   269	                rows += 1
   270	        for shadow in shadows.values():
   271	            shadow.scan(self.time)  # mismo instante de flush que la ruta engine
   272	
   273	        total = 0
   274	        mismatches: list[str] = []
   275	        for symbol, sd in self.symbol_data.items():
   276	            shadow = shadows[symbol]
   277	            for tf, period in sorted(sd.declared):
   278	                total += 1
   279	                engine_sma = sd.sma(tf, period)
   280	                manual_sma = shadow.sma(tf, period)
   281	                if (engine_sma.current.value != manual_sma.current.value
   282	                        or engine_sma.is_ready != manual_sma.is_ready):
   283	                    mismatches.append(
   284	                        f"{symbol.value} {tf}:{period} "
   285	                        f"engine={engine_sma.current.value} (samples={engine_sma.samples}, "
   286	                        f"ready={engine_sma.is_ready}) vs "
   287	                        f"manual={manual_sma.current.value} (samples={manual_sma.samples}, "
   288	                        f"ready={manual_sma.is_ready})"
   289	                    )
   290	        if not mismatches:
   291	            self.log(
   292	                f"[warmup] gate dev OK: set_warm_up ADOPTADO — {total}/{total} series "
   293	                f"exactas vs ruta manual ({rows} filas vía history[TradeBar], 1 llamada batch)"
   294	            )
   295	        else:
   296	            self.log(
   297	                f"WARNING [warmup] gate dev: {len(mismatches)}/{total} series divergen "
   298	                f"de la ruta manual → ROLLBACK requerido (D4)"
   299	            )
   300	            for mismatch in mismatches:
   301	                self.log(f"WARNING [warmup] gate: {mismatch}")
   302	
   303	    def on_end_of_algorithm(self):
   304	        """Evidencia del feed→consolidator. Con suscripción minute (T5.1) la relación es N:1
   305	        (N barras minute → 1 barra diaria), así que el chequeo 1:1 estricto de 5B ya no aplica:
   306	        se reporta el conteo informativo (barras recibidas vs diarias consolidadas + working bar)."""
   307	        for symbol, sd in self.symbol_data.items():
   308	            received = self._daily_received[symbol]
   309	            consolidated = self._daily_consolidated[symbol]
   310	            working = sd.working_bar
   311	            tail = (
   312	                f", working hasta {working.end_time}" if working is not None
   313	                else " (sin working bar)"
   314	            )
   315	            self.log(
   316	                f"[{symbol.value}] feed→consolidator: {received} barras recibidas "
   317	                f"(warmup daily + runtime minute), {consolidated} diarias consolidadas{tail}"
   318	            )
   319	
   320	    def _record_validation(
   321	        self, symbol: Symbol, tf: str, periods: tuple, bar: TradeBar
   322	    ) -> None:
   323	        """Punto de validación por barra consolidada. La SMA ya está actualizada cuando
   324	        este handler corre (orden de handlers .NET = orden de suscripción; cubierto
   325	        por test del accessor)."""
   326	        sd = self.symbol_data[symbol]
   327	        for period in periods:
   328	            sma = sd.sma(tf, period)
   329	            self._validation_rows[(symbol, tf, period)].append(
   330	                (bar.end_time, bar.close, sma.current.value, sma.samples)
   331	            )
   332	
   333	    def _write_validation_file(self) -> None:
   334	        """T3: últimos K=5 puntos por serie → validation/sma_validation_<fecha>.csv vía
   335	        ObjectStore (storage/validation/ en local). bar_end_time sigue la convención de
   336	        LEAN (C4): cae al inicio del periodo siguiente (W lunes→domingo con cierre
   337	        efectivo viernes; M mes calendario)."""
   338	        lines = ["ticker,timeframe,period,bar_end_time,bar_close,sma_value,bars_consumed"]
   339	        for symbol, tf, period in sorted(
   340	            self._validation_rows, key=lambda k: (k[0].value, k[1], k[2])
   341	        ):
   342	            for end_time, close, sma_value, samples in (
   343	                self._validation_rows[(symbol, tf, period)]
   344	            ):
   345	                lines.append(
   346	                    f"{symbol.value},{tf},{period},{end_time},{close},{sma_value},{samples}"
   347	                )
   348	        key = f"validation/sma_validation_{self.time:%Y%m%d}.csv"
   349	        self.object_store.save(key, "\n".join(lines) + "\n")
   350	        self.log(
   351	            f"[validation] {key}: {len(self._validation_rows)} series, "
   352	            f"{len(lines) - 1} filas (K=5 últimos puntos por serie)"
   353	        )
   354	
   355	    def _count_consolidated(self, symbol: Symbol) -> None:
   356	        self._daily_consolidated[symbol] += 1
   357	
   358	    def _scan_group(self, base: str, members: tuple) -> None:
   359	        """Callback del ScheduledEvent por estrategia base (D8.7/T5.2): corre el pipeline de cada
   360	        miembro (long, short), agrupa los ScanResult por dirección en `sections` y emite UNA vez al
   361	        OutputSink (Etapa 8). Conserva el log de candidatos por variante (ortogonal). Guardado
   362	        contra warmup: los ScheduledEvents también disparan con data histórica."""
   363	        if self.is_warming_up:
   364	            return
   365	        if not self._probe_done:
   366	            self._emit_probe()          # A.3: confirmar que "hoy" no está consolidado al scan
   367	            self._probe_done = True
   368	        # `sections` se siembra con la dirección de cada miembro ACTIVO (no de sus resultados): un
   369	        # lado activo sin candidatos queda como sección vacía (count 0) para que el correo muestre
   370	        # "(sin candidatos)" en ese bloque (D8.6), en vez de omitirlo.
   371	        sections: dict[str, list] = {}
   372	        partial_bar = False
   373	        for name in members:
   374	            pipeline = self.pipelines.get(name)
   375	            if pipeline is None:
   376	                continue
   377	            partial_bar = pipeline.partial_bar  # uniforme por grupo (validado en initialize)
   378	            sections.setdefault(pipeline.direction, [])
   379	            results = pipeline.scan(self.symbol_data, self.utc_time, self.log)
   380	            # Watchlist visible y reproducible en el log: una línea por candidato con su evidencia.
   381	            for r in results:
   382	                self.log(
   383	                    f"[{name}] candidato {r.ticker} {r.direction} "
   384	                    f"price={r.price:.4f} partial_bar={r.partial_bar} "
   385	                    f"passed={'|'.join(r.passed_rules)} "
   386	                    f"evidence={json.dumps(r.sma_evidence, sort_keys=True)}"
   387	                )
   388	            self.log(f"[{name}] scan @ {self.utc_time}: {len(results)} candidatos")
   389	            sections[pipeline.direction].extend(results)
   390	        # Un solo emit por estrategia base (D8.2): el switch de canal/entorno vive en OutputSink.
   391	        self.output.emit(base, self._env, self.utc_time, partial_bar, sections)
   392	        counts = ", ".join(f"{side}:{len(rs)}" for side, rs in sorted(sections.items()))
   393	        self.log(f"[{base}] emit @ {self.utc_time}: sections={{{counts}}}")
   394	
   395	    def _emit_probe(self, ticker: str = "SPY") -> None:
   396	        """Probe de emisión (A.3): loguea working_bar vs close('D') de un símbolo en el primer
   397	        scan real. Esperado (timedelta(days=1)): la barra diaria de hoy NO está consolidada al
   398	        scan → working_bar = hoy y close('D') = ayer. Si coincidieran, LEAN emitiría al cierre y
   399	        habría que activar la contingencia de day_change (D7.6). T6 registra el hallazgo."""
   400	        symbol = next((s for s in self.symbol_data if s.value == ticker), None)
   401	        if symbol is None:
   402	            return
   403	        sd = self.symbol_data[symbol]
   404	        working = sd.working_bar
   405	        wb = f"close={working.close}, end_time={working.end_time}" if working is not None else "None"
   406	        try:
   407	            daily_close = sd.close("D")
   408	        except Exception:
   409	            daily_close = None
   410	        self.log(
   411	            f"[probe A.3] {ticker} @ {self.utc_time}: working_bar=({wb}); close('D')={daily_close} "
   412	            f"→ esperado working_bar=hoy, close('D')=ayer (hoy NO consolidado)"
   413	        )
   414	
   415	    def _build_requirements(
   416	        self, env_cfg: dict, strategies_config: dict
   417	    ) -> dict[str, set[int]]:
   418	        """Series (tf → periodos) compartidas por todos los símbolos: el override de
   419	        environment (harness dev, D2) reemplaza la unión de timeframes de las
   420	        estrategias; sin override se usa la unión (prod). plan_warmup filtra después
   421	        contra el presupuesto."""
   422	        override = env_cfg.get("timeframes")
   423	        if override is not None:
   424	            return {tf: set(periods) for tf, periods in override.items()}
   425	        requirements: dict[str, set[int]] = {}
   426	        for cfg in strategies_config.values():
   427	            for tf, periods in cfg["timeframes"].items():
   428	                requirements.setdefault(tf, set()).update(periods)
   429	        return requirements
   430	
   431	    def _time_rule_for(self, schedule: str):
   432	        """Mapea el string de schedule a una time-rule de LEAN anclada a SPY. Punto de
   433	        extensión: por ahora cubre los strings de la config; desconocido -> None (se omite)."""
   434	        if schedule == "after_close":
   435	            # +1 min para asegurar que la barra de cierre ya consolidó (ver decisión D5).
   436	            return self.time_rules.after_market_close(self.spy, 1)
   437	        if schedule == "before_close_30m":
   438	            return self.time_rules.before_market_close(self.spy, 30)
   439	        return None

**Inspecting decisions and configurations**

I need to review the decisions documents relevant to ADRs and maybe look at the Stage 4 decisions by using a parallel approach. It could also be beneficial to check the configuration strategies, project configs, lean.json, and universe csv for their headers and counts. Running some read commands might help, and I want to ensure all Stage 4 points are covered. Additionally, I need to verify the ObjectStore key path and read the seed scripts.
codex
El código de Etapa 4 está en los lugares esperados: `core/universe.py`, `core/__init__.py`, `main.py` y `tests/test_universe.py`. También veo que el repositorio ya avanzó a etapas posteriores, así que separaré hallazgos propios de Etapa 4 de cambios posteriores que solo afecten su integración.
exec
/bin/zsh -lc "sed -n '1,220p' .claude/decisions/ADR-001-python-version.md" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "sed -n '1,240p' .claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# ADR-001 — Versión de Python para host y engine

**Estado:** aceptado  
**Fecha:** 2026-06-11  
**Supersede a:** —  
**Supersedido por:** —

---

## Contexto

El stack tiene dos entornos Python distintos con ciclos de vida independientes:

- **Host** (la máquina del desarrollador): corre el LEAN CLI (`pip install lean`) y scripts auxiliares del repo.
- **Engine** (Docker `quantconnect/lean`): corre el código de negocio (`main.py`, `core/`, `strategies/`).

Al iniciar el proyecto, la máquina del desarrollador tenía Python 3.13.1 instalado como sistema. La pregunta era: ¿qué versión fijar en el repo, y es necesario aislarla?

---

## Opciones evaluadas

| Opción | Pro | Contra |
|---|---|---|
| Usar Python 3.13.1 del sistema | Sin instalación extra | LEAN CLI no la lista en sus classifiers; riesgo de rotura silenciosa |
| Devcontainer con Python 3.11 | Entorno 100% reproducible | Docker-in-Docker: el CLI lanza otro contenedor → complejidad innecesaria |
| **pyenv + Python 3.11 + virtualenv** | Reproducible, sin Docker-in-Docker, coincide con engine | Requiere pyenv en cada máquina (pasos documentados en Etapa 0) |

---

## Decisión

**Fijar Python 3.11 en el repo vía pyenv** (archivo `.python-version`) y **aislar el CLI en un virtualenv `.venv`**.

Versión exacta: **3.11.11**, para coincidir con la fijada en el engine Docker.

---

## Evidencia recopilada

Fuentes consultadas el 2026-06-11:

- **LEAN CLI `setup.py`** — `python_requires=">= 3.9"`, classifiers: 3.9–3.14.  
  → El CLI técnicamente acepta 3.13, pero el engine no.  
  Fuente: https://github.com/QuantConnect/lean-cli/blob/master/setup.py

- **`DockerfileLeanFoundation`** — `Miniconda3-py311_24.9.2-0`, label `strict_python_version=3.11.11`.  
  → El engine fija exactamente 3.11.11.  
  Fuente: https://github.com/QuantConnect/Lean/blob/master/DockerfileLeanFoundation

- **PyPI `lean`** — versión 1.0.225 (marzo 2026).  
  Fuente: https://pypi.org/project/lean/

- **Docker Hub `quantconnect/lean`** — imagen oficial del engine.  
  Fuente: https://hub.docker.com/r/quantconnect/lean

---

## Consecuencias

**Positivas:**
- Host y engine corren la misma versión → sin discrepancias si un script auxiliar importa tipos de LEAN.
- `.python-version` commiteado garantiza reproducibilidad en cualquier máquina con pyenv.
- `.venv/` aislado evita contaminación del Python del sistema.

**Negativas / trade-offs:**
- Cada desarrollador nuevo necesita instalar pyenv (pasos en [etapa-00.md](../fase-1-desarrollo-local/etapa-00.md)).
- Si el engine sube a 3.12 en el futuro, habrá que crear un nuevo ADR y actualizar `.python-version`.

---

## Revisión futura

Revisar cuando `DockerfileLeanFoundation` cambie el label `strict_python_version`. El comando para chequearlo:

```bash
docker inspect quantconnect/lean:latest | grep -i python_version
```

 succeeded in 0ms:
### Etapa 4 — UniverseSpec

| # | Pendiente | Descripción |
|---|-----------|-------------|
| P1 | `UniverseSpec`: normalización de alias de columnas | Al leer el CSV, renombrar columnas según el alias map (contrato §5 de PLAN.md). El filtro declarativo usa alias; el CSV fuente usa nombres originales. `UniverseSpec` hace el rename antes de aplicar `eval()`. |
| P2 | `UniverseSpec`: footer strip | Descartar filas donde `ticker` no matchee `^[A-Z]{1,5}$`. El CSV en ObjectStore llega con footer de Barchart; la validación es responsabilidad de `UniverseSpec`, no del script de siembra. |
| P3 | `UniverseSpec`: `direction` no es campo de universo | El campo `direction` de la estrategia debe estar disponible para `ScanResult`, pero `UniverseSpec` no lo necesita (solo filtra tickers). El pipeline (Etapa 7) lo propaga. No diseñar `UniverseSpec` con ese acoplamiento. |
| P4 | `main.py`: leer `env_cfg["top_n"]` y `env_cfg["max_universe"]` | `main.py` debe leer `self.get_parameter("env", "prod")` y extraer `top_n`/`max_universe` del bloque `environments`. Estos valores se pasan al pipeline cuando se instancie en Etapa 7. En Etapa 4 ya se puede leer y loguear para verificar. |
| P7 | Actualizar spec Etapa 4 | El spec debe referenciar el contrato de alias de §5 (PLAN.md) y la regla de footer strip. `UniverseSpec` no necesita conocer `direction` ni `main_timeframe`; el pipeline (Etapa 7) los propaga al `ScanResult`. |

---

### Estado T1 — `core/universe.py` (completada 2026-06-11)

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| CSV real + `max_tickers=200`: devuelve ≤200 tickers, todos `^[A-Z]{1,5}$` | ✅ | advances=74, declines=68; todos pasan regex |
| `filter_expr="avg_vol_5d > 1e6 and price > 5"`: ~74 advances, ~68 declines | ✅ | `advances: 74 tickers`, `declines: 68 tickers` |
| Footer no aparece en la salida | ✅ | Assertion `'Downloaded' not in tickers` pasa |
| `load()` reproducible: misma entrada → mismo resultado | ✅ | Orden alfabético garantizado por `sort_values("ticker")` |
| Sin imports de `AlgorithmImports` | ✅ | `grep "^from AlgorithmImports\|^import AlgorithmImports"` → no resultados |
| `core/__init__.py` exporta `UniverseSpec` | ✅ | Agregado `from core.universe import UniverseSpec` |

**Pendientes de T1:** ninguno.

### Estado T2 — `main.py` integración (completada 2026-06-11)

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| 4 líneas `universe loaded` durante `initialize()` | ✅ | `[swing_eod]`, `[swing_eod_short]`, `[market_close]`, `[market_close_short]` |
| Conteos coherentes con el filtro | ✅ | 74 advances, 68 declines en prod; 2 de cada uno en dev |
| `env=dev` → `max=2` → `2 tickers` | ✅ | Log muestra `env=dev, max=2, 2 tickers` |
| ScheduledEvents siguen disparando | ✅ | `scan market_close @ ...`, `scan swing_eod @ ...` en cada día de backtest |
| Sin errores en backtest | ✅ | `Successfully ran 'trade-scanner'`; el ERROR de InterestRateProvider es del engine LEAN, ya presente desde Etapa 2 |

**Nota:** El spec menciona `max_universe=10` para dev, pero `strategies.json` tiene `max_universe=2` (definido en Etapa 3). El código es correcto; la discrepancia está en el número del spec. Los parámetros del algoritmo viven en `trade-scanner/config.json`, no en `lean.json` (descubrimiento D-E4: LEAN lee `get_parameter()` desde el `config.json` del proyecto).

**Pendientes para cerrar Etapa 4:**
- T3: tests unitarios T3.1–T3.5 en `tests/test_universe.py`
- Ejecutar `bash scripts/run_tests.sh` y verificar 5 tests verdes
- Commit `[Etapa 4] ...`

exec
/bin/zsh -lc "sed -n '1,320p' .claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "sed -n '1,260p' .claude/decisions/ADR-003-stooq-como-fuente-de-datos.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# ADR-003 — Stooq como fuente de datos (validación y candidato a feed primario V1)

**Estado:** investigación — decisión de feed live diferida a Etapa 9
**Fecha:** 2026-06-11
**Supersede a:** —
**Supersedido por:** —
**Relacionado:** [ADR-002](ADR-002-qc-module-auth-constraint.md) (constraint QC para brokerage Alpaca), [etapa-05b.md](../fase-1-desarrollo-local/etapa-05b.md) (F3 usa Stooq como fuente de validación)

---

## Contexto

Durante Etapa 5B surgió la pregunta de si **Stooq** podría usarse como fuente de datos primaria para la primera versión (V1) del screener, en vez de **Alpaca**, dado que:

- El screener V1 corre a EOD / swing lento y **no coloca órdenes**.
- El delay de Stooq (intradía 15–20 min; daily final tras el cierre) es **irrelevante** para un scan EOD.
- Alpaca free entrega datos IEX (un solo venue, volumen subestimado) y su path live choca con [ADR-002](ADR-002-qc-module-auth-constraint.md) (módulo de brokerage = QC paid).

Esta nota documenta la investigación. **No cierra la decisión del feed live** (eso es Etapa 9); sí fija el rol de Stooq dentro de 5B y el hallazgo arquitectónico que reabre el cálculo Alpaca-vs-Stooq.

---

## Hallazgos de la investigación

### Calidad de dato (eje: SMAs EOD)

- **Stooq EOD** es consolidado, split/dividend-adjusted, cuadra mejor con TradingView; historia 30+ años → **M:200 viable**.
- **Alpaca free = IEX**: un solo exchange, volumen subestimado (ya en CLAUDE.md); arranca **2016** → **M:200 imposible** (~17 años requeridos).
- **Veredicto de dato:** para SMAs sobre cierres en un screener EOD, **Stooq > Alpaca free**. El delay de Stooq no afecta a un scan post-cierre.

### Reframe arquitectónico (el hallazgo importante)

La razón por la que el plan arrastra Alpaca es su **integración nativa de LEAN**, que es un *brokerage* (con datos incluidos) → de ahí el bloqueo de ADR-002 (módulo NuGet `installs: true`, QC paid).

Pero **V1 no coloca órdenes → no necesita brokerage**, solo un *feed de datos*. LEAN ofrece un mecanismo sancionado que **no es un SDK de broker**: custom data vía `PythonData` (`get_source` + `reader`). El algoritmo entrega una URL (el CSV de Stooq), **LEAN hace el fetch**, el `reader` parsea cada línea. Propiedades:

- **Dentro de la API de `QCAlgorithm`** (`add_data`) → no viola "el código solo habla con QCAlgorithm; sin SDKs de datos".
- **Portable local ↔ cloud** (misma URL) → respeta la regla de portabilidad.
- **Esquiva ADR-002 por completo** — sin módulo de brokerage, sin QC paid.
- `is_live` permite zips locales en backtest y la URL de Stooq en vivo, con la misma clase.

Consecuencia: **Stooq-como-custom-data es un candidato a feed live de V1 potencialmente más limpio que Alpaca**, precisamente porque evita el brokerage.

### Límites de Stooq (todos de fiabilidad de producción, no de dato)

- **Sin API oficial** — solo interfaz CSV (`https://stooq.com/q/d/l/?s=<sym>.us&i=d`). Sin contrato, SLA ni soporte.
- **Rate limit agresivo y opaco** — devuelve "Exceeded the daily hits limit". A ~200 tickers/día hay que batchear; comportamiento **no verificado a esa escala**.
- **Fragilidad de fuente gratuita** — formato/URL puede cambiar o desaparecer sin aviso (patrón "Bye Yahoo").
- **ToS** — gratis para uso personal; scraping sistemático para producción puede violar términos.
- **Sin profundidad intradía real** (solo barras 5/60-min delayed) → insuficiente si una estrategia futura pide timeframes intradía.

Alpaca, por contraste: API formal con términos claros, rate limit documentado (100/min), y camino natural cuando V2 coloque órdenes (broker + datos integrados).

---

## Ventajas y desventajas (Stooq como feed primario V1)

**Ventajas**
- Calidad EOD superior (consolidado, ajustado, cuadra con TradingView).
- M:200 viable (historia profunda).
- Esquiva ADR-002 / QC paid vía custom `PythonData`.
- Sinergia con 5B: el fetcher/converter de F3 ya construye esta pieza → trabajo transferible.
- El feed live sería el mismo validado manualmente en F3 → confianza directa.

**Desventajas**
- Sin API oficial / SLA / soporte.
- Rate limit opaco; comportamiento a 200 símbolos sin verificar.
- Fragilidad de fuente gratuita (drift de formato, caída sin aviso).
- Riesgo de ToS para uso sistemático.
- Sin profundidad intradía real (techo si aparecen timeframes intradía).

---

## Decisión

1. **Rol de Stooq en 5B (firme):** fuente de **validación** en F3 — converter host-side que escribe zips LEAN y valida SMAs ≤0,25% contra TradingView. Sin cambios al plan.

2. **Stooq como feed primario de V1 (diferido a Etapa 9):** decisión abierta. Antes de cerrarla hace falta **evidencia empírica de fiabilidad** — el único eje donde Stooq es dudoso.

---

## Acciones propuestas

- **F4 de Etapa 5B (adición pequeña):** junto al smoke-test de conectividad de Alpaca, agregar un **smoke-test de fiabilidad de Stooq a escala** — fetch de ~200 símbolos, medir si pega el quota, latencia y estabilidad del formato. Genera la evidencia dura para el ADR de Etapa 9.
- **Etapa 9:** decidir feed live de V1 entre:
  - **Stooq vía `PythonData` custom** (sin brokerage, sin QC paid; sujeto a fiabilidad).
  - **Alpaca** (ADR-002, Opción A/B/C) — natural cuando V2 coloque órdenes.
  Actualizar este ADR con la elección.

---

## Revisión futura

Reevaluar si aparece un timeframe intradía (Stooq queda corto), si Stooq formaliza una API/quota, o cuando V2 introduzca órdenes (empuja hacia Alpaca como broker+datos).

---

## Fuentes

- [QuantStart — Introduction to Stooq Pricing Data](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/)
- [Stooq — Free Market Data](https://stooq.com/db/)
- [AmiBroker forum — Stooq download limit violation](https://forum.amibroker.com/t/stooq-download-range-control-and-download-limit-violation/1167)
- [The Financial Hacker — Bye Yahoo](https://financial-hacker.com/bye-yahoo-and-thank-you-for-the-fish/)
- [QuantConnect — Importing Custom Data (Key Concepts)](https://www.quantconnect.com/docs/v2/writing-algorithms/importing-data/key-concepts)
- [Alpaca — Market Data](https://alpaca.markets/data)

 succeeded in 0ms:
# ADR-005 — Snapshot único de posición precio↔SMA y reglas como filtros puros

**Estado:** aceptado (2026-06-14) — implementación en [Etapa 6B](../fase-1-desarrollo-local/etapa-06b.md)
**Fecha:** 2026-06-13 (propuesto) · 2026-06-14 (aceptado)
**Ámbito:** Etapa 6 (L3 features / L4 rules), preparación intradía (Fase 2+)
**Supersede a:** D4 de `etapa-06.md` (parcial — ver §"Conserva/Modifica/Elimina") y el override de umbral por-regla (`max_pct` de `NotExtended`).
**Relacionado:** [ADR-004](ADR-004-cadencia-evaluacion-intradia.md) (CUÁNDO se evalúa; este ADR es el QUÉ se calcula).

---

## 1. Contexto

Hoy cada rule llama `position_vs_sma(sd, tf, period, thresholds)` por cada `(tf, period)` dentro de su `evaluate`. Consecuencias del estado actual ([core/rules.py](../../trade-scanner/core/rules.py), [core/features.py](../../trade-scanner/core/features.py)):

- **Recomputación latente:** si dos rules comparten un `(tf, period)` (p. ej. `AboveSMA(20,D)` y otra regla sobre `D:20`), la distancia y el bucket se calculan dos veces. En V1 no se solapan, pero el contrato lo permite.
- **El umbral entra por rule, no por estrategia:** `NotExtended` (D4) inyecta `max_pct` como `thresholds["extended"]` propio → dos reglas de la misma estrategia pueden bucketizar con cortes distintos. Esto contradice la decisión ya tomada de **un solo set de buckets por estrategia**.
- **La rule tiene `sd` en la mano:** nada le impide re-medir o re-bucketizar; la pureza ("solo lee lo precalculado") es por convención, no estructural.

El rediseño hace **una sola evaluación** de posición por símbolo·scan, bucketiza **una vez** con el set resuelto de la estrategia, y convierte las rules en **filtros que solo leen** buckets ya asignados. Válido para largos y cortos sin duplicar reglas, y barato de reconstruir por barra de 2-min (intradía futuro).

**Decisiones de entrada (no se relitigan, se integran):**
- Un único set de `bucket_thresholds` por estrategia, compartido por todas sus rules. Se conserva `resolve_bucket_thresholds` (T2.2).
- Cadencia event-driven en cierre de barra del marco de decisión (ADR-004). Este ADR no toca el *trigger*.

---

## 2. Diseño final

### 2.1 Snapshot único (L3, `core/features.py`)

Estructura: **dict anidado plano** `{tf: {period: PositionResult}}` — misma forma que la evidencia, sin clase envolvente.

```python
def build_position_snapshot(
    sd: "SymbolData",
    series: Iterable[tuple[str, int]],
    thresholds: dict[str, float],
) -> dict[str, dict[int, PositionResult]]:
    """Posición precio↔SMA de un símbolo para cada (tf, period) en `series`, calculada
    una sola vez. Bucketiza con el set ya resuelto de la estrategia (D2/T2.2).

    `series` = unión de los (tf, period) que referencian las rules de la estrategia
    (NO todas las SMAs declaradas: ver §2.2). Frío: la primera serie con
    `FeatureNotReady` se propaga — el pipeline (Etapa 7) excluye el símbolo y loguea.
    """
```

- Reutiliza `position_vs_sma` tal cual como primitivo per-serie (loop fino sobre él): conserva el contrato de fríos, la normalización `float()` en la frontera L2→L3 y `_bucketize`.
- **Quién lo construye:** el pipeline (L4, Etapa 7), una vez por `(símbolo, estrategia, scan)`, antes de evaluar ninguna rule.
- **Costo:** `|series|` lecturas O(1) (`sma.current.value` + `close` + resta/división + cascada de bucket). Para 200 símbolos × ~7 series = ~1400 ops O(1) por scan. Trivial; reconstruible por barra (§7).

### 2.2 `series` = lo que las rules referencian, no lo declarado

El snapshot cubre **la unión de `(tf, period)` que usan las rules de la estrategia**, no todo `sd.declared` (que es la unión de *todas* las estrategias que comparten el símbolo). Razón doble:

1. **No malgastar:** una estrategia que declara `M:[8,20,200]` pero cuyas rules solo miran `M:20` no debe computar `M:8`/`M:200`.
2. **No sobre-excluir por frío:** si `M:200` está fría pero ninguna rule la usa, el símbolo no debe quedar fuera del scan. Construir solo lo referenciado acota la propagación de `FeatureNotReady` a lo que de verdad importa.

Esta unión se resuelve **una vez en `initialize()`** (junto a los thresholds), no por scan.

### 2.3 Firma de `Rule.evaluate` — el cambio de contrato central

```python
# Antes:  def evaluate(self, sd, thresholds) -> RuleResult
# Ahora:  def evaluate(self, snapshot) -> RuleResult
```

La rule **pierde el acceso a `sd` y a `thresholds`**. Estructuralmente ya no puede re-medir (no tiene `SymbolData`) ni re-bucketizar (no tiene cortes): solo lee `snapshot[tf][period].bucket`. La pureza pasa de convención a invariante de tipo.

### 2.4 Evidencia como proyección del snapshot

```python
def snapshot_evidence(
    snapshot: dict[str, dict[int, PositionResult]],
    series: Iterable[tuple[str, int]],
) -> dict:
    """Proyecta el snapshot al esquema de evidencia {tf:{period:{value,distance_pct,bucket}}}.
    Pura proyección — cero recompute."""
```

- `RuleResult.evidence` = proyección sobre las series de *esa* rule (se conserva el contrato T3, útil para "por qué falló esta rule").
- `ScanResult.sma_evidence` = proyección sobre la **unión** de series (Etapa 8). Ambas salen del mismo snapshot; ninguna recomputa.

---

## 3. Modelo long/short (simétrico, declarativo desde `direction`)

`PositionResult` ya es simétrico: `distance_pct` con signo, `side` derivado, y los 7 buckets espejan around `near`. La dirección **no entra en el cálculo** — entra solo en el **filtro** (qué buckets son "buenos").

**Opción elegida (la más simple): vocabulario canónico "above" + mirror en construcción.**

Las rules se autoran en vocabulario **largo/above** (canónico). `direction` → `side` (`long→"above"`, `short→"below"`) aplica `mirror_buckets` **una sola vez al construir la rule**. El `evaluate` resultante es **byte-idéntico** para largo y corto: solo cambia el set concreto de buckets permitidos.

```python
_MIRROR = {
    "extended_above": "extended_below",
    "above_strong":   "below_strong",
    "above_mild":     "below_mild",
    "near":           "near",            # autoespejo
    "below_mild":     "above_mild",
    "below_strong":   "above_strong",
    "extended_below": "extended_above",
}

def mirror_buckets(buckets: Iterable[str], side: str) -> frozenset[str]:
    """side=='above' → identidad; side=='below' → espejo. Biyección sobre los 7 buckets,
    así el resultado siempre ⊆ BUCKETS sin re-validar."""
```

Como `mirror_buckets` es biyección sobre los 7, funciona para cualquier subconjunto:
- `AboveSMA`: canónico `{above_mild, above_strong, extended_above}` → short `{below_mild, below_strong, extended_below}`.
- `NotExtended`: canónico `BUCKETS − {extended_above}` → short `BUCKETS − {extended_below}`.

**Descartado:** un parámetro `side` que la rule interprete en caliente (mete una rama por lado en el hot path), y duplicar `AboveSMA`/`BelowSMA` (la consigna pide simetría *sin* duplicar). El mirror-en-construcción no añade ramas al scan y mantiene una sola clase.

---

## 4. Reglas como filtros puros

Una sola clase genérica reemplaza `AboveSMA` y sirve de base a `NotExtended`:

```python
class SMAPositionRule:
    """Pasa si el bucket de CADA tf en `tfs` ∈ buckets_allowed (AND estricto)."""
    def __init__(self, period, tfs, buckets_allowed, side, required=True, label="SMA"):
        # 1) valida buckets_allowed canónicos ⊆ BUCKETS (fail-fast, como hoy T3)
        # 2) self.buckets_allowed = mirror_buckets(buckets_allowed, side)   # 1 vez
        ...
    @property
    def name(self) -> str:
        # label + side → "AboveSMA(20,W+M)" | "BelowSMA(20,W+M)" | "NotExtended(8,D)"
    def evaluate(self, snapshot) -> RuleResult:
        # for tf in self.tfs: pos = snapshot[tf][self.period]
        #   passed AND= pos.bucket in self.buckets_allowed
        # evidence = snapshot_evidence(snapshot, [(tf, self.period) for tf in self.tfs])
```

- **`AboveSMA`** queda como un caso de `SMAPositionRule` (`label="SMA"`, render `AboveSMA`/`BelowSMA` por `side`).
- **`NotExtended`** = **factory** que construye `SMAPositionRule(period, [tf], buckets_allowed=BUCKETS − {extended_above}, side, label="NotExtended")`. **Sin `max_pct`, sin threshold propio.** "No extendido" = "el bucket favorable-extremo está excluido"; el corte que define "extremo" es `bucket_thresholds.extended` de la estrategia (ya aplicado al bucketizar el snapshot). Esto es exactamente la propuesta 2 del rediseño ("excluir los buckets más alejados, no recalcular con otro umbral") y **supersede D4**.
- **Futuras rules** se expresan igual: un subconjunto canónico de buckets + el mirror. Sin recompute, sin `sd`.

`buckets_allowed` (qué buckets acepta una rule) **no es un threshold** — es composición de la rule, y se mantiene per-rule. Lo que se elimina es el override de *valores de corte* (`near/mild/extended`) por rule.

---

## 5. Tabla de análisis de cambios

| Cambio propuesto | ¿Merece? | Por qué | Impacto (archivos/tests) |
|---|---|---|---|
| Snapshot único `{tf:{period:PositionResult}}` 1×/símbolo·scan | **Sí** | Elimina recompute cuando ≥2 rules comparten `(tf,period)`; centraliza el seam de fríos en un punto en vez de disperso por rule | +`build_position_snapshot` en `features.py`; el pipeline (E7) lo construye. +tests de builder |
| `evaluate(snapshot)` en vez de `evaluate(sd, thresholds)` | **Sí** | Hace **estructuralmente imposible** re-medir/re-bucketizar (la rule ya no tiene `sd` ni cortes) | `rules.py` firma; migrar los 8 tests T3 (construir snapshot del stub y pasarlo) |
| Generalizar `AboveSMA` a `SMAPositionRule` side-aware con mirror en construcción | **Sí** | Simetría long/short sin duplicar reglas; `evaluate` idéntico ambos lados; cero ramas en hot path | rename de clase en `rules.py`; tests T3 añaden `side="above"` |
| `NotExtended` = factory que excluye bucket favorable-extremo, **sin `max_pct`** | **Sí** (supersede D4) | Unifica bajo el filtro genérico; elimina el override de umbral por-regla; "no extendido" = exclusión de bucket | T4 se implementa así (aún no escrito → sin migración, solo nueva forma) |
| Eliminar `max_extension_pct` de `strategies.json` | **Sí** | Redundante con `bucket_thresholds.extended` (hoy ambos = 0.10); el corte "extendido" es único y compartido | −1 línea × 4 estrategias en `config/strategies.json`; ningún consumidor aún |
| `mirror_buckets(side)` + mapa `_MIRROR` | **Sí** | Una función concentra toda la simetría; biyección ⇒ no re-valida | +pequeña en `features.py`; +test de simetría (near autoespejo, doble-mirror = identidad) |
| `series` del snapshot = referenciadas por rules, no `sd.declared` | **Sí** | Evita computar SMAs que ninguna rule usa y evita sobre-excluir por frío en ellas | el builder recibe `series` explícito; se resuelve 1× en `initialize()` |
| Evidencia per-rule = proyección del snapshot | **Sí** | Mantiene el contrato `RuleResult` (T3) con cero recompute | `rules.py` usa `snapshot_evidence` |
| Wrapper `PositionSnapshot` (clase) vs dict plano | **No** | El dict anidado basta y es la misma forma que la evidencia; un wrapper añade ceremonia. La validación `series ⊆ declared` va al pipeline (config-time, fail-fast), no al hot path | Se recomienda **dict plano**; sin archivo nuevo |
| Compartir un snapshot entre estrategias del mismo símbolo | **No** (en V1) | Requiere `thresholds` + `series` idénticos; en V1 long/short usan universos disjuntos (`swing_advances` vs `swing_declines`) → sin solape de símbolos. Optimización prematura | Ninguno ahora; nota para Fase 2 |
| Pasar `direction`/`side` por rule en caliente | **No** | Mete una rama por lado en el scan; el mirror-en-construcción lo evita | — |

---

## 6. Conserva / Modifica / Elimina (por componente)

**Conserva tal cual (sin tocar):**
- `PositionResult` (frozen, `side` derivado) — ya simétrico, sirve a ambos lados sin cambios.
- `_bucketize` + tabla de 7 buckets + invariante de frontera (T1.3).
- `position_vs_sma` — primitivo per-serie; el builder lo envuelve en un loop.
- `FeatureNotReady` — contrato de fríos (ahora aflora en el builder, un solo punto).
- `resolve_bucket_thresholds` (T2.2), `BUCKETS`, `DEFAULT_BUCKET_THRESHOLDS`.
- `RuleResult` (campos `passed/evidence/name/required`; no-frozen por D-T3.4).
- Plan de `ScanResult` (T6: `rules_passed_count`, `sma_evidence`) — sigue válido sin cambios.

**Modifica:**
- `AboveSMA` → `SMAPositionRule` genérica side-aware; firma `evaluate(snapshot)`.
- Evidencia: proyección del snapshot (`snapshot_evidence`), ya no recompute vía `position_vs_sma`.
- `config/strategies.json`: quita `max_extension_pct`; `direction` (ya presente) pasa a gobernar el mirror.

**Añade:**
- `build_position_snapshot` (L3).
- `mirror_buckets` + `_MIRROR` (L3).
- `snapshot_evidence` (L3).

**Elimina:**
- `NotExtended` como **clase con `max_pct`** (D4) → factory sin threshold.
- `max_extension_pct` de la config.
- El concepto de **override de umbral por-regla** (D4 queda obsoleto en esa parte).

### Qué de D4 queda obsoleto (explícito)

D4 decía: *"`NotExtended(period, tf, max_pct)` … mantiene `max_pct` como el `extended` efectivo de esa evaluación (se inyecta como override de `thresholds["extended"]` para esa rule)."*
→ **Obsoleto:** el parámetro `max_pct` y la inyección de `thresholds["extended"]` por-regla. **Se conserva** de D4 la idea de que `NotExtended` es *composición* sobre el filtro de buckets (no subclase) — solo que ahora sin umbral propio: excluye el bucket favorable-extremo, cuyo corte es el `extended` único de la estrategia.

---

## 7. Impacto en V1 (swing/EOD) y migración de tests

**Equivalencia observable — sí, con una condición que hoy se cumple:**

| Aspecto | Antes | Después | ¿Equivalente? |
|---|---|---|---|
| Corte de `NotExtended(8,D)` | `max_extension_pct=0.10` | `bucket_thresholds.extended=0.10` (excluye `extended_above` ≥ 0.10) | **Sí** — mismo corte 0.10 |
| Filtrado de `AboveSMA` | `buckets_allowed` | igual `buckets_allowed` (canónico) | **Sí** |
| Esquema de `evidence` | `{value,distance_pct,bucket}` | idéntico (proyección) | **Sí** |
| `ScanResult` | `rules_passed_count` + `sma_evidence` | sin cambios | **Sí** |

⚠️ **Condición:** la equivalencia se sostiene porque en la config actual `max_extension_pct == bucket_thresholds.extended` (ambos 0.10) en las 4 estrategias. Si alguna tuviera `max_extension_pct ≠ extended`, unificarlos **sería** un cambio semántico que requeriría decisión explícita. **Ninguna lo tiene** → migración limpia.

**Migración de tests:**
- **T3 (`AboveSMA`, 8 tests):** cambio mecánico — construir el snapshot desde el stub (`build_position_snapshot(stub, series, thresholds)`) y llamar `evaluate(snapshot)` en vez de `evaluate(sd, thresholds)`; añadir `side="above"`. El stub multi-tf de `test_rules.py` (D-T3.5) sirve igual.
- **T4 (`NotExtended`):** aún no escrito → se implementa directamente contra la factory nueva (sin `max_pct`). El criterio de aceptación de T4 cambia: "falla en `extended_above`, pasa en `above_strong`" sigue válido, pero el "caso con `max_pct` distinto del global" **se elimina** (ya no existe `max_pct`); se reemplaza por "un segundo `bucket_thresholds.extended` mueve el corte de NotExtended" (demuestra que el único umbral manda).
- **Tests nuevos:** `build_position_snapshot` (cálculo único, propagación de frío, `series` ⊊ declared no sobre-excluye), `mirror_buckets` (near autoespejo, doble-mirror = identidad), rule short (el mirror produce los buckets `below_*` correctos), `snapshot_evidence` (proyección exacta).

**Done-when de Etapa 6 afectados:** la línea de `NotExtended` y la de "AboveSMA/NotExtended con evidencia" se reinterpretan bajo este diseño; el formateador de log (T5) y `ScanResult` (T6) no cambian.

---

## 8. Preparación intradía (2-min, Fase 2+) — confirma que escala

El diseño **no se rediseña** para intradía; escala por construcción:

- **Costo por barra:** reconstruir el snapshot es `|series|` lecturas O(1). Aun con 200 símbolos × ~7 series por cierre de barra de 2-min (~195 barras/día regular), el cuello no es CPU (coincide con ADR-004 §"Costo"). El snapshot se reconstruye fresco en cada trigger (las SMAs solo cambian al cierre de barra de todos modos).
- **`evaluate(snapshot)` no cambia:** mismas rules, mismos filtros; solo habrá más `series` y posiblemente un snapshot que lea la barra en curso.

**Pendiente para activarlo (NO ahora, fuera de alcance):**
1. **Variante "precio vivo":** un `build_position_snapshot(..., use_working_bar=True)` o un `position_vs_sma_live` que lea `working_bar` en vez de la barra cerrada (ADR-004 §2). El builder actual lee la barra consolidada cerrada — correcto para swing.
2. **Timeframes intradía en L2:** `SymbolData` hoy solo soporta la cadena daily→W/M (lanza para `source_resolution != "daily"`, ver [symbol_data.py:38](../../trade-scanner/core/symbol_data.py#L38)). Añadir consolidators 1/5/15-min es el bloqueante real — **no las rules**.
3. **Trigger en L5:** handler del consolidator del marco de decisión (ya cubierto por ADR-004).

Las rules y el snapshot quedan listos; lo intradía es L2 (timeframes) + L5 (trigger) + una feature que lea la barra parcial.

---

## 9. Riesgos y decisiones abiertas

1. **Dónde vive la composición de rules** (lista de rules + `buckets_allowed` por rule por estrategia): ¿bloque en `strategies.json` o módulo declarativo en `strategies/`? Este ADR no lo fija (es Etapa 7), pero exige que **el `direction`→`side` se resuelva en un solo punto central** (el pipeline en `initialize()`), no esparcido. Recomendación: módulo `strategies/` que lee `direction` de config.
2. **Inclusión de `near` en `AboveSMA`:** ¿"above" incluye el bucket `near` (banda ±near alrededor de la SMA) o exige estar estrictamente por encima? Es parámetro de composición (`buckets_allowed`) — decidir en Etapa 7 / calibrar en Etapa 9. No afecta a este diseño.
3. **Rename de clase `AboveSMA` → `SMAPositionRule`:** churn en los 8 tests T3. Alternativa de menor cambio: conservar el nombre `AboveSMA` como clase y solo añadir `side` + render `BelowSMA` en `name`. Recomendación: renombrar (la clase ya no es "above"), pero es reversible si se prefiere minimizar diff.
4. **Snapshot per (símbolo, estrategia) vs per símbolo:** lógicamente per-estrategia (thresholds/series pueden diferir). "Una evaluación por símbolo y scan" se cumple *dentro* de una estrategia. Compartir entre estrategias es optimización futura gateada en `(thresholds, series)` idénticos — innecesaria en V1 (universos disjuntos).

---

## 10. Decisión (aprobada 2026-06-14)

Aprobado en bloque; se implementa en [Etapa 6B](../fase-1-desarrollo-local/etapa-06b.md):
- [x] Snapshot único `{tf:{period:PositionResult}}` + `build_position_snapshot` (L3). → 6B/T1
- [x] `evaluate(snapshot)` (rules sin `sd` ni `thresholds`). → 6B/T3
- [x] `SMAPositionRule` genérica + `mirror_buckets` (long/short canónico-above). → 6B/T2,T3
- [x] `NotExtended` sin `max_pct` (excluye bucket favorable-extremo) — **supersede D4**. → 6B/T4
- [x] Eliminar `max_extension_pct` de `config/strategies.json`. → 6B/T5
- [x] **Rename aprobado** `AboveSMA`→`SMAPositionRule` (conservando `AboveSMA` como factory `side="above"`, decisión final en 6B/T3.2). Ubicación de la composición de rules → Etapa 7.

exec
/bin/zsh -lc "sed -n '1,240p' .claude/decisions/ADR-002-qc-module-auth-constraint.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# ADR-002 — Constraint de autenticación QC para módulos de brokerage

**Estado:** aceptado  
**Fecha:** 2026-06-11  
**Supersede a:** —  
**Supersedido por:** —

---

## Contexto

Durante la Etapa 1 se investigó si la ausencia de credenciales de QuantConnect (QC) afecta alguna etapa del plan. La investigación se hizo leyendo el código fuente del LEAN CLI v1.0.225.

### Mecanismo de módulos del CLI

`lean live` y `lean data download` usan un sistema de módulos NuGet. Para cada brokerage/data-provider con `"installs": true` en `modules-1.14.json`, el CLI llama:

```
POST modules/list   { productId, organizationId }   → lista de paquetes NuGet
POST modules/read   { productId, organizationId }   → link de descarga
```

Ambas llamadas requieren credenciales QC válidas **y** que la organización tenga licencia para el módulo. El check es **server-side**; el CLI no lo valida localmente.

### Hallazgo sobre AlpacaBrokerage

```json
{
  "id": "AlpacaBrokerage",
  "installs": true,
  "minimum-seat": "Researcher",
  "product-id": "347",
  "platform": ["cloud", "local", "cli"]
}
```

- `installs: true` → el CLI intenta descargar el módulo antes de arrancar el engine.
- `minimum-seat: "Researcher"` → requiere al menos el plan Researcher de QC (de pago). El CLI almacena este valor pero **no lo verifica localmente**; el servidor lo rechaza si la org no tiene esa suscripción.

### Hallazgo sobre `lean backtest`

`lean backtest` también llama `ensure_module_installed()`, pero para el data provider por defecto (`Local`, `DefaultDataProvider`) el flag `installs` es `False`. Por eso los backtests con datos locales **no necesitan credenciales QC**.

---

## Comandos afectados vs. no afectados

| Comando | Necesita QC auth | Motivo |
|---|---|---|
| `lean backtest "trade-scanner"` (data local) | ❌ No | `DefaultDataProvider` → `installs: false` |
| `lean project-create` | ❌ No | Operación local |
| `pytest` en Docker | ❌ No | Sin CLI, sin módulos |
| `lean live "trade-scanner"` con Alpaca | ✅ Sí | `AlpacaBrokerage` → `installs: true` |
| `lean data download` con Alpaca | ✅ Sí | mismo mecanismo de módulos |

**Impacto por etapa:**
- Etapas 2–8: no afectadas (todo corre vía `lean backtest` con data local).
- **Etapa 9: bloqueada** en `lean live` y en `lean data download` si no se resuelve antes.

---

## Opciones para Etapa 9

### Opción A — Suscripción QC Researcher (pago)
Contratar el plan mínimo de QC que incluye el módulo de Alpaca. El CLI descarga el .dll automáticamente.

**Pro:** sin trabajo extra, flujo estándar.  
**Contra:** costo mensual recurrente; no alineado con el objetivo "$0/mes en Fase 1" de SPECS §7.

### Opción B — Compilar e instalar el módulo manualmente ($0)
El brokerage de Alpaca para LEAN es open source (`QuantConnect/Lean.Brokerages.Alpaca`). Se puede compilar el .dll y montarlo en el contenedor Docker con `--volume`, saltando el sistema de módulos del CLI.

**Pro:** $0; control total sobre la versión.  
**Contra:** requiere compilar C# (.NET SDK) y configurar el mount manualmente; más frágil ante actualizaciones del engine.

### Opción C — Script de descarga directa de datos desde Alpaca REST API ($0)
Para el problema de datos históricos (backtest 6–12 meses): escribir un script Python que use la API REST de Alpaca (accesible solo con la API key, sin QC) y genere archivos en el formato LEAN (`data/equity/usa/daily/<ticker>.zip`). Para `lean live`, combinar con Opción A o B.

**Pro:** $0 para datos históricos; usa las mismas credenciales Alpaca ya configuradas.  
**Contra:** requiere entender el formato interno de datos LEAN; no resuelve `lean live`.

---

## Decisión

**Diferida hasta el inicio de Etapa 9.** Las Etapas 2–8 no están bloqueadas. Antes de comenzar Etapa 9, elegir entre Opción A, B o C (o combinación) y actualizar este ADR con la elección.

La Opción C (script de datos) es independiente y puede implementarse antes de Etapa 9 si se necesitan datos históricos reales para backtests largos (Etapa 9, criterio "backtest 6–12 meses").

---

## Consecuencias inmediatas

- `lean init` también requería credenciales QC (para seleccionar organización). Se resolvió descargando `config.json` directamente del repo público de GitHub y aplicando la transformación `clean_lean_config` del CLI. Ver [etapa-01.md](../fase-1-desarrollo-local/etapa-01.md).
- Etapa 1 queda completable sin credenciales QC.
- El flag en Etapa 9 de PLAN.md apunta a este ADR.

---

## Revisión futura

Revisar si QC agrega un tier gratuito para módulos locales, o si el módulo de Alpaca pasa a estar incluido en la imagen Docker base (`quantconnect/lean`).

exec
/bin/zsh -lc "sed -n '1,260p' .claude/decisions/ADR-004-cadencia-evaluacion-intradia.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# ADR-004 — Cadencia de evaluación para reglas intradía (day trading)

**Estado:** propuesto (para Fase 2+; V1 es solo swing/EOD)
**Fecha:** 2026-06-13
**Supersede a:** —
**Supersedido por:** —

---

## Contexto

V1 del screener evalúa en horarios programados (`after_close`, `before_close_30m`) — una vez al día por estrategia (ver `main.py`, `ScheduledEvents` anclados a SPY). Las features (`position_vs_sma`) y rules (`AboveSMA`/`NotExtended`) leen estado ya calculado por `SymbolData`: `sma(tf, period).current.value` y `close(tf)`, costo **O(1) por serie**. Las SMAs W/M son estables intradía y la barra parcial del día se **excluye** a propósito (decisión de 5A: SMAs estables, deseado para swing).

Se planteó cómo cambia este panorama si en el futuro se agregan reglas de **day trading** (decisiones intradía sobre marcos de 1/5/15-min), y cuál es la cadencia óptima de evaluación: ¿cada minuto, cada N minutos, o en cada instante/tick?

Este ADR fija el criterio **antes** de implementarlo, para que la decisión no se tome ad-hoc cuando llegue Fase 2.

---

## Qué cambia con reglas intradía

1. **Timeframes intradía** — se añaden consolidators de 1/5/15-min. Implica suscripción `Resolution.MINUTE` y warmup más profundo (más barras). La profundidad de warmup ya se **deriva de config** (PLAN.md §4), así que escala sin hardcodeo.
2. **La barra parcial pasa a importar.** V1 excluye la barra en curso (SMAs estables intradía). Day trading necesita el precio *ahora* → leer `working_bar`/precio vivo, no solo la barra cerrada. Cambio semántico: una feature nueva (p. ej. `position_vs_sma_live`) o un parámetro que decida barra-cerrada vs barra-en-curso. **No** se modifica `position_vs_sma` actual (su contrato "SMA estable, barra cerrada" sigue siendo correcto para swing).
3. **Frecuencia de evaluación** — ya no 1×/día; hay que correr intradía.
4. **Datos** — Alpaca free = IEX + 15 min de delay → no apto para decisiones intradía reales. Es un límite de *datos*, no de arquitectura (ver [ADR-003](ADR-003-stooq-como-fuente-de-datos.md)).

Lo que **no** cambia: `position_vs_sma`/`AboveSMA`/`NotExtended` siguen siendo lecturas O(1) sobre `SymbolData`. Solo cambia el *trigger* de evaluación y, si la regla mira "precio ahora", la fuente del precio (barra parcial).

---

## Decisión

**Evaluar event-driven, en el cierre de barra del marco de decisión más pequeño que use la estrategia. Ni por tick/instante, ni por reloj arbitrario.**

Regla operativa: **una evaluación por barra de la señal.** Si la estrategia decide sobre barras de 5-min, se evalúa cuando consolida la barra de 5-min (handler del consolidator), no cada minuto ni cada tick.

### Por qué

| Cadencia | Veredicto | Motivo |
|---|---|---|
| **Cada instante / tick** | ❌ | No hay SMA nueva entre barras → trabajo tirado; el dato free es delayed/sampled igual; el costo escala con universo × frecuencia sin ganancia de señal |
| **Cada minuto fijo** | ⚠️ Solo si el marco de decisión es 1-min | Si se decide en 5-min, evaluar cada minuto repite 4 evaluaciones sin información nueva |
| **Event-driven en cierre de barra** | ✅ | Una evaluación por barra, alineada al dato; O(1) por serie como hoy; sin polling |

Fundamento: la **SMA no cambia entre barras**; lo único que se mueve dentro de la barra en curso es el precio de la barra parcial, que se captura al cierre de esa barra. Evaluar más fino que la barra de señal no aporta información.

---

## Encaje con lo implementado

- **Trigger:** hoy el scan se dispara con `ScheduledEvents` (time-based, 1×/día). Para intradía se cambia el *trigger* a un handler del consolidator del marco de N-min (evento en el cierre de barra), o a un `ScheduledEvent` cada N min **alineado** a la barra. La capa de orquestación (L5, `main.py`) es la única que cambia.
- **Features/rules:** sin cambios — siguen siendo lecturas O(1). Lo único nuevo sería una variante de feature que lea la barra parcial si la regla mira "precio ahora".
- **Config:** el marco de decisión y su periodo siguen declarándose en `config/strategies.json` (regla dura: nada de timeframes/cadencias hardcodeadas).

## Costo estimado (orden de magnitud)

Por evaluación: símbolos × tf × periodos lecturas+divisiones, todas O(1). Aun con 200 símbolos evaluados en cada cierre de barra de 5-min (~78 barras/día), el cuello de botella **no** es cómputo — es la **resolución/latencia del dato** y la semántica de la barra parcial.

---

## Consecuencias

- V1 (swing/EOD) **no se toca**: este ADR es para Fase 2+.
- Cuando se implemente day trading: cambiar solo el trigger en L5 + (si aplica) feature que lea barra parcial; reusar `position_vs_sma`/rules tal cual.
- Resolver antes la fuente de datos intradía (Alpaca free no sirve para decisiones reales por el delay de 15 min — ver ADR-003).

## Revisión futura

Revisar cuando: (a) se priorice una estrategia intradía en el roadmap, o (b) se consiga una fuente de datos intradía sin delay. En ese momento, confirmar el marco de decisión por estrategia y elegir trigger (consolidator handler vs scheduled alineado).

codex
La decisión propia de Etapa 4 confirma dos invariantes importantes: `UniverseSpec` no debe conocer `direction`, y la integración debía usar `get_parameter("env")` desde el `config.json` del proyecto. Voy a contrastar eso con la configuración versionada y con los CSVs que se siembran al ObjectStore.
exec
/bin/zsh -lc "sed -n '1,240p' docs/conceptos/factory-vs-composicion.md" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "sed -n '1,260p' docs/conceptos/buckets-y-simetria-largo-corto.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
# Buckets, filtros y simetría largo/corto

**Tipo:** explicación (modelo mental). No es un how-to ni un ADR — para *decisiones* ver
[ADR-005](../../.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).
**Código:** `core/features.py` (`BUCKETS`, `_bucketize`, `mirror_buckets`, `_MIRROR`,
`SIDE_BY_DIRECTION`, `resolve_bucket_thresholds`, `DEFAULT_BUCKET_THRESHOLDS`),
`core/rules.py` (`SMAPositionRule`).
**Config:** `config/strategies.json` → `storage/config/strategies.json` (ObjectStore).
**Spec:** `.claude/fase-1-desarrollo-local/etapa-06b.md` (D6B.1, D6B.4).

Este documento aclara una confusión natural: en el screener hay **dos cosas distintas** que
ambas se llaman "buckets", y la simetría largo/corto opera sobre una, no sobre la otra.
Entenderlo explica por qué `mirror_buckets` se prueba de forma exhaustiva.

---

## La escalera de los 7 buckets

La posición del precio respecto a una SMA se clasifica en una de 7 categorías ordenadas, de más
arriba a más abajo de la media (`core/features.py: BUCKETS`):

```
        extended_above     ← muy por encima de la SMA (≥ corte "extended")
        above_strong
        above_mild
  SMA → near               ← pegado a la media (autoespejo)
        below_mild
        below_strong
        extended_below     ← muy por debajo de la SMA
```

Los cortes (`near < mild < extended`) salen de `bucket_thresholds` de la estrategia
(`resolve_bucket_thresholds`), y `_bucketize(distance_pct, thresholds)` asigna el bucket a partir
de la distancia relativa `(close - sma) / sma`.

---

## Dónde se configuran los límites (thresholds)

Los límites de los buckets son los 3 cortes `near < mild < extended`. Se resuelven con
**precedencia de 3 niveles** (override de estrategia > global > defaults del código):

**1. Global — `config/strategies.json` (raíz del objeto):**
```json
"bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 }
```
Es la fuente versionada. `seed_object_store.sh` lo copia a `storage/config/strategies.json`, que el
algoritmo lee en runtime vía `self.object_store` (ObjectStore). **Nunca** con `open()` ni hardcodeado.

**2. Override por estrategia (opcional) — mismo archivo:**
```
strategies.<nombre>.bucket_thresholds   # gana CLAVE POR CLAVE sobre el global (merge poco profundo)
```
Hoy ninguna de las 4 estrategias define override.

**3. Defaults del código (última red) — `core/features.py`:**
```python
DEFAULT_BUCKET_THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}
```
Solo aplican si una clave falta tanto en el override como en el global.

La resolución vive en `resolve_bucket_thresholds(full_config, strategy_name)`: aplica la precedencia,
devuelve siempre las 3 claves y valida `0 < near < mild < extended` (único punto de control — no el
hot path `_bucketize`). El dict resuelto viaja a `build_position_snapshot → position_vs_sma → _bucketize`.

> **Convenciones.** Son **fracciones, no porcentajes** (`0.10` = 10%, no `10`). Los valores actuales
> son **placeholders**; la calibración real es **Etapa 9**. No confundir con `max_extension_pct` (clave
> redundante retirada en 6B/T5, D6B.8): el corte "extendido" único es `bucket_thresholds.extended`.

---

## Las dos cosas que se llaman "bucket"

### 1. La posición de la acción = UN bucket

Para un `(timeframe, period)` concreto, una acción cae en **exactamente un** bucket. Es el campo
`PositionResult.bucket` que guarda el snapshot:

```
AAPL, W, SMA20 → cierre +5% sobre la media → distance_pct = 0.05 → bucket = "above_strong"
```

No es un conjunto. Es un valor único por serie.

### 2. El filtro de la regla = un SUBCONJUNTO de buckets

`buckets_allowed` es **qué buckets considera aceptables una regla**. *Eso* sí es un subconjunto de
los 7, y lo decide quien compone la estrategia (Etapa 7) o la calibra (Etapa 9). Ejemplos:

```
AboveSMA estricto    → {above_mild, above_strong, extended_above}        (3 de 7)
AboveSMA con banda   → {near, above_mild, above_strong, extended_above}  (4 de 7)
NotExtended          → BUCKETS − {extended_above}                        (6 de 7)
```

La evaluación de una regla es simplemente: *¿el único bucket de la acción está dentro del
subconjunto permitido?*

```python
passed = snapshot[tf][period].bucket in self.buckets_allowed
#            └── UN bucket (la acción) ──┘    └── SUBCONJUNTO (la regla) ──┘
```

---

## La simetría largo/corto: el espejo actúa sobre el FILTRO

Una regla se escribe **una sola vez**, en vocabulario canónico "above" (largo). Para usarla en
corto no se duplica: `mirror_buckets(buckets_allowed, side)` traduce el **filtro** al lado pedido,
una vez, en construcción (D6B.4). `_MIRROR` es el espejo `above_* ↔ below_*` con `near` autoespejo.

**Largo** — `AboveSMA(20, [W])`, `side="above"` → espejo = identidad:

```
buckets_allowed = {above_mild, above_strong, extended_above}
AAPL bucket "above_strong" ∈ permitido  → PASA ✅
```

**Corto** — la *misma* regla canónica, `side="below"`:

```
mirror_buckets({above_mild, above_strong, extended_above}, "below")
    = {below_mild, below_strong, extended_below}

TSLA cotiza −5% bajo su SMA20 → bucket "below_strong" ∈ permitido  → PASA ✅ (corto válido)
una acción por encima de su media → "above_strong" ∉ {below_*}     → NO PASA ✅
```

> El espejo transforma el **conjunto permitido de la regla**, no el bucket de la acción. La acción
> siempre tiene un solo bucket; lo que cambia entre largo y corto es contra qué conjunto se compara.

`SIDE_BY_DIRECTION = {"long": "above", "short": "below"}` es la única fuente de la traducción
`direction → side` que lee la config (su uso real es de Etapa 7).

---

## Por qué `mirror_buckets` se prueba con los 128 subconjuntos

`buckets_allowed` es un **parámetro libre**: aún no sabemos qué subconjuntos usarán las estrategias
futuras (composición en Etapa 7, calibración en Etapa 9 — incluido si `near` entra o no en la
banda). El espejo debe ser correcto para **cualquier filtro posible**, no solo los 2-3 de hoy.

El conjunto potencia de 7 elementos tiene **2⁷ = 128** subconjuntos (cada bucket *está* o *no está*;
7 decisiones binarias; incluye el vacío y el total). El test recorre los 128 × 2 lados y verifica:

- **identidad** en `"above"` (no toca el filtro canónico),
- **involución**: espejar dos veces devuelve el original (`below ∘ below = id`) → traducir
  largo↔corto es reversible y limpio,
- **cierre**: el filtro espejado siempre queda ⊆ `BUCKETS` → la regla nunca termina con un bucket
  imposible que ningún snapshot podría igualar.

Bugs típicos —*"optimicé el espejo a un `if` y olvidé `near`"*, o un espejo no biyectivo que saca un
bucket fuera de la escalera— **solo se manifiestan en ciertos subconjuntos**. Probar el espacio
completo (barato: 128×2 casos en milisegundos) los blinda contra refactors futuros.

---

## Resumen en una frase

> La acción cae en **un** bucket; la regla permite un **conjunto** de buckets; el espejo transforma
> ese conjunto para reusar la misma regla en corto. Como el conjunto puede ser cualquiera de los
> 128, lo verificamos entero.

 succeeded in 0ms:
# Cápsula: factory vs composición

**Tipo:** material de estudio (cápsula breve). Para entender un patrón con ejemplos reales del proyecto.
**Relacionado:** [buckets-y-simetria-largo-corto.md](buckets-y-simetria-largo-corto.md),
[ADR-005](../../.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md),
`etapa-06b.md` (D6B.5 `SMAPositionRule`, D6B.6 `NotExtended`).

---

## La idea en una frase

- **Composición** = construir comportamiento **combinando/configurando** objetos, en vez de heredar (subclasear).
- **Factory** (constructor con nombre) = una función que **arma y devuelve** un objeto ya configurado, encapsulando el *cómo se construye*.

No son opuestos. De hecho, en este proyecto **usamos un factory para expresar composición**.

---

## Composición vs herencia (el eje de verdad)

Tenemos UNA clase genérica de regla, `SMAPositionRule`. La regla "no extendido" **no** es una
subclase nueva: es esa misma clase **configurada** de cierta forma.

```python
# COMPOSICIÓN vía factory: NotExtended ES un SMAPositionRule configurado, no una subclase.
def NotExtended(period, tf, side, required=True):
    return SMAPositionRule(
        period, [tf],
        buckets_allowed=set(BUCKETS) - {"extended_above"},  # ← el concepto, encapsulado
        side, required, label="NotExtended",
    )
```

La alternativa con **herencia** sería `class NotExtended(SMAPositionRule): ...`: más rígida, acoplada
a los detalles de la base, y multiplicaría clases (`NotExtended`, `AboveSMA`, `BelowSMA`…). La
composición mantiene **una sola clase** y muchas configuraciones con nombre. Por eso el proyecto
prefiere composición (ADR-005): reglas = *composición declarativa*, no jerarquías de clases.

---

## ¿Cuándo un factory "se gana" su nombre?

Regla práctica:

- ✅ **Encapsula conocimiento** que el llamador tendría que reproducir → vale.
  `NotExtended` calcula *qué* buckets son "no extendido" (`BUCKETS − {extended_above}`); el llamador
  no repite esa aritmética ni puede equivocarse.
- ❌ **Solo renombra o precarga** un parámetro sin añadir significado → es un **alias** vacío; mejor
  llamar al constructor directo.
  Por eso **NO** conservamos `AboveSMA` como factory: solo precargaba `side="above"` —
  `SMAPositionRule(..., side="above")` ya lo dice, y el alias escondía justo el dato útil (la dirección).

> La línea: **¿el nombre aporta semántica, o solo esconde un argumento?** Si aporta → factory con nombre.
> Si solo esconde → alias innecesario.

**Cuidado con la proliferación:** crea un constructor con nombre solo si el concepto (a) se reusa y
(b) su construcción no es obvia. Si no, vuelves a un zoo de nombres (`NearSMA`, `FarBelow`…).

---

## Glosario (términos poco comunes)

- **Composición** — diseñar combinando objetos/funciones configurables en vez de heredar. *Favorece
  composición sobre herencia* es un principio clásico de diseño OO.
- **Herencia (inheritance)** — extender una clase base con subclases (`class Hijo(Base)`). Potente pero
  acopla el hijo a los detalles del padre; fácil de sobreusar.
- **Factory / constructor con nombre** — función que crea y devuelve un objeto ya configurado.
  Encapsula el "cómo se arma". Ej.: `NotExtended(...)`.
- **Alias** — un segundo nombre para lo mismo, sin comportamiento nuevo. Si un "factory" es solo un
  alias, normalmente sobra. Ej. rechazado: `AboveSMA` como `SMAPositionRule(side="above")`.
- **Guard** — una regla/condición cuyo propósito es **bloquear** un caso no deseado, no seleccionar uno
  bueno. Ej.: `NotExtended` actúa de guard ("no persigas algo ya disparado por encima de la media").
- **Fail-fast** — validar y **reventar en construcción** (no en caliente) ante una entrada inválida.
  Ej.: `SMAPositionRule` valida `buckets_allowed ⊆ BUCKETS` al crearse, no durante el scan.
- **Hot path** — el código que corre muchísimas veces (por símbolo × timeframe × scan). Se evita
  trabajo y validaciones ahí. Ej.: `_bucketize` es hot path; la validación de thresholds vive fuera.
- **Boilerplate** — código repetitivo y mecánico sin valor conceptual. Un buen factory lo elimina
  (centraliza la aritmética de buckets en un solo sitio).
- **Syntactic sugar ("azúcar")** — sintaxis más cómoda que no añade capacidad, solo legibilidad. Un
  alias es azúcar; un factory que encapsula un concepto es **más** que azúcar.
- **DRY (Don't Repeat Yourself)** — no duplicar conocimiento. Ojo: DRY es sobre *conceptos*, no sobre
  *parámetros*; precargar un argumento (alias) no es la repetición que DRY busca evitar.
- **Preset** — una configuración con nombre lista para usar. Otra forma de leer `NotExtended`: un preset
  de `SMAPositionRule`.

---

## En una línea para recordar

> Usa **composición** (una clase, muchas configuraciones) y dale **nombre con un factory** solo cuando
> ese nombre **encapsula un concepto**; si el nombre solo esconde un parámetro, es un alias y sobra.

exec
/bin/zsh -lc 'nl -ba config/strategies.json' in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'nl -ba trade-scanner/config.json' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	{
     2	    "algorithm-language": "Python",
     3	    "parameters": {"env": "dev"},
     4	    "description": "",
     5	    "local-id": 644490384
     6	}

 succeeded in 0ms:
     1	{
     2	  "bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 },
     3	  "environments": {
     4	    "dev":  {
     5	      "top_n": 2,
     6	      "max_universe": 4,
     7	      "universe": "sample_dev",
     8	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20, 200] },
     9	      "warmup_budget": { "daily": 4300 },
    10	      "validate_warmup": true,
    11	      "sma_validation": true
    12	    },
    13	    "prod": {
    14	      "top_n": 50,
    15	      "max_universe": 200,
    16	      "warmup_budget": { "daily": 1100 }
    17	    }
    18	  },
    19	  "strategies": {
    20	    "swing_eod": {
    21	      "universe": "swing_advances",
    22	      "direction": "long",
    23	      "main_timeframe": "W",
    24	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    25	      "schedule": "after_close",
    26	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    27	    },
    28	    "swing_eod_short": {
    29	      "universe": "swing_declines",
    30	      "direction": "short",
    31	      "main_timeframe": "W",
    32	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    33	      "schedule": "after_close",
    34	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    35	    },
    36	    "market_close": {
    37	      "universe": "swing_advances",
    38	      "direction": "long",
    39	      "main_timeframe": "W",
    40	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    41	      "schedule": "before_close_30m",
    42	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    43	    },
    44	    "market_close_short": {
    45	      "universe": "swing_declines",
    46	      "direction": "short",
    47	      "main_timeframe": "W",
    48	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    49	      "schedule": "before_close_30m",
    50	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    51	    }
    52	  }
    53	}

exec
/bin/zsh -lc 'nl -ba scripts/seed_object_store.sh' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	# seed_object_store.sh — Siembra config y universos al ObjectStore local.
     3	#
     4	# POR QUÉ: la config de estrategias y los CSVs de universo viven en config/ y
     5	#   data/object-store/ respectivamente, y se leen en runtime vía self.object_store.
     6	#   El ObjectStore local del CLI es <workspace>/storage/ (montado en /Storage dentro
     7	#   de Docker). Ver PLAN.md §4 y CLAUDE.md (gotchas Etapa 2).
     8	#
     9	# QUÉ HACE:
    10	#   1. config/*.json   → storage/config/   (idempotente, siempre)
    11	#   2. data/object-store/*-advances-*.csv más reciente (no en processed/)
    12	#      → storage/universes/swing_advances.csv + mueve fuente a processed/
    13	#   3. data/object-store/*-declines-*.csv más reciente (no en processed/)
    14	#      → storage/universes/swing_declines.csv + mueve fuente a processed/
    15	#   4. universes/*.csv fixtures estáticos (ej. sample_dev) → storage/universes/
    16	#      (cp directo, idempotente; versionados, sin lógica de processed/)
    17	#
    18	# Si no hay archivos nuevos (todos ya en processed/), avisa pero no falla:
    19	#   el archivo previo en storage/universes/ permanece intacto.
    20	#
    21	# IDEMPOTENTE para config: cp sobrescribe. Para universos: un archivo fuente
    22	#   se procesa una sola vez (luego vive en processed/).
    23	
    24	set -euo pipefail
    25	
    26	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    27	WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
    28	SRC_CONFIG="$WORKSPACE/config"
    29	SRC_UNIVERSES="$WORKSPACE/universes"
    30	DATA_DIR="$WORKSPACE/data/object-store"
    31	PROCESSED_DIR="$DATA_DIR/processed"
    32	DEST="$WORKSPACE/storage"
    33	
    34	echo "Sembrando ObjectStore local ($DEST)"
    35	echo ""
    36	
    37	# --- 1. config/*.json → storage/config/ ---
    38	mkdir -p "$DEST/config"
    39	for f in "$SRC_CONFIG"/*.json; do
    40	  cp "$f" "$DEST/config/$(basename "$f")"
    41	  echo "  [config] $(basename "$f") → config/$(basename "$f")"
    42	done
    43	
    44	echo ""
    45	
    46	# --- 2 & 3. CSVs de universo ---
    47	mkdir -p "$DEST/universes"
    48	mkdir -p "$PROCESSED_DIR"
    49	
    50	seed_universe() {
    51	  local type="$1"       # "advances" o "declines"
    52	  local dest_key="$2"   # "swing_advances" o "swing_declines"
    53	
    54	  # Seleccionar el CSV más reciente no archivado (sort por nombre = sort por fecha en el nombre).
    55	  # find en lugar de ls+glob para que set -eo pipefail no aborte cuando no hay archivos.
    56	  local src
    57	  src=$(find "$DATA_DIR" -maxdepth 1 -name "*-${type}-*.csv" 2>/dev/null | sort | tail -1)
    58	
    59	  if [[ -z "$src" ]]; then
    60	    echo "  [universos] ADVERTENCIA: no hay archivos *-${type}-*.csv en $DATA_DIR"
    61	    if [[ -f "$DEST/universes/${dest_key}.csv" ]]; then
    62	      echo "  [universos] Usando archivo previo en storage/universes/${dest_key}.csv (sin cambios)"
    63	    else
    64	      echo "  [universos] No existe archivo previo en storage/universes/${dest_key}.csv"
    65	    fi
    66	    return 0
    67	  fi
    68	
    69	  local filename
    70	  filename="$(basename "$src")"
    71	  local lines
    72	  lines=$(wc -l < "$src")
    73	
    74	  cp "$src" "$DEST/universes/${dest_key}.csv"
    75	  mv "$src" "$PROCESSED_DIR/$filename"
    76	
    77	  echo "  [universos] $filename → universes/${dest_key}.csv ($lines líneas) → archivado en processed/"
    78	}
    79	
    80	seed_universe "advances" "swing_advances"
    81	seed_universe "declines" "swing_declines"
    82	
    83	# --- 4. Fixtures estáticos versionados (universes/*.csv) → storage/universes/ ---
    84	if [[ -d "$SRC_UNIVERSES" ]]; then
    85	  shopt -s nullglob
    86	  for f in "$SRC_UNIVERSES"/*.csv; do
    87	    cp "$f" "$DEST/universes/$(basename "$f")"
    88	    echo "  [universos] $(basename "$f") → universes/$(basename "$f") (fixture estático)"
    89	  done
    90	  shopt -u nullglob
    91	fi
    92	
    93	echo ""
    94	echo "Listo."

exec
/bin/zsh -lc 'nl -ba lean.json' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	{
     2	    "data-folder": "data",
     3	    "organization-id": "00000000000000000000000000000000",
     4	    "log-handler": "QuantConnect.Logging.CompositeLogHandler",
     5	    "messaging-handler": "QuantConnect.Messaging.Messaging",
     6	    "job-queue-handler": "QuantConnect.Queues.JobQueue",
     7	    "api-handler": "QuantConnect.Api.Api",
     8	    "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
     9	    "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
    10	    "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
    11	    "data-channel-provider": "DataChannelProvider",
    12	    "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
    13	    "data-aggregator": "QuantConnect.Lean.Engine.DataFeeds.AggregationManager",
    14	    "symbol-minute-limit": 10000,
    15	    "symbol-second-limit": 10000,
    16	    "symbol-tick-limit": 10000,
    17	    "seed-lookback-period": 5,
    18	    "seed-retry-minute-lookback-period": 1440,
    19	    "seed-retry-hour-lookback-period": 24,
    20	    "seed-retry-daily-lookback-period": 10,
    21	    "ignore-unknown-asset-holdings": true,
    22	    "show-missing-data-logs": false,
    23	    "maximum-warmup-history-days-look-back": 5,
    24	    "maximum-data-points-per-chart-series": 1000000,
    25	    "maximum-chart-series": 30,
    26	    "force-exchange-always-open": false,
    27	    "transaction-log": "",
    28	    "reserved-words-prefix": "@",
    29	    "live-data-url": "ws://www.quantconnect.com/api/v2/live/data/",
    30	    "live-data-port": 8020,
    31	    "live-cash-balance": "",
    32	    "live-holdings": "[]",
    33	    "ib-account": "",
    34	    "ib-user-name": "",
    35	    "ib-password": "",
    36	    "ib-agent-description": "Individual",
    37	    "ib-trading-mode": "paper",
    38	    "ib-enable-delayed-streaming-data": false,
    39	    "ib-weekly-restart-utc-time": "22:00:00",
    40	    "ib-financial-advisors-group-filter": "",
    41	    "tradier-environment": "paper",
    42	    "tradier-account-id": "",
    43	    "tradier-access-token": "",
    44	    "oanda-environment": "Practice",
    45	    "oanda-access-token": "",
    46	    "oanda-account-id": "",
    47	    "fxcm-server": "http://www.fxcorporate.com/Hosts.jsp",
    48	    "fxcm-terminal": "Demo",
    49	    "fxcm-user-name": "",
    50	    "fxcm-password": "",
    51	    "fxcm-account-id": "",
    52	    "iqfeed-iqconnect": "C:/Program Files (x86)/DTN/IQFeed/iqconnect.exe",
    53	    "iqfeed-username": "",
    54	    "iqfeed-password": "",
    55	    "iqfeed-productName": "",
    56	    "iqfeed-version": "1.0",
    57	    "coinbase-rest-api": "https://api.coinbase.com",
    58	    "coinbase-url": "wss://advanced-trade-ws.coinbase.com",
    59	    "coinbase-api-key": "",
    60	    "coinbase-api-secret": "",
    61	    "bitfinex-api-secret": "",
    62	    "bitfinex-api-key": "",
    63	    "binance-api-secret": "",
    64	    "binance-api-key": "",
    65	    "binance-api-url": "https://api.binance.com",
    66	    "binance-websocket-url": "wss://stream.binance.com:9443/ws",
    67	    "binance-orders-websocket-url": "wss://ws-api.binance.com:9443/ws-api/v3",
    68	    "binance-fapi-url": "https://fapi.binance.com",
    69	    "binance-fwebsocket-url": "wss://fstream.binance.com/private/ws",
    70	    "binance-dapi-url": "https://dapi.binance.com",
    71	    "binance-dwebsocket-url": "wss://dstream.binance.com/ws",
    72	    "binanceus-api-secret": "",
    73	    "binanceus-api-key": "",
    74	    "binanceus-api-url": "https://api.binance.us",
    75	    "binanceus-websocket-url": "wss://stream.binance.us:9443/ws",
    76	    "bybit-api-secret": "",
    77	    "bybit-api-key": "",
    78	    "bybit-api-url": "https://api.bybit.com",
    79	    "bybit-websocket-url": "wss://stream.bybit.com",
    80	    "dydx-private-key-hex": "",
    81	    "dydx-address": "",
    82	    "dydx-subaccount-number": 0,
    83	    "dydx-node-api-rest": "https://dydx-ops-rest.kingnodes.com",
    84	    "dydx-node-api-grpc": "https://dydx-ops-grpc.kingnodes.com:443",
    85	    "dydx-indexer-api-rest": "https://indexer.dydx.trade/v4",
    86	    "dydx-indexer-api-wss": "wss://indexer.dydx.trade/v4/ws",
    87	    "dydx-chain-id": "dydx-mainnet-1",
    88	    "eze-api-address-url": "",
    89	    "eze-port": "",
    90	    "eze-domain": "",
    91	    "eze-locale": "",
    92	    "eze-password": "",
    93	    "eze-user-name": "",
    94	    "eze-trading-route": "",
    95	    "eze-trading-account": "",
    96	    "kraken-api-secret": "",
    97	    "kraken-api-key": "",
    98	    "kraken-verification-tier": "Starter",
    99	    "wolverine-host": "",
   100	    "wolverine-port": "",
   101	    "wolverine-account": "",
   102	    "wolverine-sender-comp-id": "",
   103	    "wolverine-target-comp-id": "",
   104	    "wolverine-on-behalf-of-comp-id": "",
   105	    "wolverine-log-fix-messages": false,
   106	    "rbi-host": "",
   107	    "rbi-port": "",
   108	    "rbi-account": "",
   109	    "rbi-sender-comp-id": "",
   110	    "rbi-target-comp-id": "",
   111	    "rbi-on-behalf-of-comp-id": "",
   112	    "rbi-log-fix-messages": false,
   113	    "tt-user-name": "",
   114	    "tt-session-password": "",
   115	    "tt-account-name": "",
   116	    "tt-rest-app-key": "",
   117	    "tt-rest-app-secret": "",
   118	    "tt-rest-environment": "",
   119	    "tt-market-data-sender-comp-id": "",
   120	    "tt-market-data-target-comp-id": "",
   121	    "tt-market-data-host": "",
   122	    "tt-market-data-port": "",
   123	    "tt-order-routing-sender-comp-id": "",
   124	    "tt-order-routing-target-comp-id": "",
   125	    "tt-order-routing-host": "",
   126	    "tt-order-routing-port": "",
   127	    "tt-log-fix-messages": false,
   128	    "trade-station-client-id": "",
   129	    "trade-station-client-secret": "",
   130	    "trade-station-redirect-url": "http://localhost",
   131	    "trade-station-refresh-token": "",
   132	    "trade-station-api-url": "https://sim-api.tradestation.com",
   133	    "trade-station-account-type": "Cash|Margin|Futures",
   134	    "trade-station-account-id": "",
   135	    "alpaca-api-key": "",
   136	    "alpaca-api-secret": "",
   137	    "alpaca-access-token": "",
   138	    "alpaca-paper-trading": true,
   139	    "charles-schwab-api-url": "https://api.schwabapi.com",
   140	    "charles-schwab-app-key": "",
   141	    "charles-schwab-secret": "",
   142	    "charles-schwab-account-number": "",
   143	    "charles-schwab-refresh-token": "",
   144	    "charles-schwab-authorization-code-from-url": "",
   145	    "charles-schwab-redirect-url": "",
   146	    "webull-api-url": "https://api.webull.com",
   147	    "webull-trade-grpc-url": "https://events-api.webull.com",
   148	    "webull-app-key": "",
   149	    "webull-app-secret": "",
   150	    "webull-account-id": "",
   151	    "tastytrade-api-url": "",
   152	    "tastytrade-websocket-url": "",
   153	    "tastytrade-username": "",
   154	    "tastytrade-password": "",
   155	    "tastytrade-account-number": "",
   156	    "exante-client-id": "",
   157	    "exante-application-id": "",
   158	    "exante-shared-key": "",
   159	    "exante-account-id": "",
   160	    "exante-platform-type": "",
   161	    "nasdaq-auth-token": "",
   162	    "tiingo-auth-token": "",
   163	    "us-energy-information-auth-token": "",
   164	    "iex-cloud-api-key": "",
   165	    "coinapi-api-key": "",
   166	    "coinapi-product": "free",
   167	    "polygon-api-key": "",
   168	    "zerodha-access-token": "",
   169	    "zerodha-api-key": "",
   170	    "zerodha-product-type": "MIS",
   171	    "zerodha-trading-segment": "EQUITY",
   172	    "zerodha-history-subscription": "false",
   173	    "samco-client-id": "",
   174	    "samco-client-password": "",
   175	    "samco-year-of-birth": "",
   176	    "samco-product-type": "MIS",
   177	    "samco-trading-segment": "EQUITY",
   178	    "ftx-account-tier": "Tier1",
   179	    "ftx-api-secret": "",
   180	    "ftx-api-key": "",
   181	    "ftxus-account-tier": "Tier1",
   182	    "ftxus-api-secret": "",
   183	    "ftxus-api-key": "",
   184	    "regression-test-languages": [
   185	        "CSharp",
   186	        "Python"
   187	    ],
   188	    "python-additional-paths": [],
   189	    "environments": {
   190	        "backtesting": {
   191	            "live-mode": false,
   192	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler",
   193	            "result-handler": "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
   194	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed",
   195	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
   196	            "history-provider": [
   197	                "QuantConnect.Lean.Engine.HistoricalData.SubscriptionDataReaderHistoryProvider"
   198	            ],
   199	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler"
   200	        },
   201	        "live-paper": {
   202	            "live-mode": true,
   203	            "live-mode-brokerage": "PaperBrokerage",
   204	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   205	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   206	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   207	            "data-queue-handler": [
   208	                "QuantConnect.Lean.Engine.DataFeeds.Queues.LiveDataQueue"
   209	            ],
   210	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   211	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler"
   212	        },
   213	        "live-zerodha": {
   214	            "live-mode": true,
   215	            "live-mode-brokerage": "ZerodhaBrokerage",
   216	            "data-queue-handler": [
   217	                "ZerodhaBrokerage"
   218	            ],
   219	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   220	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   221	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   222	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   223	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   224	            "history-provider": [
   225	                "BrokerageHistoryProvider",
   226	                "SubscriptionDataReaderHistoryProvider"
   227	            ]
   228	        },
   229	        "live-samco": {
   230	            "live-mode": true,
   231	            "live-mode-brokerage": "SamcoBrokerage",
   232	            "data-queue-handler": [
   233	                "SamcoBrokerage"
   234	            ],
   235	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   236	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   237	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   238	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   239	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   240	            "history-provider": [
   241	                "BrokerageHistoryProvider",
   242	                "SubscriptionDataReaderHistoryProvider"
   243	            ]
   244	        },
   245	        "live-tradier": {
   246	            "live-mode": true,
   247	            "tradier-save-tokens": true,
   248	            "live-mode-brokerage": "TradierBrokerage",
   249	            "data-queue-handler": [
   250	                "TradierBrokerage"
   251	            ],
   252	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   253	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   254	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   255	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   256	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   257	            "history-provider": [
   258	                "BrokerageHistoryProvider",
   259	                "SubscriptionDataReaderHistoryProvider"
   260	            ]
   261	        },
   262	        "live-interactive": {
   263	            "live-mode": true,
   264	            "live-mode-brokerage": "InteractiveBrokersBrokerage",
   265	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   266	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   267	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   268	            "data-queue-handler": [
   269	                "InteractiveBrokersBrokerage"
   270	            ],
   271	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   272	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   273	            "history-provider": [
   274	                "BrokerageHistoryProvider",
   275	                "SubscriptionDataReaderHistoryProvider"
   276	            ]
   277	        },
   278	        "live-interactive-iqfeed": {
   279	            "live-mode": true,
   280	            "live-mode-brokerage": "InteractiveBrokersBrokerage",
   281	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   282	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   283	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   284	            "data-queue-handler": [
   285	                "QuantConnect.IQFeed.IQFeedDataQueueHandler"
   286	            ],
   287	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   288	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   289	            "history-provider": [
   290	                "QuantConnect.IQFeed.IQFeedDataQueueHandler",
   291	                "SubscriptionDataReaderHistoryProvider"
   292	            ]
   293	        },
   294	        "live-fxcm": {
   295	            "live-mode": true,
   296	            "live-mode-brokerage": "FxcmBrokerage",
   297	            "data-queue-handler": [
   298	                "FxcmBrokerage"
   299	            ],
   300	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   301	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   302	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   303	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   304	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   305	            "history-provider": [
   306	                "BrokerageHistoryProvider",
   307	                "SubscriptionDataReaderHistoryProvider"
   308	            ]
   309	        },
   310	        "live-oanda": {
   311	            "live-mode": true,
   312	            "live-mode-brokerage": "OandaBrokerage",
   313	            "data-queue-handler": [
   314	                "OandaBrokerage"
   315	            ],
   316	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   317	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   318	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   319	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   320	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   321	            "history-provider": [
   322	                "BrokerageHistoryProvider",
   323	                "SubscriptionDataReaderHistoryProvider"
   324	            ]
   325	        },
   326	        "live-coinbase": {
   327	            "live-mode": true,
   328	            "live-mode-brokerage": "CoinbaseBrokerage",
   329	            "data-queue-handler": [
   330	                "CoinbaseBrokerage"
   331	            ],
   332	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   333	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   334	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   335	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   336	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   337	            "history-provider": [
   338	                "BrokerageHistoryProvider",
   339	                "SubscriptionDataReaderHistoryProvider"
   340	            ]
   341	        },
   342	        "live-bitfinex": {
   343	            "live-mode": true,
   344	            "live-mode-brokerage": "BitfinexBrokerage",
   345	            "data-queue-handler": [
   346	                "BitfinexBrokerage"
   347	            ],
   348	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   349	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   350	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   351	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   352	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   353	            "history-provider": [
   354	                "BrokerageHistoryProvider",
   355	                "SubscriptionDataReaderHistoryProvider"
   356	            ]
   357	        },
   358	        "live-binance": {
   359	            "live-mode": true,
   360	            "live-mode-brokerage": "BinanceBrokerage",
   361	            "data-queue-handler": [
   362	                "BinanceBrokerage"
   363	            ],
   364	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   365	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   366	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   367	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   368	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   369	            "history-provider": [
   370	                "BrokerageHistoryProvider",
   371	                "SubscriptionDataReaderHistoryProvider"
   372	            ]
   373	        },
   374	        "live-futures-binance": {
   375	            "live-mode": true,
   376	            "live-mode-brokerage": "BinanceFuturesBrokerage",
   377	            "data-queue-handler": [
   378	                "BinanceFuturesBrokerage"
   379	            ],
   380	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   381	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   382	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   383	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   384	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   385	            "history-provider": [
   386	                "BrokerageHistoryProvider",
   387	                "SubscriptionDataReaderHistoryProvider"
   388	            ]
   389	        },
   390	        "live-coin-futures-binance": {
   391	            "live-mode": true,
   392	            "live-mode-brokerage": "BinanceCoinFuturesBrokerage",
   393	            "data-queue-handler": [
   394	                "BinanceCoinFuturesBrokerage"
   395	            ],
   396	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   397	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   398	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   399	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   400	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   401	            "history-provider": [
   402	                "BrokerageHistoryProvider",
   403	                "SubscriptionDataReaderHistoryProvider"
   404	            ]
   405	        },
   406	        "live-binanceus": {
   407	            "live-mode": true,
   408	            "live-mode-brokerage": "BinanceUSBrokerage",
   409	            "data-queue-handler": [
   410	                "BinanceUSBrokerage"
   411	            ],
   412	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   413	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   414	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   415	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   416	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   417	            "history-provider": [
   418	                "BrokerageHistoryProvider",
   419	                "SubscriptionDataReaderHistoryProvider"
   420	            ]
   421	        },
   422	        "live-bybit": {
   423	            "live-mode": true,
   424	            "live-mode-brokerage": "BybitBrokerage",
   425	            "data-queue-handler": [
   426	                "BybitBrokerage"
   427	            ],
   428	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   429	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   430	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   431	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   432	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   433	            "history-provider": [
   434	                "BrokerageHistoryProvider",
   435	                "SubscriptionDataReaderHistoryProvider"
   436	            ]
   437	        },
   438	        "live-trade-station": {
   439	            "live-mode": true,
   440	            "live-mode-brokerage": "TradeStationBrokerage",
   441	            "data-queue-handler": [
   442	                "TradeStationBrokerage"
   443	            ],
   444	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   445	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   446	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   447	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   448	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   449	            "history-provider": [
   450	                "BrokerageHistoryProvider",
   451	                "SubscriptionDataReaderHistoryProvider"
   452	            ]
   453	        },
   454	        "live-alpaca": {
   455	            "live-mode": true,
   456	            "live-mode-brokerage": "AlpacaBrokerage",
   457	            "data-queue-handler": [
   458	                "AlpacaBrokerage"
   459	            ],
   460	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   461	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   462	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   463	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   464	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   465	            "history-provider": [
   466	                "BrokerageHistoryProvider",
   467	                "SubscriptionDataReaderHistoryProvider"
   468	            ]
   469	        },
   470	        "live-futures-bybit": {
   471	            "live-mode": true,
   472	            "live-mode-brokerage": "BybitFuturesBrokerage",
   473	            "data-queue-handler": [
   474	                "BybitFuturesBrokerage"
   475	            ],
   476	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   477	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   478	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   479	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   480	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   481	            "history-provider": [
   482	                "BrokerageHistoryProvider",
   483	                "SubscriptionDataReaderHistoryProvider"
   484	            ]
   485	        },
   486	        "live-trading-technologies": {
   487	            "live-mode": true,
   488	            "live-mode-brokerage": "TradingTechnologiesBrokerage",
   489	            "data-queue-handler": [
   490	                "TradingTechnologiesBrokerage"
   491	            ],
   492	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   493	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   494	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   495	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   496	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"
   497	        },
   498	        "live-kraken": {
   499	            "live-mode": true,
   500	            "live-mode-brokerage": "KrakenBrokerage",
   501	            "data-queue-handler": [
   502	                "KrakenBrokerage"
   503	            ],
   504	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   505	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   506	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   507	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   508	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   509	            "history-provider": [
   510	                "BrokerageHistoryProvider",
   511	                "SubscriptionDataReaderHistoryProvider"
   512	            ]
   513	        },
   514	        "live-ftx": {
   515	            "live-mode": true,
   516	            "live-mode-brokerage": "QuantConnect.FTXBrokerage.FTXBrokerage",
   517	            "data-queue-handler": [
   518	                "QuantConnect.FTXBrokerage.FTXBrokerage"
   519	            ],
   520	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   521	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   522	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   523	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   524	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   525	            "history-provider": [
   526	                "BrokerageHistoryProvider",
   527	                "SubscriptionDataReaderHistoryProvider"
   528	            ]
   529	        },
   530	        "live-exante": {
   531	            "live-mode": true,
   532	            "live-mode-brokerage": "QuantConnect.ExanteBrokerage.ExanteBrokerage",
   533	            "data-queue-handler": [
   534	                "QuantConnect.ExanteBrokerage.ExanteBrokerage"
   535	            ],
   536	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   537	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   538	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   539	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   540	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   541	            "history-provider": "BrokerageHistoryProvider"
   542	        },
   543	        "live-ftxus": {
   544	            "live-mode": true,
   545	            "live-mode-brokerage": "QuantConnect.FTXBrokerage.FTXUSBrokerage",
   546	            "data-queue-handler": [
   547	                "QuantConnect.FTXBrokerage.FTXUSBrokerage"
   548	            ],
   549	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   550	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   551	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   552	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   553	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   554	            "history-provider": [
   555	                "BrokerageHistoryProvider",
   556	                "SubscriptionDataReaderHistoryProvider"
   557	            ]
   558	        },
   559	        "live-wolverine": {
   560	            "live-mode": true,
   561	            "live-mode-brokerage": "WolverineBrokerage",
   562	            "history-provider": [
   563	                "SubscriptionDataReaderHistoryProvider"
   564	            ],
   565	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   566	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   567	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   568	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   569	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"
   570	        },
   571	        "live-charlesschwab": {
   572	            "live-mode": true,
   573	            "live-mode-brokerage": "CharlesSchwabBrokerage",
   574	            "data-queue-handler": [
   575	                "CharlesSchwabBrokerage"
   576	            ],
   577	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   578	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   579	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   580	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   581	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   582	            "history-provider": [
   583	                "BrokerageHistoryProvider",
   584	                "SubscriptionDataReaderHistoryProvider"
   585	            ]
   586	        },
   587	        "live-tastytrade": {
   588	            "live-mode": true,
   589	            "live-mode-brokerage": "TastytradeBrokerage",
   590	            "data-queue-handler": [
   591	                "TastytradeBrokerage"
   592	            ],
   593	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   594	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   595	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   596	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   597	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   598	            "history-provider": [
   599	                "BrokerageHistoryProvider",
   600	                "SubscriptionDataReaderHistoryProvider"
   601	            ]
   602	        },
   603	        "live-rbi": {
   604	            "live-mode": true,
   605	            "live-mode-brokerage": "RBIBrokerage",
   606	            "data-queue-handler": [
   607	                "QuantConnect.Lean.Engine.DataFeeds.Queues.LiveDataQueue"
   608	            ],
   609	            "history-provider": [
   610	                "SubscriptionDataReaderHistoryProvider"
   611	            ],
   612	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   613	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   614	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   615	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   616	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"
   617	        },
   618	        "live-eze": {
   619	            "live-mode": true,
   620	            "live-mode-brokerage": "QuantConnect.EzeBrokerage.EzeBrokerage",
   621	            "data-queue-handler": [
   622	                "QuantConnect.EzeBrokerage.EzeBrokerage"
   623	            ],
   624	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   625	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   626	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   627	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   628	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   629	            "history-provider": [
   630	                "BrokerageHistoryProvider",
   631	                "SubscriptionDataReaderHistoryProvider"
   632	            ]
   633	        },
   634	        "live-webull": {
   635	            "live-mode": true,
   636	            "live-mode-brokerage": "WebullBrokerage",
   637	            "data-queue-handler": [
   638	                "WebullBrokerage"
   639	            ],
   640	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   641	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   642	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   643	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   644	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   645	            "history-provider": [
   646	                "BrokerageHistoryProvider",
   647	                "SubscriptionDataReaderHistoryProvider"
   648	            ]
   649	        },
   650	        "live-dydx": {
   651	            "live-mode": true,
   652	            "live-mode-brokerage": "dYdXBrokerage",
   653	            "data-queue-handler": [
   654	                "dYdXBrokerage"
   655	            ],
   656	            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
   657	            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
   658	            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
   659	            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
   660	            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
   661	            "history-provider": [
   662	                "BrokerageHistoryProvider",
   663	                "SubscriptionDataReaderHistoryProvider"
   664	            ]
   665	        }
   666	    },
   667	    "file-database-last-update": "06/19/2026 14:09:31",
   668	    "id": "Local",
   669	    "parameters": {
   670	        "env": "dev"
   671	    }
   672	}
**Investigating storage options**

I need to check the universe CSV sample for development and possibly storage. Since the workspace is read-only, I wonder if the storage is hidden or ignored, which could explain why it didn’t come up in the search due to being git-ignored. I have to verify if the ObjectStore contains a real CSV to confirm counts. The user mentioned no modifications, but reading is allowed. I should use `find storage -maxdepth` to locate it.
codex
La config actual de `dev` usa `max_universe=4` y `universe=sample_dev`, no el `10` del documento de etapa. Eso no es necesariamente bug de código porque el propio cierre de Etapa 4 ya documentó una deriva del número; lo trataré como evidencia de trazabilidad, no como defecto salvo que contradiga un criterio operativo.
exec
/bin/zsh -lc 'nl -ba universes/sample_dev.csv' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low","5D Avg Vol",Time
     2	SPY,"SPDR S&P 500 ETF Trust",+1.42%,595.27,2.18,+0.37%,8.34,597.10,586.93,72184500,2026-06-05
     3	AAPL,"Apple Inc",+2.10%,205.40,1.85,+0.91%,4.22,207.95,200.11,54320000,2026-06-05
     4	IBM,"International Business Machines",+0.85%,281.30,0.95,+0.34%,2.37,283.50,277.60,4510000,2026-06-05
     5	FB,"Meta Platforms Inc (sample data ticker FB)",+1.05%,294.53,1.40,+0.48%,3.06,296.50,288.90,18030000,2026-06-05
     6	"Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT"

exec
/bin/zsh -lc 'head -n 12 storage/universes/swing_advances.csv' in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'find storage -maxdepth 3 -type f | sort' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low","5D Avg Vol",Time
STI,"Solidion Technology Inc",+668.17%,35.72,13.01,+57.29%,31.07,46,4.72,28869260,2026-06-05
STAK,"Stak Inc",+413.54%,4.93,0.69,+16.27%,3.97,8.8,0.94,14689660,2026-06-05
SDOT,"Sadot Group Inc",+344.69%,12.14,0.77,+6.77%,9.41,16.55,2.78,13571539,2026-06-05
LASE,"Laser Photonics Corp",+237.29%,3.1,-0.52,-14.36%,2.18,4.49,0.89,125139875,2026-06-05
DXST,"Decent Holding Inc",+165.38%,4.14,0.77,+22.85%,2.58,7.2,1.5,18650900,2026-06-05
JLHL,"Julong Holding Limited Cl A",+128.69%,44.8,8.55,+23.59%,25.21,51.17,15.2,58060,2026-06-05
BJDX,"Bluejay Diagnostics Inc",+124.30%,4.8,-0.5,-9.43%,2.66,7,2.05,15733520,2026-06-05
SPHL,"Springview Holdings Ltd",+120.16%,5.35,2.96,+123.94%,2.92,10.71,2.3,8128420,2026-06-05
NTCL,"Netclass Technology Inc Cl A",+113.07%,2.1,-0.01,-0.47%,1.11,2.5,0.9,3650420,2026-06-05
ANY,"Sphere 3D Corp",+112.63%,4.04,-0.3,-6.91%,2.14,6.2,2.86,34598121,2026-06-05
INDP,"Indaptus Therapeutics Inc",+107.95%,3.66,-1.09,-22.95%,1.9,5.96,1.74,9483100,2026-06-05

 succeeded in 0ms:
storage/config/notifications.json
storage/config/strategies.json
storage/results/market_close/20131007-1930.csv
storage/results/market_close/20131007-1930.json
storage/results/market_close/20131008-1930.csv
storage/results/market_close/20131008-1930.json
storage/results/market_close/20131009-1930.csv
storage/results/market_close/20131009-1930.json
storage/results/market_close/20131010-1930.csv
storage/results/market_close/20131010-1930.json
storage/results/market_close/20131011-1930.csv
storage/results/market_close/20131011-1930.json
storage/results/market_close/latest.json
storage/results/swing_eod/20131007-2001.csv
storage/results/swing_eod/20131007-2001.json
storage/results/swing_eod/20131008-2001.csv
storage/results/swing_eod/20131008-2001.json
storage/results/swing_eod/20131009-2001.csv
storage/results/swing_eod/20131009-2001.json
storage/results/swing_eod/20131010-2001.csv
storage/results/swing_eod/20131010-2001.json
storage/results/swing_eod/latest.json
storage/universes/sample_dev.csv
storage/universes/swing_advances.csv
storage/universes/swing_declines.csv
storage/validation/sma_validation_20131007.csv
storage/validation/sma_validation_20160104.csv

exec
/bin/zsh -lc 'head -n 12 storage/universes/swing_declines.csv' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low","5D Avg Vol",Time
RPGL,"Republic Power Group Limited Cl A",-76.49%,2.33,-0.6,-20.48%,-7.58,13.06,2.31,1046020,2026-06-05
NXTC,"Nextcure Inc",-52.42%,2.95,-0.24,-7.52%,-3.25,6.96,2.83,299640,2026-06-05
OCS,"Oculis Holding Ag",-50.63%,11.21,-0.62,-5.24%,-11.49,16,11.17,2738020,2026-06-05
CDTG,"Cdt Environmental Technology Investment",-49.08%,3.18,-1.67,-34.43%,-3.06,15.12,3.12,357680,2026-06-05
MTC,"Mmtec Inc",-47.05%,3.5,-0.49,-12.28%,-3.11,6.81,3.45,153200,2026-06-05
FULC,"Fulcrum Therapeutics Inc",-46.68%,3.69,0.32,+9.50%,-3.23,7.02,2.83,10059020,2026-06-05
TROO,"Troops Inc",-46.15%,2.24,-1.21,-35.07%,-1.92,4.16,2.2,564020,2026-06-05
STG,"Sunlands Online Education Group ADR",-43.49%,3.47,0.06,+1.76%,-2.67,5.82,3.13,334900,2026-06-05
BRAI,"Braiin Limited",-43.16%,7.27,-0.88,-10.80%,-5.52,13.62,7.02,137820,2026-06-05
INTJ,"Intelligent Group Limited",-41.89%,5.52,-0.98,-15.08%,-3.98,9.78,5.39,11020,2026-06-05
CETX,"Cemtrex Inc",-40.65%,5.52,0.07,+1.27%,-3.78,9.78,5.32,250740,2026-06-05

exec
/bin/zsh -lc 'tail -n 8 storage/universes/swing_advances.csv' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
KSS,"Kohl's Corp",+7.66%,15.46,-0.5,-3.13%,1.1,16.11,14.33,5771120,2026-06-05
MCS,"Marcus Corp",+7.62%,20.35,0.24,+1.19%,1.44,20.75,18.71,191120,2026-06-05
DE,"Deere & Company",+7.61%,583.44,-8.31,-1.40%,41.26,604.51,528.45,1924080,2026-06-05
CVSA,"Covista Inc",+7.51%,126.65,2.2,+1.77%,8.85,128.05,116.39,280880,2026-06-05
HALO,"Halozyme Therapeutic",+7.50%,71.53,-0.07,-0.10%,4.99,72.25,65.6,1934380,2026-06-05
CWK,"Cushman & Wakefield Ltd",+7.48%,13.37,0.1,+0.75%,0.93,13.48,11.98,2320960,2026-06-05
AJG,"Arthur J. Gallagher & Company",+7.47%,216.14,5.84,+2.78%,15.03,216.73,199.68,1615400,2026-06-05
"Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT"

exec
/bin/zsh -lc 'tail -n 8 storage/universes/swing_declines.csv' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
AEVA,"Aeva Technologies Inc",-18.35%,23.01,-1.39,-5.70%,-5.17,29.4,21.33,2565720,2026-06-05
LZM,"Lifezone Metals Limited",-18.29%,4.29,-0.8,-15.72%,-0.96,5.96,4.25,489340,2026-06-05
ENHA,"Enhanced Group Inc Cl A",-18.27%,2.46,-0.17,-6.46%,-0.55,3.3,2.46,609300,2026-06-05
IVA,"Inventiva S.A. ADR",-18.26%,4.03,-0.2,-4.73%,-0.9,4.96,3.81,1443540,2026-06-05
DOMO,"Domo Inc Cl B",-18.23%,3.41,-0.46,-11.89%,-0.76,4.66,3.39,730080,2026-06-05
EVCM,"Evercommerce Inc",-18.22%,9.2,-0.31,-3.26%,-2.05,11.57,9.15,168020,2026-06-05
PSNY,"Polestar Automotive Holding UK Cl A",-18.11%,18.9,-0.51,-2.63%,-4.18,22.64,18.29,157440,2026-06-05
"Downloaded from Barchart.com as of 06-05-2026 08:52pm CDT"

codex
Voy a hacer una pasada estática de invariantes duros: órdenes prohibidas, imports de LEAN fuera de L5, lecturas `open()` contra ObjectStore y uso de APIs LEAN en `main.py` relacionado con esta etapa (`object_store.read`, `get_parameter`, `log`).
exec
/bin/zsh -lc "rg -n \"open\\(|read_csv\\(|object_store|ObjectStore|UniverseSpec|get_parameter|self\\.log|self\\.debug|schedule\\.on|add_equity|history|notify\" trade-scanner/main.py trade-scanner/core trade-scanner/strategies scripts config trade-scanner/tests" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'rg -n "AlgorithmImports" trade-scanner/core trade-scanner/strategies trade-scanner/tests' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
trade-scanner/core/output.py:3:Núcleo determinista del contrato de salida. **Sin `AlgorithmImports` ni SDK externo** a nivel de
trade-scanner/core/output.py:185:    `AlgorithmImports` (precedente D-E4) y es testeable con mocks. T3.1 (esta entrega) deja el
trade-scanner/tests/test_sma_regression.py:21:from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar
trade-scanner/strategies/base.py:2:y si su scan es intradía. Negocio puro, importable sin CLR (patrón core): cero AlgorithmImports.
trade-scanner/tests/test_pipeline.py:3:L4 negocio puro: pipeline.py no importa AlgorithmImports. T6: los formateadores solo dan formato a
trade-scanner/core/email_render.py:3:Función **pura y SDK-free** — **sin `AlgorithmImports` ni SDK de Gmail** a nivel de módulo
trade-scanner/tests/test_rules.py:3:L4 negocio puro. rules.py no importa AlgorithmImports; la suite corre dentro de
trade-scanner/tests/test_output.py:3:L4 negocio puro: output.py NO importa AlgorithmImports (verificado por test de import + grep en el
trade-scanner/tests/test_output.py:433:# Criterio (d) — output.py sin AlgorithmImports a nivel de módulo.
trade-scanner/tests/test_output.py:445:    assert not any("AlgorithmImports" in ln for ln in import_lines)
trade-scanner/tests/test_features.py:3:No usan AlgorithmImports — L3 es negocio puro; corren dentro de Docker sin CLR.
trade-scanner/tests/test_symbol_data.py:13:from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar
trade-scanner/tests/test_email_render.py:190:# (T2.1 / criterio d) email_render.py sin import de AlgorithmImports ni SDK de Gmail.
trade-scanner/tests/test_email_render.py:196:    assert not any("AlgorithmImports" in ln for ln in import_lines)
trade-scanner/tests/test_timeframes.py:3:Estos tests NO importan AlgorithmImports: la fórmula y el plan son funciones puras
trade-scanner/tests/test_timeframes.py:76:    en un intérprete limpio que importar el módulo no arrastra clr/AlgorithmImports."""
trade-scanner/tests/test_timeframes.py:79:        "assert 'clr' not in sys.modules and 'AlgorithmImports' not in sys.modules"
trade-scanner/tests/test_universe.py:3:No usan AlgorithmImports — corren dentro de Docker pero sin el CLR path.
trade-scanner/tests/test_pythonnet_bridge.py:2:AlgorithmImports y construye un objeto LEAN real (TradeBar), no un assert trivial.
trade-scanner/tests/test_pythonnet_bridge.py:5:from AlgorithmImports import TradeBar
trade-scanner/core/timeframes.py:3:Sin imports de AlgorithmImports a nivel de módulo (patrón universe.py): el CLR
trade-scanner/core/timeframes.py:14:    from AlgorithmImports import TradeBarConsolidator
trade-scanner/core/timeframes.py:20:    from AlgorithmImports import Calendar, TradeBarConsolidator
trade-scanner/core/timeframes.py:26:    from AlgorithmImports import Calendar, TradeBarConsolidator
trade-scanner/core/features.py:3:Negocio puro, importable sin CLR (patrón universe): cero AlgorithmImports.
trade-scanner/core/universe.py:3:Sin imports de AlgorithmImports — testeable con cualquier mock que tenga .read(key) -> str.
trade-scanner/tests/test_t5_stooq_crosscheck.py:24:from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar
trade-scanner/core/rules.py:3:Negocio puro, importable sin CLR (patrón features): cero AlgorithmImports. L4 no
trade-scanner/core/symbol_data.py:11:Sin imports de AlgorithmImports a nivel de módulo (patrón universe/timeframes): el
trade-scanner/core/symbol_data.py:29:        from AlgorithmImports import SimpleMovingAverage
trade-scanner/core/pipeline.py:3:Negocio puro, importable sin CLR (patrón features/rules): cero AlgorithmImports. El `ScanPipeline`

 succeeded in 0ms:
trade-scanner/main.py:14:from core.universe import UniverseSpec
trade-scanner/main.py:20:    """Orquestación L5 (Etapa 5B): config desde ObjectStore, universo efectivo por
trade-scanner/main.py:34:        # Config de negocio desde ObjectStore (key = ruta relativa bajo storage/).
trade-scanner/main.py:35:        raw = self.object_store.read("config/strategies.json")
trade-scanner/main.py:38:        env = self.get_parameter("env", "prod")
trade-scanner/main.py:50:            spec = UniverseSpec(
trade-scanner/main.py:55:            loaded = spec.load(self.object_store)
trade-scanner/main.py:57:            self.log(
trade-scanner/main.py:68:            self.log(
trade-scanner/main.py:86:            symbol = self.add_equity(
trade-scanner/main.py:101:            self.log(f"[{ticker}] SymbolData listo (series: {declared})")
trade-scanner/main.py:123:        self.spy = spy or self.add_equity("SPY", Resolution.DAILY).symbol
trade-scanner/main.py:133:                self.log(f"[{name}] sin StrategyConfig en STRATEGIES: omitida del scan")
trade-scanner/main.py:147:        # T5.1 — OutputSink (Etapa 8): L5 es el único que toca object_store/notify/live_mode/
trade-scanner/main.py:151:        notif_cfg = json.loads(self.object_store.read("config/notifications.json"))
trade-scanner/main.py:153:            self.object_store,
trade-scanner/main.py:154:            self.notify,
trade-scanner/main.py:158:            self.log,
trade-scanner/main.py:167:                self.log(f"[{base}] grupo sin pipelines activos: omitido del schedule")
trade-scanner/main.py:181:                self.log(f"[{base}] schedule desconocido: grupo omitido")
trade-scanner/main.py:183:            self.schedule.on(
trade-scanner/main.py:188:            self.log(f"[{base}] schedule registrado: miembros {list(active)}")
trade-scanner/main.py:203:            self.log(
trade-scanner/main.py:232:        self.log(
trade-scanner/main.py:239:        self.log(f"[warmup] ready: {ready}/{len(self.symbol_data)} símbolos")
trade-scanner/main.py:244:                self.log(f"WARNING [warmup] {symbol.value} series frías: {', '.join(cold)}")
trade-scanner/main.py:247:        self.log(
trade-scanner/main.py:258:        """Gate D4 (bajo flag validate_warmup): la ruta manual de 5A — history[TradeBar] tipado en UNA
trade-scanner/main.py:264:        history = self.history[TradeBar](symbols, self._warmup_depth, Resolution.DAILY)
trade-scanner/main.py:266:        for trade_bars in history:
trade-scanner/main.py:291:            self.log(
trade-scanner/main.py:293:                f"exactas vs ruta manual ({rows} filas vía history[TradeBar], 1 llamada batch)"
trade-scanner/main.py:296:            self.log(
trade-scanner/main.py:301:                self.log(f"WARNING [warmup] gate: {mismatch}")
trade-scanner/main.py:315:            self.log(
trade-scanner/main.py:335:        ObjectStore (storage/validation/ en local). bar_end_time sigue la convención de
trade-scanner/main.py:349:        self.object_store.save(key, "\n".join(lines) + "\n")
trade-scanner/main.py:350:        self.log(
trade-scanner/main.py:379:            results = pipeline.scan(self.symbol_data, self.utc_time, self.log)
trade-scanner/main.py:382:                self.log(
trade-scanner/main.py:388:            self.log(f"[{name}] scan @ {self.utc_time}: {len(results)} candidatos")
trade-scanner/main.py:393:        self.log(f"[{base}] emit @ {self.utc_time}: sections={{{counts}}}")
trade-scanner/main.py:410:        self.log(
config/notifications.json:7:    "dev":  { "channels": ["file"],               "notify_empty": false },
config/notifications.json:8:    "prod": { "channels": ["file", "host_email"], "notify_empty": false }
trade-scanner/core/output.py:4:módulo (precedente `universe.py`, D-E4): así lo importan el algoritmo (transporte `qc_notify`) y el
trade-scanner/core/output.py:6:sin CLR. Los handles de LEAN (`object_store`, `notify`) entran por constructor en T3, no por import.
trade-scanner/core/output.py:166:        destinatarios simplemente no dispara `qc_notify` (lo gestiona `OutputSink._emit_qc_notify`)."""
trade-scanner/core/output.py:187:    handlers (`file`/`qc_notify`/`host_email`) son T3.2–T3.4.
trade-scanner/core/output.py:190:    `notify_empty`. `subscribers` es un `SubscriberSource` (duck-typed: `for_strategy(base)`),
trade-scanner/core/output.py:197:        object_store,
trade-scanner/core/output.py:198:        notify,
trade-scanner/core/output.py:204:        self._object_store = object_store
trade-scanner/core/output.py:205:        self._notify = notify
trade-scanner/core/output.py:223:    def _notify_empty_for(self, env: str) -> bool:
trade-scanner/core/output.py:224:        """`notify_empty` para `env` (D8.3/D8.4): default `False` (un scan sin candidatos escribe
trade-scanner/core/output.py:226:        return bool(self._environments.get(env, {}).get("notify_empty", False))
trade-scanner/core/output.py:239:        de la tabla `{file, qc_notify, host_email}`. Ningún `if env == ...`: el entorno solo aporta
trade-scanner/core/output.py:245:            "qc_notify": self._emit_qc_notify,
trade-scanner/core/output.py:261:        self._object_store.save(f"results/{base}/{ts}.json", json_str)
trade-scanner/core/output.py:262:        self._object_store.save(f"results/{base}/{ts}.csv", serialize_csv(sections))
trade-scanner/core/output.py:263:        self._object_store.save(f"results/{base}/latest.json", json_str)
trade-scanner/core/output.py:266:    def _emit_qc_notify(self, envelope: dict, sections: dict) -> None:
trade-scanner/core/output.py:267:        """Canal `qc_notify` (cloud): `notify.email` con el render compartido (T2). Guards, en orden:
trade-scanner/core/output.py:268:        vida (D8.4/T3.3: backtest suprime), `notify_empty` (D8.3/T3.4: scan vacío no notifica salvo
trade-scanner/core/output.py:272:            self._log(f"[output] {base}: correo suprimido en backtest (qc_notify)")
trade-scanner/core/output.py:274:        if envelope.get("totals", {}).get("all", 0) == 0 and not self._notify_empty_for(
trade-scanner/core/output.py:277:            self._log(f"[output] {base}: sin candidatos; qc_notify omitido (notify_empty=false)")
trade-scanner/core/output.py:281:            self._log(f"[output] {base}: sin suscriptores; qc_notify omitido")
trade-scanner/core/output.py:284:        self._notify.email(",".join(recipients), doc.subject, doc.html_body)
trade-scanner/core/output.py:285:        self._log(f"[output] {base}: qc_notify enviado a {len(recipients)} suscriptor(es)")
trade-scanner/tests/test_sma_regression.py:3:Tercera ruta independiente (zip → TradeBars → SymbolData, sin engine ni self.history)
trade-scanner/tests/test_notify_email.py:1:"""Tests del script host-side `scripts/notify_email.py` (Etapa 8, T6).
trade-scanner/tests/test_notify_email.py:13:import notify_email
trade-scanner/tests/test_notify_email.py:29:    # El script importa la MISMA función que usa OutputSink (qc_notify): render compartido (D8.1).
trade-scanner/tests/test_notify_email.py:30:    assert notify_email.render_email is email_render.render_email
trade-scanner/tests/test_notify_email.py:56:    monkeypatch.setattr(notify_email, "send_gmail", lambda *a, **k: calls.append(a))
trade-scanner/tests/test_notify_email.py:58:    notify_email.run(_args(sample=str(FIXTURE), send=False))
trade-scanner/tests/test_notify_email.py:67:    monkeypatch.setattr(notify_email, "send_gmail", lambda doc, rcpts, creds: calls.append((doc, rcpts, creds)))
trade-scanner/tests/test_notify_email.py:69:    monkeypatch.setattr(notify_email, "resolve_recipients", lambda cfg, base: ["x@example.com"])
trade-scanner/tests/test_notify_email.py:70:    monkeypatch.setattr(notify_email, "load_notif_config", lambda: {})
trade-scanner/tests/test_notify_email.py:73:    notify_email.run(_args(sample=str(FIXTURE), send=True))
trade-scanner/tests/test_notify_email.py:88:    creds = notify_email.load_credentials()
trade-scanner/tests/test_notify_email.py:95:    src = Path(notify_email.__file__).read_text()
scripts/explore_universe.py:45:    with open(path, newline="", encoding="utf-8") as f:
trade-scanner/tests/test_output.py:171:        "dev": {"channels": ["file"], "notify_empty": False},
trade-scanner/tests/test_output.py:172:        "prod": {"channels": ["file", "host_email"], "notify_empty": True},
trade-scanner/tests/test_output.py:179:        object_store=object(), notify=object(), live_mode=live_mode,
trade-scanner/tests/test_output.py:186:    store, notify, subs = object(), object(), _StubSubscribers()
trade-scanner/tests/test_output.py:187:    sink = OutputSink(store, notify, False, _NOTIF_CONFIG, subs)
trade-scanner/tests/test_output.py:188:    assert sink._object_store is store
trade-scanner/tests/test_output.py:189:    assert sink._notify is notify
trade-scanner/tests/test_output.py:209:# (T3.1) notify_empty por entorno: default False, configurable a True.
trade-scanner/tests/test_output.py:210:def test_notify_empty_per_env():
trade-scanner/tests/test_output.py:212:    assert sink._notify_empty_for("dev") is False
trade-scanner/tests/test_output.py:213:    assert sink._notify_empty_for("prod") is True
trade-scanner/tests/test_output.py:214:    assert sink._notify_empty_for("staging") is False  # ausente → default
trade-scanner/tests/test_output.py:218:# T3.2 — emit + tabla de handlers (file / qc_notify / host_email).
trade-scanner/tests/test_output.py:245:def _emit_sink(channels, *, live_mode=True, subs=None, log=None, notify_empty=False):
trade-scanner/tests/test_output.py:246:    cfg = {"environments": {"prod": {"channels": channels, "notify_empty": notify_empty}}}
trade-scanner/tests/test_output.py:247:    store, notify = _MockStore(), _MockNotify()
trade-scanner/tests/test_output.py:248:    sink = OutputSink(store, notify, live_mode, cfg, _Subs(subs or {}), log=log)
trade-scanner/tests/test_output.py:249:    return sink, store, notify
trade-scanner/tests/test_output.py:259:# (a) file + qc_notify en live: 3 archivos bajo results/<base>/ y notify.email UNA vez.
trade-scanner/tests/test_output.py:260:def test_emit_file_and_qc_notify_live():
trade-scanner/tests/test_output.py:261:    sink, store, notify = _emit_sink(
trade-scanner/tests/test_output.py:262:        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com", "b@x.com"]}
trade-scanner/tests/test_output.py:274:    assert len(notify.calls) == 1
trade-scanner/tests/test_output.py:275:    address, subject, _message = notify.calls[0]
trade-scanner/tests/test_output.py:280:# (c) file + host_email: archivos escritos, notify.email NUNCA; log marca "listo para host".
trade-scanner/tests/test_output.py:283:    sink, store, notify = _emit_sink(["file", "host_email"], log=logged.append)
trade-scanner/tests/test_output.py:287:    assert notify.calls == []
trade-scanner/tests/test_output.py:291:# (b/T3.3) backtest: mismos canales pero notify.email NO se llama (gate de vida).
trade-scanner/tests/test_output.py:292:def test_emit_backtest_suppresses_qc_notify():
trade-scanner/tests/test_output.py:294:    sink, store, notify = _emit_sink(
trade-scanner/tests/test_output.py:295:        ["file", "qc_notify"], live_mode=False, subs={"swing_eod": ["a@x.com"]}, log=logged.append
trade-scanner/tests/test_output.py:300:    assert notify.calls == []  # correo no
trade-scanner/tests/test_output.py:304:# qc_notify sin suscriptores: no se llama notify.email (lookup por base, D8.5).
trade-scanner/tests/test_output.py:305:def test_emit_qc_notify_without_subscribers():
trade-scanner/tests/test_output.py:306:    sink, store, notify = _emit_sink(["file", "qc_notify"], subs={})  # base sin lista
trade-scanner/tests/test_output.py:308:    assert notify.calls == []
trade-scanner/tests/test_output.py:314:    sink, store, notify = _emit_sink(["file", "bogus"], log=logged.append)
trade-scanner/tests/test_output.py:321:# T3.4 — notify_empty: scan sin candidatos escribe archivo pero no notifica (salvo config).
trade-scanner/tests/test_output.py:324:# (d) totals.all==0 y notify_empty=False: archivo sí, correo no.
trade-scanner/tests/test_output.py:325:def test_emit_empty_scan_writes_file_but_no_notify():
trade-scanner/tests/test_output.py:327:    sink, store, notify = _emit_sink(
trade-scanner/tests/test_output.py:328:        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=False, log=logged.append
trade-scanner/tests/test_output.py:333:    assert notify.calls == []  # correo no
trade-scanner/tests/test_output.py:334:    assert any("notify_empty=false" in line for line in logged)
trade-scanner/tests/test_output.py:337:# notify_empty=True: un scan vacío sí dispara qc_notify (override de config).
trade-scanner/tests/test_output.py:338:def test_emit_empty_scan_notifies_when_notify_empty_true():
trade-scanner/tests/test_output.py:339:    sink, store, notify = _emit_sink(
trade-scanner/tests/test_output.py:340:        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=True
trade-scanner/tests/test_output.py:343:    assert len(notify.calls) == 1
trade-scanner/tests/test_output.py:346:# notify_empty no aplica con candidatos: scan no-vacío notifica normal.
trade-scanner/tests/test_output.py:347:def test_emit_non_empty_notifies_regardless_of_notify_empty():
trade-scanner/tests/test_output.py:348:    sink, store, notify = _emit_sink(
trade-scanner/tests/test_output.py:349:        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=False
trade-scanner/tests/test_output.py:352:    assert len(notify.calls) == 1
trade-scanner/tests/test_output.py:440:    with open(src) as fh:
trade-scanner/core/email_render.py:4:(precedente `universe.py`, D-E4): la importan *ambos* planos, el algoritmo (transporte `qc_notify`
trade-scanner/core/email_render.py:5:vía `self.notify.email`) y el script host (transporte Gmail). Flipar de cloud a local NO recompone
trade-scanner/core/email_render.py:45:    """El correo renderizado, agnóstico del transporte: el mismo objeto va a `self.notify.email`
scripts/seed_object_store.sh:2:# seed_object_store.sh — Siembra config y universos al ObjectStore local.
scripts/seed_object_store.sh:5:#   data/object-store/ respectivamente, y se leen en runtime vía self.object_store.
scripts/seed_object_store.sh:6:#   El ObjectStore local del CLI es <workspace>/storage/ (montado en /Storage dentro
scripts/seed_object_store.sh:34:echo "Sembrando ObjectStore local ($DEST)"
trade-scanner/tests/test_email_render.py:194:    with open(render_mod.__file__) as fh:
trade-scanner/core/universe.py:1:"""UniverseSpec: lee un CSV desde ObjectStore y devuelve la lista filtrada de tickers.
trade-scanner/core/universe.py:27:class UniverseSpec:
trade-scanner/core/universe.py:38:    def load(self, object_store) -> list[str]:
trade-scanner/core/universe.py:41:        object_store: cualquier objeto con .read(key: str) -> str
trade-scanner/core/universe.py:43:        raw_csv = object_store.read(self.universe_key)
trade-scanner/core/universe.py:44:        df = pd.read_csv(io.StringIO(raw_csv))
trade-scanner/core/universe.py:78:                f"[UniverseSpec] WARNING: truncating {self.universe_key} "
trade-scanner/tests/test_t5_stooq_crosscheck.py:44:    with open(csv_path) as f:
trade-scanner/tests/test_universe.py:1:"""Tests unitarios de UniverseSpec.
trade-scanner/tests/test_universe.py:4:Fixture base: MockObjectStore retorna CSV sintético construido en el test.
trade-scanner/tests/test_universe.py:8:from core.universe import UniverseSpec
trade-scanner/tests/test_universe.py:21:class MockObjectStore:
trade-scanner/tests/test_universe.py:29:class RaisingObjectStore:
trade-scanner/tests/test_universe.py:46:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:56:    result = UniverseSpec("k", FILTER, max_tickers=5).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:70:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:82:        UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:85:# T3.5 — KeyError de ObjectStore se propaga sin transformar
trade-scanner/tests/test_universe.py:86:def test_object_store_key_not_found_propagates():
trade-scanner/tests/test_universe.py:88:        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())
trade-scanner/core/__init__.py:5:from core.universe import UniverseSpec
trade-scanner/core/__init__.py:12:    "UniverseSpec",
scripts/notify_email.py:1:"""notify_email.py — Transporte host-side del correo del screener (Etapa 8, T6).
scripts/notify_email.py:15:    python scripts/notify_email.py --dry-run --sample tests/fixtures/envelope_sample.json
scripts/notify_email.py:18:    python scripts/notify_email.py --dry-run --base swing_eod
scripts/notify_email.py:21:    python scripts/notify_email.py --send --base swing_eod
scripts/notify_email.py:48:# Raíces locales: el ObjectStore local del CLI es `<workspace>/storage/` (CLAUDE.md); la config
scripts/stooq_to_lean.py:6:solo lee vía `self.history`/feed y nunca sabe de dónde vino el zip. Este script es el lado

exec
/bin/zsh -lc "rg -n \"market_order|set_holdings|liquidate|\\bbuy\\(|\\bsell\\(|order\\(\" trade-scanner config scripts docs .claude PLAN.md SPECS.md README.md AGENTS.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
AGENTS.md:20:está prohibido colocar órdenes**. Cualquier `self.market_order`, `self.set_holdings`,
AGENTS.md:21:`self.buy/sell`, `self.liquidate` o similar es un hallazgo **CRÍTICO**.
AGENTS.md:215:- Cualquier orden o gestión de portfolio (`market_order`, `set_holdings`, `liquidate`, etc.) → **CRÍTICO**.
trade-scanner/tests/test_symbol_data.py:269:def test_5b_t3_consolidator_accessor_and_observer_order():
.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md:76:  por defecto con `set_holdings("SPY", 1)` (una orden).
.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md:90:| P3 | Cuerpo de `main.py` sigue siendo scaffold con orden `set_holdings` | ✅ Resuelto (T4) | scaffold/orden eliminado; ancla SPY + ScheduledEvent que solo loguea |

exec
/bin/zsh -lc "rg -n \"self\\.object_store\\.read|def read\\(|GetParameter|GetParameter\\(|get_parameter\\(|ObjectStore|LocalObjectStore|Read\\(\" /Users/guille/Documents/quant/trade-scanner/trade-scanner /Users/guille/Documents/quant/trade-scanner/lean.json" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'rg -n "UniverseSpec|universe loaded|avg_vol_5d|price > 5|max_universe|sample_dev|swing_advances|swing_declines" README.md CLAUDE.md docs .claude/fase-1-desarrollo-local/etapa-04.md .claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md PLAN.md SPECS.md' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
/Users/guille/Documents/quant/trade-scanner/lean.json:12:    "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:20:    """Orquestación L5 (Etapa 5B): config desde ObjectStore, universo efectivo por
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:34:        # Config de negocio desde ObjectStore (key = ruta relativa bajo storage/).
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:35:        raw = self.object_store.read("config/strategies.json")
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:38:        env = self.get_parameter("env", "prod")
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:151:        notif_cfg = json.loads(self.object_store.read("config/notifications.json"))
/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:335:        ObjectStore (storage/validation/ en local). bar_end_time sigue la convención de
/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:1:"""UniverseSpec: lee un CSV desde ObjectStore y devuelve la lista filtrada de tickers.
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:4:Fixture base: MockObjectStore retorna CSV sintético construido en el test.
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:21:class MockObjectStore:
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:25:    def read(self, key: str) -> str:
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:29:class RaisingObjectStore:
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:30:    def read(self, key: str) -> str:
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:46:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:56:    result = UniverseSpec("k", FILTER, max_tickers=5).load(MockObjectStore(csv))
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:70:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:82:        UniverseSpec("k", FILTER).load(MockObjectStore(csv))
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:85:# T3.5 — KeyError de ObjectStore se propaga sin transformar
/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:88:        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())

 succeeded in 0ms:
SPECS.md:82:| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro declarativo sobre columnas normalizadas (ej. `"avg_vol_5d > 1e6 and price > 5"`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore. Footer strip (`^[A-Z]{1,5}$`). Alias normalizados (`COLUMN_ALIASES`). Filtro vía `df.query()`. Tope duro 200 post-filtro. Sin imports de `AlgorithmImports` (testeable con mock). Claves: `universes/swing_advances.csv`, `universes/swing_declines.csv`. |
SPECS.md:86:| `ScanPipeline` | Una estrategia: `UniverseSpec` + lista de `Rules` + `ScheduleSpec`. Ejecuta el scan y produce `ScanResult`. | V1: `swing_eod`, `market_close`. |
PLAN.md:53:│   │   ├── universe.py          # UniverseSpec: CSV ObjectStore + filtro simple + refresh_universe() no-op
PLAN.md:105:Claves ObjectStore: `universes/swing_advances.csv` (advances/longs) y `universes/swing_declines.csv` (declines/shorts).
PLAN.md:118:| `5D Avg Vol`   | `avg_vol_5d`      | float  | Ya numérico (sin comas)                     |
PLAN.md:124:- Filtro declarativo usa **alias normalizados**: `"avg_vol_5d > 1e6 and price > 5"`.
PLAN.md:125:- Normalización (rename de columnas) ocurre en `UniverseSpec` (Etapa 4); el CSV en ObjectStore se guarda tal cual (con footer incluido).
PLAN.md:158:Variante shorts (`*_short`): universo `swing_declines`, `direction: short` → las mismas reglas con `side="below"` por mirror (ADR-005): `AboveSMA` filtra `below_*`, `NotExtended` excluye `extended_below`. Sin reglas nuevas.
PLAN.md:237:- [x] `bash scripts/seed_object_store.sh` siembra `strategies.json` + `swing_advances.csv` + `swing_declines.csv`; mueve fuentes a `processed/`
PLAN.md:238:- [x] `storage/universes/swing_advances.csv` y `swing_declines.csv` existen con ~200 filas; archivos movidos a `data/object-store/processed/`
PLAN.md:241:> **Cierre (commit `[Etapa 3]`):** perfilado confirma contrato sin sorpresas (200 datos + 1 footer, 11 columnas, mediana vol ~995K); filtro combinado `avg_vol_5d > 1M AND price > 5` deja 74 advances / 68 declines. Contratos definitivos en §5. 4 estrategias en `strategies.json` (2 long + 2 short placeholder) + `environments` dev/prod. `seed_object_store.sh` actualizado con glob datado y archivo a `processed/`. Backtest confirma las 4 estrategias disparando. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md).
PLAN.md:243:## Etapa 4 — UniverseSpec
PLAN.md:254:> **Cierre (commit `[Etapa 4]`):** `core/universe.py` implementado con `COLUMN_ALIASES`, footer strip (`^[A-Z]{1,5}$`), filtro declarativo vía `df.query()`, orden alfabético y tope duro. Sin imports de `AlgorithmImports`. `main.py` integrado: 4 líneas `universe loaded: N tickers (env=..., max=..., key=...)` en `initialize()`; conteos 74 advances / 68 declines en prod, 2 en dev. 6 tests verdes en Docker (`bash scripts/run_tests.sh`). **Hallazgo D-E4:** `self.get_parameter()` lee parámetros escalares desde `trade-scanner/config.json["parameters"]`, NO desde `lean.json["parameters"]` (el campo en `lean.json` es configuración del engine, no del algoritmo). El parámetro `env` vive en `trade-scanner/config.json`. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes-md](.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes-md).
PLAN.md:281:- **F1 — slice vertical SPY (datos cero):** `main.py` construye `SymbolData` por símbolo, warmup batch `self.history` agrupado por resolución **cerrando con `sd.scan()`** (hallazgo #1 de 5A), `plan_warmup` global, suscripción `Resolution.DAILY` con `SPLIT_ADJUSTED`, wiring `subscription_manager.add_consolidator`. Entorno `dev` como harness: overrides `universe`/`timeframes`/`warmup_budget` a nivel environment (universo `sample_dev` = SPY/AAPL/IBM; `D/W/M:[8,20,200]` con M:200 solo en dev). Archivo `validation/sma_validation_<fecha>.csv` (solo dev, **K=5 filas/serie**) + fixture de regresión interino. Hito: *pipeline verde*.
README.md:111:Columnas adicionales son ignoradas a menos que el filtro declarativo las use. El filtro se define en `config.json` como string evaluable: `"price > 5 and avg_dollar_volume > 5e6"`. Tope duro: 200 tickers post-filtro.
.claude/fase-1-desarrollo-local/etapa-04.md:1:# Etapa 4 — UniverseSpec
.claude/fase-1-desarrollo-local/etapa-04.md:11:Al cerrar la etapa existe `core/universe.py` con la clase `UniverseSpec` que lee un CSV desde ObjectStore, aplica footer strip, normaliza alias de columnas, evalúa el filtro declarativo y devuelve la lista de tickers con tope duro de 200. `main.py` integra la carga y loguea el universo por estrategia. Los tests unitarios (dentro de Docker) cubren filtro, tope y CSV malformado.
.claude/fase-1-desarrollo-local/etapa-04.md:17:## Decisión de diseño: P3 — `UniverseSpec` no conoce `direction`
.claude/fase-1-desarrollo-local/etapa-04.md:19:> **Contexto:** el campo `direction` existe en cada estrategia (`"long"` / `"short"`) y en `ScanResult`. La pregunta era si `UniverseSpec` necesita conocerlo.
.claude/fase-1-desarrollo-local/etapa-04.md:21:**Decisión: no. `UniverseSpec` es agnóstico a la dirección.**
.claude/fase-1-desarrollo-local/etapa-04.md:25:| Lo que `UniverseSpec` hace | Lo que NO le corresponde |
.claude/fase-1-desarrollo-local/etapa-04.md:31:La "señal de dirección" en los datos **ya está codificada en la clave del universo**: `swing_advances` = longs, `swing_declines` = shorts. `UniverseSpec` no repite esa información.
.claude/fase-1-desarrollo-local/etapa-04.md:33:El campo `direction` vive en la config de la estrategia (`strategy_config["direction"]`). El pipeline (Etapa 7) lo lee de ahí y lo estampa en cada `ScanResult`. `UniverseSpec` nunca lo necesita.
.claude/fase-1-desarrollo-local/etapa-04.md:38:       ├── universe: "swing_advances"   → UniverseSpec("universes/swing_advances.csv", ...)
.claude/fase-1-desarrollo-local/etapa-04.md:42:Un UniverseSpec instanciado con "swing_declines" funciona igual de bien para una
.claude/fase-1-desarrollo-local/etapa-04.md:46:**Consecuencia práctica:** `swing_eod` y `market_close` comparten la misma clave `swing_advances`. En V1, cada uno llama `load()` por separado (el CSV es pequeño; la optimización de caché va en Etapa 7 si se decide necesaria).
.claude/fase-1-desarrollo-local/etapa-04.md:52:### T1 — `core/universe.py`: clase `UniverseSpec`
.claude/fase-1-desarrollo-local/etapa-04.md:58:class UniverseSpec:
.claude/fase-1-desarrollo-local/etapa-04.md:61:        universe_key: str,      # "universes/swing_advances.csv"
.claude/fase-1-desarrollo-local/etapa-04.md:62:        filter_expr: str,       # "avg_vol_5d > 1e6 and price > 5"
.claude/fase-1-desarrollo-local/etapa-04.md:77:4. **Alias rename:** renombrar columnas según el mapa del contrato §5 PLAN.md (ej. `"Symbol" → "ticker"`, `"5D Avg Vol" → "avg_vol_5d"`, `"Latest" → "price"`, `"5D %Chg" → "pct_chg_5d"`, `"%Change" → "pct_chg_1d"`).
.claude/fase-1-desarrollo-local/etapa-04.md:86:- Con `filter_expr="avg_vol_5d > 1e6 and price > 5"`: devuelve los mismos conteos verificados en Etapa 3 (~74 advances, ~68 declines).
.claude/fase-1-desarrollo-local/etapa-04.md:98:### T2 — `main.py`: integrar `UniverseSpec` y loguear universo por estrategia
.claude/fase-1-desarrollo-local/etapa-04.md:109:max_universe = env_cfg["max_universe"]
.claude/fase-1-desarrollo-local/etapa-04.md:114:    spec = UniverseSpec(
.claude/fase-1-desarrollo-local/etapa-04.md:117:        max_tickers=max_universe,
.claude/fase-1-desarrollo-local/etapa-04.md:120:    self.log(f"[{name}] universe loaded: {len(tickers)} tickers "
.claude/fase-1-desarrollo-local/etapa-04.md:121:             f"(env={env}, max={max_universe}, key={universe_key})")
.claude/fase-1-desarrollo-local/etapa-04.md:127:- `lean backtest "trade-scanner"` loguea 4 líneas `"[<strategy>] universe loaded: N tickers ..."` durante `initialize()`.
.claude/fase-1-desarrollo-local/etapa-04.md:129:- `env=dev` en `lean.json` → `max_universe=10` → log muestra `10 tickers` para ambos universos.
.claude/fase-1-desarrollo-local/etapa-04.md:148:- CSV sintético con 5 filas: 3 pasan `avg_vol_5d > 1e6 and price > 5`, 2 no.
.claude/fase-1-desarrollo-local/etapa-04.md:160:- CSV sin la columna `avg_vol_5d` (nombre original `5D Avg Vol`).
.claude/fase-1-desarrollo-local/etapa-04.md:178:- `core/universe.py` con clase `UniverseSpec` completa (load, footer strip, alias, filtro, tope)
.claude/fase-1-desarrollo-local/etapa-04.md:179:- Integración mínima en `main.py`: leer `env_cfg`, instanciar `UniverseSpec` por estrategia, loguear conteos
.claude/fase-1-desarrollo-local/etapa-04.md:181:- Actualizar `core/__init__.py` para exportar `UniverseSpec`
.claude/fase-1-desarrollo-local/etapa-04.md:185:- **Ranking / top_n filtering** — Etapa 7. `top_n` se lee y loguea, pero no se aplica al cargar el universo; `UniverseSpec` solo aplica el filtro declarativo + tope de seguridad.
.claude/fase-1-desarrollo-local/etapa-04.md:187:- **Propagación de `direction` en `UniverseSpec`** — ver decisión P3 arriba. `direction` viaja por el pipeline en Etapa 7.
.claude/fase-1-desarrollo-local/etapa-04.md:198:2. **`universe.py` sin imports de LEAN:** mantener el archivo libre de `AlgorithmImports`. Esto permite correrlo en el host Python (scripts, tests rápidos) y facilita los tests con mocks simples. `main.py` pasa `self.object_store` directamente; `UniverseSpec` solo necesita que tenga `.read(key) -> str`.
.claude/fase-1-desarrollo-local/etapa-04.md:204:5. **Alias map como constante de módulo:** definir en `universe.py` un `dict` `COLUMN_ALIASES = {"Symbol": "ticker", "5D Avg Vol": "avg_vol_5d", ...}`. Si en el futuro Barchart cambia un nombre de columna, hay un solo lugar para corregirlo. El alias map es el contrato §5 de PLAN.md — no duplicar en `strategies.json`.
.claude/fase-1-desarrollo-local/etapa-04.md:207:   - `max_tickers` = tope duro de seguridad en la carga del universo (≤200). Viene de `env_cfg["max_universe"]`.
.claude/fase-1-desarrollo-local/etapa-04.md:213:8. **`env=dev` en `lean.json` → `max_universe=10`:** en backtest de desarrollo, solo se cargan 10 tickers por estrategia. Los primeros 10 del DataFrame post-filtro (sin orden garantizado por pandas, pero determinista en la misma sesión). Esto acelera backtests y reduce el warmup de Etapa 5.
.claude/fase-1-desarrollo-local/etapa-04.md:219:- [ ] `core/universe.py` existe y exporta `UniverseSpec`
.claude/fase-1-desarrollo-local/etapa-04.md:220:- [ ] `lean backtest "trade-scanner"` loguea `universe loaded: N tickers` para cada una de las 4 estrategias durante `initialize()`, sin errores
.claude/fase-1-desarrollo-local/etapa-04.md:223:- [ ] `UniverseSpec` no importa nada de `AlgorithmImports` (verificado por `grep -n "AlgorithmImports" core/universe.py` → sin resultados)
.claude/fase-1-desarrollo-local/etapa-04.md:230:- [ ] **¿El filtro `df.query()` es suficiente o necesitamos expresiones más complejas?** El filtro actual (`avg_vol_5d > 1e6 and price > 5`) es sencillo y cabe en pandas `query()`. Si en el futuro se necesitan funciones (ej. `pct_chg_5d.abs() > 0.05`), `query()` lo soporta con `@variable` y funciones de pandas. No es un bloqueante para V1.
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:1:### Etapa 4 — UniverseSpec
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:5:| P1 | `UniverseSpec`: normalización de alias de columnas | Al leer el CSV, renombrar columnas según el alias map (contrato §5 de PLAN.md). El filtro declarativo usa alias; el CSV fuente usa nombres originales. `UniverseSpec` hace el rename antes de aplicar `eval()`. |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:6:| P2 | `UniverseSpec`: footer strip | Descartar filas donde `ticker` no matchee `^[A-Z]{1,5}$`. El CSV en ObjectStore llega con footer de Barchart; la validación es responsabilidad de `UniverseSpec`, no del script de siembra. |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:7:| P3 | `UniverseSpec`: `direction` no es campo de universo | El campo `direction` de la estrategia debe estar disponible para `ScanResult`, pero `UniverseSpec` no lo necesita (solo filtra tickers). El pipeline (Etapa 7) lo propaga. No diseñar `UniverseSpec` con ese acoplamiento. |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:8:| P4 | `main.py`: leer `env_cfg["top_n"]` y `env_cfg["max_universe"]` | `main.py` debe leer `self.get_parameter("env", "prod")` y extraer `top_n`/`max_universe` del bloque `environments`. Estos valores se pasan al pipeline cuando se instancie en Etapa 7. En Etapa 4 ya se puede leer y loguear para verificar. |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:9:| P7 | Actualizar spec Etapa 4 | El spec debe referenciar el contrato de alias de §5 (PLAN.md) y la regla de footer strip. `UniverseSpec` no necesita conocer `direction` ni `main_timeframe`; el pipeline (Etapa 7) los propaga al `ScanResult`. |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:18:| `filter_expr="avg_vol_5d > 1e6 and price > 5"`: ~74 advances, ~68 declines | ✅ | `advances: 74 tickers`, `declines: 68 tickers` |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:22:| `core/__init__.py` exporta `UniverseSpec` | ✅ | Agregado `from core.universe import UniverseSpec` |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:30:| 4 líneas `universe loaded` durante `initialize()` | ✅ | `[swing_eod]`, `[swing_eod_short]`, `[market_close]`, `[market_close_short]` |
.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md:36:**Nota:** El spec menciona `max_universe=10` para dev, pero `strategies.json` tiene `max_universe=2` (definido en Etapa 3). El código es correcto; la discrepancia está en el número del spec. Los parámetros del algoritmo viven en `trade-scanner/config.json`, no en `lean.json` (descubrimiento D-E4: LEAN lee `get_parameter()` desde el `config.json` del proyecto).
docs/ROADMAP.md:93:## Etapa 4 — UniverseSpec

codex
La búsqueda estática no encontró órdenes ejecutables en código del algoritmo; las coincidencias son instrucciones/documentación o nombres de tests. También confirmé que `core/universe.py` no importa `AlgorithmImports`; los imports LEAN fuera de L5 que aparecen son de etapas posteriores (`timeframes`/`symbol_data`) y no pertenecen a la superficie de Etapa 4.
exec
/bin/zsh -lc "nl -ba AGENTS.md | sed -n '1,260p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "nl -ba README.md | sed -n '90,130p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
    90	        "max_extension_pct": 0.10
    91	      }
    92	    }
    93	  }
    94	}
    95	```
    96	
    97	**Cambiar fuente de datos:** solo editar el proveedor en `lean.json` (Alpaca → QC cloud u otro soportado). El código no cambia.
    98	
    99	---
   100	
   101	## Universo de tickers
   102	
   103	El universo se carga desde un CSV en `universes/`. Columnas mínimas:
   104	
   105	```csv
   106	ticker,price,avg_dollar_volume
   107	AAPL,232.5,1200000000
   108	MSFT,415.0,950000000
   109	```
   110	
   111	Columnas adicionales son ignoradas a menos que el filtro declarativo las use. El filtro se define en `config.json` como string evaluable: `"price > 5 and avg_dollar_volume > 5e6"`. Tope duro: 200 tickers post-filtro.
   112	
   113	Para actualizar el universo:
   114	```bash
   115	# 1. Reemplazar universes/swing.csv
   116	# 2. Re-sembrar en ObjectStore
   117	bash Screener/scripts/seed_object_store.sh
   118	```
   119	
   120	---
   121	
   122	## Salida
   123	
   124	Cada ejecución de una estrategia produce un archivo en `storage/results/` (ObjectStore local del CLI):
   125	
   126	```
   127	strategy,as_of,ticker,partial_bar,day_change_pct,sma20_d,dist_sma20_d_pct,sma20_w,...,passed_rules
   128	swing_eod,2026-06-09T16:05:00Z,NVDA,false,4.32,105.2,3.1,98.4,...,"AboveSMA20_D|AboveSMA20_W|AboveSMA20_M|NotExtended"
   129	```
   130	

 succeeded in 0ms:
     1	# Instrucciones de revisión del proyecto — Screener sobre LEAN
     2	
     3	## Rol
     4	Eres un revisor de código senior **especializado en QuantConnect/LEAN y Python 3.11**.
     5	Tu misión es auditar este proyecto de forma **exhaustiva y end-to-end**: desde la
     6	arquitectura por capas hasta la corrección línea a línea de cada función, verificando
     7	que (1) usa la API de LEAN de forma real y correcta, (2) las funciones hacen lo que
     8	dicen y no tienen bugs, y (3) lo construido sigue la línea del objetivo del proyecto
     9	(SPECS/PLAN). **NO modifiques ningún archivo.** Solo lee, analiza y reporta. Run de
    10	**solo lectura**.
    11	
    12	## Contexto del proyecto (qué estás revisando)
    13	Screener multi-estrategia construido sobre el motor **LEAN** (QuantConnect, Python
    14	3.11). Carga universos desde CSV (≤200 tickers vía ObjectStore), mantiene indicadores
    15	en los timeframes que cada estrategia declara (día/semana/mes) con consolidators e
    16	indicadores nativos de LEAN, evalúa reglas declarativas en horarios programados y emite
    17	watchlists con evidencia.
    18	
    19	**Restricción de producto que condiciona toda la revisión:** en V1 **solo escanea —
    20	está prohibido colocar órdenes**. Cualquier `self.market_order`, `self.set_holdings`,
    21	`self.buy/sell`, `self.liquidate` o similar es un hallazgo **CRÍTICO**.
    22	
    23	Fuentes de verdad del diseño (consúltalas, no las contradigas): `PLAN.md` (operativa,
    24	máxima precedencia) > `SPECS.md` (producto, entidades, criterios) > `CLAUDE.md`
    25	(convenciones). Decisiones de diseño congeladas en `.claude/decisions/ADR-*.md` y
    26	`docs/conceptos/*.md`. Ante conflicto entre lo que ves en el código y estos documentos,
    27	**repórtalo como hallazgo, no asumas que el código tiene razón**.
    28	
    29	## Metodología de revisión (sigue este orden — no saltes pasos)
    30	La exhaustividad no es opcional: la calidad del reporte se mide por cuántos de estos
    31	pasos ejecutaste de verdad, no por cuántos archivos abriste.
    32	
    33	1. **Lee primero el diseño.** `PLAN.md` (§2–§5 y la etapa marcada *en progreso*/
    34	   *pendiente*), `SPECS.md` (entidades + criterios de aceptación), los ADRs y
    35	   `docs/conceptos/`. Anota los criterios de aceptación verificables: serán tu checklist
    36	   de trazabilidad en el paso 5.
    37	2. **Mapea capas → archivos** (ver "Mapa de revisión por archivo"). Confirma que la
    38	   estructura de carpetas refleja L1–L6 y que cada módulo está en su capa.
    39	3. **Lee TODO archivo** — no solo los `.py` obvios: `config/*.json`, `universes/*.csv`,
    40	   `scripts/*.{sh,py}`, `lean.json`, `trade-scanner/config.json`, `PLAN.md`, `SPECS.md`,
    41	   `README.md`, `docs/`, ADRs y los **tests** (`trade-scanner/tests/`).
    42	4. **Traza cada función de cabo a rabo.** Para cada función pública de `core/` y
    43	   `strategies/`: ¿qué entra, qué sale, qué invariantes asume? Sigue el grafo de
    44	   llamadas desde `main.py` hasta las hojas (`features` → `symbol_data`/`timeframes`).
    45	   Verifica que cada llamada a una función propia pasa los tipos/keys que la callee
    46	   espera (p. ej. `snapshot[tf][period].bucket`, `symbol_data_map: {Symbol: SymbolData}`).
    47	5. **Traza el objetivo → código (alineación).** Toma cada criterio de aceptación de
    48	   SPECS y cada "Done when" de la etapa activa de PLAN y encuéntralo en el código y en
    49	   un test. Si un criterio no tiene implementación o test que lo demuestre → hallazgo.
    50	   Si el código hace algo que NINGÚN documento pide (scope creep) → hallazgo.
    51	6. **Verifica la API de LEAN** método por método (ver sección dedicada).
    52	7. **Caza bugs** en bordes (buckets, simetría long/short, fríos, datos faltantes).
    53	8. **Cierra con el resumen ejecutivo** (top 5).
    54	
    55	## Flujo end-to-end que debes poder reconstruir y auditar
    56	Reconstruye este camino y verifica cada eslabón; un fallo en cualquiera invalida el scan:
    57	
    58	```
    59	config/strategies.json (ObjectStore)
    60	  → main.initialize(): parse config → universe (≤200) → SymbolData por símbolo
    61	    (unión de timeframes) → consolidators+indicadores → set_warmup derivado → history+flush
    62	  → ScanPipeline por estrategia (rules ya construidas con side espejado, D7.1/D7.3)
    63	  → schedule.on(horario) → pipeline.scan(symbol_data_map, as_of, log)
    64	      gate B (series referenciadas is_ready) → ranking top_n por day_change_pct
    65	      → build_position_snapshot (snapshot único, A.1) → cascada de rules → ScanResult
    66	  → core/output.py (switch local/cloud) → notificación/archivo + evidencia
    67	```
    68	Para cada etapa del camino pregúntate: ¿los datos que llegan tienen la forma que el
    69	siguiente eslabón asume? ¿se propagan los símbolos fríos/sin datos sin contaminar el scan?
    70	
    71	## Stack tecnológico (contexto para juzgar el código)
    72	| Componente | Elección |
    73	|---|---|
    74	| Engine | LEAN open source (Python 3.11) |
    75	| API del algoritmo | Solo `QCAlgorithm` (API moderna en snake_case) |
    76	| Contenerización | Docker Desktop, imagen oficial `quantconnect/lean` (engine y tests) |
    77	| Ejecución | `lean backtest` / `lean live` vía LEAN CLI |
    78	| Config y universos | ObjectStore (`config/strategies.json`, `universes/*.csv`) |
    79	| Datos Fase 1 | Stooq → LEAN (ADR-003); Alpaca free (IEX) diferido |
    80	| Datos = configuración | La fuente vive en `lean.json`, nunca en el código |
    81	| Notificación/salida | `NotificationManager` (cloud) / archivo + log (local), switch solo en `output.py` |
    82	
    83	**Principio rector:** el código solo habla con la API de `QCAlgorithm`. Fuente de
    84	datos, broker y entorno son configuración externa, jamás lógica.
    85	
    86	## Arquitectura por capas (verifica cada cambio contra estas fronteras)
    87	```
    88	L6  lean backtest | lean live (Docker)      runtime/deploy; el código no la toca
    89	L5  main.py        orquestación QCAlgorithm: config → universos → SymbolData+warmup → schedule → output
    90	L4  strategies/ + core/{pipeline,rules}.py  estrategias = composición declarativa de Rules
    91	L3  core/features.py                          cómputos reutilizables sobre SymbolData
    92	L2  core/{symbol_data,timeframes}.py          consolidators + indicadores + working bar + warmup
    93	L1  lean.json · ObjectStore (strategies.json + universos CSV)
    94	```
    95	Reporta como violación de arquitectura cualquiera de estos casos:
    96	- L3/L4 que **pidan datos o calculen indicadores** (deben leer estado de `SymbolData`; el scan es lectura, no cómputo).
    97	- L3/L4 que importen `AlgorithmImports` (deben ser negocio puro, testeable sin CLR — patrón `features`/`rules`/`pipeline`).
    98	- Uso de `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify` **fuera de `main.py`**.
    99	- L4 que hable con `QCAlgorithm` para loguear/notificar: el log debe ser un **callable inyectado** (ver `ScanPipeline.scan(..., log=...)`), no `self.debug/self.log`.
   100	- Switch local/cloud **fuera de `core/output.py`**.
   101	- Más de un `SymbolData` por símbolo (un símbolo = un `SymbolData`, unión de timeframes de todas las estrategias que lo usan).
   102	- `core/universe.py` importando `AlgorithmImports` (debe ser testeable con mock, sin CLR).
   103	
   104	## Mapa de revisión por archivo (qué buscar en cada módulo)
   105	Recorre todos; los `core/` son negocio puro y los reglones de pureza aplican a cada uno.
   106	
   107	- **`trade-scanner/main.py` (L5).** Único punto que toca `QCAlgorithm`. Verifica:
   108	  orden config→universe→SymbolData→warmup→schedule→output; warmup **derivado** de los
   109	  timeframes (no hardcodeado); flush del consolidator tras el warmup en batch
   110	  (`scan(end_time)` o barra trailing); suscripción `Resolution.MINUTE` para la barra
   111	  parcial; un solo `SymbolData` por símbolo; `direction→side` resuelto **una vez** al
   112	  construir los `ScanPipeline` (D7.3), no en el hot path; cero órdenes.
   113	- **`core/symbol_data.py` (L2).** Consolidators (diario + `Calendar.WEEKLY`/`MONTHLY`),
   114	  `register_indicator` sobre el consolidator, `working_bar`, `is_ready(tf, period)`,
   115	  `scan(time)`. Verifica que las SMAs W/M **no** incluyen la barra en curso y que
   116	  `is_ready` es por (tf, period), no global.
   117	- **`core/timeframes.py` (L2).** `TIMEFRAMES` (registro y orden canónico D, W, M),
   118	  fórmula de profundidad de warmup (PLAN.md §4: `D:n→n+5`, `W:n→n×5+10`, `M:n→n×21+21`).
   119	  Marca cualquier número de barras fijo que no salga de aquí.
   120	- **`core/features.py` (L3).** `build_position_snapshot`, `snapshot_evidence`,
   121	  `day_change_pct`, `reference_price`, `BUCKETS`, `mirror_buckets`, `FeatureNotReady`.
   122	  Negocio puro. Verifica: bucketización (fronteras, epsilon, simetría), que lee SMAs ya
   123	  listas y lanza `FeatureNotReady` (no silencia) ante indicador frío/SMA==0.
   124	- **`core/rules.py` (L4).** `SMAPositionRule`, `NotExtended`, `RuleResult`. Verifica:
   125	  validación fail-fast de `buckets_allowed ⊆ BUCKETS`; mirror al `side` aplicado **una
   126	  vez** en construcción (no en `evaluate`); AND estricto **sin short-circuit** (evidencia
   127	  completa aun si no pasa); que `evaluate` solo LEE `snapshot[tf][period].bucket`.
   128	- **`core/pipeline.py` (L4).** `ScanPipeline`, `ScanResult`, `format_*_line`. Verifica el
   129	  embudo: gate por series referenciadas (no `is_ready()` global), ranking `top_n` por
   130	  `day_change_pct` (desc long / asc short, tie-break ticker), snapshot único por símbolo,
   131	  cascada por rule, orden determinista (reproducibilidad), `log` inyectado.
   132	- **`strategies/{base,swing_eod,market_close}.py` (L4).** Composición declarativa.
   133	  Verifica que las estrategias long/short se derivan por **mirror de buckets**, no se
   134	  duplican; que los umbrales/horarios/top_n vienen de config, no del código.
   135	- **`core/output.py` (L5/salida).** Único switch local↔cloud (`live_mode` + parámetro de
   136	  entorno). Verifica que la portabilidad no depende de rutas absolutas ni `open()`.
   137	- **`core/email_render.py` / `scripts/notify_email.py`.** Render de la watchlist;
   138	  saneo de datos; sin credenciales embebidas.
   139	- **`core/universe.py` (L1↔L5).** Lee CSV vía ObjectStore (mock-friendly, sin
   140	  `AlgorithmImports`); tope duro 200 post-filtro; manejo de CSV malformado.
   141	- **`config/strategies.json`, `config/notifications.json`, `universes/*.csv`,
   142	  `lean.json`, `trade-scanner/config.json`.** Coherencia con lo que el código espera;
   143	  sin secretos; parámetros escalares en `trade-scanner/config.json`, config anidada en
   144	  ObjectStore.
   145	- **`scripts/*.{sh,py}`.** Receta de tests en Docker (`run_tests.sh`), seeds, conversión
   146	  Stooq. Sin rutas frágiles ni credenciales.
   147	- **`trade-scanner/tests/`.** Cobertura y calidad (ver sección Tests).
   148	
   149	## Validez de la API de LEAN (revisión técnica obligatoria)
   150	Para **cada método, propiedad o patrón de LEAN** que aparezca en el código, verifica
   151	que sea **real y se use correctamente**. No asumas que un nombre plausible existe.
   152	
   153	**Método de verificación (no solo "verifica"):** confirma cada símbolo de LEAN contra
   154	una fuente — los `AlgorithmImports`/stubs dentro de la imagen
   155	(`/Lean/Launcher/bin/Debug`), la doc oficial de QuantConnect, o el uso ya validado en
   156	etapas previas citado en los ADR/checkpoints. Si no puedes confirmarlo, **decláralo
   157	explícitamente como "verificar contra la API de LEAN"** en el hallazgo en vez de
   158	afirmar que existe o que está mal.
   159	
   160	- **API moderna en snake_case.** LEAN Python expone `self.schedule.on`,
   161	  `self.add_equity`, `register_indicator`, `self.history`, `self.object_store`,
   162	  `self.set_warmup`, etc. Marca llamadas en PascalCase obsoleto o nombres inventados
   163	  que no existen en `QCAlgorithm`.
   164	- **Barras W/M con consolidators nativos.** Deben usarse `TradeBarConsolidator` con
   165	  `Calendar.WEEKLY` / `Calendar.MONTHLY` e indicadores vía `register_indicator` sobre
   166	  el consolidator. **Prohibido resampling manual con pandas** dentro del algoritmo
   167	  para construir barras/SMAs semanales o mensuales → hallazgo ALTO.
   168	- **Convención de calendario.** `Calendar.WEEKLY` agrupa lunes→domingo (cierre
   169	  efectivo viernes); `Calendar.MONTHLY` es mes calendario. Si el código asume otra
   170	  cosa, repórtalo.
   171	- **Warmup derivado, nunca hardcodeado.** La profundidad de historia se deriva de los
   172	  timeframes declarados (fórmula en PLAN.md §4: `D:n→n+5`, `W:n→n×5+10`,
   173	  `M:n→n×21+21`). Un número de barras fijo en código es un hallazgo.
   174	- **Emisión perezosa del consolidator.** Los consolidators no emiten la barra hasta
   175	  que llega una posterior o se llama `scan(time)`. El warmup debe cerrar con un flush
   176	  (`scan()` o barra trailing). Revisa que el código no asuma emisión inmediata.
   177	- **Barra parcial del día** = `working_bar` del consolidator diario (requiere
   178	  suscripción `Resolution.MINUTE`). Los indicadores W/M **no** incluyen la barra en
   179	  curso: eso es correcto y deseado. Marca como bug cualquier intento de "corregir" esto.
   180	- **Indicadores fríos.** Símbolos con warmup incompleto deben excluirse del scan
   181	  (`is_ready()` por tf/period); evaluar reglas con indicadores no listos es un hallazgo.
   182	- **ObjectStore, no `open()`.** Config y universos se leen vía `self.object_store`
   183	  (en local vive en `storage/`, no en `data/object-store/`). Rutas absolutas con
   184	  `open()` rompen portabilidad → hallazgo.
   185	- **Parámetros.** `self.get_parameter()` lee de `trade-scanner/config.json`, no de
   186	  `lean.json`; solo para escalares (ej. `env`). La config anidada de estrategias va a
   187	  ObjectStore. Marca umbrales/horarios/top_n/archivos de universo **hardcodeados en
   188	  código** o puestos en el `config.json` del proyecto cuando deberían estar en
   189	  `config/strategies.json`.
   190	
   191	## Corrección funcional (¿las funciones realmente funcionan?)
   192	Más allá de que la API exista, verifica que cada función produce el resultado correcto:
   193	
   194	- **Contratos de entrada/salida.** Cada función pública: ¿valida sus precondiciones o
   195	  asume? ¿el tipo/forma de retorno coincide con lo que el caller usa? Rastrea las keys
   196	  de los dicts compartidos (`snapshot[tf][period]`, `symbol_data_map`, evidencia anidada
   197	  `{tf:{period:{value,distance_pct,bucket}}}`) extremo a extremo.
   198	- **Pureza declarada vs. real.** `features`/`rules`/`pipeline` se declaran negocio puro:
   199	  confirma cero `AlgorithmImports`, cero side effects, cero estado mutable compartido.
   200	- **Determinismo/reproducibilidad.** El scan debe ser reproducible (orden estable por
   201	  ticker, sorts con tie-break definido). Marca cualquier iteración sobre sets/dicts cuyo
   202	  orden afecte la salida.
   203	- **Simetría long/short.** Verifica que el lado short es el espejo exacto del long vía
   204	  `mirror_buckets` (un solo punto), no lógica duplicada ni con signos invertidos a mano.
   205	  Un bucket o umbral espejado mal es un bug silencioso.
   206	- **Propagación de fallos.** `FeatureNotReady` debe aflorar y excluir el símbolo (gate o
   207	  backstop), nunca tragarse ni convertirse en un valor por defecto que entre al ranking.
   208	- **Coherencia con la evidencia.** El `ScanResult` debe reflejar lo que las rules
   209	  evaluaron (mismas series, mismos buckets); `sma_evidence` es proyección del snapshot
   210	  único, no un recompute → verifica que no diverja.
   211	
   212	## Qué revisar
   213	
   214	### Reglas duras del proyecto (violarlas = PR rechazado)
   215	- Cualquier orden o gestión de portfolio (`market_order`, `set_holdings`, `liquidate`, etc.) → **CRÍTICO**.
   216	- SDKs de Alpaca/brokers/proveedores de datos embebidos en el código (solo `QCAlgorithm`).
   217	- Cualquier cosa que rompa la portabilidad local ↔ QC cloud sin cambios de código.
   218	- Credenciales (QC, Alpaca, Gmail/SMTP) dentro del repo o en archivos versionados.
   219	- Universo por encima del tope duro de 200 tickers post-filtro.
   220	
   221	### Calidad de código
   222	- Inconsistencias de estilo entre archivos (snake_case, type hints en `core/` y `strategies/`).
   223	- Código duplicado o lógica que debería abstraerse (ej. reglas largo/corto que deberían derivarse por mirror de buckets, no duplicarse).
   224	- Funciones largas o con múltiples responsabilidades.
   225	- Variables mal nombradas o confusas; docstrings que explican el "cómo" en vez del "qué/por qué".
   226	- Magic numbers o strings hardcodeados (umbrales de buckets, periodos de SMA, horarios → deben venir de config).
   227	
   228	### Bugs y lógica
   229	- Condiciones de borde de SMAs/buckets (frontera exacta, epsilon, simetría largo/corto).
   230	- Manejo de símbolos con datos faltantes o warmup incompleto.
   231	- Manejo de errores ausente al leer ObjectStore / parsear CSV / aplicar filtros declarativos.
   232	- Validaciones faltantes en config de estrategias (buckets permitidos, direction, thresholds) — deben validarse en construcción (fail-fast), no en el hot path.
   233	- Off-by-one en `top_n`, ranking, o profundidad de warmup.
   234	
   235	### Seguridad
   236	- Secrets o credenciales en código o en archivos versionados (deben estar solo en `.env` gitignoreado).
   237	- Inputs externos no saneados (CSV de universo, filtros declarativos, config de estrategias).
   238	- Dependencias desactualizadas con vulnerabilidades conocidas.
   239	
   240	### Arquitectura
   241	- Violaciones de separación de capas (ver sección de arquitectura arriba).
   242	- Acoplamiento excesivo entre módulos; dependencias circulares.
   243	- Estructura de carpetas que no refleja las capas L1–L6.
   244	
   245	### Alineación con el objetivo (trazabilidad)
   246	- Cada criterio de aceptación de `SPECS.md` y cada "Done when" de la etapa activa de
   247	  `PLAN.md` tiene implementación **y** un test que lo demuestra. Lista los que no.
   248	- Scope creep: código que implementa algo que ningún documento de diseño pide.
   249	- Desviaciones de los ADRs / `docs/conceptos/` sin justificación documentada.
   250	
   251	### Tests
   252	- Cobertura ausente en funciones críticas (features, rules, buckets, warmup, pipeline, output, universe).
   253	- Tests que validan implementación en vez de comportamiento; SMAs que no son verificables a mano (valores construidos con `TradeBar`s sintéticos donde la SMA esperada se calcula a ojo).
   254	- Setup frágil: los tests corren **dentro de la imagen LEAN** vía `scripts/run_tests.sh`
   255	  (pytest local fuera de Docker no tiene `AlgorithmImports`). Marca tests que asuman
   256	  pytest del host o que construyan símbolos con `Symbol.create(..., EQUITY, ...)`
   257	  (lanza NullReference fuera del engine; usar `SecurityIdentifier.generate_equity`).
   258	- Tests que NO cubren la simetría long/short, los fríos, ni la reproducibilidad.
   259	
   260	## Formato de salida

exec
/bin/zsh -lc "nl -ba docs/ROADMAP.md | sed -n '80,115p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
    80	- [x] strategies.json con environments y 4 estrategias
    81	- [x] Seed de CSVs a ObjectStore
    82	- [x] Archivo de fuentes procesadas
    83	
    84	### Done when
    85	- [x] Reporte de ambos CSVs generado
    86	- [x] Contrato de entrada actualizado
    87	- [x] Contrato de salida actualizado
    88	- [x] ObjectStore sembrado correctamente
    89	- [x] Backtest dispara las 4 estrategias
    90	
    91	---
    92	
    93	## Etapa 4 — UniverseSpec
    94	
    95	Estado: completada  
    96	Objetivo: cargar universos por estrategia desde ObjectStore con filtro declarativo.
    97	
    98	### Alcance
    99	- [x] core/universe.py
   100	- [x] Alias normalizados de columnas
   101	- [x] Footer strip
   102	- [x] Filtro vía df.query()
   103	- [x] Tope duro de 200 símbolos
   104	- [x] refresh_universe() no-op
   105	- [x] Tests de universo
   106	
   107	### Done when
   108	- [x] Backtest loguea conteo por estrategia
   109	- [x] Tests de filtro, tope y CSV malformado verdes
   110	- [x] Sin imports de AlgorithmImports
   111	
   112	---
   113	
   114	## Etapa 5A — TimeframeSpec + SymbolData
   115	

exec
/bin/zsh -lc "nl -ba CLAUDE.md | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	# CLAUDE.md — Screener de Acciones sobre LEAN
     2	
     3	Screener multi-estrategia sobre el motor LEAN (QuantConnect, Python 3.11). Carga universos desde CSV (≤200 tickers), mantiene indicadores en los timeframes que cada estrategia declara, evalúa reglas en horarios programados y emite watchlists con evidencia. **Solo escanea: prohibido colocar órdenes en V1.**
     4	
     5	## Documentos y precedencia
     6	
     7	1. `PLAN.md` — plan de trabajo por etapas con estado y checkboxes. **Fuente de verdad operativa.**
     8	2. `SPECS.md` — contexto de producto, entidades, criterios de aceptación.
     9	3. Ante conflicto: PLAN.md > SPECS.md > este archivo.
    10	
    11	## Flujo de trabajo (spec-driven, obligatorio)
    12	
    13	1. Lee `PLAN.md` y localiza la primera etapa con **Estado: pendiente** o **en progreso**.
    14	2. Trabaja SOLO esa etapa. No mezcles alcance de etapas futuras.
    15	3. Al empezar: cambia su Estado a `en progreso`. Al cumplir cada criterio: marca su checkbox `- [x]`.
    16	4. Una etapa se cierra solo cuando TODOS sus "Done when" están verificados (no asumidos: ejecutados).
    17	5. Cierre: Estado a `completada`, commit, resumen breve de lo hecho y qué sigue.
    18	6. Si algo del plan es inviable o ambiguo: detente y pregunta ANTES de desviarte. Si cambia el diseño, propón la edición a PLAN.md y espera aprobación.
    19	
    20	## Comandos
    21	
    22	```bash
    23	lean backtest "trade-scanner"            # backtest local (Docker)
    24	lean live "trade-scanner"                # paper live local (requiere QC paid — ver ADR-002)
    25	lean research "trade-scanner"            # Jupyter para exploración
    26	bash scripts/run_tests.sh                # pytest DENTRO de la imagen LEAN (único modo válido)
    27	bash scripts/seed_object_store.sh        # config/*.json (+ universes/*.csv) → storage/ (ObjectStore real)
    28	bash scripts/seed_sample_data.sh         # SPY sample data libre → data/equity/ (avanza el reloj del backtest)
    29	python scripts/explore_universe.py <csv> # perfilado del CSV de universo
    30	```
    31	
    32	Ejecuta todos los comandos `lean` desde la raíz del workspace (donde vive `lean.json`).
    33	Activa el virtualenv antes de cualquier comando lean: `source .venv/bin/activate`.
    34	
    35	## Arquitectura (resumen; detalle en PLAN.md §2–§4)
    36	
    37	```
    38	L6 lean backtest | lean live (Docker)   boundary de runtime/deploy; el código no la toca
    39	L5 main.py        orquestación: config → universos → SymbolData+warmup → schedule → output
    40	L4 strategies/ + core/{pipeline,rules}.py   estrategias = composición declarativa de Rules
    41	L3 core/features.py    cómputos reutilizables sobre SymbolData
    42	L2 core/{symbol_data,timeframes}.py   consolidators + indicadores + working bar + warmup
    43	L1 lean.json · ObjectStore (config/strategies.json + universos CSV)
    44	```
    45	
    46	Restricciones entre capas — verifícalas en cada cambio:
    47	- L3/L4 leen estado de `SymbolData`; NUNCA piden datos ni calculan indicadores.
    48	- Solo `main.py` usa `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify`.
    49	- Un símbolo = un `SymbolData` compartido (unión de timeframes de todas las estrategias que lo usan).
    50	- El switch local/cloud vive SOLO en `core/output.py`.
    51	
    52	## Reglas duras (violarlas = PR rechazado)
    53	
    54	- El código solo habla con la API de `QCAlgorithm`. Sin SDKs de Alpaca/brokers/datos.
    55	- Portable local ↔ QC cloud sin cambios de código. Fuente de datos = solo `lean.json`.
    56	- Barras y SMAs de W/M/etc. con consolidators e indicadores de LEAN (`Calendar.WEEKLY`, `Calendar.MONTHLY`, `register_indicator`). PROHIBIDO resampling manual con pandas dentro del algoritmo.
    57	- Timeframes NO fijos: cada estrategia los declara en `config/strategies.json` (ObjectStore); consolidators y profundidad de warmup se derivan de ahí (fórmula en PLAN.md §4). Nunca un número de warmup hardcodeado.
    58	- Umbrales, horarios, top_n, archivos de universo: en `config/strategies.json` (ObjectStore), jamás en código ni en el `config.json` del proyecto (solo archivo de LEAN). Ver PLAN.md §4.
    59	- Universo: tope duro 200 tickers post-filtro.
    60	- Cero órdenes: nada de `self.market_order` ni similares.
    61	- Credenciales (QC, Alpaca) fuera del repo siempre.
    62	
    63	## Convenciones de código
    64	
    65	- API Python moderna de LEAN en snake_case (`self.schedule.on`, `self.add_equity`, `register_indicator`).
    66	- Patrón `SymbolData` por símbolo; features como propiedades/métodos de lectura.
    67	- Type hints en todo `core/` y `strategies/`. Docstrings cortos: qué y por qué, no cómo.
    68	- Tests: pytest con `TradeBar`s sintéticos construidos a mano (valores de SMA verificables manualmente). Corren dentro de la imagen LEAN vía `scripts/run_tests.sh` — nunca asumas que pytest local fuera de Docker tiene `AlgorithmImports`.
    69	- Commits: uno por unidad coherente, mensaje imperativo, referencia a la etapa (`[Etapa 5] ...`).
    70	
    71	## Gotchas de LEAN (memorízalos)
    72	
    73	- `Calendar.WEEKLY` agrupa lunes→domingo (cierre efectivo viernes); `Calendar.MONTHLY` mes calendario. Las SMAs deben cuadrar con la plataforma de referencia del trader (validación en Etapa 5).
    74	- Warmup: pide historia en batch (`self.history(symbols, n, Resolution.DAILY)`) y empuja cada barra a los consolidators del símbolo; los indicadores registrados se actualizan solos.
    75	- Barra parcial del día = `working_bar` del consolidator diario (requiere suscripción `Resolution.MINUTE`). Los indicadores W/M NO incluyen la barra en curso: eso es correcto y deseado (SMAs estables intradía).
    76	- ObjectStore local vive en `storage/` del workspace (el CLI lo monta en `/Storage` dentro de Docker); **no** es `data/object-store/`. La key `config/strategies.json` se lee desde `storage/config/strategies.json`. En cloud es transparente. Lee siempre vía `self.object_store`, nunca con `open()` a rutas absolutas.
    77	- Entorno: `self.live_mode` + parámetro de entorno deciden el sink de salida (solo dentro de `output.py`).
    78	- Alpaca free: datos IEX (volumen subestimado → usa volumen relativo, no absoluto), 15 min de delay, 100 calls/min (afecta warmup, no el scan).
    79	- Símbolos con warmup incompleto: excluir del scan y loguear, nunca evaluar reglas con indicadores fríos (`is_ready()`).
    80	- Python del host: el CLI y scripts auxiliares corren sobre Python 3.11 del virtualenv (`.venv`). El engine y los tests corren siempre dentro de la imagen Docker (`quantconnect/lean`). `python3` del sistema puede ser una versión diferente — nunca lo uses directamente.
    81	
    82	## Gotchas del workspace (descubiertos en Etapa 1)
    83	
    84	- **`lean init` requiere QC pago.** Pide seleccionar una organización vía API. En su lugar: descargar `Launcher/config.json` del repo público de LEAN en GitHub, aplicar `clean_lean_config()`, y añadir `"organization-id"` en `lean.json`.
    85	- **`organization-id` obligatorio en lean.json.** El CLI v1.0.x lanza error si el campo es nulo. Para backtest local usar placeholder `"00000000000000000000000000000000"` — nunca se valida contra QC. Reemplazar con org-id real antes de `lean live`.
    86	- **El CLI reformatea lean.json a JSON estándar.** Elimina comentarios `//` en la primera escritura. Comportamiento esperado; el engine lo acepta igual.
    87	- **`lean project-create` requiere `--language python` explícito** si `default-language` no está seteado en la config del CLI.
    88	- **`${VAR}` NO se expande en lean.json.** El CLI no hace sustitución de variables de entorno. Credenciales en campos vacíos en lean.json (commiteado) + valores reales solo en `.env` (gitignoreado).
    89	- **`lean live` con Alpaca requiere QC paid (plan Researcher).** AlpacaBrokerage tiene `installs: true` → el CLI intenta descargar un módulo NuGet via API de QC. Sin licencia falla. Ver [ADR-002](.claude/decisions/ADR-002-qc-module-auth-constraint.md) y el flag en Etapa 9 de PLAN.md.
    90	- **Gitignore para artefactos del CLI:** añadir `**/backtests/`, `**/.idea/`, `**/.vscode/`, `**/research.ipynb` — el CLI los genera automáticamente y no deben commitearse.
    91	
    92	### Descubiertos en Etapa 2
    93	
    94	- **El ObjectStore local del CLI es `storage/`, NO `data/object-store/`.** El CLI monta `<workspace>/storage/` en `/Storage` (`lean_runner.py`: `storage_dir = cli_root/"storage"`). Sembrar en `data/object-store/` da `Object with path '...' was not found`. `storage/` está gitignoreado (copia regenerable; la fuente versionada vive en `config/`).
    95	- **Tests en Docker = receta pythonnet.** La imagen embebe Python en .NET y no trae pytest ni pythonnet standalone. `run_tests.sh`: `--entrypoint bash`, `pip install clr_loader pytest`, `PYTHONNET_RUNTIME=coreclr` + `PYTHONNET_CORECLR_RUNTIME_CONFIG=<Launcher.runtimeconfig.json>`, y `cd /Lean/Launcher/bin/Debug` (donde viven `AlgorithmImports.py` y los DLLs).
    96	- **El reloj del backtest no avanza sin datos.** Sin sample data el engine procesa "1 data point" y los `ScheduledEvents` no disparan. SPY como ancla de calendario (`Resolution.MINUTE`) + `seed_sample_data.sh` resuelven esto.
    97	
    98	### Descubiertos en Etapa 4
    99	
   100	- **`self.get_parameter()` lee de `trade-scanner/config.json`, NO de `lean.json`.** El campo `"parameters"` en `lean.json` (raíz del workspace) es configuración del engine LEAN y es ignorado por `get_parameter()`. Los parámetros escalares del algoritmo (ej. `"env": "dev"`) deben estar en `trade-scanner/config.json["parameters"]`. Config de negocio anidada sigue yendo a ObjectStore.
   101	- **`core/universe.py` no debe importar `AlgorithmImports`.** Mantenerlo libre de imports LEAN permite testearlo con `MockObjectStore` simple (sin CLR) y usarlo desde scripts del host. `main.py` pasa `self.object_store` en runtime; los tests pasan su propio mock.
   102	
   103	### Descubiertos en Etapa 5A
   104	
   105	- **La emisión del consolidator es perezosa SIEMPRE.** Incluso una barra diaria que llena exactamente el periodo `timedelta(days=1)` queda en `working_data` hasta que llega una barra posterior o un `scan(time)`; el lag se encadena a W/M. Consecuencia: el warmup debe cerrar con `SymbolData.scan(end_time de la última barra)` y los tests flushean con trailing bar o `scan()`.
   106	- **`scan()` también emite en consolidators de calendario** (`Calendar.WEEKLY`/`MONTHLY`): permite refrescar SMAs W/M el mismo día del cierre de periodo en runtime, sin esperar la primera barra diaria del periodo siguiente.
   107	- **Equivalencia exacta warmup/runtime verificada (T3.9).** El consolidator diario redondea `time` a 00:00: la barra construida desde minutos es idéntica a la diaria directa, y la cadena W/M hereda la identidad. No hay asimetría que compensar en `main.py`.
   108	- **`Symbol.create(..., EQUITY, ...)` fuera del engine lanza NullReference** (exige map file provider). En tests: `Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")`. Para scripts directos en la imagen (no `python -m pytest`), añadir `/Lean/Launcher/bin/Debug` al `PYTHONPATH`.
   109	
   110	## Definición de "verificado"
   111	
   112	Un checkbox de PLAN.md se marca solo si:
   113	1. `bash scripts/run_tests.sh` pasa, y
   114	2. cuando aplica, `lean backtest "trade-scanner"` corre sin errores y los logs/archivos demuestran el criterio (cita la evidencia en el resumen de cierre de etapa).

**Avoiding heredoc issues**

I encountered a problem with the Python heredoc failing because zsh in read-only can't create a temp file. So, I need to avoid heredoc and instead use a one-liner like `python -c '...'` which doesn’t require writing to a temporary file. Also, importing Python could create a pycache, but I might be able to prevent this with the `PYTHONDONTWRITEBYTECODE` environment variable. It seems that avoiding heredoc is the way forward!
codex
El intento de validación dinámica con heredoc falló porque el shell quiso crear un temporal y el sandbox es de solo lectura. Lo repito con `python -c`, que no escribe archivos y mantiene `PYTHONDONTWRITEBYTECODE=1`.
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python -c \"import sys; from pathlib import Path; sys.path.insert(0, 'trade-scanner'); from core.universe import UniverseSpec;\\nclass Store:\\n    def read(self, key): return Path('storage', key).read_text()\\nfor key in ['universes/swing_advances.csv','universes/swing_declines.csv','universes/sample_dev.csv']:\\n    result = UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 200).load(Store()); print(key, len(result), result[:10], result[-3:])\\nfor key in ['universes/swing_advances.csv','universes/swing_declines.csv','universes/sample_dev.csv']:\\n    result = UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 4).load(Store()); print(key, 'cap4', len(result), result)\"" in /Users/guille/Documents/quant/trade-scanner
 exited 1 in 0ms:
  File "<string>", line 1
    import sys; from pathlib import Path; sys.path.insert(0, 'trade-scanner'); from core.universe import UniverseSpec;\nclass Store:\n    def read(self, key): return Path('storage', key).read_text()\nfor key in ['universes/swing_advances.csv','universes/swing_declines.csv','universes/sample_dev.csv']:\n    result = UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 200).load(Store()); print(key, len(result), result[:10], result[-3:])\nfor key in ['universes/swing_advances.csv','universes/swing_declines.csv','universes/sample_dev.csv']:\n    result = UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 4).load(Store()); print(key, 'cap4', len(result), result)
                                                                                                                       ^
SyntaxError: unexpected character after line continuation character

codex
El segundo intento fue solo un problema de quoting. Haré la misma validación con una clase construida en una línea para evitar cualquier heredoc o archivo temporal.
exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python -c \"import sys; from pathlib import Path; sys.path.insert(0, 'trade-scanner'); from core.universe import UniverseSpec; Store=type('Store', (), {'read': lambda self, key: Path('storage', key).read_text()}); keys=['universes/swing_advances.csv','universes/swing_declines.csv','universes/sample_dev.csv']; [print(key, len(UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 200).load(Store())), UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 200).load(Store())[:10], UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 200).load(Store())[-3:]) for key in keys]; [print(key, 'cap4', len(UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 4).load(Store())), UniverseSpec(key, 'avg_vol_5d > 1e6 and price > 5', 4).load(Store())) for key in keys]\"" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 492ms:
universes/swing_advances.csv 74 ['AAOI', 'ACDC', 'ADEA', 'ADPT', 'AJG', 'ALOY', 'AMN', 'AMPG', 'AVR', 'AXON'] ['VSA', 'VSH', 'WRB']
universes/swing_declines.csv 68 ['ABVX', 'ACHR', 'AEVA', 'AG', 'ASM', 'ASST', 'ASTC', 'AVEX', 'BKKT', 'BKSY'] ['XE', 'XNDU', 'XXI']
universes/sample_dev.csv 4 ['AAPL', 'FB', 'IBM', 'SPY'] ['FB', 'IBM', 'SPY']
[UniverseSpec] WARNING: truncating universes/swing_advances.csv from 74 to 4 tickers
[UniverseSpec] WARNING: truncating universes/swing_advances.csv from 74 to 4 tickers
universes/swing_advances.csv cap4 4 ['AAOI', 'ACDC', 'ADEA', 'ADPT']
[UniverseSpec] WARNING: truncating universes/swing_declines.csv from 68 to 4 tickers
[UniverseSpec] WARNING: truncating universes/swing_declines.csv from 68 to 4 tickers
universes/swing_declines.csv cap4 4 ['ABVX', 'ACHR', 'AEVA', 'AG']
universes/sample_dev.csv cap4 4 ['AAPL', 'FB', 'IBM', 'SPY']

**Evaluating test execution options**

I see that the stage spec indicates tests should run inside Docker, but in my current sandbox, I can only execute the host for UniverseSpec due to missing AlgorithmImports. However, should I specify that I didn't run the Docker script because it's read-only? Maybe it’s worth checking if I can run `bash scripts/run_tests.sh` instead? I need to inspect this further to clarify what my options really are.
codex
La validación con los CSVs reales del ObjectStore local cuadra con el cierre de Etapa 3/4: 74 advances, 68 declines y 4 en `sample_dev`; el tope `max_tickers` se aplica después del filtro y del orden alfabético. Voy a revisar la receta de tests antes de decidir si ejecuto algo sin romper el modo solo lectura.
exec
/bin/zsh -lc 'nl -ba scripts/run_tests.sh' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	# run_tests.sh — Corre pytest DENTRO de la imagen quantconnect/lean (ÚNICO modo válido).
     3	#
     4	# POR QUÉ: los tests importan AlgorithmImports y construyen objetos LEAN (TradeBar, etc.),
     5	#   que requieren el CLR de .NET + los assemblies de QuantConnect cargados vía pythonnet.
     6	#   El pytest del host NO resuelve AlgorithmImports. Este script monta el proyecto en la
     7	#   imagen LEAN y corre pytest allí. Contrato para todas las etapas siguientes.
     8	#
     9	# CÓMO: la imagen embebe Python dentro de .NET; para arrancar pythonnet en modo standalone
    10	#   hay que (1) instalar clr_loader, (2) forzar el runtime coreclr con el runtimeconfig de
    11	#   Lean, y (3) ubicarse en el dir Debug (donde viven AlgorithmImports.py, clr.py y los DLLs).
    12	#   El ENTRYPOINT de la imagen arranca el engine, por eso se sobreescribe con `bash`.
    13	
    14	set -euo pipefail
    15	
    16	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    17	WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
    18	PROJECT="$WORKSPACE/trade-scanner"   # proyecto pusheable: core/, strategies/, tests/
    19	
    20	IMAGE="quantconnect/lean:latest"
    21	DEBUG_DIR="/Lean/Launcher/bin/Debug"
    22	RUNTIME_CONFIG="$DEBUG_DIR/QuantConnect.Lean.Launcher.runtimeconfig.json"
    23	
    24	docker run --rm --entrypoint bash \
    25	  -e PYTHONNET_RUNTIME=coreclr \
    26	  -e PYTHONNET_CORECLR_RUNTIME_CONFIG="$RUNTIME_CONFIG" \
    27	  -e PYTHONPATH=/Project:/Scripts \
    28	  -e PYTHONDONTWRITEBYTECODE=1 \
    29	  -e TRADE_SCANNER_DATA=/Data \
    30	  -v "$PROJECT":/Project \
    31	  -v "$WORKSPACE/scripts":/Scripts:ro \
    32	  -v "$WORKSPACE/data":/Data:ro \
    33	  "$IMAGE" -c "
    34	    set -e
    35	    pip install -q --root-user-action=ignore clr_loader pytest
    36	    cd '$DEBUG_DIR'
    37	    python -m pytest /Project/tests -q -p no:cacheprovider
    38	  "

exec
/bin/zsh -lc "nl -ba scripts/explore_universe.py | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc 'nl -ba scripts/seed_sample_data.sh' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	# seed_sample_data.sh — Siembra la sample data libre de SPY en data/equity/usa/.
     3	#
     4	# POR QUÉ: un backtest SIN data no avanza el reloj (procesa "1 data point" y dispara
     5	#   OnEndOfAlgorithm de inmediato; los ScheduledEvents nunca corren). SPY como ancla
     6	#   de calendario necesita estas barras para que el esqueleto "camine". Ver el hallazgo
     7	#   del reloj en .claude/fase-1-desarrollo-local/etapa-02.md y CLAUDE.md.
     8	#
     9	# DE DÓNDE: repo público de LEAN en GitHub (Data/equity/usa/...), vía raw, sin auth QC.
    10	#   Es la misma sample data abierta (SPY ~2013, minute/hour/daily) que QuantConnect
    11	#   distribuye libremente; NO requiere licencia. No confundir con `lean data download`
    12	#   ni AlpacaBrokerage, que sí la requieren (ADR-002, relevante en Etapa 9, no aquí).
    13	#
    14	# IDEMPOTENTE: si el archivo destino ya existe, no lo vuelve a bajar.
    15	
    16	set -euo pipefail
    17	
    18	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    19	WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
    20	DATA_DIR="$WORKSPACE/data/equity/usa"
    21	BASE_URL="https://raw.githubusercontent.com/QuantConnect/Lean/master/Data/equity/usa"
    22	
    23	fetch() {
    24	  # fetch <ruta-relativa-a-equity/usa>
    25	  local rel="$1"
    26	  local dest="$DATA_DIR/$rel"
    27	  if [[ -f "$dest" ]]; then
    28	    echo "  skip (ya existe): $rel"
    29	    return 0
    30	  fi
    31	  mkdir -p "$(dirname "$dest")"
    32	  echo "  bajando: $rel"
    33	  curl -fsSL "$BASE_URL/$rel" -o "$dest"
    34	}
    35	
    36	echo "Sembrando sample data de SPY desde el repo público de LEAN -> $DATA_DIR"
    37	
    38	# Minute: trade + quote. Cubre la ventana por defecto del backtest (2013-10-07..11).
    39	for d in 20131004 20131007 20131008 20131009 20131010 20131011; do
    40	  fetch "minute/spy/${d}_trade.zip"
    41	  fetch "minute/spy/${d}_quote.zip"
    42	done
    43	
    44	# Resoluciones superiores (consolidación W/M parte de barras diarias en etapas futuras).
    45	fetch "hour/spy.zip"
    46	fetch "daily/spy.zip"
    47	
    48	# Map y factor files: LEAN los necesita para resolver el símbolo de equity US.
    49	fetch "map_files/spy.csv"
    50	fetch "factor_files/spy.csv"
    51	
    52	# Universo dev multi-símbolo (Etapa 5B T5.1): daily + map/factor de AAPL/IBM/FB.
    53	# FB solo tiene historia propia desde la IPO 2012 → M:200 no-ready (decisión 2026-06-11).
    54	for sym in aapl ibm fb; do
    55	  fetch "daily/${sym}.zip"
    56	  fetch "map_files/${sym}.csv"
    57	done
    58	# factor_files reales del repo LEAN para FB (zip LEAN, OK usar factores reales).
    59	fetch "factor_files/fb.csv"
    60	
    61	# factor_files NEUTROS para AAPL/IBM (Etapa 5B T5.3): sus zips provienen del converter
    62	# Stooq (split-only adjusted, sin dividendos — descargados con "skip dividends").
    63	# Usar los factores reales del repo LEAN causaría doble ajuste. factor=1 → LEAN sirve
    64	# los precios tal cual, sin re-ajustar. Stooq split-only + factor=1 es coherente con
    65	# DataNormalizationMode.SPLIT_ADJUSTED y con TradingView vista "Adjusted".
    66	for sym_date in "aapl:19840907" "ibm:19620102"; do
    67	  sym="${sym_date%%:*}"
    68	  first_date="${sym_date##*:}"
    69	  dest="$DATA_DIR/factor_files/${sym}.csv"
    70	  echo "  factor_files/${sym}.csv → neutro (${first_date},1,1,1)"
    71	  printf "%s,1,1,1\n" "$first_date" > "$dest"
    72	done
    73	
    74	echo "Listo."

 succeeded in 0ms:
     1	"""
     2	Perfilado de un CSV de universo exportado de Barchart.
     3	Uso: python scripts/explore_universe.py <ruta_csv>
     4	"""
     5	import sys
     6	import csv
     7	import re
     8	from pathlib import Path
     9	
    10	EXPECTED_COLUMNS = [
    11	    "Symbol", "Name", "5D %Chg", "Latest", "Change",
    12	    "%Change", "5D Chg", "5D High", "5D Low", "5D Avg Vol", "Time",
    13	]
    14	SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")
    15	PERCENT_COLUMNS = ["5D %Chg", "%Change"]
    16	NUMERIC_COLUMNS = ["Latest", "Change", "5D Chg", "5D High", "5D Low", "5D Avg Vol"]
    17	VOL_THRESHOLDS = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
    18	
    19	
    20	def parse_percent(value: str) -> float | None:
    21	    try:
    22	        return float(value.strip().lstrip("+").rstrip("%")) / 100
    23	    except (ValueError, AttributeError):
    24	        return None
    25	
    26	
    27	def parse_numeric(value: str) -> float | None:
    28	    try:
    29	        return float(value.strip().replace(",", ""))
    30	    except (ValueError, AttributeError):
    31	        return None
    32	
    33	
    34	def run(csv_path: str) -> None:
    35	    path = Path(csv_path)
    36	    if not path.exists():
    37	        print(f"ERROR: archivo no encontrado: {csv_path}")
    38	        sys.exit(1)
    39	
    40	    print(f"\n{'='*70}")
    41	    print(f"PERFILADO: {path.name}")
    42	    print(f"{'='*70}")
    43	
    44	    # --- Lectura bruta ---
    45	    with open(path, newline="", encoding="utf-8") as f:
    46	        reader = csv.DictReader(f)
    47	        columns_present = reader.fieldnames or []
    48	        raw_rows = list(reader)
    49	
    50	    total_raw = len(raw_rows)
    51	
    52	    # --- Detección de footer (símbolo inválido) ---
    53	    data_rows = []
    54	    footer_rows = []
    55	    for row in raw_rows:
    56	        sym = row.get("Symbol", "").strip()
    57	        if SYMBOL_RE.match(sym):
    58	            data_rows.append(row)
    59	        else:
    60	            footer_rows.append(row)
    61	
    62	    # --- Sección 1: estructura general ---
    63	    print(f"\n--- Estructura general ---")
    64	    print(f"  Filas totales (incluyendo footer): {total_raw}")
    65	    print(f"  Filas de datos:                    {len(data_rows)}")
    66	    print(f"  Filas de footer descartadas:       {len(footer_rows)}")
    67	    if footer_rows:
    68	        for fr in footer_rows:
    69	            print(f"  Footer detectado: {dict(fr)}")
    70	
    71	    print(f"\n  Columnas esperadas ({len(EXPECTED_COLUMNS)}): {EXPECTED_COLUMNS}")
    72	    print(f"  Columnas presentes ({len(columns_present)}): {list(columns_present)}")
    73	    missing = [c for c in EXPECTED_COLUMNS if c not in columns_present]
    74	    extra = [c for c in columns_present if c not in EXPECTED_COLUMNS]
    75	    if missing:
    76	        print(f"  FALTANTES: {missing}")
    77	    if extra:
    78	        print(f"  EXTRA (se ignorarán): {extra}")
    79	    if not missing and not extra:
    80	        print("  Columnas: coinciden exactamente con las esperadas.")
    81	
    82	    # --- Sección 2: análisis por columna ---
    83	    print(f"\n--- Análisis por columna ---")
    84	
    85	    for col in columns_present:
    86	        values_raw = [r.get(col, "").strip() for r in data_rows]
    87	        nulls = sum(1 for v in values_raw if v == "")
    88	
    89	        if col in PERCENT_COLUMNS:
    90	            parsed = [parse_percent(v) for v in values_raw if v != ""]
    91	            valid = [v for v in parsed if v is not None]
    92	            samples = [v for v in values_raw if v != ""][:3]
    93	            print(f"  {col:15s} | tipo: percent% → float | nulos: {nulls} | "
    94	                  f"rango: [{min(valid)*100:.2f}%, {max(valid)*100:.2f}%] | "
    95	                  f"muestras crudas: {samples}")
    96	
    97	        elif col in NUMERIC_COLUMNS:
    98	            parsed = [parse_numeric(v) for v in values_raw if v != ""]
    99	            valid = [v for v in parsed if v is not None]
   100	            if valid:
   101	                print(f"  {col:15s} | tipo: float | nulos: {nulls} | "
   102	                      f"rango: [{min(valid):.2f}, {max(valid):.2f}]")
   103	            else:
   104	                print(f"  {col:15s} | tipo: float | nulos: {nulls} | sin valores válidos")
   105	
   106	        else:
   107	            samples = [v for v in values_raw if v != ""][:3]
   108	            print(f"  {col:15s} | tipo: string | nulos: {nulls} | muestras: {samples}")
   109	
   110	    # --- Sección 3: simulación de filtros ---
   111	    print(f"\n--- Simulación de filtros de volumen (5D Avg Vol) ---")
   112	    vols = [parse_numeric(r.get("5D Avg Vol", "")) for r in data_rows]
   113	    prices = [parse_numeric(r.get("Latest", "")) for r in data_rows]
   114	
   115	    print(f"  {'Umbral':>12s} | {'Tickers que pasan':>18s}")
   116	    print(f"  {'-'*12}-+-{'-'*18}")
   117	    for threshold in VOL_THRESHOLDS:
   118	        passing = sum(1 for v in vols if v is not None and v > threshold)
   119	        label = f"> {threshold/1e6:.1f}M" if threshold >= 1_000_000 else f"> {threshold/1e3:.0f}K"
   120	        print(f"  {label:>12s} | {passing:>18d}")
   121	
   122	    # Filtro combinado
   123	    combined = sum(
   124	        1 for v, p in zip(vols, prices)
   125	        if v is not None and p is not None and v > 1_000_000 and p > 5
   126	    )
   127	    print(f"\n  Filtro combinado (avg_vol_5d > 1M AND price > 5): {combined} tickers pasan")
   128	
   129	    # Volumen: estadísticas adicionales
   130	    vols_valid = [v for v in vols if v is not None]
   131	    if vols_valid:
   132	        sorted_vols = sorted(vols_valid)
   133	        n = len(sorted_vols)
   134	        median_vol = sorted_vols[n // 2]
   135	        print(f"  Mediana vol: {median_vol:,.0f} | Máximo: {max(vols_valid):,.0f}")
   136	
   137	    # --- Sección 4: símbolos no estándar ---
   138	    non_standard = [r.get("Symbol", "").strip() for r in data_rows
   139	                    if not SYMBOL_RE.match(r.get("Symbol", "").strip())]
   140	    print(f"\n--- Símbolos no estándar (no ^[A-Z]{{1,5}}$) en filas de datos ---")
   141	    if non_standard:
   142	        print(f"  Encontrados ({len(non_standard)}): {non_standard}")
   143	    else:
   144	        print("  Ninguno — todos los símbolos son estándar.")
   145	
   146	    print(f"\n{'='*70}\n")
   147	
   148	
   149	if __name__ == "__main__":
   150	    if len(sys.argv) < 2:
   151	        print("Uso: python scripts/explore_universe.py <ruta_csv>")
   152	        sys.exit(1)
   153	    run(sys.argv[1])

exec
/bin/zsh -lc 'nl -ba config/notifications.json' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	{
     2	  "notification_groups": {
     3	    "swing_eod":    ["swing_eod", "swing_eod_short"],
     4	    "market_close": ["market_close", "market_close_short"]
     5	  },
     6	  "environments": {
     7	    "dev":  { "channels": ["file"],               "notify_empty": false },
     8	    "prod": { "channels": ["file", "host_email"], "notify_empty": false }
     9	  },
    10	  "email": {
    11	    "from": "trade-scanner@example.com",
    12	    "subject_prefix": "[trade-scanner]"
    13	  },
    14	  "subscribers": {
    15	    "swing_eod":    ["guillermosanchezh@gmail.com"],
    16	    "market_close": ["guillermosanchezh@gmail.com"]
    17	  }
    18	}

exec
/bin/zsh -lc "nl -ba storage/config/strategies.json | sed -n '1,80p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	{
     2	  "bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 },
     3	  "environments": {
     4	    "dev":  {
     5	      "top_n": 2,
     6	      "max_universe": 4,
     7	      "universe": "sample_dev",
     8	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20, 200] },
     9	      "warmup_budget": { "daily": 4300 },
    10	      "validate_warmup": true,
    11	      "sma_validation": true
    12	    },
    13	    "prod": {
    14	      "top_n": 50,
    15	      "max_universe": 200,
    16	      "warmup_budget": { "daily": 1100 }
    17	    }
    18	  },
    19	  "strategies": {
    20	    "swing_eod": {
    21	      "universe": "swing_advances",
    22	      "direction": "long",
    23	      "main_timeframe": "W",
    24	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    25	      "schedule": "after_close",
    26	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    27	    },
    28	    "swing_eod_short": {
    29	      "universe": "swing_declines",
    30	      "direction": "short",
    31	      "main_timeframe": "W",
    32	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    33	      "schedule": "after_close",
    34	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    35	    },
    36	    "market_close": {
    37	      "universe": "swing_advances",
    38	      "direction": "long",
    39	      "main_timeframe": "W",
    40	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    41	      "schedule": "before_close_30m",
    42	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    43	    },
    44	    "market_close_short": {
    45	      "universe": "swing_declines",
    46	      "direction": "short",
    47	      "main_timeframe": "W",
    48	      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
    49	      "schedule": "before_close_30m",
    50	      "universe_filter": "avg_vol_5d > 1e6 and price > 5"
    51	    }
    52	  }
    53	}

**Considering testing options**

I need to run universe tests, but I’m worried about whether pytest is installed. If it's not, that could cause an issue. Running tests shouldn't modify anything, except possibly for no pycache. The script `run_tests.sh` might not be able to execute due to Docker limitations. It sounds like it uses a read-write mount, while pytest generally doesn't write. Running Docker might complicate things since it could potentially affect the repository in unexpected ways. There are many unknowns here!
**Evaluating testing within constraints**

I might try to connect, but in a managed read-only environment, the command could run without modifying the repo. However, there's a restriction on networking. Installing packages like `clr_loader` and `pytest` could fail due to lack of cached data, which isn’t ideal. I should avoid running full tests because of potential network issues and changes. While the methodology suggests running tests inside Docker, the no-network policy complicates things. Perhaps I can run just the universe host to verify the unit tests. Let’s see!
codex
Para los tests de Etapa 4 en particular, `test_universe.py` no depende del CLR. Voy a ejecutarlo con cache de pytest deshabilitada y bytecode deshabilitado; no ejecutaré la suite Docker completa si requiere instalar paquetes o escribir fuera del sandbox.
exec
/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider trade-scanner/tests/test_universe.py' in /Users/guille/Documents/quant/trade-scanner
 exited 1 in 212ms:
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pytest/__main__.py", line 9, in <module>
    raise SystemExit(pytest.console_main())
                     ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/config/__init__.py", line 223, in console_main
    code = main()
           ^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/config/__init__.py", line 193, in main
    config = _prepareconfig(new_args, plugins)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/config/__init__.py", line 361, in _prepareconfig
    config: Config = pluginmanager.hook.pytest_cmdline_parse(
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/helpconfig.py", line 124, in pytest_cmdline_parse
    config = yield
             ^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
          ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/config/__init__.py", line 1192, in pytest_cmdline_parse
    self.parse(args)
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/config/__init__.py", line 1562, in parse
    self.hook.pytest_load_initial_conftests(
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 167, in _multicall
    raise exception
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 139, in _multicall
    teardown.throw(exception)
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/warnings.py", line 128, in pytest_load_initial_conftests
    return (yield)
            ^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/pluggy/_callers.py", line 116, in _multicall
    next(function_gen)  # first yield
    ^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/capture.py", line 170, in pytest_load_initial_conftests
    capman.start_global_capturing()
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/capture.py", line 773, in start_global_capturing
    self._global_capturing = _get_multicapture(self._method)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/capture.py", line 714, in _get_multicapture
    return MultiCapture(in_=FDCapture(0), out=FDCapture(1), err=FDCapture(2))
                                              ^^^^^^^^^^^^
  File "/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/_pytest/capture.py", line 493, in __init__
    TemporaryFile(buffering=0),
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/.pyenv/versions/3.11.11/lib/python3.11/tempfile.py", line 628, in TemporaryFile
    prefix, suffix, dir, output_type = _sanitize_params(prefix, suffix, dir)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/.pyenv/versions/3.11.11/lib/python3.11/tempfile.py", line 127, in _sanitize_params
    dir = gettempdir()
          ^^^^^^^^^^^^
  File "/Users/guille/.pyenv/versions/3.11.11/lib/python3.11/tempfile.py", line 316, in gettempdir
    return _os.fsdecode(_gettempdir())
                        ^^^^^^^^^^^^^
  File "/Users/guille/.pyenv/versions/3.11.11/lib/python3.11/tempfile.py", line 309, in _gettempdir
    tempdir = _get_default_tempdir()
              ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/guille/.pyenv/versions/3.11.11/lib/python3.11/tempfile.py", line 224, in _get_default_tempdir
    raise FileNotFoundError(_errno.ENOENT,
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/b6/b1k1x5b56v94z941yg6_wj0w0000gn/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/guille/Documents/quant/trade-scanner']

codex
El pytest del host no llegó a ejecutar tests: Python no tiene un directorio temporal escribible en este sandbox de solo lectura, incluso con cache deshabilitada. Probaré una vez sin captura, que evita el `TemporaryFile` de pytest; si vuelve a bloquearse, dejaré la verificación como no ejecutable en este entorno.
exec
/bin/zsh -lc 'PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -s -p no:cacheprovider trade-scanner/tests/test_universe.py' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 513ms:
.[UniverseSpec] WARNING: truncating k from 10 to 5 tickers
....
5 passed in 0.35s

**Evaluating test run options**

I think I might need to run `bash scripts/run_tests.sh`, but I'm unsure about Docker and pip needing temporary access. The script can mount the project read-write without caching, and it could run, but installing packages in the container with network access may not work. We're not running the Docker suite due to the read-only restrictions. If we proceed, I should check the `docker` status, but running could hang. Should I report if I don’t run it?
**Inspecting Docker and logs**

To be thorough, I could check if the Docker image is present and whether there's a network connection, though restricted access means pulling could modify the Docker cache. The user mentioned no commands should alter the repo or states, and Docker pulls can change the Docker state, so it might be best to avoid that. The script does include a `pip install` that modifies the container only. I also need to look at previous log reports for stage 04, especially to gather evidence from backtests. Should I check the logs now?
codex
Los 5 tests de `test_universe.py` pasan en host con captura deshabilitada (`5 passed`), lo cual cubre la unidad de Etapa 4 sin depender de LEAN. No ejecutaré `scripts/run_tests.sh` completo porque el script usa Docker y `pip install` dentro del contenedor; eso queda fuera de lo que puedo garantizar en este sandbox de solo lectura/restricted network.
exec
/bin/zsh -lc 'find revisiones -type f | sort' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
revisiones/20260619-205134/etapa-01-informe.md
revisiones/20260619-205134/etapa-01-log.md
revisiones/20260619-205134/etapa-02-informe.md
revisiones/20260619-205134/etapa-02-log.md
revisiones/20260619-205134/etapa-03-informe.md
revisiones/20260619-205134/etapa-03-log.md
revisiones/20260619-205134/etapa-04-log.md

exec
/bin/zsh -lc "nl -ba revisiones/20260619-205134/etapa-04-log.md | sed -n '1,260p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	OpenAI Codex v0.139.0
     2	--------
     3	workdir: /Users/guille/Documents/quant/trade-scanner
     4	model: gpt-5.5
     5	provider: openai
     6	approval: never
     7	sandbox: read-only
     8	reasoning effort: xhigh
     9	reasoning summaries: detailed
    10	session id: 019ee2cd-56f0-7270-a057-047d2a0b19d2
    11	--------
    12	user
    13	Revisa exhaustivamente SOLO la Etapa 4 del proyecto, siguiendo la metodología y los criterios de AGENTS.md. Usa el documento .claude/fase-1-desarrollo-local/etapa-04.md como definición del alcance y los criterios de aceptación (Done when) de esta etapa, y PLAN.md/SPECS.md como fuentes de verdad del diseño. Traza objetivo->codigo->test para cada criterio de la etapa, verifica la API de LEAN y la corrección funcional de las funciones tocadas y que se relacionen en la etapa (dependencias de etapas previas) en esta etapa. Reporta hallazgos con archivo:linea, severidad y sugerencia. No modifiques archivos.
    14	**Planning file operations**
    15	
    16	I want to begin by looking at the present working directory (pwd) and searching through files with "rg." I think I should also consider staging documents, planning, and checking the specifications. To streamline this, I could use multi-tool parallel for independent readings since I don't need any chained commands at this point. Also, starting the commentary seems like the right move. This should help keep things organized!
    17	codex
    18	Voy a revisar en modo solo lectura, empezando por el alcance de Etapa 4 y las fuentes de verdad (`PLAN.md`/`SPECS.md`). Después trazaré los archivos y tests que implementan esa etapa contra cada criterio.
    19	  → Leer alcance Etapa 4 y documentos de diseño aplicables
    20	  • Mapear archivos y dependencias tocadas por Etapa 4
    21	  • Auditar implementación, API LEAN y corrección funcional
    22	  • Auditar tests y trazabilidad objetivo-código-test
    23	  • Redactar hallazgos y resumen ejecutivo
    24	exec
    25	/bin/zsh -lc pwd in /Users/guille/Documents/quant/trade-scanner
    26	 succeeded in 0ms:
    27	/Users/guille/Documents/quant/trade-scanner
    28	
    29	exec
    30	/bin/zsh -lc 'rg --files' in /Users/guille/Documents/quant/trade-scanner
    31	 succeeded in 0ms:
    32	CLAUDE.md
    33	SPECS.md
    34	PLAN.md
    35	revision-quality-20260618.md
    36	lean.json
    37	review-report-clean.md
    38	README.md
    39	AGENTS.md
    40	LICENSE
    41	revisiones/20260619-205134/etapa-02-log.md
    42	revisiones/20260619-205134/etapa-02-informe.md
    43	revisiones/20260619-205134/etapa-04-log.md
    44	revisiones/20260619-205134/etapa-01-log.md
    45	revisiones/20260619-205134/etapa-03-informe.md
    46	revisiones/20260619-205134/etapa-03-log.md
    47	revisiones/20260619-205134/etapa-01-informe.md
    48	trade-scanner/main.py
    49	config/notifications.json
    50	universes/sample_dev.csv
    51	config/strategies.json
    52	trade-scanner/config.json
    53	scripts/seed_sample_data.sh
    54	scripts/run_review.sh
    55	scripts/seed_object_store.sh
    56	scripts/notify_email.py
    57	scripts/run_tests.sh
    58	scripts/explore_universe.py
    59	scripts/stooq_to_lean.py
    60	trade-scanner/tests/test_sma_regression.py
    61	trade-scanner/tests/test_strategies.py
    62	trade-scanner/tests/test_pipeline.py
    63	trade-scanner/tests/test_symbol_data.py
    64	trade-scanner/tests/test_rules.py
    65	trade-scanner/tests/test_timeframes.py
    66	trade-scanner/tests/test_universe.py
    67	trade-scanner/strategies/base.py
    68	trade-scanner/strategies/market_close.py
    69	trade-scanner/strategies/swing_eod.py
    70	trade-scanner/strategies/__init__.py
    71	docs/DEVLOG.md
    72	docs/ROADMAP.md
    73	trade-scanner/core/__init__.py
    74	trade-scanner/core/timeframes.py
    75	trade-scanner/core/rules.py
    76	trade-scanner/tests/test_pythonnet_bridge.py
    77	trade-scanner/tests/test_email_render.py
    78	trade-scanner/tests/test_t5_stooq_crosscheck.py
    79	trade-scanner/tests/test_features.py
    80	trade-scanner/tests/test_output.py
    81	trade-scanner/tests/__init__.py
    82	trade-scanner/tests/test_notify_email.py
    83	trade-scanner/core/output.py
    84	trade-scanner/core/email_render.py
    85	trade-scanner/core/symbol_data.py
    86	trade-scanner/core/pipeline.py
    87	trade-scanner/core/universe.py
    88	trade-scanner/core/features.py
    89	trade-scanner/tests/fixtures/envelope_sample.json
    90	docs/conceptos/buckets-y-simetria-largo-corto.md
    91	docs/conceptos/factory-vs-composicion.md
    92	
    93	exec
    94	/bin/zsh -lc "sed -n '1,240p' .claude/fase-1-desarrollo-local/etapa-04.md" in /Users/guille/Documents/quant/trade-scanner
    95	exec
    96	/bin/zsh -lc "sed -n '1,260p' PLAN.md" in /Users/guille/Documents/quant/trade-scanner
    97	exec
    98	/bin/zsh -lc "sed -n '1,260p' SPECS.md" in /Users/guille/Documents/quant/trade-scanner
    99	 succeeded in 0ms:
   100	# SPECS — Screener de Acciones sobre LEAN
   101	
   102	**Versión:** 0.1 (V1) · **Fecha:** 2026-06-19 · **Estado:** en desarrollo — Etapas 1–5A y 6 completadas; 6B en cierre (capa de reglas rediseñada — ADR-005: snapshot único + reglas como filtros puros); 5B en progreso; 7 completada (pipeline end-to-end + composición declarativa + minute subscription + schedule); **8 completada** (T1–T7, 2026-06-19: `OutputSink` con salida por entorno aislada — envelope por estrategia base persistido CSV/JSON + correo híbrido render-puro-compartido/canal-por-config + script host `notify_email.py` dry-run; backtest dev verificado. Envío real Gmail + `qc_notify` cloud live diferidos a Etapa 9). El backtest a escala ≥3 meses se difiere a Etapa 9 por límite de datos minute — decisión usuario.
   103	
   104	---
   105	
   106	## 1. Contexto
   107	
   108	**Problema.** Los traders manejan un universo de ideas (tickers) demasiado amplio para revisar manualmente. Necesitan filtrarlo con criterios técnicos (y a futuro fundamentales) de forma sistemática, repetible y programada, en los momentos del día que cada estrategia exige.
   109	
   110	**Solución.** Un screener construido sobre el motor LEAN que carga un universo desde CSV, mantiene indicadores precisos en tres marcos de tiempo (día, semana, mes), valida reglas por estrategia en horarios programados, y entrega una watchlist con evidencia de por qué cada ticker pasó los filtros.
   111	
   112	**Usuario.** Traders discrecionales que operan una o más estrategias (swing, earnings, etc.) y usan el screener como primer filtro antes de su análisis manual. El screener **no decide ni ejecuta**: propone candidatos.
   113	
   114	---
   115	
   116	## 2. Stack tecnológico
   117	
   118	| Componente | Elección |
   119	|---|---|
   120	| Engine | LEAN open source (Python 3.11) |
   121	| Lenguaje | Python |
   122	| IDE / Dev | VSCode + LEAN CLI (local desde día uno) |
   123	| Python host | pyenv + Python 3.11; virtualenv `.venv` por proyecto |
   124	| Contenerización | Docker Desktop; imagen oficial `quantconnect/lean` para engine y tests |
   125	| Ejecución | `lean backtest` / `lean live` vía CLI |
   126	| Datos Fase 1 | Alpaca free (IEX, 15 min delay, 100 calls/min) |
   127	| Datos backtest | Flexible: `lean data download` (Alpaca u otro provider soportado) |
   128	| Notificación | `NotificationManager` (QC cloud) / archivo + sink local |
   129	
   130	**Principio rector:** el código solo habla con la API de `QCAlgorithm`. La fuente de datos, el broker y el entorno son configuración externa (`lean.json` / parámetros), nunca lógica.
   131	
   132	---
   133	
   134	## 3. Arquitectura por capas
   135	
   136	```
   137	┌─────────────────────────────────────────────────────────┐
   138	│ L6 · EJECUCIÓN                                          │
   139	│   lean backtest | lean live (Docker quantconnect/lean)  │
   140	│   Fase 1: local · Fase 2: VPS · portable a QC cloud     │
   141	├─────────────────────────────────────────────────────────┤
   142	│ L5 · ORQUESTACIÓN (main.py — QCAlgorithm)               │
   143	│   initialize → carga config → carga universos →         │
   144	│   crea SymbolData + warmup → registra ScheduledEvents   │
   145	│   Un solo nodo, todas las estrategias por schedule      │
   146	├─────────────────────────────────────────────────────────┤
   147	│ L4 · ESTRATEGIAS (ScanPipeline)                         │
   148	│   universo asignado + lista de Rules + schedule         │
   149	│   V1: swing_eod (fin de día) · market_close (15:30 ET)  │
   150	├─────────────────────────────────────────────────────────┤
   151	│ L3 · FEATURES / PRIMITIVAS (LEAN-nativas, reutilizables)│
   152	│   Cómputos reutilizables sobre SymbolData               │
   153	│   Features: posición vs SMA(n) por timeframe,           │
   154	│   extensión vs SMA(8), pullback, % cambio, barra        │
   155	│   parcial del día (working bar)                         │
   156	├─────────────────────────────────────────────────────────┤
   157	│ L2 · DATOS DERIVADOS (SymbolData)                       │
   158	│   SymbolData: consolidators D/W/M + indicadores         │
   159	│   TradeBarConsolidator diario · Calendar.WEEKLY ·       │
   160	│   Calendar.MONTHLY · working_bar                        │
   161	│   Warmup derivado de timeframes declarados (PLAN §4)    │
   162	├─────────────────────────────────────────────────────────┤
   163	│ L1 · DATOS Y CONFIG EXTERNA                             │
   164	│   lean.json (provider: Alpaca | QC cloud | otro)        │
   165	│   CSV de universo(s) vía ObjectStore (portable)         │
   166	│   Parámetros de estrategia (umbrales, horarios)         │
   167	└─────────────────────────────────────────────────────────┘
   168	```
   169	
   170	**Reglas entre capas:**
   171	- L3 y L4 nunca consultan la fuente de datos directamente: consumen el estado de `SymbolData`, que el engine mantiene actualizado.
   172	- L4 no calcula indicadores: solo evalúa predicados (Rules) sobre features ya computadas. El scan es lectura, no cómputo.
   173	- L5 es el único lugar con `self.schedule`, `self.history`, `self.add_equity`, `self.notify`.
   174	
   175	---
   176	
   177	## 4. Entidades core
   178	
   179	| Entidad | Responsabilidad | Notas de implementación |
   180	|---|---|---|
   181	| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro declarativo sobre columnas normalizadas (ej. `"avg_vol_5d > 1e6 and price > 5"`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore. Footer strip (`^[A-Z]{1,5}$`). Alias normalizados (`COLUMN_ALIASES`). Filtro vía `df.query()`. Tope duro 200 post-filtro. Sin imports de `AlgorithmImports` (testeable con mock). Claves: `universes/swing_advances.csv`, `universes/swing_declines.csv`. |
   182	| `SymbolData` | Estado técnico de un símbolo: consolidators D/W/M, indicadores registrados, barra parcial del día. | Patrón idiomático LEAN. SMAs vía `register_indicator` sobre cada consolidator. Warmup en construcción. |
   183	| `Feature` | Cómputo reutilizable y nombrado sobre `SymbolData`. Ej.: `position_vs_sma(n, timeframe)`, `extension_pct(n)`, `is_pullback()`, `day_change_pct()`. | Funciones/propiedades puras de lectura. Compartidas por todas las estrategias. |
   184	| `Rule` | Filtro puro sobre el snapshot de posición precio↔SMA (no recalcula): pasa/no-pasa + evidencia. Ej.: `AboveSMA(20, ["D","W","M"])`, `NotExtended(8, "D")`. Largos/cortos por mirror del set de buckets desde `direction` (sin duplicar reglas). | `evaluate(snapshot)` — sin `sd` ni thresholds. `buckets_allowed` desde config (validado en construcción). `NotExtended` excluye el bucket extremo; el corte es el `bucket_thresholds.extended` único de la estrategia, no un umbral por-regla (ADR-005). |
   185	| `ScanPipeline` | Una estrategia: `UniverseSpec` + lista de `Rules` + `ScheduleSpec`. Ejecuta el scan y produce `ScanResult`. | V1: `swing_eod`, `market_close`. |
   186	| `ScheduleSpec` | Cuándo corre cada pipeline. Ej.: `swing_eod` → tras el cierre; `market_close` → 30 min antes del cierre. | Implementado con `self.schedule.on(date_rules, time_rules)` sobre el calendario del mercado. |
   187	| `ScanResult` | Watchlist: lista de candidatos con evidencia por regla (valores de SMAs, % extensión, % cambio, timestamp `as_of`, flag `partial_bar`). | Serializable a CSV/JSON. |
   188	| `OutputSink` | Persistencia + notificación según entorno (Etapa 8). Unidad = **envelope por estrategia base·scan** (long+short en uno, D8.2). SIEMPRE escribe archivo (CSV+JSON+`latest.json` en `results/<base>/` vía ObjectStore); la notificación es condicional. | Dispatch por **tabla de canales leída de `config/notifications.json`** (`file`/`qc_notify`/`host_email`, D8.4), no por ramas `if env ==`. El correo se parte en **render puro compartido** (`core/email_render.py`) + **transporte por entorno**: cloud → `self.notify.email`; local/VPS → script host `scripts/notify_email.py` (Gmail, fuera del algoritmo). Gate de vida suprime correo en backtest. Suscriptores por estrategia base vía `JsonSubscriberSource` (swappable a DB, D8.5). |
   189	
   190	---
   191	
   192	## 5. Decisiones técnicas consolidadas
   193	
   194	1. **Barras y SMAs de semana y mes se calculan dentro de LEAN** con la mejor configuración del framework: `TradeBarConsolidator(Calendar.WEEKLY)` y `Calendar.MONTHLY`, con los indicadores registrados sobre el consolidator. Nada de resampling manual con pandas.
   195	2. **Warmup explícito y verificable.** Al crear cada `SymbolData`, se pide la historia necesaria (`self.history`) y se empuja a los consolidators. La profundidad se deriva dinámicamente de los timeframes declarados (ver fórmula en PLAN.md §4): `D:n → n+5` barras diarias; `W:n → n×5+10`; `M:n → n×21+21`. Ej.: `M:[20]` → ~441 barras. El número no es fijo.
   196	3. **SMAs estables intradía.** Los indicadores W/M solo se actualizan al cierre de su barra (comportamiento natural del consolidator). En el scan intradía, el precio actual se compara contra medias del último cierre.
   197	4. **Barra parcial del día en el scan intradía.** Suscripción en `Resolution.MINUTE`; el OHLC en curso del día se lee del `working_bar` del consolidator diario (mecanismo LEAN-nativo, agnóstico de la fuente). El `ScanResult` la marca como `partial_bar=True` con su `as_of`.
   198	5. **Un nodo, múltiples estrategias.** Un solo algoritmo registra todos los `ScheduledEvents`. Las estrategias comparten los `SymbolData` de los símbolos que tengan en común (un símbolo = un `SymbolData`, aunque esté en varios universos).
   199	6. **Fuente de datos = configuración.** Cambiar Alpaca ↔ QC cloud ↔ otro provider solo toca `lean.json` (y credenciales). El algoritmo no contiene referencias a la fuente.
   200	7. **Portabilidad local/cloud.** Solo API `QCAlgorithm`, universos y config de estrategias (`config/strategies.json`) vía ObjectStore. `self.get_parameter` solo para escalares sueltos (ej. `env`) — no para la config anidada de estrategias, que no es portable a la UI plana de parámetros de cloud (ver PLAN.md §4). Nota D-E4: los parámetros escalares del algoritmo se definen en `trade-scanner/config.json["parameters"]`, no en `lean.json`. El mismo proyecto debe correr en LEAN CLI local y en QC cloud sin cambios de código.
   201	8. **Solo escaneo en V1.** Cero órdenes. El diseño deja el punto de extensión: un `ScanResult` validado por expertos podrá alimentar un módulo de ejecución futuro sin reestructurar las capas (L4 produce candidatos; un futuro L4.5 los consumiría).
   202	
   203	---
   204	
   205	## 6. Alcance V1
   206	
   207	1. Cargar universo principal desde **archivo CSV**, aplicar un **filtro simple** sobre sus columnas y extraer los tickers (máx ~200). Soporte para variantes de universo por estrategia.
   208	2. Conexión a datos **live o backtest** con **Alpaca o QuantConnect cloud**, configurable **solo modificando `lean.json`**.
   209	3. **Programación por horas del día**: ej. *Swing* al final del día; *Cierre de mercado* 30 min antes del cierre. Todas las estrategias en un mismo nodo vía schedule.
   210	4. **Features reutilizables** entre estrategias (ej. detección de posición respecto a SMA), implementadas con indicadores y consolidators de LEAN.
   211	5. **Filtro técnico en tres marcos de tiempo** (día, semana, mes) sobre el universo.
   212	6. **Archivo de salida + notificación según el ambiente**: `NotificationManager` en QC cloud; archivo/log en local.
   213	
   214	### Estrategia de referencia V1 (refinada)
   215	
   216	**`swing_eod`** — corre tras el cierre:
   217	1. Universo: CSV swing (≤200), filtro simple de liquidez/precio del propio CSV.
   218	2. Ranking interno: top N por `day_change_pct` (gainers; losers vía la variante `*_short` con `direction: short`).
   219	3. Snapshot único: posición precio↔SMA(8/20) en D/W/M, calculada **una vez** por símbolo·scan y clasificada en 7 buckets con los `bucket_thresholds` de la estrategia.
   220	4. Regla: precio sobre SMA20 en D, W y M (`AboveSMA(20, [D,W,M])` — filtro de buckets `above_*`; para shorts, mirror a `below_*`).
   221	5. Regla: NO extendida (`NotExtended(8, D)` — excluye el bucket `extended_above`, cuyo corte es `bucket_thresholds.extended`, default 10% **a calibrar**; sin umbral por-regla).
   222	6. Salida: watchlist con evidencia (proyección del snapshot).
   223	
   224	**`market_close`** — corre 15:30 ET (mismas reglas que swing_eod):
   225	- Usa la barra parcial del día (working bar) como precio/OHLC actual.
   226	- SMAs del último cierre (decisión 3). Resultado marcado provisional.
   227	
   228	---
   229	
   230	## 7. Fases
   231	
   232	**FASE 1 — Desarrollo local ($0/mes)**
   233	- LEAN CLI + VSCode en máquina local, Docker.
   234	- Datos: Alpaca free (100 calls/min, IEX, 15 min delay).
   235	- Backtest + paper trading local (paper solo valida el flujo de datos live; no ejecuta órdenes).
   236	
   237	**FASE 2 — Validación en servidor (~$25/mes)**
   238	- LEAN self-hosted en VPS cloud, mismo proyecto sin cambios de código.
   239	- Datos: Alpaca free (igual que Fase 1).
   240	- Paper trading live en servidor; salida y notificación operando de forma desatendida.
   241	
   242	---
   243	
   244	## 8. Fuera de alcance (V1)
   245	
   246	- **Definición/descubrimiento del universo inicial**: solo se filtra un CSV provisto. La fuente del CSV de "best market movers" está **A DEFINIR** (ver §11).
   247	- **Ejecución de órdenes**: ninguna orden, ni paper. Se habilitará tras validación con expertos.
   248	- Datos fundamentales, earnings calendar, scoring/ranking avanzado, persistencia histórica de scans (candidatos a V2).
   249	
   250	---
   251	
   252	## 9. Restricciones
   253	
   254	- Desarrollo local de algoritmos con **LEAN CLI** exclusivamente.
   255	- El código **solo habla con la API de `QCAlgorithm`** (sin SDKs de brokers/datos embebidos).
   256	- **Portable** a QuantConnect cloud o local sin cambios.
   257	- **Todas las estrategias corren en un mismo nodo** con schedule.
   258	- **Flexibilidad en fuentes de datos**: la fuente es configuración externa (`lean.json`).
   259	- Universo fijo en primeras versiones, con `refresh_universe()` como punto de extensión.
   260	

exec
/bin/zsh -lc "nl -ba review-report-clean.md | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	# Code Review Report
     2	## Executive Summary
     3	- Total issues by severity: Critical 0, High 2, Medium 7, Low 3.
     4	- Main system risks: `market_close` cannot produce a real intraday partial bar while subscriptions remain daily; Etapa 7 is not end-to-end because `ScanPipeline` is missing and `main.py` still uses a scan stub; stale price handling and day-change assumptions can create false rankings or false positives; config, tests, and README can drift from the PLAN/SPECS contract.
     5	- General recommendation: finish Etapa 7 integration first, with minute subscriptions, real pipeline execution, fail-fast strategy/config validation, and backtest evidence for partial bars, emission timing, readiness exclusion, and reproducibility.
     6	
     7	## Critical
     8	No Critical issues found.
     9	
    10	## High
    11	### Daily Subscriptions Block Intraday Partial Bar
    12	- Severity: High
    13	- Files: [trade-scanner/main.py:78](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:78), [trade-scanner/main.py:115](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:115)
    14	- Problem: `main.py` subscribes symbols with `Resolution.DAILY`, but Etapa 7 D7.4/T5 requires `Resolution.MINUTE` so `working_bar` represents the current intraday daily bar.
    15	- Why it matters: With daily subscriptions, `market_close` cannot reliably emit `partial_bar=True` using live intraday data. `reference_price` and `day_change_pct` can miss today's price action, which changes rankings, rule evidence, and V1 acceptance criteria.
    16	- Recommendation: Change universe and anchor subscriptions to `Resolution.MINUTE` during Etapa 7 T5, keep warmup at `set_warm_up(..., Resolution.DAILY)`, and validate consolidator emission timing in backtest.
    17	
    18	### ScanPipeline Missing From Etapa 7 Flow
    19	- Severity: High
    20	- Files: [trade-scanner/core/pipeline.py:11](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:11), [trade-scanner/main.py:296](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:296)
    21	- Problem: `ScanPipeline` is not implemented and `main.py` still runs `_scan_stub()`.
    22	- Why it matters: The system cannot perform the real strategy workflow: referenced-series readiness gate, `top_n` ranking, one snapshot per symbol, rule cascade, evidence collection, or complete `ScanResult` generation. Etapa 7 remains non-functional end to end.
    23	- Recommendation: Implement `ScanPipeline.scan()` per Etapa 7 T4 and replace `_scan_stub()` with the real scheduled pipeline callback in T5.
    24	
    25	## Medium
    26	### Reference Price Can Use Stale Working Bar
    27	- Severity: Medium
    28	- Files: [trade-scanner/core/features.py:96](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:96)
    29	- Problem: `reference_price()` uses any available `working_bar` without checking whether it belongs to the scan date/session.
    30	- Why it matters: Symbols with missing recent data can be ranked and evaluated against a stale price from a prior session, causing false positives, false negatives, and misleading evidence.
    31	- Recommendation: Pass `as_of` or scan date into the helper, validate `working_bar.end_time` against the expected session, and log or fallback explicitly when the bar is not fresh.
    32	
    33	### Day Change Assumes Daily Close Is Previous Close
    34	- Severity: Medium
    35	- Files: [trade-scanner/core/features.py:111](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:111)
    36	- Problem: `day_change_pct()` assumes `sd.close("D")` is yesterday's close, while Etapa 7 notes this depends on actual LEAN emission timing.
    37	- Why it matters: If the daily consolidator has already emitted today's bar at the scan time, the change can collapse to 0 or otherwise be calculated from the wrong baseline, breaking ranking and reproducibility.
    38	- Recommendation: Keep the emission-timing probe as a required backtest gate. If `close("D")` includes today, add a `previous_close` or `RollingWindow` path as described in D7.6.
    39	
    40	### Strategy Series Not Validated Against Config
    41	- Severity: Medium
    42	- Files: [trade-scanner/strategies/swing_eod.py:18](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/swing_eod.py:18), [config/strategies.json:24](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:24)
    43	- Problem: Strategy rules hardcode referenced series (`D:8`, `D:20`, `W:20`, `M:20`) while config declares strategy timeframes, but there is no validation that `StrategyConfig.series(side)` is a subset of the effective config.
    44	- Why it matters: Config drift can fail late with `KeyError`, cold indicators, or missing evidence during scans instead of failing at initialization.
    45	- Recommendation: In `initialize()`, fail fast if any referenced series is absent from the effective strategy config or excluded by the warmup budget.
    46	
    47	### Universe Filter Executes External Query Directly
    48	- Severity: Medium
    49	- Files: [trade-scanner/core/universe.py:70](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:70)
    50	- Problem: `df.query(self.filter_expr)` executes a filter expression loaded from ObjectStore directly, and pandas syntax or missing-column errors are not wrapped with project context.
    51	- Why it matters: Bad or unexpected filter expressions can produce unclear failures during universe loading. Because the expression is external input, the accepted aliases and operators should be constrained.
    52	- Recommendation: Validate the filter against allowed aliases/operators before execution and wrap pandas errors in a `ValueError` that includes `universe_key` and the expression.
    53	
    54	### Test Environment Is Not Pinned
    55	- Severity: Medium
    56	- Files: [scripts/run_tests.sh:20](/Users/guille/Documents/quant/trade-scanner/scripts/run_tests.sh:20), [scripts/run_tests.sh:34](/Users/guille/Documents/quant/trade-scanner/scripts/run_tests.sh:34)
    57	- Problem: The test runner uses `quantconnect/lean:latest` and installs unpinned dependencies (`clr_loader pytest`) on every run.
    58	- Why it matters: External image or dependency changes can break tests or change behavior without any repository change, reducing reproducibility of regression results.
    59	- Recommendation: Pin the LEAN Docker image tag or digest and pin known-good versions of test dependencies.
    60	
    61	### Precision Regression Tests Can Be Skipped
    62	- Severity: Medium
    63	- Files: [trade-scanner/tests/test_t5_stooq_crosscheck.py:85](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_t5_stooq_crosscheck.py:85), [trade-scanner/tests/test_sma_regression.py:70](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_sma_regression.py:70)
    64	- Problem: Critical regression and precision tests skip when expected zip or CSV fixtures are missing.
    65	- Why it matters: The suite can report green without validating real SMA precision, masking data or fixture omissions that directly affect the screener's core signal quality.
    66	- Recommendation: Separate optional external-data tests from required validation gates, or make the validation job fail when authoritative fixtures for the current stage are absent.
    67	
    68	### README Contradicts PLAN/SPECS
    69	- Severity: Medium
    70	- Files: [README.md:72](/Users/guille/Documents/quant/trade-scanner/README.md:72), [README.md:103](/Users/guille/Documents/quant/trade-scanner/README.md:103)
    71	- Problem: README says configuration lives in `Screener/config.json`, still mentions `max_extension_pct`, and describes a `ticker,price,avg_dollar_volume` CSV instead of the current Barchart/ObjectStore contract.
    72	- Why it matters: Documentation drift can lead contributors to place config in the wrong file, reintroduce retired parameters, or seed incompatible universe CSVs.
    73	- Recommendation: Update README to match PLAN/SPECS: `config/strategies.json` via ObjectStore, Barchart universe normalization, and removal of `max_extension_pct`.
    74	
    75	## Low
    76	### SMAPositionRule Allows Empty Rule Inputs
    77	- Severity: Low
    78	- Files: [trade-scanner/core/rules.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:38)
    79	- Problem: `SMAPositionRule` does not validate `period > 0` or non-empty `tfs`.
    80	- Why it matters: A rule with no timeframes passes by vacuity and produces empty evidence, making broken strategy composition hard to diagnose.
    81	- Recommendation: Validate at construction time that `period >= 1` and `tfs` is non-empty.
    82	
    83	### StrategyConfig Shares Mutable Rule List
    84	- Severity: Low
    85	- Files: [trade-scanner/strategies/base.py:18](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/base.py:18), [trade-scanner/strategies/market_close.py:16](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/market_close.py:16)
    86	- Problem: `StrategyConfig` is frozen but contains a mutable `list` of rule factories, and `market_close.rules is swing_eod.rules` shares the same list.
    87	- Why it matters: Accidental mutation of the list changes multiple strategies at once, undermining the expectation that strategy configs are immutable declarations.
    88	- Recommendation: Store rule factories as `tuple[Callable[..., ...], ...]` and share the immutable tuple explicitly.
    89	
    90	### Universe Required Columns Are Hardcoded
    91	- Severity: Low
    92	- Files: [trade-scanner/core/universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:52)
    93	- Problem: Required-column validation is fixed to `avg_vol_5d` and `price` rather than the columns actually referenced by `filter_expr`.
    94	- Why it matters: Future filters using fields like `pct_chg_5d` will fail later and with less actionable errors, increasing debugging cost.
    95	- Recommendation: Extract and validate aliases referenced by the declarative filter, or define an explicit allowed filter schema.

exec
/bin/zsh -lc "nl -ba revision-quality-20260618.md | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	OpenAI Codex v0.139.0
     2	--------
     3	workdir: /Users/guille/Documents/quant/trade-scanner
     4	model: gpt-5.5
     5	provider: openai
     6	approval: never
     7	sandbox: read-only
     8	reasoning effort: none
     9	reasoning summaries: none
    10	session id: 019ede02-882c-7873-87af-ef89e8f08903
    11	--------
    12	user
    13	Revisa exhaustivamente todo el proyecto siguiendo el AGENTS.md. desde la etapa 1 hasta la etapa 7 tarea 3. Si el contexto es demasiado grande, prioriza: 1. core 2. strategies 3. main.py 4. tests. Enfócate en calidad de código y bugs potenciales: lógica, edge cases, manejo de errores, duplicación de código.
    14	codex
    15	Voy a hacer una revisión solo lectura siguiendo esas reglas: primero cargo los documentos de diseño y el árbol del repo, luego inspecciono `core`, `strategies`, `main.py` y tests, y cierro con hallazgos priorizados. No voy a modificar archivos ni ejecutar nada que escriba en el workspace.
    16	exec
    17	/bin/zsh -lc 'git status --short' in /Users/guille/Documents/quant/trade-scanner
    18	 succeeded in 0ms:
    19	git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
    20	git: error: couldn't create cache file '/tmp/xcrun_db-w40THj2y' (errno=Operation not permitted)
    21	git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
    22	git: error: couldn't create cache file '/tmp/xcrun_db-hM2RuCBD' (errno=Operation not permitted)
    23	 M .claude/fase-1-desarrollo-local/etapa-07-t1-decisiones-y-pendientes.md
    24	 M .claude/fase-1-desarrollo-local/etapa-07.md
    25	 M PLAN.md
    26	 M SPECS.md
    27	 M trade-scanner/core/features.py
    28	 M trade-scanner/strategies/__init__.py
    29	 M trade-scanner/tests/test_features.py
    30	?? .claude/fase-1-desarrollo-local/etapa-07-t2-decisiones-y-pendientes.md
    31	?? .claude/fase-1-desarrollo-local/etapa-07-t3-decisiones-y-pendientes.md
    32	?? revision-quality-20260618.md
    33	?? trade-scanner/strategies/base.py
    34	?? trade-scanner/strategies/market_close.py
    35	?? trade-scanner/strategies/swing_eod.py
    36	?? trade-scanner/tests/test_strategies.py
    37	
    38	exec
    39	/bin/zsh -lc 'pwd && rg --files' in /Users/guille/Documents/quant/trade-scanner
    40	 succeeded in 0ms:
    41	/Users/guille/Documents/quant/trade-scanner
    42	LICENSE
    43	CLAUDE.md
    44	SPECS.md
    45	README.md
    46	lean.json
    47	PLAN.md
    48	AGENTS.md
    49	revision-quality-20260618.md
    50	universes/sample_dev.csv
    51	scripts/seed_sample_data.sh
    52	scripts/seed_object_store.sh
    53	trade-scanner/config.json
    54	trade-scanner/main.py
    55	scripts/run_tests.sh
    56	scripts/explore_universe.py
    57	scripts/stooq_to_lean.py
    58	config/strategies.json
    59	trade-scanner/core/symbol_data.py
    60	docs/DEVLOG.md
    61	trade-scanner/core/rules.py
    62	trade-scanner/core/__init__.py
    63	trade-scanner/core/timeframes.py
    64	trade-scanner/core/universe.py
    65	trade-scanner/core/features.py
    66	trade-scanner/core/pipeline.py
    67	docs/ROADMAP.md
    68	trade-scanner/strategies/base.py
    69	trade-scanner/strategies/market_close.py
    70	trade-scanner/strategies/swing_eod.py
    71	trade-scanner/strategies/__init__.py
    72	docs/conceptos/buckets-y-simetria-largo-corto.md
    73	docs/conceptos/factory-vs-composicion.md
    74	trade-scanner/tests/test_t5_stooq_crosscheck.py
    75	trade-scanner/tests/test_features.py
    76	trade-scanner/tests/test_pythonnet_bridge.py
    77	trade-scanner/tests/__init__.py
    78	trade-scanner/tests/test_sma_regression.py
    79	trade-scanner/tests/test_strategies.py
    80	trade-scanner/tests/test_pipeline.py
    81	trade-scanner/tests/test_symbol_data.py
    82	trade-scanner/tests/test_rules.py
    83	trade-scanner/tests/test_timeframes.py
    84	trade-scanner/tests/test_universe.py
    85	
    86	exec
    87	/bin/zsh -lc "find . -maxdepth 3 -type f \\( -name 'PLAN.md' -o -name 'SPECS.md' -o -name 'CLAUDE.md' -o -name 'AGENTS.md' \\) -print" in /Users/guille/Documents/quant/trade-scanner
    88	 succeeded in 0ms:
    89	./SPECS.md
    90	./PLAN.md
    91	./AGENTS.md
    92	./CLAUDE.md
    93	
    94	codex
    95	Ya tengo el inventario inicial. Hay cambios sin commitear, así que trataré todo como estado de trabajo del usuario y no tocaré nada; también noto que `git status` emitió errores de cache por el sandbox, pero sí devolvió el estado. Ahora voy a leer las fuentes de verdad y los archivos de implementación con numeración de líneas para poder citar hallazgos.
    96	exec
    97	/bin/zsh -lc 'nl -ba SPECS.md' in /Users/guille/Documents/quant/trade-scanner
    98	exec
    99	/bin/zsh -lc 'nl -ba PLAN.md' in /Users/guille/Documents/quant/trade-scanner
   100	 succeeded in 0ms:
   101	     1	# SPECS — Screener de Acciones sobre LEAN
   102	     2	
   103	     3	**Versión:** 0.1 (V1) · **Fecha:** 2026-06-18 · **Estado:** en desarrollo — Etapas 1–5A y 6 completadas; 6B en cierre (capa de reglas rediseñada — ADR-005: snapshot único + reglas como filtros puros); 5B en progreso
   104	     4	
   105	     5	---
   106	     6	
   107	     7	## 1. Contexto
   108	     8	
   109	     9	**Problema.** Los traders manejan un universo de ideas (tickers) demasiado amplio para revisar manualmente. Necesitan filtrarlo con criterios técnicos (y a futuro fundamentales) de forma sistemática, repetible y programada, en los momentos del día que cada estrategia exige.
   110	    10	
   111	    11	**Solución.** Un screener construido sobre el motor LEAN que carga un universo desde CSV, mantiene indicadores precisos en tres marcos de tiempo (día, semana, mes), valida reglas por estrategia en horarios programados, y entrega una watchlist con evidencia de por qué cada ticker pasó los filtros.
   112	    12	
   113	    13	**Usuario.** Traders discrecionales que operan una o más estrategias (swing, earnings, etc.) y usan el screener como primer filtro antes de su análisis manual. El screener **no decide ni ejecuta**: propone candidatos.
   114	    14	
   115	    15	---
   116	    16	
   117	    17	## 2. Stack tecnológico
   118	    18	
   119	    19	| Componente | Elección |
   120	    20	|---|---|
   121	    21	| Engine | LEAN open source (Python 3.11) |
   122	    22	| Lenguaje | Python |
   123	    23	| IDE / Dev | VSCode + LEAN CLI (local desde día uno) |
   124	    24	| Python host | pyenv + Python 3.11; virtualenv `.venv` por proyecto |
   125	    25	| Contenerización | Docker Desktop; imagen oficial `quantconnect/lean` para engine y tests |
   126	    26	| Ejecución | `lean backtest` / `lean live` vía CLI |
   127	    27	| Datos Fase 1 | Alpaca free (IEX, 15 min delay, 100 calls/min) |
   128	    28	| Datos backtest | Flexible: `lean data download` (Alpaca u otro provider soportado) |
   129	    29	| Notificación | `NotificationManager` (QC cloud) / archivo + sink local |
   130	    30	
   131	    31	**Principio rector:** el código solo habla con la API de `QCAlgorithm`. La fuente de datos, el broker y el entorno son configuración externa (`lean.json` / parámetros), nunca lógica.
   132	    32	
   133	    33	---
   134	    34	
   135	    35	## 3. Arquitectura por capas
   136	    36	
   137	    37	```
   138	    38	┌─────────────────────────────────────────────────────────┐
   139	    39	│ L6 · EJECUCIÓN                                          │
   140	    40	│   lean backtest | lean live (Docker quantconnect/lean)  │
   141	    41	│   Fase 1: local · Fase 2: VPS · portable a QC cloud     │
   142	    42	├─────────────────────────────────────────────────────────┤
   143	    43	│ L5 · ORQUESTACIÓN (main.py — QCAlgorithm)               │
   144	    44	│   initialize → carga config → carga universos →         │
   145	    45	│   crea SymbolData + warmup → registra ScheduledEvents   │
   146	    46	│   Un solo nodo, todas las estrategias por schedule      │
   147	    47	├─────────────────────────────────────────────────────────┤
   148	    48	│ L4 · ESTRATEGIAS (ScanPipeline)                         │
   149	    49	│   universo asignado + lista de Rules + schedule         │
   150	    50	│   V1: swing_eod (fin de día) · market_close (15:30 ET)  │
   151	    51	├─────────────────────────────────────────────────────────┤
   152	    52	│ L3 · FEATURES / PRIMITIVAS (LEAN-nativas, reutilizables)│
   153	    53	│   Cómputos reutilizables sobre SymbolData               │
   154	    54	│   Features: posición vs SMA(n) por timeframe,           │
   155	    55	│   extensión vs SMA(8), pullback, % cambio, barra        │
   156	    56	│   parcial del día (working bar)                         │
   157	    57	├─────────────────────────────────────────────────────────┤
   158	    58	│ L2 · DATOS DERIVADOS (SymbolData)                       │
   159	    59	│   SymbolData: consolidators D/W/M + indicadores         │
   160	    60	│   TradeBarConsolidator diario · Calendar.WEEKLY ·       │
   161	    61	│   Calendar.MONTHLY · working_bar                        │
   162	    62	│   Warmup derivado de timeframes declarados (PLAN §4)    │
   163	    63	├─────────────────────────────────────────────────────────┤
   164	    64	│ L1 · DATOS Y CONFIG EXTERNA                             │
   165	    65	│   lean.json (provider: Alpaca | QC cloud | otro)        │
   166	    66	│   CSV de universo(s) vía ObjectStore (portable)         │
   167	    67	│   Parámetros de estrategia (umbrales, horarios)         │
   168	    68	└─────────────────────────────────────────────────────────┘
   169	    69	```
   170	    70	
   171	    71	**Reglas entre capas:**
   172	    72	- L3 y L4 nunca consultan la fuente de datos directamente: consumen el estado de `SymbolData`, que el engine mantiene actualizado.
   173	    73	- L4 no calcula indicadores: solo evalúa predicados (Rules) sobre features ya computadas. El scan es lectura, no cómputo.
   174	    74	- L5 es el único lugar con `self.schedule`, `self.history`, `self.add_equity`, `self.notify`.
   175	    75	
   176	    76	---
   177	    77	
   178	    78	## 4. Entidades core
   179	    79	
   180	    80	| Entidad | Responsabilidad | Notas de implementación |
   181	    81	|---|---|---|
   182	    82	| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro declarativo sobre columnas normalizadas (ej. `"avg_vol_5d > 1e6 and price > 5"`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore. Footer strip (`^[A-Z]{1,5}$`). Alias normalizados (`COLUMN_ALIASES`). Filtro vía `df.query()`. Tope duro 200 post-filtro. Sin imports de `AlgorithmImports` (testeable con mock). Claves: `universes/swing_advances.csv`, `universes/swing_declines.csv`. |
   183	    83	| `SymbolData` | Estado técnico de un símbolo: consolidators D/W/M, indicadores registrados, barra parcial del día. | Patrón idiomático LEAN. SMAs vía `register_indicator` sobre cada consolidator. Warmup en construcción. |
   184	    84	| `Feature` | Cómputo reutilizable y nombrado sobre `SymbolData`. Ej.: `position_vs_sma(n, timeframe)`, `extension_pct(n)`, `is_pullback()`, `day_change_pct()`. | Funciones/propiedades puras de lectura. Compartidas por todas las estrategias. |
   185	    85	| `Rule` | Filtro puro sobre el snapshot de posición precio↔SMA (no recalcula): pasa/no-pasa + evidencia. Ej.: `AboveSMA(20, ["D","W","M"])`, `NotExtended(8, "D")`. Largos/cortos por mirror del set de buckets desde `direction` (sin duplicar reglas). | `evaluate(snapshot)` — sin `sd` ni thresholds. `buckets_allowed` desde config (validado en construcción). `NotExtended` excluye el bucket extremo; el corte es el `bucket_thresholds.extended` único de la estrategia, no un umbral por-regla (ADR-005). |
   186	    86	| `ScanPipeline` | Una estrategia: `UniverseSpec` + lista de `Rules` + `ScheduleSpec`. Ejecuta el scan y produce `ScanResult`. | V1: `swing_eod`, `market_close`. |
   187	    87	| `ScheduleSpec` | Cuándo corre cada pipeline. Ej.: `swing_eod` → tras el cierre; `market_close` → 30 min antes del cierre. | Implementado con `self.schedule.on(date_rules, time_rules)` sobre el calendario del mercado. |
   188	    88	| `ScanResult` | Watchlist: lista de candidatos con evidencia por regla (valores de SMAs, % extensión, % cambio, timestamp `as_of`, flag `partial_bar`). | Serializable a CSV/JSON. |
   189	    89	| `OutputSink` | Persistencia + notificación según entorno: ObjectStore + `NotificationManager` en QC cloud; archivo CSV/JSON (+ log) en local/VPS. | Selección por detección de entorno (`self.live_mode` + config), no por ramas de lógica de negocio. |
   190	    90	
   191	    91	---
   192	    92	
   193	    93	## 5. Decisiones técnicas consolidadas
   194	    94	
   195	    95	1. **Barras y SMAs de semana y mes se calculan dentro de LEAN** con la mejor configuración del framework: `TradeBarConsolidator(Calendar.WEEKLY)` y `Calendar.MONTHLY`, con los indicadores registrados sobre el consolidator. Nada de resampling manual con pandas.
   196	    96	2. **Warmup explícito y verificable.** Al crear cada `SymbolData`, se pide la historia necesaria (`self.history`) y se empuja a los consolidators. La profundidad se deriva dinámicamente de los timeframes declarados (ver fórmula en PLAN.md §4): `D:n → n+5` barras diarias; `W:n → n×5+10`; `M:n → n×21+21`. Ej.: `M:[20]` → ~441 barras. El número no es fijo.
   197	    97	3. **SMAs estables intradía.** Los indicadores W/M solo se actualizan al cierre de su barra (comportamiento natural del consolidator). En el scan intradía, el precio actual se compara contra medias del último cierre.
   198	    98	4. **Barra parcial del día en el scan intradía.** Suscripción en `Resolution.MINUTE`; el OHLC en curso del día se lee del `working_bar` del consolidator diario (mecanismo LEAN-nativo, agnóstico de la fuente). El `ScanResult` la marca como `partial_bar=True` con su `as_of`.
   199	    99	5. **Un nodo, múltiples estrategias.** Un solo algoritmo registra todos los `ScheduledEvents`. Las estrategias comparten los `SymbolData` de los símbolos que tengan en común (un símbolo = un `SymbolData`, aunque esté en varios universos).
   200	   100	6. **Fuente de datos = configuración.** Cambiar Alpaca ↔ QC cloud ↔ otro provider solo toca `lean.json` (y credenciales). El algoritmo no contiene referencias a la fuente.
   201	   101	7. **Portabilidad local/cloud.** Solo API `QCAlgorithm`, universos y config de estrategias (`config/strategies.json`) vía ObjectStore. `self.get_parameter` solo para escalares sueltos (ej. `env`) — no para la config anidada de estrategias, que no es portable a la UI plana de parámetros de cloud (ver PLAN.md §4). Nota D-E4: los parámetros escalares del algoritmo se definen en `trade-scanner/config.json["parameters"]`, no en `lean.json`. El mismo proyecto debe correr en LEAN CLI local y en QC cloud sin cambios de código.
   202	   102	8. **Solo escaneo en V1.** Cero órdenes. El diseño deja el punto de extensión: un `ScanResult` validado por expertos podrá alimentar un módulo de ejecución futuro sin reestructurar las capas (L4 produce candidatos; un futuro L4.5 los consumiría).
   203	   103	
   204	   104	---
   205	   105	
   206	   106	## 6. Alcance V1
   207	   107	
   208	   108	1. Cargar universo principal desde **archivo CSV**, aplicar un **filtro simple** sobre sus columnas y extraer los tickers (máx ~200). Soporte para variantes de universo por estrategia.
   209	   109	2. Conexión a datos **live o backtest** con **Alpaca o QuantConnect cloud**, configurable **solo modificando `lean.json`**.
   210	   110	3. **Programación por horas del día**: ej. *Swing* al final del día; *Cierre de mercado* 30 min antes del cierre. Todas las estrategias en un mismo nodo vía schedule.
   211	   111	4. **Features reutilizables** entre estrategias (ej. detección de posición respecto a SMA), implementadas con indicadores y consolidators de LEAN.
   212	   112	5. **Filtro técnico en tres marcos de tiempo** (día, semana, mes) sobre el universo.
   213	   113	6. **Archivo de salida + notificación según el ambiente**: `NotificationManager` en QC cloud; archivo/log en local.
   214	   114	
   215	   115	### Estrategia de referencia V1 (refinada)
   216	   116	
   217	   117	**`swing_eod`** — corre tras el cierre:
   218	   118	1. Universo: CSV swing (≤200), filtro simple de liquidez/precio del propio CSV.
   219	   119	2. Ranking interno: top N por `day_change_pct` (gainers; losers vía la variante `*_short` con `direction: short`).
   220	   120	3. Snapshot único: posición precio↔SMA(8/20) en D/W/M, calculada **una vez** por símbolo·scan y clasificada en 7 buckets con los `bucket_thresholds` de la estrategia.

**Evaluating filter function**

I'm thinking about a filter that uses `chg_1d`. If it hasn't been renamed, it might mean that the query is missing. I need to find out whether it's functioning properly or if there's a glitch in how it's set up. I'll need to look into what could happen if the filter isn't working as intended. It's like solving a puzzle, trying to figure out where things might be going awry.
**Considering config validations**

I'm thinking about "max_tickers," which is capped at 200 according to the config. I realize there's a lack of validation to ensure this limit isn’t exceeded, which could lead to issues down the line. It feels like there’s a latent risk associated with this configuration. I might need to implement some checks to treat any violations as a warning, to prevent potential chaos in our system. Just wanting to keep things running smoothly!
exec
/bin/zsh -lc "rg -n \"refresh_universe|UniverseSpec\\(\" trade-scanner config .claude PLAN.md SPECS.md" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
PLAN.md:53:│   │   ├── universe.py          # UniverseSpec: CSV ObjectStore + filtro simple + refresh_universe() no-op
PLAN.md:248:- `core/universe.py`: lee CSV desde `self.object_store`, aplica `universe_filter` declarativo, valida tope 200, expone símbolos por estrategia (variantes por clave de universo), `refresh_universe()` no-op documentado.
SPECS.md:82:| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro declarativo sobre columnas normalizadas (ej. `"avg_vol_5d > 1e6 and price > 5"`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore. Footer strip (`^[A-Z]{1,5}$`). Alias normalizados (`COLUMN_ALIASES`). Filtro vía `df.query()`. Tope duro 200 post-filtro. Sin imports de `AlgorithmImports` (testeable con mock). Claves: `universes/swing_advances.csv`, `universes/swing_declines.csv`. |
SPECS.md:160:- Universo fijo en primeras versiones, con `refresh_universe()` como punto de extensión.
trade-scanner/main.py:50:            spec = UniverseSpec(
trade-scanner/tests/test_universe.py:46:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:56:    result = UniverseSpec("k", FILTER, max_tickers=5).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:70:    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:82:        UniverseSpec("k", FILTER).load(MockObjectStore(csv))
trade-scanner/tests/test_universe.py:88:        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())
.claude/fase-1-desarrollo-local/etapa-04.md:38:       ├── universe: "swing_advances"   → UniverseSpec("universes/swing_advances.csv", ...)
.claude/fase-1-desarrollo-local/etapa-04.md:94:- `refresh_universe()` **no-op documentado:** la instancia carga el universo en `initialize()` y no se refresca en runtime V1. Si en el futuro se necesita refresh diario, se sobreescribe este método; el pipeline lo llama antes del scan.
.claude/fase-1-desarrollo-local/etapa-04.md:114:    spec = UniverseSpec(
.claude/fase-1-desarrollo-local/etapa-04.md:186:- **Refresh del universo en runtime** — `refresh_universe()` se deja como no-op documentado; se implementará si se necesita en Fase 2.
trade-scanner/core/universe.py:85:    def refresh_universe(self) -> None:
.claude/fase-1-desarrollo-local/etapa-05b-decisiones-y-pendientes.md:24:`UniverseSpec("universes/sample_dev.csv", "avg_vol_5d > 1e6 and price > 5").load(store)`
.claude/fase-1-desarrollo-local/etapa-05b-decisiones-y-pendientes.md:55:- `UniverseSpec("universes/sample_dev.csv", "<filtro dev>", max_tickers=2)` leído **desde storage**
.claude/fase-1-desarrollo-local/etapa-05b-decisiones-y-pendientes.md:382:- `UniverseSpec("universes/sample_dev.csv", "avg_vol_5d > 1e6 and price > 5", max_tickers=4)`
.claude/fase-1-desarrollo-local/etapa-07.md:210:- **Backtest a escala prod (≈74 tickers)** y **`lean live`/smoke-test Alpaca** — **Etapa 9**. **`refresh_universe` real** sigue no-op.

exec
/bin/zsh -lc "find .venv -path '*AlgorithmImports.py' -o -path '*QuantConnect*' | head -n 40" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
.venv/lib/python3.11/site-packages/QuantConnect
.venv/lib/python3.11/site-packages/QuantConnect/Research
.venv/lib/python3.11/site-packages/QuantConnect/Research/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/Research/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/Research/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/Research/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/Statistics
.venv/lib/python3.11/site-packages/QuantConnect/Statistics/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/Statistics/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/Statistics/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/Statistics/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DataSource
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/QuiverQuant
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/QuiverQuant/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/QuiverQuant/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/QuiverQuant/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/QuiverQuant/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/Constants
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/Constants/__init__.pyi
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/Constants/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/Constants/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/Constants/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/Models/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/Launcher/__pycache__/__init__.cpython-311.pyc
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/__init__.py
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/__pycache__
.venv/lib/python3.11/site-packages/QuantConnect/DownloaderDataProvider/__pycache__/__init__.cpython-311.pyc

**Inspecting virtual environment**

I’m noticing that I’ve found a `.venv` that seems to have a `pycache` potentially from before. It’s not writing anything right now, which makes me wonder if I should inspect the stubs for `QCAlgorithm`. Maybe that’s where the issue lies. I think examining those carefully could help clear things up and ensure everything is functioning as it should. It feels like troubleshooting is part of the process here!
codex
Hay stubs locales de QuantConnect en `.venv`, pero para el algoritmo runtime la fuente fuerte siguen siendo los stubs de la imagen LEAN. Como no voy a arrancar Docker, usaré los checkpoints D-E4/CLAUDE y el `lean.json` local para los métodos de Etapa 4, y marcaré cualquier símbolo no confirmado si aparece.
exec
/bin/zsh -lc "rg -n \"class QCAlgorithm|def get_parameter|def object_store|object_store|def log\\(|schedule\" .venv/lib/python3.11/site-packages/QuantConnect -g '*.pyi' -g '*.py'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:686:    def delete_object_store(self, organization_id: str, key: str) -> QuantConnect.Api.RestResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:766:    def get_object_store(self, organization_id: str, keys: typing.List[str], destination_folder: str = None) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:777:    def get_object_store_properties(self, organization_id: str, key: str) -> QuantConnect.Api.PropertiesObjectStoreResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1066:    def set_object_store(self, organization_id: str, key: str, object_data: typing.List[int]) -> QuantConnect.Api.RestResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1345:    def schedule(self) -> QuantConnect.Scheduling.ScheduleManager:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1346:        """Gets schedule manager for adding/removing scheduled events"""
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1556:    def object_store(self) -> QuantConnect.Storage.ObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1709:    def get_parameter(self, name: str, default_value: str = None) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1721:    def get_parameter(self, name: str, default_value: int) -> int:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1733:    def get_parameter(self, name: str, default_value: float) -> float:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1744:    def get_parameters(self) -> Common.Util.ReadOnlyExtendedDictionary[str, str]:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1763:    def log(self, message: str) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:2093:    def set_object_store(self, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:2097:        :param object_store: The object store
.venv/lib/python3.11/site-packages/QuantConnect/Configuration/__init__.pyi:257:    def get_parameter_or_default(options_object: typing.Dict[str, System.Object], parameter: str, default_value: str) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Configuration/__init__.pyi:262:    def get_parameter_or_exit(options_object: typing.Dict[str, System.Object], parameter: str) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:20:    """Base rule scheduler"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:206:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 30.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:217:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 30
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:228:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 30.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:240:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 30
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:252:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 30.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:263:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 30
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:296:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 92.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:307:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 92
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:318:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 92.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:330:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 92
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:342:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 92.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:353:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 92
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:452:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 365.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:463:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 365
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:474:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 365.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:486:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 365
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:498:        :param days_offset: The amount of days to offset the schedule by; must be between 0 and 365.
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:509:        :param days_offset: The amount of tradable days to offset the schedule by; must be between 0 and 365
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:687:        """Convenience property for running a scheduled event at midnight in the algorithm time zone"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:692:        """Convenience property for running a scheduled event at noon in the algorithm time zone"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:941:        """Event that fires each time this scheduled event happens"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:959:        """Gets the next time this scheduled event will fire in UTC"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1034:    """Specifies the callback component of a scheduled event, as well as final filters"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1057:    """Specifies the time rule component of a scheduled event"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1102:    """Specifies the date rule component of a scheduled event"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1144:    """Provides the ability to add/remove scheduled events from the real time handler"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1146:    def add(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1148:        Adds the specified event to the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1150:        :param scheduled_event: The event to be scheduled, including the date/times the event fires and the callback
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1154:    def remove(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1156:        Removes the specified event from the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1158:        :param scheduled_event: The event to be removed
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1187:    def add(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1189:        Adds the specified event to the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1191:        :param scheduled_event: The event to be scheduled, including the date/times the event fires and the callback
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1197:        """Entry point for the fluent scheduled event builder"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1202:        """Entry point for the fluent scheduled event builder"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1274:    def remove(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1276:        Removes the specified event from the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1278:        :param scheduled_event: The event to be removed
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1282:    def set_event_schedule(self, event_schedule: QuantConnect.Scheduling.IEventSchedule) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1286:        :param event_schedule: The event schedule implementation to be used. This is the IRealTimeHandler
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1337:    def __init__(self, schedule: QuantConnect.Scheduling.ScheduleManager, securities: QuantConnect.Securities.SecurityManager, name: str = None) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1341:        :param schedule: The schedule to send created events to
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1349:    """Throw this if there is an exception in the callback function of the scheduled event"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1352:    def scheduled_event_name(self) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1353:        """Gets the name of the scheduled event"""
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1360:        :param name: The name of the scheduled event
.venv/lib/python3.11/site-packages/QuantConnect/Parameters/__init__.pyi:46:    def get_parameters_from_assembly(assembly: System.Reflection.Assembly) -> System.Collections.Generic.Dictionary[str, str]:
.venv/lib/python3.11/site-packages/QuantConnect/Parameters/__init__.pyi:56:    def get_parameters_from_type(type: typing.Type) -> typing.Sequence[System.Collections.Generic.KeyValuePair[str, str]]:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/Factories/__init__.pyi:26:    def __init__(self, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/Factories/__init__.pyi:30:        :param object_store: The object store to use
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/Factories/__init__.pyi:79:    def __init__(self, time_provider: QuantConnect.ITimeProvider, object_store: QuantConnect.Interfaces.IObjectStore, date_adjustment: typing.Callable[[datetime.datetime], datetime.datetime] = None, minimum_interval_check: typing.Optional[datetime.timedelta] = None) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/Factories/__init__.pyi:84:        :param object_store: The object store to use
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/Framework/Selection/__init__.pyi:863:    """Defines a universe selection model that invokes a selector function on a specific scheduled given by an IDateRule and an ITimeRule"""
.venv/lib/python3.11/site-packages/QuantConnect/Api/__init__.pyi:3197:    def delete_object_store(self, organization_id: str, key: str) -> QuantConnect.Api.RestResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Api/__init__.pyi:3309:    def get_object_store(self, organization_id: str, keys: typing.List[str], destination_folder: str = None) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Api/__init__.pyi:3320:    def get_object_store_properties(self, organization_id: str, key: str) -> QuantConnect.Api.PropertiesObjectStoreResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Api/__init__.pyi:3362:    def list_object_store(self, organization_id: str, path: str) -> QuantConnect.Api.ListObjectStoreResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Api/__init__.pyi:3646:    def set_object_store(self, organization_id: str, key: str, object_data: typing.List[int]) -> QuantConnect.Api.RestResponse:
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Cfd/__init__.pyi:138:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/__init__.pyi:1210:    This enumerator will filter out data of the underlying enumerator based on a provided schedule.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/__init__.pyi:1211:    Will respect the schedule above the data, meaning will let older data through if the underlying provides none for the schedule date
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/__init__.pyi:1219:    def __init__(self, underlying_enumerator: System.Collections.Generic.IEnumerator[QuantConnect.Data.BaseData], scheduled_times: typing.List[datetime.datetime], frontier_time_provider: QuantConnect.ITimeProvider, schedule_time_zone: typing.Any, start_time: typing.Union[datetime.datetime, datetime.date]) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/__init__.pyi:1224:        :param scheduled_times: The scheduled times to emit new data points
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Enumerators/__init__.pyi:1226:        :param schedule_time_zone: 
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Equity/__init__.pyi:36:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/__init__.pyi:9864:    def consume(isolator_limit_provider: QuantConnect.IIsolatorLimitResultProvider, scheduled_event: QuantConnect.Scheduling.ScheduledEvent, scan_time_utc: typing.Union[datetime.datetime, datetime.date], time_monitor: QuantConnect.Scheduling.TimeMonitor) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/__init__.pyi:9865:        """Convenience method for invoking a scheduled event's Scan method inside the IsolatorLimitResultProvider"""
.venv/lib/python3.11/site-packages/QuantConnect/__init__.pyi:11508:        def scheduled_event_name(event_name: str) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/__init__.pyi:12157:    class QCAlgorithm(System.Object):
.venv/lib/python3.11/site-packages/QuantConnect/Securities/CryptoFuture/__init__.pyi:87:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Forex/__init__.pyi:34:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__init__.pyi:3052:        """Start date of next trading embargo ahead of scheduled results announcment"""
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__init__.pyi:37596:            ECB_UNSCHEDULED_MEETING_TO_DISCUSS_MARKETS: str = "EUR/ecb_unscheduled_meeting_to_discuss_markets"
.venv/lib/python3.11/site-packages/QuantConnect/DataSource/__init__.pyi:37597:            """Ecb Unscheduled Meeting To Discuss Markets"""
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Future/__init__.pyi:373:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:467:    def for_source(source: QuantConnect.Data.SubscriptionDataSource, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, config: QuantConnect.Data.SubscriptionDataConfig, date: typing.Union[datetime.datetime, datetime.date], is_live_mode: bool, factory: QuantConnect.Data.BaseData, data_provider: QuantConnect.Interfaces.IDataProvider, object_store: QuantConnect.Interfaces.IObjectStore) -> QuantConnect.Lean.Engine.DataFeeds.ISubscriptionDataSourceReader:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:1671:    def add_schedule_wrapper(self, request: QuantConnect.Data.UniverseSelection.SubscriptionRequest, underlying: System.Collections.Generic.IEnumerator[QuantConnect.Data.BaseData], time_provider: QuantConnect.ITimeProvider) -> System.Collections.Generic.IEnumerator[QuantConnect.Data.BaseData]:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:1673:        Returns a scheduled enumerator from the given arguments. It can also return the given underlying enumerator
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:1971:    def create_and_schedule_worker(request: QuantConnect.Data.UniverseSelection.SubscriptionRequest, enumerator: System.Collections.Generic.IEnumerator[QuantConnect.Data.BaseData], factor_file_provider: QuantConnect.Interfaces.IFactorFileProvider, enable_price_scale: bool, daily_strict_end_time_enabled: bool) -> QuantConnect.Lean.Engine.DataFeeds.Subscription:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2043:    def object_store(self) -> QuantConnect.Interfaces.IObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2064:    def __init__(self, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, is_live_mode: bool, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2207:    def __init__(self, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, config: QuantConnect.Data.SubscriptionDataConfig, date: typing.Union[datetime.datetime, datetime.date], is_live_mode: bool, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2215:        :param object_store: The object storage for data persistence.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2466:    def __init__(self, config: QuantConnect.Data.SubscriptionDataConfig, data_request: QuantConnect.Data.BaseDataRequest, map_file_provider: QuantConnect.Interfaces.IMapFileProvider, factor_file_provider: QuantConnect.Interfaces.IFactorFileProvider, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, data_provider: QuantConnect.Interfaces.IDataProvider, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2621:    def __init__(self, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, config: QuantConnect.Data.SubscriptionDataConfig, date: typing.Union[datetime.datetime, datetime.date], is_live_mode: bool, data_provider: QuantConnect.Interfaces.IDataProvider, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2638:    def __init__(self, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, config: QuantConnect.Data.SubscriptionDataConfig, date: typing.Union[datetime.datetime, datetime.date], is_live_mode: bool, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2646:        :param object_store: The object storage for data persistence
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2707:    def __init__(self, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, config: QuantConnect.Data.SubscriptionDataConfig, date: typing.Union[datetime.datetime, datetime.date], is_live_mode: bool, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:2984:    def get_scheduled_universe_utc_time_shift(current_utc_date_time: typing.Union[datetime.datetime, datetime.date]) -> datetime.timedelta:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:3022:    Allows to setup a real time scheduled event, internally using a Thread,
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:3028:        """Event fired when the scheduled time is past"""
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/__init__.pyi:3047:    def schedule_event(self, due_time: datetime.timedelta, utc_now: typing.Union[datetime.datetime, datetime.date]) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:209:    def schedule(self) -> QuantConnect.Scheduling.ScheduleManager:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:210:        """Gets schedule manager for adding/removing scheduled events"""
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:247:    def object_store(self) -> QuantConnect.Storage.ObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:514:    def get_parameter(self, name: str, default_value: str = None) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:526:    def get_parameter(self, name: str, default_value: int) -> int:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:538:    def get_parameter(self, name: str, default_value: float) -> float:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:549:    def get_parameters(self) -> Common.Util.ReadOnlyExtendedDictionary[str, str]:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:568:    def log(self, message: str) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:902:    def set_object_store(self, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/AlgorithmFactory/Python/Wrappers/__init__.pyi:906:        :param object_store: The object store
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Index/__init__.pyi:107:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/WorkScheduling/__init__.pyi:47:    """Base work scheduler abstraction"""
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Transport/__init__.pyi:209:    def __init__(self, object_store: QuantConnect.Interfaces.IObjectStore, key: str) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/DataFeeds/Transport/__init__.pyi:213:        :param object_store: The IObjectStore used to retrieve a stream of data
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/Results/__init__.pyi:723:        Called by scheduled event every night at midnight algorithm time
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/Results/__init__.pyi:1082:        Called once a day by scheduled event in AlgorithmManager
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3076:class QCAlgorithm(System.MarshalByRefObject, QuantConnect.Interfaces.IAlgorithm):
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3241:    def schedule(self) -> QuantConnect.Scheduling.ScheduleManager:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3242:        """Gets schedule manager for adding/removing scheduled events"""
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3447:    def object_store(self) -> QuantConnect.Storage.ObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5352:    def get_parameter(self, name: str, default_value: str = None) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5364:    def get_parameter(self, name: str, default_value: int) -> int:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5376:    def get_parameter(self, name: str, default_value: float) -> float:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5387:    def get_parameters(self) -> Common.Util.ReadOnlyExtendedDictionary[str, str]:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5781:    def log(self, message: typing.Any) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5790:    def log(self, message: str) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5799:    def log(self, message: int) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:5808:    def log(self, message: float) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:7293:    def set_object_store(self, object_store: QuantConnect.Interfaces.IObjectStore) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:7297:        :param object_store: The object store
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:33:        for processing via long-running scheduled events. In LEAN, we use the LeakyBucket
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:44:        spent to give execution time for things such as training scheduled events
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:58:        At time of writing, this is intended to be used to provide training scheduled events
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:77:        At time of writing, this is intended to be used to provide training scheduled events
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:279:    def object_store(self) -> QuantConnect.Interfaces.IObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:293:    def __init__(self, results: QuantConnect.Lean.Engine.Results.IResultHandler, setup: QuantConnect.Lean.Engine.Setup.ISetupHandler, data_feed: QuantConnect.Lean.Engine.DataFeeds.IDataFeed, transactions: QuantConnect.Lean.Engine.TransactionHandlers.ITransactionHandler, real_time: QuantConnect.Lean.Engine.RealTime.IRealTimeHandler, map_file_provider: QuantConnect.Interfaces.IMapFileProvider, factor_file_provider: QuantConnect.Interfaces.IFactorFileProvider, data_provider: QuantConnect.Interfaces.IDataProvider, object_store: QuantConnect.Interfaces.IObjectStore, data_permissions_manager: QuantConnect.Interfaces.IDataPermissionManager, live_mode: bool, research_mode: bool = False, data_monitor: QuantConnect.Interfaces.IDataMonitor = None) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/__init__.pyi:305:        :param object_store: The object store used for persistence
.venv/lib/python3.11/site-packages/QuantConnect/Securities/__init__.pyi:673:    Represents the schedule of a security exchange. This includes daily regular and extended market hours
.venv/lib/python3.11/site-packages/QuantConnect/Securities/__init__.pyi:728:        :param market_hours_for_each_day_of_week: The exchange's schedule for each day of the week
.venv/lib/python3.11/site-packages/QuantConnect/Securities/__init__.pyi:912:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:21:    """Provides methods for creating common scheduled events"""
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:47:        :param current_utc_time: Specfies the current time in UTC, before which, no events will be scheduled. Specify null to skip this filter.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:64:        :param current_utc_time: Specfies the current time in UTC, before which, no events will be scheduled. Specify null to skip this filter.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:80:        :param current_utc_time: Specfies the current time in UTC, before which, no events will be scheduled. Specify null to skip this filter.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:105:        Scan for past events that didn't fire because there was no data at the scheduled time.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:141:    def scheduled_events(self) -> System.Collections.Concurrent.ConcurrentDictionary[QuantConnect.Scheduling.ScheduledEvent, int]:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:143:        The scheduled events container
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:180:    def add(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:182:        Adds the specified event to the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:184:        :param scheduled_event: The event to be scheduled, including the date/times
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:193:    def get_scheduled_event_unique_id(self) -> int:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:195:        Gets a new scheduled event unique id
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:204:        Get's the timeout the scheduled task time monitor should use
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:215:    def remove(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:217:        Removes the specified event from the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:219:        :param scheduled_event: The event to be removed
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:225:        Scan for past events that didn't fire because there was no data at the scheduled time.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:262:    def add(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:264:        Adds the specified event to the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:266:        :param scheduled_event: The event to be scheduled, including the date/times the event fires and the callback
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:270:    def remove(self, scheduled_event: QuantConnect.Scheduling.ScheduledEvent) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:272:        Removes the specified event from the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:274:        :param scheduled_event: The event to be removed
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:280:        Scan for past events that didn't fire because there was no data at the scheduled time.
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:299:    def sort_first_element(scheduled_events: typing.List[QuantConnect.Scheduling.ScheduledEvent]) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:363:        Get's the timeout the scheduled task time monitor should use
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/RealTime/__init__.pyi:392:        Scan for past events that didn't fire because there was no data at the scheduled time.
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Crypto/__init__.pyi:105:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Securities/Option/__init__.pyi:1927:        :param exchange_hours: Contains the weekly exchange schedule plus holidays
.venv/lib/python3.11/site-packages/QuantConnect/Lean/Engine/Storage/__init__.pyi:111:    default_object_store: str
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:36:    """Entity in charge of managing a schedule"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:40:        """True if this schedule is set"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:44:        """Creates a new instance holding the same schedule if any"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:48:        """Gets the current schedule for a given start time"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:52:        """Set a IDateRule for this schedule"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:87:    def schedule(self) -> QuantConnect.Data.UniverseSelection.Schedule:
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:89:        If configured, will be used to determine universe selection schedule and filter or skip selection data
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:90:        that does not fit the schedule
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:94:    @schedule.setter
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:95:    def schedule(self, value: QuantConnect.Data.UniverseSelection.Schedule) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Data/UniverseSelection/__init__.pyi:182:        :param selection_date_rule: If provided, will be used to determine universe selection schedule
.venv/lib/python3.11/site-packages/QuantConnect/Data/__init__.pyi:971:    def object_store(self) -> QuantConnect.Interfaces.IObjectStore:
.venv/lib/python3.11/site-packages/QuantConnect/Data/__init__.pyi:980:    def __init__(self, job: QuantConnect.Packets.AlgorithmNodePacket, api: QuantConnect.Interfaces.IApi, data_provider: QuantConnect.Interfaces.IDataProvider, data_cache_provider: QuantConnect.Interfaces.IDataCacheProvider, map_file_provider: QuantConnect.Interfaces.IMapFileProvider, factor_file_provider: QuantConnect.Interfaces.IFactorFileProvider, status_update_action: typing.Callable[[int], typing.Any], parallel_history_requests_enabled: bool, data_permission_manager: QuantConnect.Interfaces.IDataPermissionManager, object_store: QuantConnect.Interfaces.IObjectStore, algorithm_settings: QuantConnect.Interfaces.IAlgorithmSettings) -> None:
.venv/lib/python3.11/site-packages/QuantConnect/Data/__init__.pyi:993:        :param object_store: The object store to use
.venv/lib/python3.11/site-packages/QuantConnect/Orders/Fees/__init__.pyi:680:    https://www.binance.com/en/fee/schedule
.venv/lib/python3.11/site-packages/QuantConnect/Orders/Fees/__init__.pyi:686:    https://www.binance.com/en/fee/schedule
.venv/lib/python3.11/site-packages/QuantConnect/Orders/Fees/__init__.pyi:1124:    https://www.kraken.com/features/fee-schedule#kraken-pro
.venv/lib/python3.11/site-packages/QuantConnect/Orders/Fees/__init__.pyi:1130:    https://www.kraken.com/features/fee-schedule#kraken-pro
.venv/lib/python3.11/site-packages/QuantConnect/Orders/Fees/__init__.pyi:1136:    https://www.kraken.com/features/fee-schedule#stablecoin-fx-pairs
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:28454:    """Sum of the carrying values as of the balance sheet date of all long-term debt, which is debt initially having maturities due after one year or beyond the operating cycle, if longer, but excluding the portions thereof scheduled to be repaid within one year or the normal operating cycle, if longer. Long-term debt includes notes payable, bonds payable, mortgage loans, convertible debt, subordinated debt and other types of long term debt."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:44933:    """Debt due under 1 year according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:44994:    """Debt due under 2 years according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:45055:    """Debt due within 5 year if the company provide maturity schedule in range e.g. 1-5 years, 2-5 years. Debt due under 5 years according to the debt maturity schedule reported by the company. If a range is reported by the company, the value will be collected under the maximum number of years (eg. 1-5 years, 3-5 years or 5 years will all be collected under this data point.)"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:45116:    """Debt maturing beyond 5 years (eg. 5-10 years) or with no specified maturity, according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:45878:        """Sum of the carrying values as of the balance sheet date of all long-term debt, which is debt initially having maturities due after one year or beyond the operating cycle, if longer, but excluding the portions thereof scheduled to be repaid within one year or the normal operating cycle, if longer. Long-term debt includes notes payable, bonds payable, mortgage loans, convertible debt, subordinated debt and other types of long term debt."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:47098:        """Debt due under 1 year according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:47103:        """Debt due under 2 years according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:47108:        """Debt due within 5 year if the company provide maturity schedule in range e.g. 1-5 years, 2-5 years. Debt due under 5 years according to the debt maturity schedule reported by the company. If a range is reported by the company, the value will be collected under the maximum number of years (eg. 1-5 years, 3-5 years or 5 years will all be collected under this data point.)"""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:47113:        """Debt maturing beyond 5 years (eg. 5-10 years) or with no specified maturity, according to the debt maturity schedule reported by the company."""
.venv/lib/python3.11/site-packages/QuantConnect/Data/Fundamental/__init__.pyi:47117:    def total_debt_in_maturity_schedule(self) -> QuantConnect.Data.Fundamental.TotalDebtInMaturityScheduleBalanceSheet:

exec
/bin/zsh -lc "find .venv/lib/python3.11/site-packages -name 'AlgorithmImports.py' -o -name 'AlgorithmImports.pyi'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 162ms:
codex
Los stubs locales confirman `QCAlgorithm.object_store`, `get_parameter()` y `log()` en snake_case. Para `object_store.read()` voy a leer el stub de `QuantConnect.Storage.ObjectStore` directamente, porque es el punto LEAN específico de Etapa 4.
exec
/bin/zsh -lc "rg -n \"class ObjectStore|def read\\(|def save\\(|def contains_key|def get_file_path|def read_bytes\" .venv/lib/python3.11/site-packages/QuantConnect/Storage .venv/lib/python3.11/site-packages/QuantConnect/Interfaces -g '*.pyi'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:113:class ObjectStore(System.Object, QuantConnect.Interfaces.IObjectStore, typing.Iterable[System.Collections.Generic.KeyValuePair[str, typing.List[int]]]):
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:171:    def contains_key(self, path: str) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:201:    def get_file_path(self, path: str) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:222:    def read(self, path: str, encoding: System.Text.Encoding = None) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:232:    def read_bytes(self, path: str) -> typing.List[int]:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:252:    def save(self, path: str) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi:262:    def save(self, path: str, text: str, encoding: System.Text.Encoding = None) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:146:class ObjectStoreErrorRaisedEventArgs(System.EventArgs):
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1176:    def contains_key(self, path: str) -> bool:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1194:    def get_file_path(self, path: str) -> str:
.venv/lib/python3.11/site-packages/QuantConnect/Interfaces/__init__.pyi:1215:    def read_bytes(self, path: str) -> typing.List[int]:

exec
/bin/zsh -lc "nl -ba .venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi | sed -n '5348,5388p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "nl -ba .venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi | sed -n '3438,3455p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "nl -ba .venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi | sed -n '5778,5802p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
  3438	    def error_messages(self, value: System.Collections.Concurrent.ConcurrentQueue[str]) -> None:
  3439	        ...
  3440	
  3441	    @property
  3442	    def current_slice(self) -> QuantConnect.Data.Slice:
  3443	        """Returns the current Slice object"""
  3444	        ...
  3445	
  3446	    @property
  3447	    def object_store(self) -> QuantConnect.Storage.ObjectStore:
  3448	        """Gets the object store, used for persistence"""
  3449	        ...
  3450	
  3451	    @property
  3452	    def statistics(self) -> QuantConnect.Statistics.StatisticsResults:
  3453	        """The current statistics for the running algorithm."""
  3454	        ...
  3455	

 succeeded in 0ms:
  5778	        ...
  5779	
  5780	    @overload
  5781	    def log(self, message: typing.Any) -> None:
  5782	        """
  5783	        Added another method for logging if user guessed.
  5784	        
  5785	        :param message: String message to log.
  5786	        """
  5787	        ...
  5788	
  5789	    @overload
  5790	    def log(self, message: str) -> None:
  5791	        """
  5792	        Added another method for logging if user guessed.
  5793	        
  5794	        :param message: String message to log.
  5795	        """
  5796	        ...
  5797	
  5798	    @overload
  5799	    def log(self, message: int) -> None:
  5800	        """
  5801	        Added another method for logging if user guessed.
  5802	        

 succeeded in 0ms:
  5348	        """Gets whether or not this algorithm has been locked and fully initialized"""
  5349	        ...
  5350	
  5351	    @overload
  5352	    def get_parameter(self, name: str, default_value: str = None) -> str:
  5353	        """
  5354	        Gets the parameter with the specified name. If a parameter with the specified name does not exist,
  5355	        the given default value is returned if any, else null
  5356	        
  5357	        :param name: The name of the parameter to get
  5358	        :param default_value: The default value to return
  5359	        :returns: The value of the specified parameter, or default_value if not found or null if there's no default value.
  5360	        """
  5361	        ...
  5362	
  5363	    @overload
  5364	    def get_parameter(self, name: str, default_value: int) -> int:
  5365	        """
  5366	        Gets the parameter with the specified name parsed as an integer. If a parameter with the specified name does not exist,
  5367	        or the conversion is not possible, the given default value is returned
  5368	        
  5369	        :param name: The name of the parameter to get
  5370	        :param default_value: The default value to return
  5371	        :returns: The value of the specified parameter, or default_value if not found or null if there's no default value.
  5372	        """
  5373	        ...
  5374	
  5375	    @overload
  5376	    def get_parameter(self, name: str, default_value: float) -> float:
  5377	        """
  5378	        Gets the parameter with the specified name parsed as a double. If a parameter with the specified name does not exist,
  5379	        or the conversion is not possible, the given default value is returned
  5380	        
  5381	        :param name: The name of the parameter to get
  5382	        :param default_value: The default value to return
  5383	        :returns: The value of the specified parameter, or default_value if not found or null if there's no default value.
  5384	        """
  5385	        ...
  5386	
  5387	    def get_parameters(self) -> Common.Util.ReadOnlyExtendedDictionary[str, str]:
  5388	        """Gets a read-only dictionary with all current parameters"""

exec
/bin/zsh -lc "nl -ba .venv/lib/python3.11/site-packages/QuantConnect/Storage/__init__.pyi | sed -n '113,235p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
   113	class ObjectStore(System.Object, QuantConnect.Interfaces.IObjectStore, typing.Iterable[System.Collections.Generic.KeyValuePair[str, typing.List[int]]]):
   114	    """Helper class for easier access to IObjectStore methods"""
   115	
   116	    @property
   117	    def max_size(self) -> int:
   118	        """Gets the maximum storage limit in bytes"""
   119	        ...
   120	
   121	    @property
   122	    def max_files(self) -> int:
   123	        """Gets the maximum number of files allowed"""
   124	        ...
   125	
   126	    @property
   127	    def error_raised(self) -> _EventContainer[typing.Callable[[System.Object, QuantConnect.Interfaces.ObjectStoreErrorRaisedEventArgs], typing.Any], typing.Any]:
   128	        """Event raised each time there's an error"""
   129	        ...
   130	
   131	    @error_raised.setter
   132	    def error_raised(self, value: _EventContainer[typing.Callable[[System.Object, QuantConnect.Interfaces.ObjectStoreErrorRaisedEventArgs], typing.Any], typing.Any]) -> None:
   133	        ...
   134	
   135	    @property
   136	    def keys(self) -> System.Collections.Generic.ICollection[str]:
   137	        """Returns the file paths present in the object store. This is specially useful not to load the object store into memory"""
   138	        ...
   139	
   140	    @property
   141	    def read_json(self) -> QuantConnect.Storage._ObjectStore_ReadJson:
   142	        ...
   143	
   144	    @property
   145	    def read_xml(self) -> QuantConnect.Storage._ObjectStore_ReadXml:
   146	        ...
   147	
   148	    @property
   149	    def save_json(self) -> QuantConnect.Storage._ObjectStore_SaveJson:
   150	        ...
   151	
   152	    @property
   153	    def save_xml(self) -> QuantConnect.Storage._ObjectStore_SaveXml:
   154	        ...
   155	
   156	    def __init__(self, store: QuantConnect.Interfaces.IObjectStore) -> None:
   157	        """
   158	        Initializes a new instance of the ObjectStore class
   159	        
   160	        :param store: The IObjectStore instance to wrap
   161	        """
   162	        ...
   163	
   164	    def __iter__(self) -> typing.Iterator[System.Collections.Generic.KeyValuePair[str, typing.List[int]]]:
   165	        ...
   166	
   167	    def clear(self) -> None:
   168	        """Will clear the object store state cache. This is useful when the object store is used concurrently by nodes which want to share information"""
   169	        ...
   170	
   171	    def contains_key(self, path: str) -> bool:
   172	        """
   173	        Determines whether the store contains data for the specified path
   174	        
   175	        :param path: The object path
   176	        :returns: True if the key was found.
   177	        """
   178	        ...
   179	
   180	    def delete(self, path: str) -> bool:
   181	        """
   182	        Deletes the object data for the specified path
   183	        
   184	        :param path: The object path
   185	        :returns: True if the delete operation was successful.
   186	        """
   187	        ...
   188	
   189	    def dispose(self) -> None:
   190	        """Performs application-defined tasks associated with freeing, releasing, or resetting unmanaged resources."""
   191	        ...
   192	
   193	    def get_enumerator(self) -> System.Collections.Generic.IEnumerator[System.Collections.Generic.KeyValuePair[str, typing.List[int]]]:
   194	        """
   195	        Returns an enumerator that iterates through the collection.
   196	        
   197	        :returns: A System.Collections.Generic.IEnumerator`1 that can be used to iterate through the collection.
   198	        """
   199	        ...
   200	
   201	    def get_file_path(self, path: str) -> str:
   202	        """
   203	        Returns the file path for the specified path
   204	        
   205	        :param path: The object path
   206	        :returns: The path for the file.
   207	        """
   208	        ...
   209	
   210	    def initialize(self, user_id: int, project_id: int, user_token: str, controls: QuantConnect.Packets.Controls, algorithm_mode: QuantConnect.AlgorithmMode) -> None:
   211	        """
   212	        Initializes the object store
   213	        
   214	        :param user_id: The user id
   215	        :param project_id: The project id
   216	        :param user_token: The user token
   217	        :param controls: The job controls instance
   218	        :param algorithm_mode: The algorithm mode
   219	        """
   220	        ...
   221	
   222	    def read(self, path: str, encoding: System.Text.Encoding = None) -> str:
   223	        """
   224	        Returns the string object data for the specified path
   225	        
   226	        :param path: The object path
   227	        :param encoding: The string encoding used
   228	        :returns: A string containing the data.
   229	        """
   230	        ...
   231	
   232	    def read_bytes(self, path: str) -> typing.List[int]:
   233	        """
   234	        Returns the object data for the specified path
   235	        

**Inspecting scheduling methods**

I need to look at `QuantConnect/Scheduling`, particularly the `schedule.on` method, and check if it's related to Stage 4. I'll also verify the `ScheduledEvents` from the previous stage. The user wants to know about dependencies from earlier stages, so exploring the schedule methods would be helpful. Currently, `self.schedule.on` is being used on line 183, but Stage 4 completes while `ScheduledEvents` still fire. I'll check if `schedule.on`, `date_rules.every_day`, and `time_rules` are correctly configured.
exec
/bin/zsh -lc 'rg -n "date_rules|time_rules" .venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi' in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
3270:    def date_rules(self) -> QuantConnect.Scheduling.DateRules:
3275:    def time_rules(self) -> QuantConnect.Scheduling.TimeRules:

exec
/bin/zsh -lc "rg -n \"def on\\(|def every_day\\(|def after_market_close\\(|def before_market_close\\(\" .venv/lib/python3.11/site-packages/QuantConnect/Algorithm .venv/lib/python3.11/site-packages/QuantConnect/Scheduling -g '*.pyi'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:170:    def every_day(self, symbol: typing.Union[QuantConnect.Symbol, str, QuantConnect.Data.Market.BaseContract, QuantConnect.Securities.Security], extended_market_hours: bool = False) -> QuantConnect.Scheduling.IDateRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:181:    def every_day(self) -> QuantConnect.Scheduling.IDateRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:190:    def every_day(self, symbol: str, extended_market_hours: bool = False) -> QuantConnect.Scheduling.IDateRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:271:    def on(self, year: int, month: int, day: int) -> QuantConnect.Scheduling.IDateRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:282:    def on(self, *dates: typing.Union[datetime.datetime, typing.Iterable[datetime.datetime]]) -> QuantConnect.Scheduling.IDateRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:707:    def after_market_close(self, symbol: typing.Union[QuantConnect.Symbol, str, QuantConnect.Data.Market.BaseContract, QuantConnect.Securities.Security], minutes_after_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:719:    def after_market_close(self, minutes_after_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:732:    def after_market_close(self, symbol: str, minutes_after_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:839:    def before_market_close(self, symbol: typing.Union[QuantConnect.Symbol, str, QuantConnect.Data.Market.BaseContract, QuantConnect.Securities.Security], minutes_before_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:851:    def before_market_close(self, minutes_before_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:864:    def before_market_close(self, symbol: str, minutes_before_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.ITimeRule:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1088:    def before_market_close(self, symbol: typing.Union[QuantConnect.Symbol, str, QuantConnect.Data.Market.BaseContract, QuantConnect.Securities.Security], minute_before_close: float = 0, extended_market_close: bool = False) -> QuantConnect.Scheduling.IFluentSchedulingRunnable:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1109:    def every_day(self, symbol: typing.Union[QuantConnect.Symbol, str, QuantConnect.Data.Market.BaseContract, QuantConnect.Securities.Security]) -> QuantConnect.Scheduling.IFluentSchedulingTimeSpecifier:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1114:    def every_day(self) -> QuantConnect.Scheduling.IFluentSchedulingTimeSpecifier:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1129:    def on(self, year: int, month: int, day: int) -> QuantConnect.Scheduling.IFluentSchedulingTimeSpecifier:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1134:    def on(self, *dates: typing.Union[datetime.datetime, typing.Iterable[datetime.datetime]]) -> QuantConnect.Scheduling.IFluentSchedulingTimeSpecifier:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1206:    def on(self, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Any) -> QuantConnect.Scheduling.ScheduledEvent:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1217:    def on(self, name: str, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Any) -> QuantConnect.Scheduling.ScheduledEvent:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1229:    def on(self, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Callable[[], typing.Any]) -> QuantConnect.Scheduling.ScheduledEvent:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1240:    def on(self, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Callable[[str, datetime.datetime], typing.Any]) -> QuantConnect.Scheduling.ScheduledEvent:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1251:    def on(self, name: str, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Callable[[], typing.Any]) -> QuantConnect.Scheduling.ScheduledEvent:
.venv/lib/python3.11/site-packages/QuantConnect/Scheduling/__init__.pyi:1263:    def on(self, name: str, date_rule: QuantConnect.Scheduling.IDateRule, time_rule: QuantConnect.Scheduling.ITimeRule, callback: typing.Callable[[str, datetime.datetime], typing.Any]) -> QuantConnect.Scheduling.ScheduledEvent:

**Considering code review concerns**

I need to think about possibly adding `add_equity` in a previous stage since it's currently used only in the post-stage. Stage 4's scope doesn’t include it for tickers, which feels like scope creep since the repo has advanced. I might check the git status, but it’s probably not necessary; I could see temporary warnings. I should also inspect some documents and `core/universe.py`, as there are no tests for reproducibility or real CSVs. There’s a need for a more rigorous testing approach overall.
**Assessing testing requirements**

I'm looking at the need for reproducibility under T1 acceptance and noting that tests for T3 lack explicit reproducibility. I should report the gap as MEDIO/BAJO. There's a count discrepancy in real storage (74/68), and while there’s no automated test for real CSV counts, that might be acceptable due to ObjectStore being external. The user wants to trace the objective to code and tests. I must highlight if any Done when lacks a test, especially regarding integration in `main.py`, which seems to be untested. Overall, it feels like manual backtest evidence is not executed properly.
**Evaluating test acceptance criteria**

I'm considering whether a lean backtest should count as acceptance rather than a unit test. The user is asking for "implementation and a test" for each criterion, which makes me think we should report if there's no corresponding code or test. The AGENTS guidelines say that if a criterion lacks implementation or a test, it should be marked as a finding. For the "backtest loguea" with implementation but no repo test, it might not fit as a unit test, so I'm wondering if I should just mark it as N/A for manual.
**Evaluating code issues**

I realize the current code isn't passing the per-strategy universe to the pipeline, which seems critical. The user is only asking about Stage 4 and its dependencies, but I wonder if that connects to the underlying issue. The UniverseSpec states "Lista de símbolos de una estrategia," but the main function only seems to unite tickers, losing the mapping from the strategy to its universe. I should look into how to align that better.
**Reviewing strategy functionality**

I’m scanning through the strategy functionalities and noticed a significant bug related to how it handles the universe in Stage4. The objective here is to expose symbols by strategy, but it seems the current code isn't storing per-strategy tickers correctly; instead, it’s just giving a union. This could create issues later because we’re not using those tickers until Stage5. I’ll need to inspect the pipeline to verify what’s going wrong.
codex
Estoy revisando una interacción importante con etapas posteriores: si los tickers cargados por estrategia se conservan como universo por estrategia o si se mezclan solo como unión global. Aunque el repo avanzó más allá de Etapa 4, esto afecta directamente si `UniverseSpec` sigue cumpliendo su contrato de “universo por estrategia”.
exec
/bin/zsh -lc "nl -ba trade-scanner/strategies/base.py | sed -n '1,240p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "nl -ba trade-scanner/core/pipeline.py | sed -n '1,260p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	"""Pipeline (L4): el embudo end-to-end de una estrategia + el contrato de salida `ScanResult`.
     2	
     3	Negocio puro, importable sin CLR (patrón features/rules): cero AlgorithmImports. El `ScanPipeline`
     4	recibe TODO resuelto en initialize() (D7.1) — rules ya construidas con su `side`, `series`,
     5	`thresholds`, `top_n`, `partial_bar` — y su `scan` solo LEE estado de `SymbolData`: gate por series
     6	referenciadas (B, D7.7), ranking `top_n` por `day_change_pct`, snapshot único por símbolo (A.1) y
     7	cascada de rules → `ScanResult`. La salida a archivo/notificación es Etapa 8; aquí vive en memoria +
     8	log, este último vía un callable INYECTADO (L4 no habla con `QCAlgorithm`).
     9	"""
    10	from collections.abc import Callable, Iterable
    11	from dataclasses import dataclass, field
    12	from datetime import datetime
    13	from typing import TYPE_CHECKING
    14	
    15	from core.features import (
    16	    FeatureNotReady,
    17	    build_position_snapshot,
    18	    day_change_pct,
    19	    reference_price,
    20	    snapshot_evidence,
    21	)
    22	from core.timeframes import TIMEFRAMES
    23	
    24	if TYPE_CHECKING:
    25	    from core.rules import SMAPositionRule
    26	    from core.symbol_data import SymbolData
    27	
    28	
    29	@dataclass
    30	class ScanResult:
    31	    """Contrato de salida (L4): un candidato de la watchlist. El pipeline lo llena (Etapa 7);
    32	    la serialización CSV/JSON es Etapa 8.
    33	
    34	    Campos de §5 de PLAN.md (D7.8). `price` = el `reference_price` único (no per-tf). `sma_evidence`
    35	    = `snapshot_evidence` proyectado sobre la unión de series (proyección del snapshot único, NO un
    36	    recompute — D6B.7). `rules_passed_count` = nº de rules `required` que pasaron (score de ranking).
    37	    Todos los campos traen default → el contrato mínimo de 6B (`ScanResult()`) sigue construible.
    38	    """
    39	
    40	    strategy: str = ""
    41	    as_of: datetime | None = None
    42	    ticker: str = ""
    43	    direction: str = ""
    44	    partial_bar: bool = False
    45	    price: float = 0.0
    46	    time_frames_evaluated: list[str] = field(default_factory=list)
    47	    sma_evidence: dict = field(default_factory=dict)
    48	    passed_rules: list[str] = field(default_factory=list)
    49	    rules_passed_count: int = 0
    50	
    51	
    52	class ScanPipeline:
    53	    """Una estrategia resuelta (D7.1): el bundle inmutable de su composición + el embudo `scan`.
    54	
    55	    Construido en initialize() con el `side` ya resuelto (`direction→side` en un solo punto, D7.3);
    56	    las `rules` llegan ya espejadas. El scan es lectura pura sobre `SymbolData`: cero parsing de
    57	    config, cero resolución de `direction` en el hot path.
    58	    """
    59	
    60	    def __init__(
    61	        self,
    62	        strategy_name: str,
    63	        direction: str,
    64	        side: str,
    65	        rules: list["SMAPositionRule"],
    66	        series: Iterable[tuple[str, int]],
    67	        thresholds: dict[str, float],
    68	        top_n: int,
    69	        partial_bar: bool,
    70	    ) -> None:
    71	        self.strategy_name = strategy_name
    72	        self.direction = direction
    73	        self.side = side  # ya horneado en las rules; se guarda como estado resuelto del pipeline
    74	        self.rules = rules
    75	        self.series = set(series)
    76	        self.thresholds = thresholds
    77	        self.top_n = top_n
    78	        self.partial_bar = partial_bar
    79	        # Timeframes evaluados en orden canónico del registro (D, W, M — como §5), no alfabético.
    80	        order = list(TIMEFRAMES)
    81	        self.time_frames_evaluated = sorted(
    82	            {tf for tf, _period in self.series},
    83	            key=lambda tf: order.index(tf) if tf in order else len(order),
    84	        )
    85	
    86	    def scan(
    87	        self,
    88	        symbol_data_map: dict,
    89	        as_of: datetime | None,
    90	        log: Callable[[str], None] | None = None,
    91	    ) -> list[ScanResult]:
    92	        """Embudo end-to-end: gate (B) → ranking top_n → snapshot+cascada → ScanResult.
    93	
    94	        `symbol_data_map`: `{symbol: SymbolData}` (clave LEAN Symbol; el ticker sale de
    95	        `sd.symbol.value`). `log`: callable opcional que recibe cada línea de exclusión/embudo
    96	        (inyectado por main.py; los tests capturan en una lista). Orden determinista por ticker
    97	        (reproducibilidad, consideración #8).
    98	        """
    99	        emit = log or (lambda _msg: None)
   100	        candidates = sorted(symbol_data_map.values(), key=lambda sd: sd.symbol.value)
   101	
   102	        # 1. Gate (B, D7.7): excluir si alguna serie REFERENCIADA está fría. No is_ready() global.
   103	        gated = []
   104	        for sd in candidates:
   105	            cold = next(
   106	                ((tf, p) for tf, p in sorted(self.series) if not sd.is_ready(tf, p)), None
   107	            )
   108	            if cold is not None:
   109	                emit(
   110	                    f"[{self.strategy_name}] excluido {sd.symbol.value}: "
   111	                    f"warmup incompleto, serie {cold[0]}:{cold[1]} fría"
   112	                )
   113	                continue
   114	            gated.append(sd)
   115	
   116	        # 2. Ranking por day_change_pct: desc long (gainers) / asc short (decliners); tie-break
   117	        #    ticker alfabético (sort estable: ticker primero, luego day_change con reverse).
   118	        scored: list[tuple[float, "SymbolData"]] = []
   119	        for sd in gated:
   120	            try:
   121	                change = day_change_pct(sd)
   122	            except FeatureNotReady as exc:
   123	                emit(f"[{self.strategy_name}] excluido {sd.symbol.value}: {exc}")
   124	                continue
   125	            scored.append((change, sd))
   126	        scored.sort(key=lambda item: item[1].symbol.value)
   127	        scored.sort(key=lambda item: item[0], reverse=self.direction == "long")
   128	        top = [sd for _change, sd in scored[: self.top_n]]
   129	
   130	        # 3. Snapshot único por símbolo + evaluación de TODAS las rules (sin short-circuit →
   131	        #    evidencia completa). Backstop: FeatureNotReady del builder (p. ej. SMA==0) excluye.
   132	        evaluated: list[tuple] = []
   133	        for sd in top:
   134	            try:
   135	                snapshot = build_position_snapshot(sd, self.series, self.thresholds)
   136	            except FeatureNotReady as exc:
   137	                emit(f"[{self.strategy_name}] excluido {sd.symbol.value}: {exc}")
   138	                continue
   139	            results = [rule.evaluate(snapshot) for rule in self.rules]
   140	            evaluated.append((sd, snapshot, results))
   141	
   142	        # Embudo (arranca en top_n, tras gate+ranking): cascada por rule. Las `required` narrowan;
   143	        # las `optional` informan sin descartar (en V1 todas son required).
   144	        surviving = evaluated
   145	        for i, rule in enumerate(self.rules):
   146	            passers = [entry for entry in surviving if entry[2][i].passed]
   147	            kind = "required" if rule.required else "optional"
   148	            emit(format_filter_line(self.strategy_name, rule.name, len(surviving), len(passers), kind))
   149	            if rule.required:
   150	                surviving = passers
   151	        emit(format_final_line(self.strategy_name, len(surviving)))
   152	
   153	        # 4. ScanResult por superviviente (orden de ranking preservado).
   154	        results_out: list[ScanResult] = []
   155	        for sd, snapshot, rule_results in surviving:
   156	            results_out.append(
   157	                ScanResult(
   158	                    strategy=self.strategy_name,
   159	                    as_of=as_of,
   160	                    ticker=sd.symbol.value,
   161	                    direction=self.direction,
   162	                    partial_bar=self.partial_bar,
   163	                    price=reference_price(sd),
   164	                    time_frames_evaluated=list(self.time_frames_evaluated),
   165	                    sma_evidence=snapshot_evidence(snapshot, self.series),
   166	                    passed_rules=[r.name for r in rule_results if r.passed],
   167	                    rules_passed_count=sum(1 for r in rule_results if r.required and r.passed),
   168	                )
   169	            )
   170	        return results_out
   171	
   172	
   173	def format_filter_line(
   174	    strategy: str, rule_name: str, n_in: int, n_out: int, kind: str
   175	) -> str:
   176	    """Una línea del embudo de filtrado: cuántos símbolos sobreviven a una rule.
   177	
   178	    `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)`, con
   179	    `dropped = n_in - n_out` y `kind ∈ {"required","optional"}`. Pura: solo da formato a
   180	    contadores ya calculados. Símbolos exactos: flecha U+2192 y signo menos U+2212 (no ASCII).
   181	    """
   182	    dropped = n_in - n_out
   183	    return f"[{strategy}] {rule_name}: {n_in} → {n_out} (−{dropped} {kind})"
   184	
   185	
   186	def format_final_line(strategy: str, n: int) -> str:
   187	    """Línea de cierre del embudo: total de candidatos tras todas las rules.
   188	
   189	    `[<strategy>] final: <n> candidatos`.
   190	    """
   191	    return f"[{strategy}] final: {n} candidatos"

 succeeded in 0ms:
     1	"""StrategyConfig (L4): composición declarativa de una estrategia — qué rules canónicas usa
     2	y si su scan es intradía. Negocio puro, importable sin CLR (patrón core): cero AlgorithmImports.
     3	
     4	D7.2: la lista de rules es *código de composición* (referencia a clases de core/rules.py), no
     5	datos de strategies.json. D7.3: las rules se autoran en vocabulario canónico "above" y el `side`
     6	lo inyecta el pipeline una sola vez (direction→side) al llamar build_rules — StrategyConfig nunca
     7	mira `direction`. Por eso guarda *factories* `side -> rule`, no instancias (que tendrían un side
     8	fijo): la misma composición se proyecta a long/short sin re-declararse.
     9	"""
    10	from collections.abc import Callable
    11	from dataclasses import dataclass
    12	from typing import TYPE_CHECKING
    13	
    14	if TYPE_CHECKING:
    15	    from core.rules import SMAPositionRule
    16	
    17	
    18	@dataclass(frozen=True)
    19	class StrategyConfig:
    20	    """Composición de una estrategia V1: nombre, flag de barra parcial y sus rules (factories).
    21	
    22	    `rules`: lista de factories `side -> SMAPositionRule` (no instancias). Cada una construye su
    23	    rule con el `side` que inyecta el pipeline, que la espeja internamente (D6B.4); mantener
    24	    factories deja la simetría long/short resuelta en un solo punto sin duplicar la composición.
    25	    `partial_bar`: metadato del horario (market_close mercado-abierto=True / swing_eod
    26	    cerrado=False, D7.4); NO cambia la fuente de precio. Puro: sin estado de mercado, sin CLR.
    27	    """
    28	
    29	    name: str
    30	    partial_bar: bool
    31	    rules: list[Callable[[str], "SMAPositionRule"]]
    32	
    33	    def build_rules(self, side: str) -> list["SMAPositionRule"]:
    34	        """Materializa las rules para `side` ("above"/"below"); instancias frescas cada llamada.
    35	
    36	        El pipeline lo llama una vez en initialize() con el `side` ya resuelto (D7.1/D7.3). Un
    37	        `side` inválido (p. ej. "long", que es una *direction*) aflora como ValueError fail-fast
    38	        desde mirror_buckets vía el constructor de la rule — no se revalida aquí por duplicado.
    39	        """
    40	        return [make_rule(side) for make_rule in self.rules]
    41	
    42	    def series(self, side: str) -> set[tuple[str, int]]:
    43	        """Unión deduplicada de las `(tf, period)` que las rules referencian (D6B.2).
    44	
    45	        El gate de exclusión del pipeline (B) la usa para chequear SOLO las series que de verdad
    46	        se evalúan, no toda SMA declarada en `SymbolData`. Se deriva de las rules construidas (no
    47	        se almacena aparte); es side-independiente (`tf`/`period` no cambian con el espejo), pero
    48	        construir las rules es lo que permite introspeccionar sus `.tfs`/`.period`.
    49	        """
    50	        return {(tf, rule.period) for rule in self.build_rules(side) for tf in rule.tfs}

exec
/bin/zsh -lc "nl -ba trade-scanner/strategies/market_close.py | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
exec
/bin/zsh -lc "nl -ba trade-scanner/strategies/swing_eod.py | sed -n '1,220p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	"""market_close: misma composición que swing_eod, evaluada ~30 min antes del cierre.
     2	
     3	Reusa LAS MISMAS rules de swing_eod (D7.2; PLAN §6), sin lógica nueva: comparte el mismo list
     4	de factories (`swing_eod.rules`), así "mismas reglas" es literal, no una copia que pueda divergir.
     5	Única diferencia: `partial_bar=True`, porque corre con el mercado ABIERTO y su working bar es el
     6	OHLC parcial del día en curso (D7.4). El precio sigue saliendo del working bar (reference_price),
     7	igual que swing_eod — `partial_bar` es solo metadato del horario, no cambia la fuente de precio.
     8	Puro: sin CLR.
     9	"""
    10	from strategies.base import StrategyConfig
    11	from strategies.swing_eod import swing_eod
    12	
    13	market_close = StrategyConfig(
    14	    name="market_close",
    15	    partial_bar=True,
    16	    rules=swing_eod.rules,  # mismas factories que swing_eod: "mismas reglas" literal (PLAN §6)
    17	)

 succeeded in 0ms:
     1	"""swing_eod: estrategia swing evaluada tras el cierre (long/short según `direction`).
     2	
     3	Composición declarativa (D7.2), sin lógica nueva: precio sobre SMA20 en W y M (una rule
     4	multi-tf), precio sobre SMA20 en D, y no-extendido sobre la SMA8 diaria. Las rules se autoran
     5	en vocabulario canónico "above"; el pipeline inyecta el `side` (D7.3). `partial_bar=False`:
     6	corre con el mercado ya cerrado, su working bar es la sesión completa aún no consolidada (D7.4).
     7	market_close (T3.3) reusa estas mismas rules con `partial_bar=True`. Puro: sin CLR.
     8	"""
     9	from core.rules import NotExtended, SMAPositionRule
    10	from strategies.base import StrategyConfig
    11	
    12	# "above" ESTRICTO: `near` excluido — perseguir solo lo claramente sobre la SMA, no lo que está
    13	# pegado a ella. La inclusión de `near` en "above" es calibración de Etapa 9 (ADR-005 §9.2); el
    14	# default de V1 es estricto. Local a la estrategia: el seam natural si E9 calibra por estrategia.
    15	ABOVE = frozenset({"above_mild", "above_strong", "extended_above"})
    16	
    17	
    18	swing_eod = StrategyConfig(
    19	    name="swing_eod",
    20	    partial_bar=False,
    21	    rules=[
    22	        lambda side: SMAPositionRule(20, ["W", "M"], ABOVE, side, label="SMA"),
    23	        lambda side: SMAPositionRule(20, ["D"], ABOVE, side, label="SMA"),
    24	        lambda side: NotExtended(8, "D", side),
    25	    ],
    26	)

exec
/bin/zsh -lc "nl -ba trade-scanner/tests/test_pipeline.py | sed -n '1,320p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	"""Tests de core/pipeline.py — ScanResult (T7) + formateadores del log de filtrado (T6), Etapa 6B.
     2	
     3	L4 negocio puro: pipeline.py no importa AlgorithmImports. T6: los formateadores solo dan formato a
     4	contadores (NO ejecutan filtrado — eso es Etapa 7); el test reproduce LITERALMENTE las 4 líneas del
     5	ejemplo de la spec, incluidos la flecha U+2192 y el signo menos U+2212 (no el guion ASCII). T7:
     6	contrato mínimo de ScanResult — construible sin args, campos nuevos con sus defaults, sin lógica de
     7	llenado (eso es Etapa 7).
     8	"""
     9	from types import SimpleNamespace
    10	
    11	import pytest
    12	
    13	from core.pipeline import ScanPipeline, ScanResult, format_filter_line, format_final_line
    14	from core.rules import RuleResult
    15	from strategies.swing_eod import swing_eod
    16	
    17	
    18	# (criterio T6) las 4 líneas del ejemplo, reproducidas literalmente desde contadores
    19	def test_filter_log_reproduces_example_lines_literally():
    20	    lines = [
    21	        format_filter_line("swing_eod", "AboveSMA(20,W+M)", 50, 38, "required"),
    22	        format_filter_line("swing_eod", "AboveSMA(20,D)", 38, 29, "required"),
    23	        format_filter_line("swing_eod", "NotExtended(8,D)", 29, 22, "required"),
    24	        format_final_line("swing_eod", 22),
    25	    ]
    26	    assert lines == [
    27	        "[swing_eod] AboveSMA(20,W+M): 50 → 38 (−12 required)",
    28	        "[swing_eod] AboveSMA(20,D): 38 → 29 (−9 required)",
    29	        "[swing_eod] NotExtended(8,D): 29 → 22 (−7 required)",
    30	        "[swing_eod] final: 22 candidatos",
    31	    ]
    32	
    33	
    34	# dropped = n_in - n_out (incluso 0); kind="optional" se renderiza tal cual
    35	def test_filter_line_computes_dropped_and_renders_optional():
    36	    assert (
    37	        format_filter_line("market_close", "NotExtended(8,D)", 29, 29, "optional")
    38	        == "[market_close] NotExtended(8,D): 29 → 29 (−0 optional)"
    39	    )
    40	
    41	
    42	# símbolos exactos: flecha U+2192 y signo menos U+2212 (no '->' ni guion ASCII '-')
    43	def test_filter_line_uses_exact_unicode_symbols():
    44	    line = format_filter_line("s", "R", 10, 3, "required")  # dropped = 7
    45	    assert "→" in line                 # → flecha
    46	    assert "(−7 required)" in line     # − signo menos
    47	    assert "->" not in line                 # no la flecha ASCII
    48	    assert "-7" not in line                 # no el guion ASCII en el dropped
    49	
    50	
    51	# ---------------------------------------------------------------------------
    52	# T7 (Etapa 6B) — ScanResult: contrato mínimo (sin lógica de llenado, eso es Etapa 7).
    53	# Campos nuevos del rediseño del snapshot: rules_passed_count + sma_evidence (proyección).
    54	# ---------------------------------------------------------------------------
    55	
    56	# (T7) contrato mínimo: construible sin args; los campos nuevos traen sus defaults
    57	def test_scanresult_minimal_contract_defaults():
    58	    result = ScanResult()
    59	    assert result.rules_passed_count == 0
    60	    assert result.sma_evidence == {}
    61	
    62	
    63	# (T7) sma_evidence admite la proyección del snapshot {tf:{period:{value,distance_pct,bucket}}}
    64	def test_scanresult_accepts_snapshot_projection_shape():
    65	    evidence = {"D": {20: {"value": 150.20, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    66	    result = ScanResult(rules_passed_count=2, sma_evidence=evidence)
    67	    assert result.rules_passed_count == 2
    68	    assert result.sma_evidence == evidence
    69	
    70	
    71	# (T7) default_factory: cada instancia tiene su PROPIO dict (no el clásico bug de default mutable)
    72	def test_scanresult_evidence_default_is_per_instance():
    73	    a = ScanResult()
    74	    a.sma_evidence["D"] = {20: {}}
    75	    assert ScanResult().sma_evidence == {}  # una instancia nueva no ve la mutación de `a`
    76	
    77	
    78	# (T4.2) ScanResult extendido con los campos de §5, todos con default → contrato mínimo intacto
    79	def test_scanresult_section5_fields_have_defaults():
    80	    r = ScanResult()
    81	    assert r.strategy == "" and r.ticker == "" and r.direction == ""
    82	    assert r.as_of is None and r.partial_bar is False and r.price == 0.0
    83	    assert r.time_frames_evaluated == [] and r.passed_rules == []
    84	
    85	
    86	# ---------------------------------------------------------------------------
    87	# T4.1 — ScanPipeline: gate (B) → ranking top_n → snapshot+cascada → ScanResult.
    88	# Stubs sintéticos (sin CLR). Las rules reales (swing_eod) ejercitan la cascada de
    89	# verdad; StubRule controla la orquestación cuando no importa la lógica de buckets.
    90	# ---------------------------------------------------------------------------
    91	
    92	THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}
    93	SWING_SERIES = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
    94	
    95	
    96	class FakeSymbolData:
    97	    """SymbolData sintético para el pipeline: `.symbol.value` (ticker), `.working_bar` (precio
    98	    "ahora"), `.close("D")` (cierre de ayer), `.is_ready`/`.sma` por serie. `price=None` → sin
    99	    working bar; `cold` marca series no-ready."""
   100	
   101	    def __init__(self, ticker, price, daily_close, smas, cold=frozenset()):
   102	        self.symbol = SimpleNamespace(value=ticker)
   103	        self.working_bar = None if price is None else SimpleNamespace(close=price)
   104	        self._daily_close = daily_close
   105	        self._smas = dict(smas)
   106	        self._cold = set(cold)
   107	
   108	    def is_ready(self, tf, period):
   109	        return (tf, period) not in self._cold
   110	
   111	    def sma(self, tf, period):
   112	        return SimpleNamespace(current=SimpleNamespace(value=self._smas[(tf, period)]))
   113	
   114	    def close(self, tf):
   115	        return self._daily_close
   116	
   117	
   118	class StubRule:
   119	    """Rule de orquestación: `name`/`required` del contrato de SMAPositionRule; `evaluate`
   120	    devuelve un veredicto fijo e ignora el snapshot (la lógica de buckets se prueba en
   121	    test_rules). Para tests donde solo importa el flujo del pipeline, no el filtrado real."""
   122	
   123	    def __init__(self, name, passed=True, required=True):
   124	        self.name = name
   125	        self._passed = passed
   126	        self.required = required
   127	
   128	    def evaluate(self, snapshot):
   129	        return RuleResult(passed=self._passed, evidence={}, name=self.name, required=self.required)
   130	
   131	
   132	def _pipeline(rules, *, direction="long", side="above", series=SWING_SERIES, top_n=50,
   133	              partial_bar=False):
   134	    return ScanPipeline(
   135	        strategy_name="swing_eod", direction=direction, side=side, rules=rules,
   136	        series=series, thresholds=THRESHOLDS, top_n=top_n, partial_bar=partial_bar,
   137	    )
   138	
   139	
   140	def _as_map(symbols):
   141	    return {sd.symbol.value: sd for sd in symbols}
   142	
   143	
   144	# price=102 vs SMA=100 en las 4 series → above_mild en todas → pasa las rules "above".
   145	def _passing(ticker, daily_close):
   146	    return FakeSymbolData(
   147	        ticker, price=102.0, daily_close=daily_close,
   148	        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0},
   149	    )
   150	
   151	
   152	# price=98 vs SMA=100 → below_mild → pasa las rules "below" (decliners).
   153	def _below_passing(ticker, daily_close):
   154	    return FakeSymbolData(
   155	        ticker, price=98.0, daily_close=daily_close,
   156	        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0},
   157	    )
   158	
   159	
   160	# (b) gate: serie REFERENCIADA fría excluye; serie declarada-NO-referenciada fría NO excluye
   161	def test_gate_excludes_referenced_cold_keeps_unreferenced_cold():
   162	    log = []
   163	    series = {("D", 20), ("W", 20)}
   164	    a = FakeSymbolData("AAA", 102.0, 100.0, {("D", 20): 100.0, ("W", 20): 100.0},
   165	                       cold={("W", 20)})                       # W:20 referenciada y fría
   166	    b = FakeSymbolData("BBB", 102.0, 100.0,
   167	                       {("D", 20): 100.0, ("W", 20): 100.0, ("W", 200): 0.0},
   168	                       cold={("W", 200)})                      # W:200 fría pero NO referenciada
   169	    results = _pipeline([StubRule("R1")], series=series).scan(
   170	        _as_map([a, b]), as_of="t0", log=log.append
   171	    )
   172	    assert [r.ticker for r in results] == ["BBB"]
   173	    assert any("AAA" in line and "W:20 fría" in line for line in log)
   174	
   175	
   176	# (c) ranking long: desc por day_change_pct, tie-break ticker, corta en top_n
   177	def test_ranking_long_desc_and_top_n():
   178	    syms = [_passing("AAA", 100.0), _passing("BBB", 98.0),
   179	            _passing("CCC", 101.0), _passing("DDD", 100.0)]
   180	    # day_change: BBB≈0.0408, AAA=0.02, DDD=0.02, CCC≈0.0099 → top2 desc = BBB, AAA (tie→ticker)
   181	    results = _pipeline([StubRule("R1")], direction="long", top_n=2).scan(_as_map(syms), "t0")
   182	    assert [r.ticker for r in results] == ["BBB", "AAA"]
   183	
   184	
   185	# (c) ranking short: asc por day_change_pct (mayores caídas primero), con rules "below" reales
   186	def test_ranking_short_asc_and_top_n():
   187	    syms = [_below_passing("AAA", 100.0), _below_passing("BBB", 102.0),
   188	            _below_passing("CCC", 99.0)]
   189	    # day_change: BBB≈-0.0392, AAA=-0.02, CCC≈-0.0101 → top2 asc = BBB, AAA
   190	    results = _pipeline(swing_eod.build_rules("below"), direction="short", side="below",
   191	                        top_n=2).scan(_as_map(syms), "t0")
   192	    assert [r.ticker for r in results] == ["BBB", "AAA"]
   193	
   194	
   195	# (a) solo los que pasan TODAS las required quedan; rules reales (cascada de verdad)
   196	def _ok():
   197	    return _passing("AAA", 100.0)                                  # above_mild en todo → pasa
   198	
   199	
   200	def _fails_above_d():
   201	    return FakeSymbolData("BBB", 102.0, 100.0,
   202	        {("D", 8): 100.0, ("D", 20): 130.0, ("W", 20): 100.0, ("M", 20): 100.0})  # D:20 below
   203	
   204	
   205	def _fails_not_extended():
   206	    return FakeSymbolData("CCC", 102.0, 100.0,
   207	        {("D", 8): 90.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0})   # D:8 extended
   208	
   209	
   210	def test_only_symbols_passing_all_required_become_results():
   211	    results = _pipeline(swing_eod.build_rules("above")).scan(
   212	        _as_map([_ok(), _fails_above_d(), _fails_not_extended()]), "t0"
   213	    )
   214	    assert [r.ticker for r in results] == ["AAA"]
   215	    assert results[0].rules_passed_count == 3
   216	    assert results[0].passed_rules == ["AboveSMA(20,W+M)", "AboveSMA(20,D)", "NotExtended(8,D)"]
   217	
   218	
   219	# (c) embudo: format_filter_line por rule (cascada) + format_final_line; arranca tras gate+ranking
   220	def test_funnel_cascade_lines():
   221	    log = []
   222	    _pipeline(swing_eod.build_rules("above")).scan(
   223	        _as_map([_ok(), _fails_above_d(), _fails_not_extended()]), "t0", log=log.append
   224	    )
   225	    assert log == [
   226	        "[swing_eod] AboveSMA(20,W+M): 3 → 3 (−0 required)",
   227	        "[swing_eod] AboveSMA(20,D): 3 → 2 (−1 required)",
   228	        "[swing_eod] NotExtended(8,D): 2 → 1 (−1 required)",
   229	        "[swing_eod] final: 1 candidatos",
   230	    ]
   231	
   232	
   233	# (d) ScanResult: campos de §5, price único, partial_bar, evidencia consistente (mismo precio 3 tf)
   234	def test_scanresult_fields_and_single_price_evidence():
   235	    sd = FakeSymbolData("AAA", price=105.0, daily_close=100.0,
   236	        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 102.0, ("M", 20): 103.0})
   237	    [res] = _pipeline(swing_eod.build_rules("above"), partial_bar=False).scan(
   238	        _as_map([sd]), as_of="2026-06-19T21:00:00Z"
   239	    )
   240	    assert res.strategy == "swing_eod"
   241	    assert res.ticker == "AAA"
   242	    assert res.direction == "long"
   243	    assert res.partial_bar is False
   244	    assert res.price == 105.0
   245	    assert res.as_of == "2026-06-19T21:00:00Z"
   246	    assert res.time_frames_evaluated == ["D", "W", "M"]   # orden canónico, no alfabético
   247	    assert res.rules_passed_count == 3
   248	    # evidencia internamente consistente: value·(1+distance_pct) == el precio único (105) en cada serie
   249	    for periods in res.sma_evidence.values():
   250	        for entry in periods.values():
   251	            assert entry["value"] * (1 + entry["distance_pct"]) == pytest.approx(105.0, abs=1e-9)
   252	
   253	
   254	# (c) build_position_snapshot se invoca UNA vez por símbolo
   255	def test_build_snapshot_called_once_per_symbol(monkeypatch):
   256	    import core.pipeline as pipeline_mod
   257	
   258	    calls = []
   259	    real = pipeline_mod.build_position_snapshot
   260	
   261	    def spy(sd, series, thresholds):
   262	        calls.append(sd.symbol.value)
   263	        return real(sd, series, thresholds)
   264	
   265	    monkeypatch.setattr(pipeline_mod, "build_position_snapshot", spy)
   266	    _pipeline([StubRule("R1")]).scan(_as_map([_passing("AAA", 100.0), _passing("BBB", 100.0)]), "t0")
   267	    assert sorted(calls) == ["AAA", "BBB"]
   268	    assert len(calls) == len(set(calls))  # exactamente una vez por símbolo
   269	
   270	
   271	# (backstop) pasa el gate (series ready) pero una SMA es degenerada (==0) → build_position_snapshot
   272	# levanta FeatureNotReady; el pipeline lo excluye+loguea sin crashear (no es el gate primario).
   273	def test_snapshot_backstop_excludes_degenerate_sma():
   274	    log = []
   275	    sd = FakeSymbolData("AAA", 102.0, 100.0,
   276	        {("D", 8): 100.0, ("D", 20): 0.0, ("W", 20): 100.0, ("M", 20): 100.0})  # D:20 SMA==0
   277	    results = _pipeline([StubRule("R1")]).scan(_as_map([sd]), "t0", log=log.append)
   278	    assert results == []
   279	    assert any("AAA" in line for line in log)  # excluido y logueado
   280	
   281	
   282	# (d) partial_bar de la estrategia se propaga al ScanResult (market_close=True vs swing_eod=False)
   283	def test_partial_bar_propagates_to_scanresult():
   284	    [res] = _pipeline(swing_eod.build_rules("above"), partial_bar=True).scan(
   285	        _as_map([_passing("AAA", 100.0)]), "t0"
   286	    )
   287	    assert res.partial_bar is True
   288	
   289	
   290	# (a) watchlist reproducible: mismo input → misma salida (tickers + orden)
   291	def test_results_reproducible_across_runs():
   292	    def run():
   293	        syms = [_passing("CCC", 98.0), _passing("AAA", 100.0), _passing("BBB", 100.0)]
   294	        results = _pipeline([StubRule("R1")], top_n=3).scan(_as_map(syms), "t0")
   295	        return [r.ticker for r in results]
   296	
   297	    # CCC (change≈0.0408) primero; AAA y BBB empatan en 0.02 → tie-break ticker asc
   298	    assert run() == ["CCC", "AAA", "BBB"]
   299	    assert run() == run()

exec
/bin/zsh -lc "nl -ba trade-scanner/tests/test_strategies.py | sed -n '1,260p'" in /Users/guille/Documents/quant/trade-scanner
 succeeded in 0ms:
     1	"""Tests de strategies/ (Etapa 7).
     2	
     3	T3.1: StrategyConfig — mecanismo de composición (build_rules above/below con names y espejo,
     4	series dedup + side-independiente, partial_bar/name, instancias frescas, side inválido). Se
     5	prueba con un StrategyConfig sintético (rules reales de core/rules.py, pero la estrategia
     6	concreta swing_eod/market_close es T3.2/T3.3). Sin CLR: L4 es negocio puro.
     7	"""
     8	import pytest
     9	
    10	from core.rules import NotExtended, SMAPositionRule
    11	from strategies import STRATEGIES
    12	from strategies.base import StrategyConfig
    13	from strategies.market_close import market_close
    14	from strategies.swing_eod import swing_eod
    15	
    16	# Vocabulario canónico "above" estricto: `near` excluido (calibración de near = E9, ADR-005 §9.2).
    17	ABOVE = {"above_mild", "above_strong", "extended_above"}
    18	
    19	
    20	def _sample_config(partial_bar: bool = False) -> StrategyConfig:
    21	    """Config sintética con la forma de swing_eod (T3.2) pero definida aquí: aísla el mecanismo
    22	    de StrategyConfig de la estrategia concreta. Las `rules` son factories `side -> rule`."""
    23	    return StrategyConfig(
    24	        name="sample",
    25	        partial_bar=partial_bar,
    26	        rules=[
    27	            lambda side: SMAPositionRule(20, ["W", "M"], ABOVE, side, label="SMA"),
    28	            lambda side: SMAPositionRule(20, ["D"], ABOVE, side, label="SMA"),
    29	            lambda side: NotExtended(8, "D", side),
    30	        ],
    31	    )
    32	
    33	
    34	# (a) build_rules("above") → names canónicos AboveSMA + NotExtended, con el side propagado
    35	def test_build_rules_above_names_and_side():
    36	    rules = _sample_config().build_rules("above")
    37	    assert [r.name for r in rules] == ["AboveSMA(20,W+M)", "AboveSMA(20,D)", "NotExtended(8,D)"]
    38	    assert all(r.side == "above" for r in rules)
    39	
    40	
    41	# (a) build_rules("below") → names espejados Below* y buckets espejados (NotExtended excluye
    42	# extended_below en short; AboveSMA → BelowSMA con su set permitido reflejado)
    43	def test_build_rules_below_names_and_mirror():
    44	    rules = _sample_config().build_rules("below")
    45	    assert [r.name for r in rules] == ["BelowSMA(20,W+M)", "BelowSMA(20,D)", "NotExtended(8,D)"]
    46	    assert all(r.side == "below" for r in rules)
    47	    assert rules[0].buckets_allowed == frozenset(
    48	        {"below_mild", "below_strong", "extended_below"}
    49	    )  # ABOVE espejado
    50	    not_extended = rules[2].buckets_allowed
    51	    assert "extended_below" not in not_extended  # el extremo favorable-short queda excluido
    52	    assert "extended_above" in not_extended      # su espejo sí permitido
    53	
    54	
    55	# (b) series(side) = unión deduplicada de (tf, period), independiente del side
    56	def test_series_is_dedup_union_and_side_independent():
    57	    cfg = _sample_config()
    58	    expected = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
    59	    assert cfg.series("above") == expected
    60	    assert cfg.series("below") == expected  # mismo set: tf/period no cambian con el espejo
    61	
    62	
    63	# build_rules devuelve instancias FRESCAS cada llamada (no comparte estado mutable entre scans)
    64	def test_build_rules_returns_fresh_instances():
    65	    cfg = _sample_config()
    66	    first, second = cfg.build_rules("above"), cfg.build_rules("above")
    67	    assert first is not second
    68	    assert all(a is not b for a, b in zip(first, second))
    69	
    70	
    71	# name y partial_bar se guardan tal cual (partial_bar = metadato del horario, D7.4)
    72	def test_name_and_partial_bar_stored():
    73	    assert _sample_config(partial_bar=True).partial_bar is True
    74	    assert _sample_config().partial_bar is False
    75	    assert _sample_config().name == "sample"
    76	
    77	
    78	# side inválido (p. ej. 'long', que es una direction) → ValueError fail-fast desde build_rules
    79	def test_build_rules_invalid_side_raises():
    80	    with pytest.raises(ValueError, match="side inválido"):
    81	        _sample_config().build_rules("long")
    82	
    83	
    84	# ---------------------------------------------------------------------------
    85	# T3.2 — swing_eod: la StrategyConfig concreta (config real, no el stub sintético).
    86	# Los asserts pinchan los buckets EXACTOS (no el constante ABOVE) para fijar de verdad
    87	# el "above estricto" (near excluido) sin re-derivar del mismo símbolo.
    88	# ---------------------------------------------------------------------------
    89	
    90	# (a) build_rules("above"): 3 rules canónicas con names exactos, en orden
    91	def test_swing_eod_above_rule_names():
    92	    assert [r.name for r in swing_eod.build_rules("above")] == [
    93	        "AboveSMA(20,W+M)",
    94	        "AboveSMA(20,D)",
    95	        "NotExtended(8,D)",
    96	    ]
    97	
    98	
    99	# (a) build_rules("below"): names espejados + buckets espejados (NotExtended excluye extended_below)
   100	def test_swing_eod_below_rule_names_and_mirror():
   101	    rules = swing_eod.build_rules("below")
   102	    assert [r.name for r in rules] == ["BelowSMA(20,W+M)", "BelowSMA(20,D)", "NotExtended(8,D)"]
   103	    below = frozenset({"below_mild", "below_strong", "extended_below"})
   104	    assert rules[0].buckets_allowed == below  # W+M: ABOVE espejado
   105	    assert rules[1].buckets_allowed == below  # D
   106	    assert "extended_below" not in rules[2].buckets_allowed  # NotExtended short
   107	    assert "extended_above" in rules[2].buckets_allowed      # su espejo sí permitido
   108	
   109	
   110	# (a) "above" ESTRICTO: las AboveSMA excluyen `near` (decisión de etapa, ADR-005 §9.2). NotExtended
   111	# NO es "above estricto" — permite near; solo excluye el extremo favorable.
   112	def test_swing_eod_above_excludes_near():
   113	    above = swing_eod.build_rules("above")
   114	    strict = frozenset({"above_mild", "above_strong", "extended_above"})
   115	    assert above[0].buckets_allowed == strict
   116	    assert above[1].buckets_allowed == strict
   117	    assert "near" not in above[0].buckets_allowed
   118	    assert "near" not in above[1].buckets_allowed
   119	
   120	
   121	# (b) series de swing_eod = unión deduplicada, independiente del side
   122	def test_swing_eod_series():
   123	    expected = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
   124	    assert swing_eod.series("above") == expected
   125	    assert swing_eod.series("below") == expected
   126	
   127	
   128	# (c) partial_bar False (swing corre con el mercado ya cerrado, D7.4); name correcto
   129	def test_swing_eod_partial_bar_and_name():
   130	    assert swing_eod.partial_bar is False
   131	    assert swing_eod.name == "swing_eod"
   132	
   133	
   134	# ---------------------------------------------------------------------------
   135	# T3.3 — market_close: misma composición que swing_eod, solo difiere partial_bar.
   136	# ---------------------------------------------------------------------------
   137	
   138	# (c) market_close.partial_bar True (corre con el mercado abierto, D7.4); name correcto
   139	def test_market_close_partial_bar_and_name():
   140	    assert market_close.partial_bar is True
   141	    assert market_close.name == "market_close"
   142	
   143	
   144	# (c) rules IDÉNTICAS a swing_eod: mismo list de factories (literal) → mismos names/buckets
   145	# en ambos sides; la única diferencia entre las dos configs es partial_bar.
   146	def test_market_close_rules_identical_to_swing_eod():
   147	    assert market_close.rules is swing_eod.rules  # mismas factories, no una copia
   148	    for side in ("above", "below"):
   149	        mc, se = market_close.build_rules(side), swing_eod.build_rules(side)
   150	        assert [r.name for r in mc] == [r.name for r in se]
   151	        assert [r.buckets_allowed for r in mc] == [r.buckets_allowed for r in se]
   152	    assert market_close.series("above") == swing_eod.series("above")
   153	    assert market_close.partial_bar != swing_eod.partial_bar  # único campo que difiere
   154	
   155	
   156	# ---------------------------------------------------------------------------
   157	# T3.4 — STRATEGIES: registro nombre-de-config → StrategyConfig (4 claves → 2 instancias).
   158	# ---------------------------------------------------------------------------
   159	
   160	# (d) las 4 claves de config mapean a 2 instancias; *_short apunta a la MISMA instancia que su long
   161	def test_strategies_registry_maps_four_keys_to_two_instances():
   162	    assert set(STRATEGIES) == {"swing_eod", "swing_eod_short", "market_close", "market_close_short"}
   163	    assert STRATEGIES["swing_eod"] is swing_eod
   164	    assert STRATEGIES["swing_eod_short"] is swing_eod          # misma instancia (side vía direction)
   165	    assert STRATEGIES["market_close"] is market_close
   166	    assert STRATEGIES["market_close_short"] is market_close    # misma instancia
   167	    assert len({id(cfg) for cfg in STRATEGIES.values()}) == 2  # 4 claves, 2 instancias distintas

**Analyzing data mapping implications**

I'm considering how the union is enough for SymbolData but not for the pipeline. It looks like we've got "universe loaded per strategy," and in the current stage 7, losing mapping is critical. But if later `ScanPipeline.scan` processes everything, it might cause contamination between long and short universes. This doesn't align with Etapa 4 acceptance standards and seems to disrupt the overall flow. I'm thinking through the implications of this situation!
**Clarifying file claims**

I need to ensure I don’t claim that I've read "all files" if that’s not the case. I’ve read the relevant documents and files, but I didn’t go through all the tests. It's not necessary for "SOLO Etapa4," but I inspected related content. I should definitely mention the scope of what I reviewed and maybe update the plan to reflect what’s been completed before finalizing everything. It’s all about being accurate!
codex
Ya tengo los hallazgos principales y la matriz de trazabilidad. Voy a cerrar el plan y redactar el reporte en formato de revisión, separando defectos de Etapa 4 de limitaciones de verificación por el sandbox.
  ✓ Leer alcance Etapa 4 y documentos de diseño aplicables
  ✓ Mapear archivos y dependencias tocadas por Etapa 4
  ✓ Auditar implementación, API LEAN y corrección funcional
  ✓ Auditar tests y trazabilidad objetivo-código-test
  → Redactar hallazgos y resumen ejecutivo
  ✓ Leer alcance Etapa 4 y documentos de diseño aplicables
  ✓ Mapear archivos y dependencias tocadas por Etapa 4
  ✓ Auditar implementación, API LEAN y corrección funcional
  ✓ Auditar tests y trazabilidad objetivo-código-test
  ✓ Redactar hallazgos y resumen ejecutivo
codex
**Hallazgos**

**Corrección Funcional**
1. [trade-scanner/core/universe.py:76](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:76)  
Severidad: **ALTO**  
`max_tickers` no valida el tope duro de producto `≤200`. Si `config/strategies.json` define por error `max_universe=500`, `UniverseSpec` puede devolver más de 200 tickers, violando PLAN/SPECS y AGENTS.  
Sugerencia: validar en `__init__` que `1 <= max_tickers <= 200` o truncar siempre con `min(max_tickers, 200)` y fallar si la config intenta superar 200.

2. [trade-scanner/main.py:47](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:47), [trade-scanner/main.py:55](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:55), [trade-scanner/core/pipeline.py:100](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:100)  
Severidad: **ALTO**  
La carga por estrategia se convierte en una unión global de tickers y no queda persistida como universo por estrategia. En el estado actual posterior, `ScanPipeline.scan()` recibe todo `symbol_data_map`, así que una estrategia long puede evaluar símbolos de `swing_declines` y una short símbolos de `swing_advances`. Esto rompe la entidad `UniverseSpec` de SPECS: “lista de símbolos de una estrategia”.  
Sugerencia: conservar `self.universe_by_strategy[name] = set(loaded)` en `main.py` y pasar al pipeline un mapa filtrado por esa estrategia, o hacer que `ScanPipeline` reciba explícitamente su universo.

3. [trade-scanner/core/universe.py:10](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:10)  
Severidad: **MEDIO**  
`COLUMN_ALIASES` solo normaliza una parte del contrato de PLAN §5. Faltan aliases como `Name→name`, `Change→chg_1d`, `5D Chg→chg_5d`, `5D High→high_5d`, `5D Low→low_5d`, `Time→date`. Hoy el filtro usa `avg_vol_5d` y `price`, pero el contrato dice que `UniverseSpec` normaliza el mapa de columnas ratificado.  
Sugerencia: completar `COLUMN_ALIASES` con todo el contrato §5 y parsear numéricos/porcentajes de esas columnas cuando existan.

4. [trade-scanner/core/universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:52)  
Severidad: **MEDIO**  
La validación de columnas requeridas está hardcodeada a `avg_vol_5d` y `price`, no a las columnas realmente usadas por `filter_expr`. Un filtro futuro sobre `pct_chg_5d` exigiría columnas que no usa; un filtro sobre un alias no mapeado fallaría tarde en `df.query()` con poco contexto.  
Sugerencia: validar contra un allowlist de aliases soportados y envolver errores de `df.query()` con `universe_key` y `filter_expr`.

**Tests**
5. [trade-scanner/tests/test_universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:52)  
Severidad: **MEDIO**  
No hay test que demuestre el tope duro absoluto de 200 cuando `max_tickers` viene mal configurado, ni test del alias map completo del contrato PLAN §5. Los tests cubren el caso feliz actual, pero no blindan los invariantes más importantes de Etapa 4.  
Sugerencia: añadir casos `max_tickers=201`/CSV >200, alias completo, y filtro que use un alias distinto a `avg_vol_5d`/`price`.

**Alineación / Documentación**
6. [README.md:103](/Users/guille/Documents/quant/trade-scanner/README.md:103), [README.md:111](/Users/guille/Documents/quant/trade-scanner/README.md:111)  
Severidad: **BAJO**  
README aún describe un CSV `ticker,price,avg_dollar_volume` y dice que el filtro vive en `config.json`. Eso contradice PLAN/SPECS de Etapa 4: CSV Barchart vía ObjectStore y filtro en `config/strategies.json`.  
Sugerencia: actualizar README al contrato real de `UniverseSpec`.

**API LEAN / Reglas Duras**
No encontré órdenes en código ejecutable. `UniverseSpec` no importa `AlgorithmImports`. Los métodos LEAN relevantes de Etapa 4 están en snake_case y confirmados en stubs locales: `QCAlgorithm.object_store`, `ObjectStore.read(path) -> str`, `get_parameter()`, `log()`, `schedule.on`, `date_rules.every_day`, `time_rules.after_market_close/before_market_close`.

**Trazabilidad Etapa 4**

| Criterio | Código | Test / evidencia | Estado |
|---|---|---|---|
| `core/universe.py` existe y exporta `UniverseSpec` | [universe.py:27](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:27), [__init__.py:5](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/__init__.py:5) | import en [test_universe.py:8](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:8) | ✅ |
| Lee CSV desde ObjectStore, footer strip, alias, filtro, orden, tope | [universe.py:43](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:43) | `test_universe.py` 5 tests pasan | ✅ parcial: falta hard cap 200 |
| Con CSV real: advances≈74, declines≈68 | [config/strategies.json:21](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:21) | Validé localmente `storage`: 74 / 68 | ✅ |
| `main.py` loguea universo por 4 estrategias | [main.py:48](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:48), [main.py:57](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:57) | No re-ejecuté `lean backtest` en este sandbox | ⚠️ |
| `env=dev` usa `max_universe` | [config.json:3](/Users/guille/Documents/quant/trade-scanner/trade-scanner/config.json:3), [strategies.json:4](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:4), [main.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:38) | Validé `sample_dev` devuelve 4 | ✅ |
| `UniverseSpec` sin `AlgorithmImports` | [universe.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:1) | `rg AlgorithmImports trade-scanner/core/universe.py` sin import real | ✅ |
| Tests T3.1–T3.5 verdes | [test_universe.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:38) | `5 passed in 0.35s` con pytest host sin captura | ✅ |

**Verificación Ejecutada**

Ejecuté `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -s -p no:cacheprovider trade-scanner/tests/test_universe.py`: `5 passed`.

No ejecuté `bash scripts/run_tests.sh` completo ni `lean backtest` porque este entorno está en sandbox de solo lectura y red restringida; el runner Docker instala paquetes dentro del contenedor.

**Resumen Ejecutivo**

1. Cerrar el agujero del tope duro `≤200`; hoy depende de que la config nunca se equivoque.  
2. No perder el universo por estrategia: ahora se mezcla en una unión global y el pipeline puede escanear símbolos del universo equivocado.  
3. Completar el alias map de PLAN §5 y validar `filter_expr` contra aliases soportados.  
4. Añadir tests para hard cap 200, alias completo y reproducibilidad explícita.  
5. Actualizar README para no documentar un contrato de universo obsoleto.
tokens used
192,302
**Hallazgos**

**Corrección Funcional**
1. [trade-scanner/core/universe.py:76](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:76)  
Severidad: **ALTO**  
`max_tickers` no valida el tope duro de producto `≤200`. Si `config/strategies.json` define por error `max_universe=500`, `UniverseSpec` puede devolver más de 200 tickers, violando PLAN/SPECS y AGENTS.  
Sugerencia: validar en `__init__` que `1 <= max_tickers <= 200` o truncar siempre con `min(max_tickers, 200)` y fallar si la config intenta superar 200.

2. [trade-scanner/main.py:47](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:47), [trade-scanner/main.py:55](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:55), [trade-scanner/core/pipeline.py:100](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:100)  
Severidad: **ALTO**  
La carga por estrategia se convierte en una unión global de tickers y no queda persistida como universo por estrategia. En el estado actual posterior, `ScanPipeline.scan()` recibe todo `symbol_data_map`, así que una estrategia long puede evaluar símbolos de `swing_declines` y una short símbolos de `swing_advances`. Esto rompe la entidad `UniverseSpec` de SPECS: “lista de símbolos de una estrategia”.  
Sugerencia: conservar `self.universe_by_strategy[name] = set(loaded)` en `main.py` y pasar al pipeline un mapa filtrado por esa estrategia, o hacer que `ScanPipeline` reciba explícitamente su universo.

3. [trade-scanner/core/universe.py:10](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:10)  
Severidad: **MEDIO**  
`COLUMN_ALIASES` solo normaliza una parte del contrato de PLAN §5. Faltan aliases como `Name→name`, `Change→chg_1d`, `5D Chg→chg_5d`, `5D High→high_5d`, `5D Low→low_5d`, `Time→date`. Hoy el filtro usa `avg_vol_5d` y `price`, pero el contrato dice que `UniverseSpec` normaliza el mapa de columnas ratificado.  
Sugerencia: completar `COLUMN_ALIASES` con todo el contrato §5 y parsear numéricos/porcentajes de esas columnas cuando existan.

4. [trade-scanner/core/universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:52)  
Severidad: **MEDIO**  
La validación de columnas requeridas está hardcodeada a `avg_vol_5d` y `price`, no a las columnas realmente usadas por `filter_expr`. Un filtro futuro sobre `pct_chg_5d` exigiría columnas que no usa; un filtro sobre un alias no mapeado fallaría tarde en `df.query()` con poco contexto.  
Sugerencia: validar contra un allowlist de aliases soportados y envolver errores de `df.query()` con `universe_key` y `filter_expr`.

**Tests**
5. [trade-scanner/tests/test_universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:52)  
Severidad: **MEDIO**  
No hay test que demuestre el tope duro absoluto de 200 cuando `max_tickers` viene mal configurado, ni test del alias map completo del contrato PLAN §5. Los tests cubren el caso feliz actual, pero no blindan los invariantes más importantes de Etapa 4.  
Sugerencia: añadir casos `max_tickers=201`/CSV >200, alias completo, y filtro que use un alias distinto a `avg_vol_5d`/`price`.

**Alineación / Documentación**
6. [README.md:103](/Users/guille/Documents/quant/trade-scanner/README.md:103), [README.md:111](/Users/guille/Documents/quant/trade-scanner/README.md:111)  
Severidad: **BAJO**  
README aún describe un CSV `ticker,price,avg_dollar_volume` y dice que el filtro vive en `config.json`. Eso contradice PLAN/SPECS de Etapa 4: CSV Barchart vía ObjectStore y filtro en `config/strategies.json`.  
Sugerencia: actualizar README al contrato real de `UniverseSpec`.

**API LEAN / Reglas Duras**
No encontré órdenes en código ejecutable. `UniverseSpec` no importa `AlgorithmImports`. Los métodos LEAN relevantes de Etapa 4 están en snake_case y confirmados en stubs locales: `QCAlgorithm.object_store`, `ObjectStore.read(path) -> str`, `get_parameter()`, `log()`, `schedule.on`, `date_rules.every_day`, `time_rules.after_market_close/before_market_close`.

**Trazabilidad Etapa 4**

| Criterio | Código | Test / evidencia | Estado |
|---|---|---|---|
| `core/universe.py` existe y exporta `UniverseSpec` | [universe.py:27](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:27), [__init__.py:5](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/__init__.py:5) | import en [test_universe.py:8](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:8) | ✅ |
| Lee CSV desde ObjectStore, footer strip, alias, filtro, orden, tope | [universe.py:43](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:43) | `test_universe.py` 5 tests pasan | ✅ parcial: falta hard cap 200 |
| Con CSV real: advances≈74, declines≈68 | [config/strategies.json:21](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:21) | Validé localmente `storage`: 74 / 68 | ✅ |
| `main.py` loguea universo por 4 estrategias | [main.py:48](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:48), [main.py:57](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:57) | No re-ejecuté `lean backtest` en este sandbox | ⚠️ |
| `env=dev` usa `max_universe` | [config.json:3](/Users/guille/Documents/quant/trade-scanner/trade-scanner/config.json:3), [strategies.json:4](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:4), [main.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:38) | Validé `sample_dev` devuelve 4 | ✅ |
| `UniverseSpec` sin `AlgorithmImports` | [universe.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:1) | `rg AlgorithmImports trade-scanner/core/universe.py` sin import real | ✅ |
| Tests T3.1–T3.5 verdes | [test_universe.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:38) | `5 passed in 0.35s` con pytest host sin captura | ✅ |

**Verificación Ejecutada**

Ejecuté `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -s -p no:cacheprovider trade-scanner/tests/test_universe.py`: `5 passed`.

No ejecuté `bash scripts/run_tests.sh` completo ni `lean backtest` porque este entorno está en sandbox de solo lectura y red restringida; el runner Docker instala paquetes dentro del contenedor.

**Resumen Ejecutivo**

1. Cerrar el agujero del tope duro `≤200`; hoy depende de que la config nunca se equivoque.  
2. No perder el universo por estrategia: ahora se mezcla en una unión global y el pipeline puede escanear símbolos del universo equivocado.  
3. Completar el alias map de PLAN §5 y validar `filter_expr` contra aliases soportados.  
4. Añadir tests para hard cap 200, alias completo y reproducibilidad explícita.  
5. Actualizar README para no documentar un contrato de universo obsoleto.
