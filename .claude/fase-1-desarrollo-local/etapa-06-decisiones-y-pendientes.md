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

- **T1.2** — `position_vs_sma(sd, tf, period, thresholds)` + `FeatureNotReady` (contrato de fríos).
- **T1.3** — `_bucketize` (7 buckets, 6 cortes exactos) + test parametrizado de fronteras con dos sets de thresholds.
- **T2** — `bucket_thresholds` en `config/strategies.json` + `resolve_bucket_thresholds` (3 rutas de merge).
- **T3** — `AboveSMA` + `RuleResult` en `core/rules.py`.
- **T4** — `NotExtended` (composición sobre `AboveSMA`).
- **T5** — Formateador del log de filtrado (4 líneas literales).
- **T6** — `ScanResult` (`rules_passed_count`, `sma_evidence`) + reconciliación §5 de PLAN.md.
- **Accesor `SymbolData.close(tf)`** (D3, única modificación permitida a L2) — necesario para T1.2.
- **Preguntas abiertas del spec sin resolver:** ubicación del dataclass `ScanResult` (¿`core/pipeline.py` ya en esta etapa?) y si habrá alguna rule `required=false` en V1 — decidir antes de T6.
