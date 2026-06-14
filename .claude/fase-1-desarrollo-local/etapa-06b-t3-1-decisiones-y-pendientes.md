# T3.1 (Etapa 6B) — `SMAPositionRule` (filtro puro sobre snapshot) (2026-06-14)

L4, `core/rules.py`. Clase genérica que reemplazará a `AboveSMA` y será base de `NotExtended`
(D6B.5). **Solo T3.1**: se *añade* la clase + tests; la migración de `AboveSMA` (T3.2), la
limpieza de código muerto (T3.3) y la reescritura/reubicación de tests (T3.4) quedan pendientes.

## Resultado contra el criterio de aceptación

> El bloque (a)–(f) es de **todo T3**. Hoy implemento T3.1: cubro la **funcionalidad** de la
> nueva clase (a–e); la **migración y el cero-código-muerto (f)** son T3.2–T3.4 → pendientes.

| Criterio T3 | Aplica hoy | Estado | Evidencia |
|---|---|---|---|
| (a) Largo: todos los tf ∈ permitidos → `passed=True`; uno fuera → `False` (AND) | T3.1 | ✅ | `test_long_passes_when_all_tfs_in_allowed_buckets`, `test_long_fails_when_one_tf_out_of_range` |
| (b) Corto: mirror produce filtrado `below_*` (extended_below pasa; above_* no) | T3.1 | ✅ | `test_short_mirror_filters_below_buckets`, `test_short_name_renders_below` |
| (c) Evidencia completa para todos los tf, también al fallar (sin short-circuit) | T3.1 | ✅ | `test_smarule_evidence_complete_even_when_first_tf_fails` |
| (d) `buckets_allowed` inválido → `ValueError` en construcción | T3.1 | ✅ | `test_smarule_invalid_buckets_allowed_raises_at_construction` (+ `side` inválido) |
| (e) `evaluate` no maneja fríos; `name` correcto 1/N tf ambos lados | T3.1 | ✅ | `test_evaluate_does_not_handle_cold_missing_series_is_keyerror`, `test_name_variants` |
| (a) Migración de los 8 tests de T3 a `evaluate(snapshot)` | **T3.4** | ⏳ | Los 8 tests de `AboveSMA` siguen intactos y verdes (se migran en T3.4) |
| (f) **Cero código muerto** (sin `evaluate(sd`, sin `position_vs_sma` en rules.py, un solo símbolo de clase) | **T3.2–T3.3** | ⏳ | `AboveSMA` y `SMAPositionRule` coexisten a propósito (ver D-T3.1.1) |
| `bash scripts/run_tests.sh` verde | — | ✅ | **137 passed, 13 warnings in 3.89s** (Docker `quantconnect/lean:latest`) |

**Veredicto: ✅ T3.1 cumplida** (funcionalidad a–e verificada). El "Done when" #3 de la etapa
**no se marca**: requiere T3.2–T3.4 (migración + cero-código-muerto).

## Implementación

`core/rules.py` — `SMAPositionRule` añadida tras `AboveSMA` (que NO se toca):

- Import ampliado: `from core.features import BUCKETS, mirror_buckets, position_vs_sma, snapshot_evidence`
  (se conserva `position_vs_sma` porque `AboveSMA` aún lo usa; se elimina en **T3.3**).
- `__init__`: fail-fast `set(buckets_allowed) − BUCKETS` (sobre buckets **canónicos**, consideración
  técnica #6) → luego `self.buckets_allowed = mirror_buckets(buckets_allowed, side)` (una vez,
  `frozenset`; `mirror_buckets` valida `side`).
- `name` (property): `label=="SMA"` → `AboveSMA(...)`/`BelowSMA(...)` por `side`; otro label →
  `<label>(period,tfs)`.
- `evaluate(snapshot)`: AND sobre todos los tf sin short-circuit; `evidence =
  snapshot_evidence(snapshot, [(tf,period) for tf in tfs])`. No `sd`, no `position_vs_sma`, no try/except.

`tests/test_rules.py` — 11 tests nuevos (sección T3.1) + helper `_snapshot(spec)` (arma
`{tf:{period:PositionResult}}` desde `{(tf,period):(value,distance_pct,bucket)}`). Reusa el
`_assert_evidence` ya presente. Import ampliado con `PositionResult` y `SMAPositionRule`.

## Decisiones tomadas

### D-T3.1.1 — `AboveSMA` y `SMAPositionRule` coexisten temporalmente (NO commitear T3 aún)
T3.1 solo añade la clase nueva; `AboveSMA` (cuerpo viejo `evaluate(sd, thresholds)`, evidencia
inline, import `position_vs_sma`) sigue presente y testeado. Es el estado intermedio esperado al
fraccionar T3 en subtareas. **Consecuencia operativa:** por la regla "cero código muerto / mismo
commit" (consideración técnica #9), **T3 no debe commitearse hasta cerrar T3.2–T3.4**. La decisión
"conservar `AboveSMA` como factory `side="above"` o eliminarlo" es de T3.2 (pregunta abierta del spec).

### D-T3.1.2 — Colisión de nombres de test detectada y corregida
Dos tests nuevos reusaban nombres de tests existentes de `AboveSMA`
(`test_evidence_complete_even_when_first_tf_fails`, `test_invalid_buckets_allowed_raises_at_construction`):
Python rebindea sin error y pytest **dejó de ejecutar los 2 viejos** (la suite pasó de los 137
esperados a 135). Renombrados a `test_smarule_*`. Verificado: `grep` de duplicados vacío, conteo
137 = 126 + 11. **Lección:** al añadir tests en un módulo con clase predecesora, prefijar para
evitar shadowing silencioso (relevante también para T3.4 al migrar).

### D-T3.1.3 — Tests del filtro con `PositionResult` directo (helper `_snapshot`), no stub/builder
`evaluate` solo lee `snapshot[tf][period].bucket`; construir el snapshot a mano con buckets
explícitos aísla el filtro de la medición y hace los casos legibles (qué bucket tiene cada tf).
Un test extra (`KeyError` en serie ausente) fija que `evaluate` asume snapshot caliente y completo.

### D-T3.1.4 — `evaluate` y serie ausente → `KeyError`, no frío
Coherente con D6B.3 y con la decisión de T1.2 (`snapshot ⊇ series`): la rule no envuelve nada;
una serie que falta es error de programación del call site (E7), no un frío que se silencie.

## Pendiente

- **T3.2** — Migrar `AboveSMA` → `SMAPositionRule(label="SMA")`. **Resolver la pregunta abierta**:
  ¿conservar `AboveSMA` como factory delgada `side="above"` o eliminarlo del namespace? (un solo
  símbolo de clase, sin alias residual salvo decisión explícita).
- **T3.3** — Limpieza en `rules.py`: borrar `evaluate(sd, thresholds)` viejo + evidencia inline
  (`rules.py:69-75` original) + import `position_vs_sma`; actualizar docstring del módulo
  ("filtra sobre el snapshot precalculado").
- **T3.4** — Limpieza de tests: reubicar `StubSymbolData` y `test_cold_series_propagates_feature_not_ready`
  a `test_features.py`; reescribir los 8 tests de `AboveSMA` a `evaluate(snapshot)` (o sustituirlos por
  los 11 de T3.1 si los cubren); quitar `THRESHOLDS` si queda sin uso. Cero stubs/tests huérfanos.
- **Verificación de cierre (f):** `grep -n "evaluate(sd\|position_vs_sma" core/rules.py` vacío;
  `grep "class AboveSMA\|class SMAPositionRule"` → un solo símbolo (o `AboveSMA` factory explícita).
- **T4–T7** sin tocar.
- **Commit:** pendiente de tu visto bueno. **No commitear T3 hasta T3.2–T3.4** (cero código muerto).
  Acumulado sin commitear: T2 (features.py/test_features.py) + T3.1 (rules.py/test_rules.py) + docs/conceptos
  + bitácoras T2/T3.1 + ediciones de `etapa-06b.md`.
