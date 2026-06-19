# T2 (Etapa 7) — `day_change_pct`: score del ranking top_n (2026-06-18)

L3, `core/features.py` + `tests/test_features.py`. Feature **puramente aditiva** (sin acoplamiento, a
diferencia de T1.2): el movimiento de hoy con el que el pipeline rankea el `top_n` (gainers para long,
decliners para short). Reusa `reference_price` (T1) y se apoya en A.2 para no tocar L2.

## Resultado contra el criterio de aceptación (T2)

| Criterio | Estado | Evidencia |
|---|---|---|
| (a) con working bar: `(c1 − c0)/c0` | ✅ | `test_day_change_with_working_bar` (0.05, −0.05, 0.0, 0.2) |
| (a) sin working bar: `reference_price = close("D")` ⇒ cambio 0 (degenerado documentado) | ✅ | `test_day_change_without_working_bar_is_zero` |
| (b) `FeatureNotReady` si falta el cierre consolidado | ✅ | `test_day_change_missing_daily_close_raises` (AttributeError → FeatureNotReady, antes de reference_price) |
| (b) `FeatureNotReady` si el cierre consolidado es 0 | ✅ | `test_day_change_zero_daily_close_raises` (evita /0) |
| (c) `core/features.py` sin `AlgorithmImports`/`QCAlgorithm` | ✅ | `grep` → ninguno |
| `run_tests.sh` verde | ✅ | **153 passed, 13 warnings in 6.41s** (Docker) — 146 previos + 7 de T2 |

**Veredicto: ✅ T2 cerrada.** No marca ningún Done-when por sí sola: `day_change_pct` es insumo del
ranking, que se materializa en el pipeline (T4, Done-when #3). L2 quedó intacto (no hay accesor nuevo),
condición del Done-when de cierre.

## Cambios

**`core/features.py`:** nueva función pura `day_change_pct(sd) -> float` (junto a `reference_price`, que
reusa): `try: prev_close = sd.close("D")` → `(reference_price(sd) − prev_close)/prev_close`. Docstring:
dependencia de A.2 (`close("D")`=ayer al scan), dirección del ranking (`desc` long / `asc` short), caso
degenerado sin working bar (cambio 0) y la contingencia D7.6 (no implementada).

**`tests/test_features.py`:** import de `day_change_pct` + sección T2.1 con `DayChangeStub` (`.close("D")`
+ `.working_bar`, `daily_raises` para simular barra consolidada None) y 4 tests (7 casos). `146 → 153`.

## Decisiones tomadas

### D-T2.a — `try/except AttributeError` para "cierre no disponible", no un guard `is_ready`
`position_vs_sma` guarda con `is_ready` **antes** de leer, pero `day_change_pct(sd)` no puede: su firma
es `(sd)` sola — no sabe qué periodo `D` está declarado para consultar `is_ready("D", period)` — y D7.6
prohíbe añadir un accesor a L2 (p. ej. `has_daily_close`). El modo de fallo real de `sd.close("D")` con
barra consolidada None es `None.close` → **AttributeError**; lo capturo y reconvierto a `FeatureNotReady`.
Es el único punto de la feature donde un fallo de lectura L2 se traduce al vocabulario de fríos de L3.

### D-T2.b — Es un backstop, no la ruta normal
El gate B (T4) corre `is_ready(tf, period)` sobre las series referenciadas (incluyen `D:8`/`D:20`) **antes**
de llamar `day_change_pct` en el ranking. Si esas SMAs están listas, el consolidator diario emitió ≥period
barras ⇒ `consolidated` no es None ⇒ `close("D")` existe. Así que el except AttributeError es defensivo
(no debería dispararse en el flujo real); el caso realista que sí puede pasar es `prev_close == 0`.

### D-T2.c — Capturo `AttributeError` específico, no `Exception`
Precisión sobre amplitud: el `try` envuelve **solo** `sd.close("D")` y el único fallo esperado ahí es
AttributeError (None.close vía pythonnet: C# null → Python None). `reference_price` se llama **fuera** del
try, así que un bug suyo no queda enmascarado. Si T6 revelara otro tipo en el borde C#/pythonnet, se
ampliaría; el gate B lo hace improbable.

### D-T2.d — Sin caller en producción todavía (esperado)
`day_change_pct` queda implementado y testeado pero **aún no se invoca**: el ranking que lo usa es T4
(pipeline). Igual que `reference_price` tras T1.1 — deliberado por el alcance incremental, no código muerto.

## Pendiente

- **T3** — composición declarativa en `strategies/` (`StrategyConfig`, `build_rules(side)`, `series(side)`,
  registro `STRATEGIES`). Es la siguiente subtarea natural; no depende de T2 directamente.
- **T4** — `ScanPipeline`: aquí `day_change_pct` se usa de verdad (ranking `top_n`, `desc`/`asc`,
  tie-break ticker) y `build_position_snapshot` (snapshot 1×/símbolo). Gate B antes del ranking.
- **T5/T6** — integración `main.py` (minute subscription) + backtest. **T6 valida la contingencia D7.6**:
  registra si la diaria de hoy se consolida al scan (esperado: no → `close("D")`=ayer → `day_change` OK).
- **Contingencia D7.6 (no implementada):** si T6 muestra emisión-al-cierre, `close("D")` sería hoy →
  `day_change`=0 en `swing_eod`; ahí se añade `previous_close()` (RollingWindow de 2) y se desambigua por
  presencia de working bar. Solo si la verificación lo exige.
- **Commit:** gated por el usuario. Acumulado sin commitear (T1+T2): `core/features.py`, `tests/test_features.py`,
  `etapa-07.md`, bitácoras `etapa-07-t1-…` y `etapa-07-t2-…`.
