# T1.2 (Etapa 6B) — `snapshot_evidence` (proyección de evidencia) (2026-06-14)

L3, `core/features.py`. Proyecta el snapshot único al esquema de evidencia
`{tf:{period:{value,distance_pct,bucket}}}` (D6B.7). Completa T1; cierra el "Done when" #1.

## Resultado contra el criterio de aceptación

| Criterio T1 | Estado | Evidencia |
|---|---|---|
| (d) Reproduce el esquema exacto para un **subconjunto** de series | ✅ | `test_snapshot_evidence_projects_exact_schema_for_subset` (M y D:20 quedan fuera) |
| (d) `distance_pct` con tolerancia `1e-9` | ✅ | `_assert_evidence` usa `pytest.approx(dist, abs=1e-9)` en todos los tests |
| (d) **No incluye `side`** | ✅ | `test_snapshot_evidence_drops_side` (origen `side="below"`, entry sin `side`) |
| (d-extra) Dos `period` mismo `tf` anidan bajo una clave | ✅ | `test_snapshot_evidence_multiple_periods_same_tf` |
| (d-extra) Proyección de un snapshot real = forma inline de E6 | ✅ | `test_snapshot_evidence_reproduces_builder_snapshot_schema` (idéntica a `rules.py:69-75`) |
| `bash scripts/run_tests.sh` verde | ✅ | **112 passed, 13 warnings in 4.76s** (Docker `quantconnect/lean:latest`) |

**Veredicto: ✅ T1.2 cumplida.** Con T1.1, el **"Done when" #1 de la etapa queda marcado `[x]`**.

## Implementación

`core/features.py` — función nueva tras `build_position_snapshot`:

```python
def snapshot_evidence(snapshot, series) -> dict:
    evidence: dict = {}
    for tf, period in series:
        pos = snapshot[tf][period]
        evidence.setdefault(tf, {})[period] = {
            "value": pos.value, "distance_pct": pos.distance_pct, "bucket": pos.bucket,
        }
    return evidence
```

- Misma forma de anidado (`setdefault`) que `build_position_snapshot`, simétrica con la evidencia.
- El dict de salida es **idéntico** al que hoy arma `AboveSMA.evaluate` inline (`rules.py:69-75`):
  3 claves `{value, distance_pct, bucket}`, sin `side`. Eso habilita el swap de T3 (sustituir
  la construcción inline por `snapshot_evidence(snapshot, [(tf,period) for tf in tfs])`).
- Pura lectura: sin `sd`, sin `position_vs_sma`, sin recompute (la firma no recibe `SymbolData`).
- L3 sigue sin CLR.

`tests/test_features.py` — 4 tests nuevos + helper `_assert_evidence` (gemelo del de
`test_rules.py`, validación de esquema con tolerancia `1e-9`) + `_sample_snapshot()` (snapshot
armado a mano con `PositionResult`, aísla la proyección sin stub ni builder).
`snapshot_evidence` añadido al bloque de imports.

## Decisiones tomadas

### D-T1.2.1 — Contrato `series ⊆ snapshot`; `(tf,period)` ausente → `KeyError`
La función no defiende contra una serie pedida que no esté en el snapshot: deja propagar
`KeyError` (lectura `snapshot[tf][period]`). Justificación: el call site siempre proyecta un
subconjunto de lo que construyó (la rule proyecta sus propias series ⊆ la unión de la
estrategia; `sma_evidence` proyecta la unión completa). Defender aquí sería ceremonia inútil
en una proyección pura. Documentado en el docstring.

### D-T1.2.2 — Tests con snapshot armado a mano (`PositionResult` directo), no solo vía builder
Para aislar la **proyección** de la **construcción**, los tests de esquema/`side`/multi-period
usan `_sample_snapshot()` (dict literal de `PositionResult`), sin stub ni `build_position_snapshot`.
Un test adicional sí parte del builder real (`MultiSeriesStub` → `build_position_snapshot` →
`snapshot_evidence`) para fijar que la cadena completa produce la forma inline de E6.

### D-T1.2.3 — `_assert_evidence` duplicado (no compartido aún con `test_rules.py`)
Repliqué el helper `_assert_evidence` en `test_features.py` en vez de importarlo de
`test_rules.py`. Motivo: en **T3.4** los tests de rules se reescriben para usar el snapshot, y
el `StubSymbolData` multi-tf de `test_rules.py` se reubica a `test_features.py`; ese refactor es
el momento natural para unificar helpers/stubs en un `conftest.py` si se decide. Hoy evito
acoplar dos archivos de test que van a moverse. (Misma nota que D-T1.1.2 sobre convergencia de stubs.)

## Pendiente

- **T2** (siguiente) — `mirror_buckets` + `_MIRROR` + `SIDE_BY_DIRECTION` (L3): biyección sobre
  los 7 buckets, `near` autoespejo, involución; criterio (a–e). FABLE xhigh.
- **T3–T7** — `SMAPositionRule` (`evaluate(snapshot)`, migra `AboveSMA`, limpia el inline y el
  import `position_vs_sma` de `rules.py`), `NotExtended` factory, retiro `max_extension_pct`,
  formateador de log, `ScanResult`. Sin tocar todavía.
- **Done when** restantes de la etapa: solo #1 marcado; faltan mirror, `SMAPositionRule`,
  `NotExtended`, config, formateador, `ScanResult`, cero-código-muerto, suite final.
- **Commit pendiente de tu visto bueno.** Sin commitear desde T1.1: `core/features.py`
  (+2 funciones, +import), `tests/test_features.py` (+9 tests, +stub, +helper), `etapa-06b.md`
  (Estado→en progreso, bullets T1.1/T1.2 ✅, Done-when #1 `[x]`) y las 2 bitácoras. Mensaje
  sugerido si se commitea T1 entero:
  `add: [Etapa 6B] T1 build_position_snapshot + snapshot_evidence (snapshot único {tf:{period:...}}) + tests`.
