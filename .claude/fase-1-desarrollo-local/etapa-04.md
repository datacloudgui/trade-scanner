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
