# T1.1 (Etapa 6B) — `build_position_snapshot` (snapshot único) (2026-06-14)

L3, `core/features.py`. Implementa el snapshot único `{tf:{period:PositionResult}}`
(ADR-005 / D6B.1–D6B.3). Es la primera tarea de la Etapa 6B; Estado de la etapa → `en progreso`.

## Resultado contra el criterio de aceptación

> El bloque "Criterio de aceptación" de T1 cubre T1.1 (a/b/c) **y** T1.2 (d).
> Hoy es **solo T1.1** → reporto a/b/c; (d) es de T1.2 (pendiente).

| Criterio T1 | Aplica hoy | Estado | Evidencia |
|---|---|---|---|
| (a) Forma exacta `{tf:{period:PositionResult}}` con `value/distance_pct/bucket` esperados | T1.1 | ✅ | `test_snapshot_shape_and_values` (W:20→above_strong, M:20/D:8→above_mild) |
| (a) `position_vs_sma` invocado **una vez por serie**, args correctos, nunca dos veces | T1.1 | ✅ | `test_each_series_computed_exactly_once` (spy via `monkeypatch`: `calls == [(sd,W,20,th),(sd,M,20,th),(sd,D,8,th)]`) |
| (a-extra) Dos `period` sobre el mismo `tf` anidan bajo una sola clave `tf` | T1.1 | ✅ | `test_multiple_periods_same_tf_nest_under_one_tf_key` (`{"D":{8,20}}`) |
| (b) Serie fría → `FeatureNotReady` que **detiene** la construcción; mensaje con símbolo+serie | T1.1 | ✅ | `test_cold_series_halts_and_propagates` (`match=r"STUB.*W:20"`; `M:20` nunca consultada) |
| (c) Serie declarada-pero-no-referenciada **no se computa** ni excluye el símbolo | T1.1 | ✅ | `test_unreferenced_declared_series_not_computed_nor_excluding` (`M:200` fría fuera de `series` → snapshot OK, `is_ready(M,200)` nunca llamada) |
| (d) `snapshot_evidence` proyecta el esquema exacto (sin `side`) | **T1.2** | ⏳ pendiente | Fuera del alcance de hoy |
| `bash scripts/run_tests.sh` verde | — | ✅ | **108 passed, 13 warnings in 5.63s** (Docker `quantconnect/lean:latest`) |

**Veredicto: ✅ T1.1 cumplida** (a/b/c verificados en Docker). El "Done when" #1 de la etapa
**no se marca aún** porque agrupa también `snapshot_evidence` (T1.2), todavía pendiente.

## Implementación

`core/features.py` — función nueva entre `_bucketize` y `resolve_bucket_thresholds`:

```python
def build_position_snapshot(sd, series, thresholds) -> dict[str, dict[int, PositionResult]]:
    snapshot: dict[str, dict[int, PositionResult]] = {}
    for tf, period in series:
        snapshot.setdefault(tf, {})[period] = position_vs_sma(sd, tf, period, thresholds)
    return snapshot
```

- Import añadido: `from collections.abc import Iterable` (anotación `series: Iterable[tuple[str,int]]`).
- Cero `AlgorithmImports`: L3 sigue importable sin CLR (pureza de capa intacta).
- El frío aflora aquí (un solo punto, D6B.3) porque `position_vs_sma` no se captura.

`tests/test_features.py` — 5 tests nuevos + stub `MultiSeriesStub` (registra llamadas;
`close(tf)` depende solo de `tf` como la API real, `sma`/`is_ready` per-`(tf,period)`).
`build_position_snapshot` añadido al bloque de imports de arriba.

## Decisiones tomadas

### D-T1.1.1 — `setdefault` para el anidado, sin deduplicar (call site = E7)
El builder agrupa con `snapshot.setdefault(tf, {})[period] = ...`: una sola pasada,
una llamada a `position_vs_sma` por elemento de `series`, en el orden recibido. **No
deduplica** (consideración técnica #4 del spec): si `series` trae una serie repetida,
`position_vs_sma` se llamaría dos veces — el dedup es responsabilidad del call site, que
en Etapa 7 pasará la unión como `set`. El test de "una vez por serie" usa `series` sin
repetidos (verifica que no hay recómputo accidental, no el dedup).

### D-T1.1.2 — Stub de test propio `MultiSeriesStub`, no reusar el de E6
El `StubSymbolData` existente en `test_features.py` es single-value (un `sma`/`close`
para todo). Para probar multi-`(tf,period)`, buckets distintos por serie, conteo de
llamadas y series frías selectivas, añadí `MultiSeriesStub`. No toqué el stub de E6 (sus
tests `position_vs_sma`/`_bucketize` siguen verdes). Nota: en **T3.4** la reubicación del
stub multi-tf de `test_rules.py` a `test_features.py` puede converger con éste — al llegar
a T3, revisar si `MultiSeriesStub` y el stub migrado se unifican (evitar dos stubs ~iguales).

### D-T1.1.3 — `position_vs_sma` referenciado como global del módulo (testeable con `monkeypatch`)
`build_position_snapshot` llama `position_vs_sma` por nombre de módulo (no import local),
así `monkeypatch.setattr("core.features.position_vs_sma", spy)` lo intercepta. Eso permite
el test de "una vez por serie / args correctos" con un sentinela, sin recomputar PositionResult.

### D-T1.1.4 — "Done when" #1 NO marcado todavía
El checkbox #1 de "Done when" bundlea `build_position_snapshot` + `snapshot_evidence`.
Como T1.2 está pendiente, dejo el box en `[ ]` (reporte honesto). Marqué el bullet **T1.1**
en la sección Tareas con ✅ + puntero a esta bitácora.

## Pendiente

- **T1.2** (siguiente) — `snapshot_evidence(snapshot, series) -> dict`: proyección pura
  `{tf:{period:{value,distance_pct,bucket}}}` (descarta `side`); criterio (d) con tolerancia
  `1e-9`. Es la **única** fuente de evidencia de aquí en adelante (T3 elimina la construcción
  inline de `AboveSMA.evaluate`). Al cerrarla, ya se puede marcar el "Done when" #1.
- **T2–T7** — mirror/`SMAPositionRule`/`NotExtended`/retiro de `max_extension_pct`/formateador
  de log/`ScanResult`. Sin tocar todavía.
- **Commit** — pendiente de decisión del usuario. Cambios sin commitear:
  `core/features.py` (+función +import), `tests/test_features.py` (+5 tests +stub),
  `etapa-06b.md` (Estado→en progreso, bullet T1.1 ✅) y esta bitácora. Mensaje sugerido:
  `add: [Etapa 6B] T1.1 build_position_snapshot (snapshot único {tf:{period:PositionResult}}) + tests a/b/c`.
