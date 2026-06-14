# T2.1 (Etapa 6B) — `mirror_buckets` + `_MIRROR` + `SIDE_BY_DIRECTION` (2026-06-14)

L3, `core/features.py`. Espejo above↔below de los 7 buckets para la simetría largo/corto
sin duplicar reglas (ADR-005 / D6B.4, consideración técnica #5). No necesité aclaraciones del
usuario: la tarea estaba cerrada en el spec.

## Resultado contra el criterio de aceptación

| Criterio T2 | Estado | Evidencia |
|---|---|---|
| (a) `mirror_buckets(X,"above") == frozenset(X)` (identidad) | ✅ | `test_mirror_exhaustive_identity_involution_and_closure` (128 subconjuntos) |
| (b) `near` autoespejo en below | ✅ | `test_mirror_near_is_self_symmetric` + `_MIRROR["near"]=="near"` |
| (c) **Involución** para cualquier subconjunto de los 7 | ✅ | exhaustivo `below∘below == id` sobre los 128 subconjuntos |
| (d) `{above_mild,above_strong,extended_above}` → `{below_*}` | ✅ | `test_mirror_above_set_to_below_set` |
| (e) Resultado siempre ⊆ `BUCKETS` | ✅ | cierre verificado en ambos lados sobre los 128 subconjuntos |
| (e) `side` inválido → `ValueError` | ✅ | `test_mirror_invalid_side_raises` (7 casos: `long/short/ABOVE/Below/""/up/None`) |
| (extra) `_MIRROR` biyección total e involutiva | ✅ | `test_mirror_table_is_total_involutive_bijection` |
| (extra) `mirror_buckets` devuelve `frozenset`; vacío → `frozenset()` | ✅ | `test_mirror_returns_frozenset`, `test_mirror_empty_set` |
| (extra) `SIDE_BY_DIRECTION == {"long":"above","short":"below"}` | ✅ | `test_side_by_direction_mapping` |
| `bash scripts/run_tests.sh` verde | ✅ | **126 passed, 13 warnings in 5.07s** (Docker `quantconnect/lean:latest`) |

**Veredicto: ✅ T2.1 cumplida.** "Done when" #2 marcado `[x]`.

## Implementación

`core/features.py` — junto a `BUCKETS` (vocabulario de buckets):

```python
_MIRROR: dict[str, str] = {
    "extended_above": "extended_below", "above_strong": "below_strong",
    "above_mild": "below_mild", "near": "near",
    "below_mild": "above_mild", "below_strong": "above_strong",
    "extended_below": "extended_above",
}
SIDE_BY_DIRECTION: dict[str, str] = {"long": "above", "short": "below"}

def mirror_buckets(buckets, side) -> frozenset[str]:
    if side not in ("above", "below"):
        raise ValueError(f"side inválido: {side!r}; válidos: 'above', 'below'")
    if side == "above":
        return frozenset(buckets)
    return frozenset(_MIRROR[b] for b in buckets)
```

L3 sigue sin CLR.

## Decisiones tomadas

### D-T2.1.1 — `mirror_buckets` valida SOLO `side`, no la pertenencia de `buckets` a `BUCKETS`
La validación `buckets ⊆ BUCKETS` es responsabilidad de la rule en construcción (consideración
técnica #6: "validación antes del mirror"), no del espejo. `mirror_buckets` asume input canónico:
para `side=="below"`, un bucket desconocido daría `KeyError` en `_MIRROR[b]` (guarda natural);
para `side=="above"` pasaría a través. Coherente con "el resultado de un set canónico válido
siempre ⊆ BUCKETS" — no se re-valida en caliente. T3 hará el fail-fast de `buckets_allowed`.

### D-T2.1.2 — Ubicación junto a `BUCKETS`, no junto a las rules
`_MIRROR`/`mirror_buckets`/`SIDE_BY_DIRECTION` viven en `features.py` (L3) pegados a `BUCKETS`:
son vocabulario de buckets/side, negocio puro, y los consume tanto la rule (T3) como, vía
`SIDE_BY_DIRECTION`, el pipeline (E7). Mantenerlos en L3 evita que L4 (`rules.py`) defina
vocabulario base.

### D-T2.1.3 — Test exhaustivo (128 subconjuntos) en un solo test, no parametrizado
Identidad + involución + cierre se prueban recorriendo el powerset completo de los 7 buckets
dentro de un único test (loop), en vez de 128×N entradas parametrizadas: cubre "cualquier
subconjunto" (criterios a/c/e) sin inflar el conteo de la suite. Los casos nombrados (near,
above→below, side inválido) sí van como tests/params separados para localizar fallos.

### D-T2.1.4 — `SIDE_BY_DIRECTION` definido pero aún sin consumidor
El mapa direction→side se añade ahora (D6B.4) pero su uso real (leer `direction` del
`strategies.json` y traducir) es de Etapa 7. Queda como única fuente de esa traducción; el test
fija su contenido y la coherencia con los `side` que acepta `mirror_buckets`.

## Pendiente

- **T3** (siguiente) — `SMAPositionRule` (L4, `core/rules.py`): generaliza `AboveSMA`, firma
  `evaluate(snapshot)`, almacena `mirror_buckets(buckets_allowed, side)` una vez, `name` por
  `side`+`label`, evidencia vía `snapshot_evidence`. **Incluye limpieza dura** (T3.3/T3.4):
  borrar el `evaluate(sd, thresholds)` viejo, la evidencia inline (`rules.py:69-75`) y el import
  `position_vs_sma`; reubicar `StubSymbolData` y el test de frío de `test_rules.py` a
  `test_features.py`; reescribir los 8 tests de T3. Cero código muerto.
- **T4–T7** — `NotExtended` factory, retiro `max_extension_pct` (config), formateador de log,
  `ScanResult`. Sin tocar.
- **Done when**: marcados #1 (T1) y #2 (T2); faltan `SMAPositionRule`, `NotExtended`, config,
  formateador, `ScanResult`, cero-código-muerto, suite final + commit.
- **Commit pendiente de tu visto bueno.** Acumulado sin commitear (T1+T2): `core/features.py`
  (+4 símbolos: `build_position_snapshot`, `snapshot_evidence`, `_MIRROR`/`mirror_buckets`,
  `SIDE_BY_DIRECTION`; +imports), `tests/test_features.py` (+23 tests, +stub, +helpers),
  `etapa-06b.md` (Estado + bullets T1.1/T1.2/T2.1 ✅ + Done-when #1/#2 `[x]`) y 3 bitácoras.
