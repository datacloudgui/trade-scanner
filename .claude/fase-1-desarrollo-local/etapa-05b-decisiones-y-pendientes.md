# Etapa 5B — Decisiones y pendientes

## T1.1 — `universes/sample_dev.csv` (2026-06-11)

**Estado:** ✅ completada (criterio de T1.1 verificado por ejecución).

### Decisiones tomadas

- **Ubicación: `universes/` en la raíz del workspace (directorio versionado nuevo).**
  El plan dicta el path `universes/sample_dev.csv`. Se eligió un dir versionado propio
  para distinguir este fixture estático de:
  - `data/object-store/*.csv` → movers Barchart efímeros (gitignoreados, fuente de los swing).
  - `storage/universes/*.csv` → copia runtime regenerable (gitignoreada).
  `sample_dev.csv` es un fixture de harness de validación → debe versionarse.
- **Formato:** header Barchart §5 idéntico al de `swing_advances.csv` (columnas con comillas).
  Se incluyó la línea footer `"Downloaded from Barchart.com…"` a propósito, para ejercitar
  el footer strip de `UniverseSpec` (`_TICKER_RE`).
- **Valores SPY (2026-06-05):** `Latest=595.27`, `5D Avg Vol=72184500`.
  Pasan el filtro dev `avg_vol_5d > 1e6 and price > 5` con holgura.
- **Solo SPY:** AAPL/IBM se añaden en T5.2 (Fase 2), fuera del alcance de hoy.

### Verificación

`UniverseSpec("universes/sample_dev.csv", "avg_vol_5d > 1e6 and price > 5").load(store)`
→ `["SPY"]`. Footer descartado, alias map aplicado, filtro OK.
(Ejecutado en host venv; `core/universe.py` no importa `AlgorithmImports`.)

## T1.2 — overrides `environments.dev` en `strategies.json` (2026-06-11)

**Estado:** ✅ completada.

- Añadidos a `environments.dev`: `universe: "sample_dev"`,
  `timeframes: {D:[8,20,200], W:[8,20,200], M:[8,20,200]}` (incluye M:200, que prod NO usa),
  `warmup_budget: {"daily": 4300}`.
- `top_n:2` / `max_universe:2` conservados (cambio 5→2 / 10→2 intencional, per T1.2).
- Prod sin tocar (su SMA 200 / budget bajo es T7.1).
- JSON validado (`json.load` OK).

## T1.3 — wiring del seed para fixtures estáticos (2026-06-11)

**Estado:** ✅ completada.

### Decisión

- En `seed_object_store.sh` agregué una **rama §4 genérica**: copia *todos* los `universes/*.csv`
  (no solo `sample_dev`) a `storage/universes/` con `cp` directo, idempotente, **sin** la lógica
  de `processed/` de los movers. Razón: son fixtures versionados estáticos, no movers Barchart
  efímeros con fecha en el nombre. Generalizar a glob evita tocar el script al añadir más fixtures.
- `shopt -s nullglob` para que el `for` no falle si `universes/` está vacío.

### Verificación (criterio AGREGADO de T1 — ahora cumplido)

- `bash scripts/seed_object_store.sh` → loguea `sample_dev.csv → universes/sample_dev.csv
  (fixture estático)` y deja `storage/universes/sample_dev.csv` (244 B).
- `UniverseSpec("universes/sample_dev.csv", "<filtro dev>", max_tickers=2)` leído **desde storage**
  → `["SPY"]`.

### Pendiente (siguientes tareas de Fase 1, fuera de hoy)

- **T2** — integración del warmup en `main.py`: leer estos overrides dev (`universe`, `timeframes`,
  `warmup_budget`), construir `SymbolData` por símbolo, `set_warm_up`-primero con rollback manual.
  Hoy nada en `main.py` lee aún estos campos → sin impacto en runtime todavía.
- No corrí `run_tests.sh` (Docker): T1.2/T1.3 no cambian código en `core/`; la validación de T1 es
  seed + parse, ejecutada en host. Los tests de `test_universe.py` no se ven afectados.

## T2.1 — suscripción DAILY + SymbolData + wiring consolidator en `main.py` (2026-06-11)

**Estado:** ✅ completada (criterio verificado por ejecución: backtest + tests).

### Decisiones tomadas

- **Pregunta abierta nº4 del spec RESUELTA — mecanismo del override `timeframes`:** se adoptó
  la propuesta escrita: si `environment.timeframes` existe, **reemplaza** la unión de estrategias
  para construir `requirements` (`_build_requirements` en `main.py`); sin override (prod) se usa
  la **unión global** de los `timeframes` de todas las estrategias.
- **Unión global, no por símbolo (simplificación deliberada):** `requirements` es compartido por
  todos los símbolos en vez de "unión de las estrategias que usan ese símbolo" (CLAUDE.md). Hoy es
  equivalente: las 4 estrategias prod declaran timeframes idénticos, y dev fuerza un solo universo.
  Además habilita `plan_warmup` global una sola vez (R4, requirements idénticos entre símbolos).
  Si en el futuro las estrategias divergen en timeframes, refinar a unión por símbolo.
- **Ancla de calendario SPY pasa de MINUTE a DAILY (D5):** la minute data local solo cubre
  2013-10 y la ventana 5B exige `start ≥ 2016`. El ancla **reusa la suscripción del universo** si
  SPY está suscrito (dev); fallback a `add_equity("SPY", DAILY)` propio (prod sin SPY). El reloj
  avanza con barras diarias y los `ScheduledEvents` disparan por exchange hours (consideración #4
  del spec, **confirmada empíricamente**: scans a las 15:30 y 16:01 cada día hábil de la ventana).
- **Ventana:** `2016-01-04 → 2016-01-15` (10 días hábiles, cruza el cierre semanal del vie 08).
  SPY-zip arranca 1998-01-02 → ~4530 barras diarias previas al start ≥ 4221 (M:200 viable, T2.2).
- **`add_equity(..., Resolution.DAILY, DataNormalizationMode.SPLIT_ADJUSTED)`** per D5/T2.1.
  Ojo (consideración #5): el SPY-zip trae factors REALES → este símbolo sí ejercita el wiring del
  modo; la data convertida en F3 (factors neutros) será insensible al modo.
- **Evidencia 1:1 con contadores de instrumentación:** `on_data` cuenta barras diarias entregadas
  por la suscripción; un handler extra sobre `data_consolidated` cuenta emisiones del consolidator;
  `on_end_of_algorithm` cruza: `recibidas == consolidadas + working` (emisión perezosa, hallazgo #1
  de 5A, ahora confirmado también en runtime con feed del engine).
- **SymbolData construye las 9 series del override** (`D/W/M × 8/20/200`). El filtrado de series
  `excluded` por presupuesto llega con `plan_warmup` en T2.2 (con budget dev 4300 hoy no se
  excluiría nada de todos modos).

### Verificación (criterio de T2.1)

- `lean backtest "trade-scanner"` (env=dev) corre sin errores. Log:
  - `[swing_eod] universe loaded: 1 tickers (env=dev, max=2, key=universes/sample_dev.csv)` ×4
    estrategias → override `universe` operativo.
  - `[SPY] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)` →
    override `timeframes` operativo (9 series, incluye M:200).
  - **`[SPY] feed daily→consolidator 1:1 OK: 10 recibidas, 9 consolidadas, working hasta
    2016-01-16 00:00:00`** → la suscripción daily alimenta el consolidator diario 1:1 (la décima
    barra retenida como working bar = emisión perezosa esperada).
- Único data request fallido: `/alternative/interest-rate/usa/interest-rate.csv` — interno del
  engine (risk-free rate para estadísticas), no relacionado con nuestra suscripción. Benigno.
- `bash scripts/run_tests.sh` → **31 passed** (sin cambios en `core/`; main.py no se unit-testea,
  es boundary del engine — su verificación es el backtest).

### Pendiente (T2.2–T2.3, fuera de hoy)

- **T2.2** — warmup: `set_warm_up` primero (los consolidators YA quedan añadidos antes de
  cualquier warmup, requisito cumplido por construcción en `initialize`), gate de cross-check
  contra fixture T4, rollback manual (`history[TradeBar]` + `scan()` de cierre) si diverge;
  guard `if self.is_warming_up: return` en `on_data`/scans; series `plan.excluded` → warning
  y no construirlas (hoy SymbolData construye todo el override).
- **T2.3** — logs de evidencia: profundidad con driver (W:200→1010, M:200→4221), duración del
  warmup, conteo ready/no-ready, decisión de estrategia de warmup.
- Los **contadores 1:1 son instrumentación de T2.1**: decidir en T2.3 si se conservan como
  evidencia permanente del wiring o se retiran al cerrar F1.
- Las SMAs siguen **frías** (sin warmup todavía): `is_ready` no se validó hoy — es exactamente
  lo que T2.2 resuelve.
