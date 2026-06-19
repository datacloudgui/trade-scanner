# T4 (Etapa 7) — `ScanPipeline` + `ScanResult` completo (2026-06-19)

L4, `core/pipeline.py` + `tests/test_pipeline.py`. El embudo end-to-end de una estrategia: gate (B) →
ranking `top_n` → snapshot único + cascada de rules → `ScanResult`. Primer uso real de `reference_price`,
`day_change_pct`, `build_position_snapshot`, `snapshot_evidence` (T1/T2) y de las rules compuestas (T3).

> **T4.1 arrastró T4.2** (igual que T1.2→T1.3/T1.4): el paso 4 de T4.1 construye un `ScanResult` con los
> campos de §5, que el dataclass mínimo de 6B no tenía. Construir ese objeto **exige** extender el
> dataclass. Inseparables → se hicieron juntos. Cierra el Done-when #3 (unit-testeable, sin backtest).

## Resultado contra el criterio de aceptación (T4)

| Criterio T4 | Estado | Evidencia |
|---|---|---|
| (a) `scan` produce `ScanResult` solo para los que pasan TODAS las required; conteo/orden reproducibles | ✅ | `test_only_symbols_passing_all_required_become_results`, `test_results_reproducible_across_runs` |
| (b) gate: serie **referenciada** (W:20) fría excluye+loguea; serie **declarada-no-referenciada** (W:200) fría NO excluye | ✅ | `test_gate_excludes_referenced_cold_keeps_unreferenced_cold` |
| (c) ranking long `desc` / short `asc` por `day_change_pct`, tie-break ticker, corta en `top_n` | ✅ | `test_ranking_long_desc_and_top_n`, `test_ranking_short_asc_and_top_n` |
| (c) embudo reproduce formato 6B/T6; arranca tras gate+ranking | ✅ | `test_funnel_cascade_lines` (4 líneas literales) |
| (c) `build_position_snapshot` 1× por símbolo | ✅ | `test_build_snapshot_called_once_per_symbol` (spy) |
| (d) `ScanResult` con `price` único, `partial_bar`, `sma_evidence` consistente (mismo precio 3 tf), `rules_passed_count` + campos §5 | ✅ | `test_scanresult_fields_and_single_price_evidence` (value·(1+dist)==105 en cada tf) |
| (d) tests mínimos de 6B/T7 siguen verdes | ✅ | `test_scanresult_minimal_contract_defaults` + 2 más, intactos; +`test_scanresult_section5_fields_have_defaults` |
| (d) `partial_bar` de la estrategia se propaga al `ScanResult` (True y False) | ✅ | `test_partial_bar_propagates_to_scanresult` (True) + `test_scanresult_fields...` (False) |
| backstop del paso 3: `build_position_snapshot` `FeatureNotReady` post-gate (SMA==0) excluye+loguea | ✅ | `test_snapshot_backstop_excludes_degenerate_sma` |
| (e) `core/pipeline.py` sin `AlgorithmImports`; `run_tests.sh` verde | ✅ | `grep` → solo docstrings; **178 passed, 13 warnings in 5.77s** (Docker) — 167 + 11 de T4 |

**Veredicto: ✅ T4 cerrada (T4.1 + T4.2).** Done-when #3 marcado `[x]` en `etapa-07.md`.

## Cambios

**`core/pipeline.py`:**
- `ScanResult` extendido (T4.2) con los campos de §5 (`strategy`, `as_of`, `ticker`, `direction`,
  `partial_bar`, `price`, `time_frames_evaluated`, `passed_rules`) — todos con default → `ScanResult()`
  del contrato mínimo de 6B sigue construible.
- `ScanPipeline(strategy_name, direction, side, rules, series, thresholds, top_n, partial_bar)` con
  `scan(symbol_data_map, as_of, log=None) -> list[ScanResult]`: gate B → ranking → snapshot+cascada →
  ScanResult. Importa `build_position_snapshot`/`day_change_pct`/`reference_price`/`snapshot_evidence`
  (core.features) y `TIMEFRAMES` (core.timeframes) — todos CLR-free a nivel de módulo.
- `format_filter_line`/`format_final_line` sin cambios (6B/T6).

**`tests/test_pipeline.py`:** +9 tests T4 con `FakeSymbolData`/`StubRule` + rules reales de swing_eod;
+1 test del contrato §5. `167 → 176`.

## Decisiones tomadas

### D-T4.a — Logging por **callable inyectado** (`log`), no `self.log`
L4 es puro (sin CLR, no habla con `QCAlgorithm`) ⇒ no puede usar `self.log`. `scan` recibe un `log`
opcional (`Callable[[str], None]`, default no-op); main.py (T5) inyectará `self.log`/`self.debug`, los
tests capturan en una lista (`log.append`). Mantiene la pureza y hace el embudo verificable sin engine.

### D-T4.b — Ticker = `sd.symbol.value` (contrato LEAN Symbol, duck-typed)
`main.py` pasa `self.symbol_data` (clave LEAN Symbol). El ticker string sale de `sd.symbol.value` (no
`str(symbol)`, que da el SID). Es duck typing (sin importar Symbol): los stubs exponen `.symbol.value`.
La iteración se ordena por ticker (reproducibilidad, consideración #8).

### D-T4.c — Ranking: sort estable doble (ticker asc, luego day_change con `reverse`)
Tie-break por ticker **alfabético** independiente de la dirección: primero `sort` por ticker asc, luego
`sort` por `day_change` con `reverse=(direction=="long")`. El sort estable de Python preserva el orden
de ticker en los empates de `day_change`. `desc` para long (gainers), `asc` para short (decliners).

### D-T4.d — `day_change_pct` se computa **1× por símbolo** en el ranking, con `try/except` defensivo
Se calcula una sola vez por símbolo gated y se guarda `(change, sd)` para ordenar (no dos veces). Si
levantara `FeatureNotReady` (degenerado post-gate: `close("D")==0`), se excluye+loguea — backstop, no
debería pasar tras el gate. `reference_price` sí se llama de nuevo por superviviente (paso 4): es
idempotente y barato, no recomputa el snapshot.

### D-T4.e — Evaluar TODAS las rules por símbolo (evidencia completa); el embudo es la cascada
Por símbolo se evalúan todas las rules sin short-circuit (`[rule.evaluate(snapshot) for rule in rules]`)
→ evidencia y `passed_rules` completos. El **embudo** (`format_filter_line` por rule) se deriva como
cascada: cada `required` narrowa el conjunto; las `optional` informan sin descartar (en V1 todas son
required). `rules_passed_count` = nº de required que pasaron (= total required para un superviviente).

### D-T4.f — `time_frames_evaluated` en orden canónico de `TIMEFRAMES` (D, W, M), no alfabético
§5 muestra `["D","W","M"]` (cronológico), no alfabético (`D,M,W`). Se ordena por el orden de claves del
registro `TIMEFRAMES` (importable sin CLR). Se computa 1× en `__init__` (es fijo para el pipeline).

### D-T4.g — `side` se guarda pero no se usa en `scan` (las rules ya lo llevan)
El constructor recibe `side` (parte del bundle resuelto, D7.1) y se guarda como `self.side`. El `scan`
no lo usa: las rules llegan ya espejadas (T3) y el ranking usa `direction`. Se conserva como estado
resuelto introspectable (y para logs/main.py), no se re-deriva.

## Pendiente

- **T5** — integración en `main.py` (L5): suscripción `Resolution.MINUTE` (working bar), un
  `ScanPipeline` por estrategia construido en `initialize()` (`side = SIDE_BY_DIRECTION[cfg["direction"]]`
  → **cierra el wiring `direction→side` del Done-when #2**), reemplazar `_scan_stub` por el callback real
  (`pipeline.scan(self.symbol_data, self.utc_time, self.log)`), probe de emisión (A.3).
- **T6** — backtest ≥3 meses: schedule, working bar, timing de emisión, reproducibilidad (no
  unit-testeable; valida los 3 Done-when del PLAN + registra el hallazgo de emisión A.3).
- **Commit:** gated por el usuario. Acumulado sin commitear (T1+T2+T3+T4): `core/features.py`,
  `core/pipeline.py`, `strategies/*.py`, `tests/test_features.py`, `tests/test_strategies.py`,
  `tests/test_pipeline.py`, `etapa-07.md`, `PLAN.md`, `SPECS.md`, bitácoras `etapa-07-t1/t2/t3/t4-…`.
