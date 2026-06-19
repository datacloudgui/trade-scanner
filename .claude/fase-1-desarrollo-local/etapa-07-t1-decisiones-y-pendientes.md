# T1 (Etapa 7) — Precio único de referencia: `reference_price` + refactor de `position_vs_sma` (2026-06-18)

L3, `core/features.py` + `tests/test_features.py`. Decisión A (precio único): un solo precio "ahora"
(working bar) comparado contra las 3 SMAs, en vez del cierre por-timeframe (W/M rancios) que codificó E6.
**T1 cerrada completa** (T1.1–T1.4), en dos pasos:

- **T1.1** (sesión previa del día) — `reference_price(sd)` helper del "precio ahora".
- **T1.2/T1.3/T1.4** (esta sesión) — `position_vs_sma` recibe el precio inyectado y deja de leer
  `sd.close(tf)`; `build_position_snapshot` computa `reference_price` 1× y lo inyecta; tests E6 migrados.

> **Por qué T1.2 arrastró T1.3+T1.4.** Cambiar la firma de `position_vs_sma` rompe su único caller
> (`build_position_snapshot`) y todos los tests E6 que la invocan. "Run_tests verde" es criterio de T1
> y regla dura del proyecto ⇒ los tres son un refactor atómico inseparable. Hacer solo T1.2 dejaría el
> repo en rojo. Se hicieron juntos; queda cerrado el Done-when #1.

## Resultado contra el criterio de aceptación (T1)

| Criterio T1 | Estado | Evidencia |
|---|---|---|
| (a) `reference_price` → `working_bar.close` con working bar y `close("D")` sin él (stub) | ✅ | `test_reference_price_uses_working_bar_when_present`, `..._falls_back_to_daily_close_without_working_bar`, `..._casts_working_bar_close_to_float` |
| (b) `position_vs_sma` ya **no** referencia `sd.close(tf)`; `distance_pct` usa el `price` inyectado | ✅ | `grep "sd.close" features.py` → solo línea 108 (dentro de `reference_price`, el fallback); `test_position_vs_sma_does_not_read_close` (stub levanta si se llamara `close()`) |
| (b) fríos y `sma==0` siguen levantando `FeatureNotReady` | ✅ | `test_cold_series_raises_feature_not_ready` (corta tras `is_ready`), `test_zero_sma_raises_feature_not_ready` |
| (c) los 3 tf usan **el mismo** precio; evidencia consistente (`value·(1+dist)≈price`, tol 1e-9) | ✅ | `test_snapshot_uses_single_price_consistently`, `test_snapshot_shape_and_values` |
| (c) `position_vs_sma` 1×/serie; `reference_price` 1×/símbolo | ✅ | `test_each_series_computed_once_with_single_price` (spies: `ref_calls==[sd]`, precio 42.0 a las 3 series) |
| (d) `core/features.py` sin `AlgorithmImports` a nivel de módulo | ✅ | `grep` → solo el docstring; cero imports |
| `bash scripts/run_tests.sh` verde | ✅ | **146 passed, 13 warnings in 5.90s** (Docker) — 144 previos + 2 netos de T1.2–T1.4 |

**Veredicto: ✅ T1 cerrada.** Done-when #1 (Precio único A.1) marcado `[x]` en `etapa-07.md`.

## Cambios (esta sesión, T1.2–T1.4)

**`core/features.py`:**
- `position_vs_sma(sd, tf, period, thresholds, price)` — nuevo parámetro `price` (último, posicional);
  `distance_pct = (price − sma)/sma`; **eliminado** `float(sd.close(tf))`. Contrato de fríos
  (`is_ready`, `sma==0` → `FeatureNotReady`) y `_bucketize` intactos. Docstring reescrito: el precio se
  inyecta (A.1), la fuente la decide el caller, no esta función por-tf.
- `build_position_snapshot` — computa `price = reference_price(sd)` **una vez** antes del loop y lo pasa
  a cada `position_vs_sma`. Firma externa intacta (sigue sin recibir precio). Docstring: nota de precio
  único A.1/A.2.

**`tests/test_features.py` (migración T1.4, cero tests muertos):**
- `StubSymbolData`: quitado `close_value`; `close()` ahora **levanta AssertionError** (blinda en runtime
  que `position_vs_sma` no lo toca). Tests de `position_vs_sma`/cortes pasan `price=` inyectado.
- `MultiSeriesStub`: `closes` → `working_bar` (`SimpleNamespace(close=price)`), el precio único que el
  builder inyecta; `close()` levanta (con working bar, el fallback de `reference_price` no se usa).
- Tests reescritos con **un solo precio** contra varias SMAs (antes: cierre por-tf). +2 tests nuevos:
  `test_position_vs_sma_does_not_read_close` (b), `test_snapshot_uses_single_price_consistently` (c).
  `test_each_series_computed_exactly_once` → `..._once_with_single_price` (spies position_vs_sma +
  reference_price). `144 → 146 passed`.

**`.claude/fase-1-desarrollo-local/etapa-07.md`:** Done-when #1 marcado `[x]`.

## Decisiones tomadas (T1.2–T1.4)

### D-T1.2.a — `price` es el último parámetro posicional, sin default
Firma `position_vs_sma(sd, tf, period, thresholds, price)` exacta a la spec. **Sin** default (p. ej.
`price=None` con fallback a `sd.close`): un default reintroduciría la lectura del cierre por-tf que A.1
elimina, y dejaría dos rutas de precio. El precio es obligatorio: lo provee el builder, siempre.

### D-T1.2.b — `close()` de los stubs **levanta**, no solo se omite del registro
Para verificar (b) "grep vacío de `sd.close(tf)`" se refuerza en runtime: si `position_vs_sma` (o el
builder con working bar) llamara `close()`, el test falla con mensaje claro, no en silencio. Más fuerte
que asertar `("close",…) not in calls` y a prueba de refactors futuros.

### D-T1.2.c — `price` no se re-envuelve en `float()` dentro de `position_vs_sma`
`reference_price` (único caller real vía el builder) ya devuelve `float`. El `float()` se aplica donde
nace el decimal C# (working bar, en `reference_price`) y a la SMA (frontera L2→L3), no de nuevo aquí.

### D-T1.3.a — `reference_price` se computa 1× en el builder, fuera del loop de series
`price = reference_price(sd)` antes del `for`: un solo precio "ahora" para las 3 SMAs (invariante de
consistencia de la evidencia). Computarlo por-serie sería redundante y, si el working bar cambiara entre
llamadas (no en V1), rompería la consistencia. Testeado con spy (`ref_calls == [sd]`).

### D-T1.4.a — Migración de datos de test al modelo de precio único
Los stubs multi-tf antes daban un cierre por tf (W:105, M:102, D:101 → 3 distancias). Ahora un solo
`price` (working bar) contra SMAs distintas (p. ej. 105 vs {100, 105, 120} → 0.05 / 0.0 / −0.125),
eligiendo SMAs que son fracciones limpias del precio para que `value·(1+dist)` reconstruya el precio
exacto. Esto **es** la verificación de (c), no solo cosmética.

## Pendiente

- **T2** — `day_change_pct(sd) = (reference_price(sd) − sd.close("D")) / sd.close("D")` para el ranking
  `top_n` (siguiente subtarea natural; ya con `reference_price` disponible).
- **T3** — composición declarativa en `strategies/` (`StrategyConfig`, `build_rules`, `series`).
- **T4** — `ScanPipeline` + `ScanResult` completo: aquí `build_position_snapshot` empieza a usarse de
  verdad (snapshot 1×/símbolo con precio único) y el gate B por series referenciadas.
- **T5/T6** — integración `main.py` (minute subscription) + backtest de validación.
- **Caso degenerado (documentado, no implementado):** sin working bar **ni** cierre consolidado,
  `reference_price` propaga el error de LEAN al leer `close("D")`. El gate B (T4) excluye esos símbolos
  antes; no necesita guard propio.
- **Commit:** gated por el usuario. Acumulado sin commitear de T1 (ambas sesiones): `core/features.py`
  (`reference_price` + refactor `position_vs_sma`/`build_position_snapshot`), `tests/test_features.py`
  (T1.1 + migración T1.4), `etapa-07.md` (Estado `en progreso` + Done-when #1), esta bitácora.
