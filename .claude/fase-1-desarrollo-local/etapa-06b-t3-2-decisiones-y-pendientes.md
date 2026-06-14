# T3.2–T3.4 (Etapa 6B) — Eliminar `AboveSMA` + limpieza (cierre de T3) (2026-06-14)

L4, `core/rules.py` + `tests/test_rules.py`. El usuario decidió **eliminar `AboveSMA`** (no
conservarlo como factory). Eliminar la clase obliga a cerrar T3.3 (limpieza de `rules.py`) y T3.4
(limpieza de tests) en el mismo cambio para mantener verde la suite y cumplir "cero código muerto /
mismo commit" (consideración técnica #9). Por eso esta unidad cierra **T3 completo**.

## Resultado contra el criterio de aceptación (T3, criterios a–f)

| Criterio T3 | Estado | Evidencia |
|---|---|---|
| (a) Largo AND + migración de los tests a `evaluate(snapshot)` | ✅ | Los 11 tests de `SMAPositionRule` (T3.1) cubren los 8 viejos; éstos se borraron |
| (b) Corto: mirror a `below_*` correcto | ✅ | `test_short_mirror_filters_below_buckets`, `test_short_name_renders_below` |
| (c) Evidencia completa aun al fallar (sin short-circuit) | ✅ | `test_smarule_evidence_complete_even_when_first_tf_fails` |
| (d) `buckets_allowed` inválido → `ValueError` en construcción | ✅ | `test_smarule_invalid_buckets…`, `test_invalid_side…` |
| (e) `evaluate` no maneja fríos; `name` 1/N tf ambos lados | ✅ | `test_evaluate_does_not_handle_cold…`, `test_name_variants` |
| (f) **Cero código muerto** | ✅ | greps abajo |
| `bash scripts/run_tests.sh` verde | ✅ | **129 passed, 13 warnings in 4.48s** (Docker) |

**Veredicto: ✅ T3 cerrado** (a–f). "Done when" #3 marcado `[x]`.

### Verificación de cero código muerto (criterio f)

```
grep -nE "evaluate\(sd|position_vs_sma" core/rules.py        → VACÍO ✅
grep -nE "^class " core/rules.py                             → RuleResult, SMAPositionRule (un solo símbolo de regla) ✅
grep -rn "AboveSMA" --include=*.py (como símbolo)            → solo prosa de comentarios + string-label "AboveSMA(...)" ✅
grep StubSymbolData|THRESHOLDS|FeatureNotReady|SimpleNamespace en test_rules.py → solo prosa de comentario ✅
```

## Cambios

**`core/rules.py`:**
- Clase `AboveSMA` **eliminada** entera (cuerpo `evaluate(sd, thresholds)` + construcción inline de evidencia).
- Import: `from core.features import BUCKETS, mirror_buckets, snapshot_evidence` (fuera `position_vs_sma`).
- Eliminado `from typing import TYPE_CHECKING` + bloque `if TYPE_CHECKING: from core.symbol_data import SymbolData` (ya no se referencia `SymbolData`: `evaluate(snapshot: dict)`).
- Docstring del módulo reescrito: de "evalúa `position_vs_sma` (L3)" a "filtra sobre el snapshot precalculado; solo LEE buckets ya asignados".
- Queda: `RuleResult` (dataclass) + `SMAPositionRule` (de T3.1, sin cambios).

**`tests/test_rules.py`:**
- Borrados los 8 tests de `AboveSMA`, la clase `StubSymbolData`, la constante `THRESHOLDS`.
- Imports podados: fuera `AboveSMA`, `FeatureNotReady`, `from types import SimpleNamespace`. Quedan `BUCKETS`, `PositionResult`, `RuleResult`, `SMAPositionRule`, `pytest`, `ABOVE`, `_assert_evidence`, `_snapshot`.
- Docstring del módulo actualizado (SMAPositionRule, no AboveSMA).

**`tests/test_features.py`:** comentario stale corregido (referenciaba `AboveSMA.evaluate (rules.py:69-75)`, ya inexistente) → ahora apunta a `SMAPositionRule.evaluate` / `snapshot_evidence`.

## Decisiones tomadas

### D-T3.2.1 — `AboveSMA` ELIMINADO (no factory) — recomendación senior aceptada
Tras el rediseño no hay semántica "above-específica": `AboveSMA` ≡ `SMAPositionRule(side="above")`.
Conservar una factory reintroduciría la dualidad que el rediseño quitó, empujaría a crear simétricos
(`BelowSMA`, etc.) y escondería el único parámetro informativo (`side`). E7 es config-driven
(`direction→side` vía `SIDE_BY_DIRECTION`) → `side` no se teclea a mano casi nunca → la factory aporta
poco. Reintroducirla es trivial (3 líneas) si E7 muestra fricción real. El `name` sigue mostrando
`AboveSMA(...)`/`BelowSMA(...)` como **etiqueta de log** (string), independiente del símbolo de clase.

### D-T3.2.2 — `StubSymbolData` ELIMINADO en vez de reubicado (desvío justificado del spec)
T3.4 pedía *reubicar* `StubSymbolData` de `test_rules.py` a `test_features.py` "porque lo necesita el
builder (T1)". Pero el builder ya usa `MultiSeriesStub` (creado en T1.1, D-T1.1.2), que cubre esa
necesidad. Reubicar el stub viejo crearía un duplicado/huérfano — justo lo que el spec quería evitar.
**Sigo la intención (sin stubs huérfanos, builder con cobertura) sobre la letra (reubicar):** lo borro.

### D-T3.2.3 — Los 8 tests de `AboveSMA` se BORRAN (no se reescriben)
Los 11 tests de `SMAPositionRule` (T3.1) ya cubren los 8 viejos bajo el nuevo contrato
`evaluate(snapshot)` (passes/fails AND, evidencia completa, fail-fast, name, required, both sides).
"Migrar los 8" se materializa como "borrarlos: su cobertura ya existe en forma nueva". El test de frío
(`test_cold_series_propagates_feature_not_ready`) se borra: su intención está en
`test_cold_series_halts_and_propagates` (test_features.py, T1.1), donde el frío ahora aflora (el builder).

### D-T3.2.4 — Eliminado el bloque `TYPE_CHECKING`/`SymbolData` de rules.py
Era para anotar `evaluate(sd: "SymbolData")`. Sin esa firma, queda huérfano → fuera (cero código muerto
también en imports de tipos).

## Conteo de la suite

129 passed = 137 (post-T3.1) − 8 tests de `AboveSMA` borrados. Los 11 de `SMAPositionRule` intactos.

## Pendiente

- **T4** (siguiente) — `NotExtended(period, tf, side, required=True)`: factory que retorna
  `SMAPositionRule(period, [tf], buckets_allowed=BUCKETS−{"extended_above"}, side, label="NotExtended")`.
  Sin `max_pct`. `name == NotExtended(8,D)`. Ya hay base (`SMAPositionRule` + `name` con label custom).
- **T5** — Retirar `max_extension_pct` de `config/strategies.json` (4 bloques) + reseed + round-trip.
- **T6** — Formateador de log (`format_filter_line`/`format_final_line`); decidir `rules.py` vs `pipeline.py`.
- **T7** — `ScanResult` (contrato mínimo en `core/pipeline.py`) + alinear nota §5 de PLAN.md.
- **Done when:** marcados #1 (T1), #2 (T2), #3 (T3). #7 (cero código muerto) **parcial**: la parte de
  `rules.py`/tests está limpia, pero #7 también exige `max_extension_pct` retirado (T5) → se marca al cerrar T5.
- **Commit:** ahora T3 SÍ es commiteable como unidad (sin código muerto). Acumulado sin commitear:
  T2 (features) + T3 completo (rules + tests) + `docs/conceptos/` + bitácoras T2/T3.1/T3.2 + ediciones de spec.
  Sugerencia: commitear **T2** y **T3** por separado (dos unidades coherentes), o T2+T3 juntos si prefieres.
