# Etapa 6 — Decisiones y pendientes

Bitácora acumulativa de la etapa (una sección por tarea).

---

## T1.1 — `PositionResult` (2026-06-11)

### Resultado contra el criterio de aceptación

El criterio de aceptación del spec cubre el bloque T1 completo (T1.1+T1.2+T1.3); de él, lo validable con solo T1.1 es el contrato del dataclass:

| Criterio (parte T1.1) | Estado | Evidencia |
|---|---|---|
| Dataclass `frozen=True` en `core/features.py` | ✅ | `core/features.py`; `test_frozen_rejects_mutation` (FrozenInstanceError) verde |
| Campos `value: float`, `distance_pct: float`, `side: str`, `bucket: str` | ✅ | Orden del spec respetado; type hints completos |
| `side` derivado del signo de `distance_pct` (`>= 0 → "above"`) | ✅ | `test_side_derives_from_distance_sign` parametrizado: `0.05/0.0/-0.0 → above`, `-0.05 → below` |
| Comparable por igualdad para asserts directos | ✅ | `test_equality_by_value` + `test_inequality_when_any_field_differs` verdes |
| Sin imports CLR (`AlgorithmImports`) en `core/features.py` | ✅ | Módulo puro (solo `dataclasses`); patrón universe |
| `run_tests.sh` verde | ✅ | 43 passed (35 previos + 8 nuevos) |
| Test parametrizado 7 buckets + 6 cortes exactos | ⏳ | Requiere `position_vs_sma` + `_bucketize` (T1.2/T1.3) |
| Caso SMA fría → `FeatureNotReady` | ⏳ | Requiere T1.2 |

**Veredicto: ✅ T1.1 cumplido** (la parte ⏳ del criterio pertenece a T1.2/T1.3, fuera del alcance de hoy).

### Decisiones tomadas

#### D-T1.1.1 — `side` se deriva en `__post_init__`, no es argumento del constructor

El spec define la regla del signo dentro de T1.1 (no de T1.2), así que la invariante vive en el dataclass: `side: str = field(init=False)` + `object.__setattr__` en `__post_init__`. Consecuencias:

- `position_vs_sma` (T1.2) NO calcula `side`: construye `PositionResult(value, distance_pct, bucket)` y el lado sale solo.
- Es imposible construir un resultado inconsistente (`side="above"` con distancia negativa); pasar `side` lanza `TypeError` (testeado).
- La igualdad por valor no se ve afectada (`side` participa en `__eq__` pero es función de `distance_pct`).
- Verificado que un campo sin default (`bucket`) puede seguir a un `field(init=False)`: el orden de campos del spec se mantiene tal cual.

#### D-T1.1.2 — `-0.0` clasifica como `"above"`

`-0.0 >= 0` es `True` en IEEE 754/Python → mismo lado que `0.0`. Caso de frontera cubierto en el test parametrizado para que nadie lo "arregle" por accidente.

### Pendiente (resto de la etapa)

- **T1.2** — `position_vs_sma(sd, tf, period, thresholds)` + `FeatureNotReady` (contrato de fríos). → ✅ hecho (ver sección T1.2)
- **T1.3** — `_bucketize` (7 buckets, 6 cortes exactos) + test parametrizado de fronteras con dos sets de thresholds. → ✅ hecho (ver sección T1.3)
- **T2** — `bucket_thresholds` en `config/strategies.json` + `resolve_bucket_thresholds` (3 rutas de merge).
- **T3** — `AboveSMA` + `RuleResult` en `core/rules.py`.
- **T4** — `NotExtended` (composición sobre `AboveSMA`).
- **T5** — Formateador del log de filtrado (4 líneas literales).
- **T6** — `ScanResult` (`rules_passed_count`, `sma_evidence`) + reconciliación §5 de PLAN.md.
- **Accesor `SymbolData.close(tf)`** (D3, única modificación permitida a L2) — necesario para T1.2. → ✅ hecho (ver sección T1.2)
- **Preguntas abiertas del spec sin resolver:** ubicación del dataclass `ScanResult` (¿`core/pipeline.py` ya en esta etapa?) y si habrá alguna rule `required=false` en V1 — decidir antes de T6.

---

## T1.2 — `position_vs_sma` + `FeatureNotReady` + accesor `close(tf)` (2026-06-12)

> Sesión interrumpida a mitad de tarea: la implementación (`features.py` + `symbol_data.py`) quedó aplicada sin commitear; al retomar se validó el working tree con `git diff`, se añadieron los tests, suite y bitácora. Sin pérdida de trabajo.

### Resultado contra el criterio de aceptación

Del criterio del bloque T1, lo que corresponde a T1.2:

| Criterio (parte T1.2) | Estado | Evidencia |
|---|---|---|
| `position_vs_sma(sd, tf, period, thresholds) -> PositionResult` | ✅ | `core/features.py`; firma y orden de args del spec (D3: `tf, period`) |
| Lee `sd.sma(tf, period).current.value` y `sd.close(tf)` — solo API de SymbolData | ✅ | `test_delegates_bucket_and_reads_declared_series`: el stub registra exactamente `[is_ready, sma, close]` con los args pedidos |
| Accesor `close(tf)` añadido en L2 (única modificación permitida, pura lectura) | ✅ | `SymbolData.close()`; `test_etapa6_close_reads_last_consolidated_close_per_timeframe` con cadena real D→W (W=20.0, D=99.0, KeyError en tf no construido) |
| Calcula `distance_pct = (close - sma) / sma` | ✅ | `test_distance_pct_formula` parametrizado (+0.05 / −0.05 / 0.0), tolerancia `1e-9` |
| Delega el bucket en `_bucketize` | ✅ | monkeypatch registra `(distance_pct, thresholds)` y su retorno aterriza en `result.bucket` sin recálculo |
| `FeatureNotReady` tipada en `core/features.py` | ✅ | Hereda de `Exception`; mensaje incluye símbolo y serie (`SPY: SMA W:20 fría`) para el log de exclusión de Etapa 7 |
| Fríos: `not is_ready` → raise | ✅ | `test_cold_series_raises_feature_not_ready` (y verifica que NO lee `close` tras el corte) |
| Fríos: `sma == 0` → raise | ✅ | `test_zero_sma_raises_feature_not_ready` |
| Sin imports CLR en `core/features.py` | ✅ | `SymbolData` solo bajo `TYPE_CHECKING`; tests corren sin CLR path |
| `run_tests.sh` verde | ✅ | 50 passed (43 previos + 7 nuevos) |
| Test parametrizado 7 buckets + 6 cortes exactos | ⏳ | Es T1.3: `_bucketize` real + fronteras con dos sets de thresholds |

**Veredicto: ✅ T1.2 cumplido** (la parte ⏳ pertenece a T1.3).

### Decisiones tomadas

#### D-T1.2.1 — `_bucketize` queda como placeholder `NotImplementedError` hasta T1.3

T1.2 "delega el bucket en `_bucketize`" pero la tabla de buckets es T1.3. Para no mezclar alcance (granularidad una-tarea-por-sesión), `_bucketize` existe con firma y docstring pero lanza `NotImplementedError`; los tests del camino caliente de T1.2 lo stubean con `monkeypatch` y verifican la **delegación** (args y retorno), no la clasificación. El propio criterio del spec avala el "stub mínimo". T1.3 lo sustituye por la tabla real + tests de frontera.

#### D-T1.2.2 — Normalización a `float` en la frontera L2→L3

`.current.value` y `.consolidated.close` son `decimal` de C# vía pythonnet. `close(tf)` castea `float()` (honra su hint `-> float`) y `position_vs_sma` castea la SMA antes de operar. Evita aritmética mixta decimal-C#/float y hace estables los asserts de igualdad. Es el mismo patrón que ya usaban los tests de 5A (`float(...)` en cada lectura).

#### D-T1.2.3 — `close(tf)` sin guard de `consolidated is None`

El accesor es mínimo, como dicta D3. El contrato de fríos vive en L3: `position_vs_sma` exige `is_ready` **antes** de leer (si una serie está ready, su consolidator ya emitió ≥ period barras → `consolidated` nunca es None por esa vía). Documentado en el docstring del accesor.

#### D-T1.2.4 — Orden de verificación: `is_ready` → leer SMA → `sma == 0` → leer close

El corte por frío ocurre antes de tocar cualquier estado caliente (testeado: con `ready=False` no se llama `close`). El caso `sma == 0` es defensa contra división degenerada, no un estado esperable de una SMA ready con precios reales.

### Pendiente tras T1.2

Sin pendientes propios de la tarea. Siguiente: **T1.3** (`_bucketize` real — al implementarla, el placeholder y su `NotImplementedError` desaparecen; los tests de delegación de T1.2 quedan como están porque stubean por monkeypatch).

---

## T1.3 — `_bucketize`: tabla de 7 buckets (2026-06-12)

### Resultado contra el criterio de aceptación

Cierra el criterio del bloque T1 completo (T1.1+T1.2+T1.3):

| Criterio T1 | Estado | Evidencia |
|---|---|---|
| `_bucketize(distance_pct, thresholds) -> str` con la tabla de 7 buckets | ✅ | Cascada de arriba hacia abajo en `core/features.py`; exhaustiva y sin solapes por construcción |
| Cortes `near < mild < extended` leídos de `thresholds`; sin números mágicos | ✅ | Los 3 cortes se leen una sola vez al inicio; el cuerpo solo usa esas variables |
| Lado `below` espeja a `above` | ✅ | `test_bucketize_mirror_symmetry`: `bucketize(-d) == espejo(bucketize(d))` para interiores Y cortes |
| Test parametrizado: 7 buckets cubiertos | ✅ | `test_seven_buckets_and_six_exact_cuts` (7 interiores, vía `position_vs_sma` + stub SMA=100) |
| 6 cortes exactos con inclusión/exclusión de la tabla (`>=` piso above, `<=` techo below) | ✅ | Mismo test (6 casos de corte exacto) + `test_bucketize_boundary_ownership_with_epsilon` (12 casos: cada corte y su vecino a `±1e-12` hacia el centro) |
| `distance_pct` con tolerancia `1e-9` | ✅ | Assert con `pytest.approx(abs=1e-9)` en los 13 casos |
| Segundo set de thresholds mueve los cortes (no-hardcodeo) | ✅ | `test_second_threshold_set_moves_the_cuts`: `{near:0.01, mild:0.05, extended:0.08}` — 6 casos donde default y custom clasifican distinto, incl. cortes exactos del set custom (±0.08) |
| Caso con SMA fría levanta `FeatureNotReady` | ✅ | Cubierto en T1.2 (`test_cold_series_raises_feature_not_ready`) |
| `run_tests.sh` verde | ✅ | 82 passed (50 previos + 32 nuevos) |

**Veredicto: ✅ T1.3 cumplido → bloque T1 completo.** Primer "Done when" de la etapa marcado `[x]` en etapa-06.md y PLAN.md.

### Decisiones tomadas

#### D-T1.3.1 — Cascada de extremos hacia el centro, fiel a la invariante de frontera

La tabla se implementa como cascada `extended_above → … → extended_below`. La invariante (un corte exacto pertenece al bucket más alejado de la SMA) queda expresada con `>=` en el lado above y `>` sobre el corte negado en el lado below (equivalente al `<=` de la tabla), documentada en el docstring. No se usa `abs()` ni duplicación de cortes: cada corte aparece una vez por lado.

#### D-T1.3.2 — Constante `BUCKETS` a nivel de módulo (set cerrado de 7)

Se define ya en `core/features.py` porque: (a) los tests de propiedad la usan para verificar que `_bucketize` solo emite buckets conocidos, y (b) T3.1 la necesita para el fail-fast de `buckets_allowed` en el constructor de `AboveSMA` — definir el set canónico junto a quien lo produce evita dos fuentes de verdad.

#### D-T1.3.3 — Doble batería de frontera: división real + epsilon directo

Los cortes exactos se testean por dos vías complementarias: (a) vía `position_vs_sma` con SMA=100 y cierres que producen el corte exacto tras la división (`(103-100)/100 == 0.03` en doble precisión); (b) directo sobre `_bucketize` con `corte ± 1e-12` — valores que la división real difícilmente produce pero que pinean el ownership de cada frontera contra off-by-epsilon (`<` vs `<=`) en refactors. La propiedad espejo cubre además la simetría completa en un solo test.

### Pendiente tras T1.3

Sin pendientes propios de la tarea. **Propuesta para T2.2** (decidir al empezar T2): `resolve_bucket_thresholds` debería validar `0 < near < mild < extended` al resolver la config — hoy nadie lo verifica y unos thresholds desordenados invertirían los intervalos en silencio. Validar una vez en la resolución (entrada de config) y no en `_bucketize` (hot path por símbolo×tf).
