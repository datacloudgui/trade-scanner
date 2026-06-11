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
