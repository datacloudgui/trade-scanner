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
