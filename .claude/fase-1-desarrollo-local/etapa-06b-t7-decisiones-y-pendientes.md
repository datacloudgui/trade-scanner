# T7 (Etapa 6B) — `ScanResult` (contrato mínimo) + reconciliación §5 (2026-06-18)

L4, `core/pipeline.py` (creado en T6) + `tests/test_pipeline.py` + nota de §5 en `PLAN.md`. Portado de
Etapa 6/T6. Cierra la **última** tarea de la Etapa 6B. Solo el **contrato** del dataclass — la lógica
de llenado (pipeline) es Etapa 7 y la serialización CSV/JSON es Etapa 8.

## Resultado contra el criterio de aceptación (T7)

| Criterio T7 | Estado | Evidencia |
|---|---|---|
| Test de construcción confirma los campos nuevos con sus defaults | ✅ | `test_scanresult_minimal_contract_defaults` (`ScanResult()` → `rules_passed_count==0`, `sma_evidence=={}`) |
| `sma_evidence` admite la proyección `{tf:{period:{value,distance_pct,bucket}}}` | ✅ | `test_scanresult_accepts_snapshot_projection_shape` |
| `default_factory` por-instancia (sin bug de default mutable) | ✅ | `test_scanresult_evidence_default_is_per_instance` |
| §5 de PLAN.md ya usa `distance_pct` + `bucket` (reconciliado en E6) | ✅ | Verificado: tabla (línea 141) + ejemplo (líneas 148–150) ya los usan desde E6 |
| Nota del ejemplo de §5 alineada a "proyección del snapshot único (Etapa 6B)" | ✅ | Editada la línea 145 de PLAN.md |
| `run_tests.sh` verde | ✅ | **141 passed, 13 warnings in 4.34s** (Docker) — 138 (T6) + 3 de T7 |

**Veredicto: ✅ T7 cerrado.** "Done when" #ScanResult marcado `[x]`.

## Cambios

**`core/pipeline.py`:**
- `from dataclasses import dataclass, field`.
- `@dataclass class ScanResult` con `rules_passed_count: int = 0` y `sma_evidence: dict =
  field(default_factory=dict)`. Docstring: `sma_evidence` es proyección del snapshot único
  (`snapshot_evidence` sobre la unión), no recompute (D6B.7); documenta que E7 añade el resto de la
  fila de §5.
- Docstring del módulo actualizado: ahora viven aquí `ScanResult` + los formateadores; ya no dice
  "ScanResult llega en T7".

**`tests/test_pipeline.py`:** +3 tests T7; docstring del módulo ampliado (T6 + T7). `138 → 141 passed`.

**`PLAN.md`:** nota del ejemplo de §5 (línea 145) reescrita → "proyección del snapshot único
(Etapa 6B), no un recompute; `distance_pct`/`bucket` se añadieron en Etapa 6 y `distance_pct` es
fracción, no porcentaje". (La tabla de §5 ya estaba reconciliada desde E6 — sin cambios ahí.)

## Decisiones tomadas

### D-T7.1 — `ScanResult` MÍNIMO (solo los 2 campos nuevos), no la fila §5 completa
La spec dice "dataclass **mínimo** ... con **al menos** `rules_passed_count` y `sma_evidence` ...
**sin lógica de llenado** — eso es Etapa 7", y el criterio solo testea "los campos nuevos con sus
defaults". Implemento exactamente esos dos. Los otros 8 campos de §5 (`strategy`, `ticker`, `as_of`,
`direction`, `price`, `partial_bar`, `time_frames_evaluated`, `passed_rules`) los añade **Etapa 7** al
construir el `ScanResult` de verdad: meterlos ahora exigiría decidir tipos (¿`as_of` datetime vs str?,
¿`direction` enum?) que pertenecen al pipeline, y sería scope-creep hacia E7/E8 (explícitamente fuera
de alcance). Extender el dataclass en E7 es aditivo y trivial. **Reversible** si se prefiere el
contrato §5 completo ya.

### D-T7.2 — `ScanResult` no-frozen (coherente con `RuleResult`)
E7 lo construye/llena (posiblemente incremental); un dataclass mutable encaja con ese uso y con el
precedente de `RuleResult` (no-frozen, D6B.5). `PositionResult` sí es frozen porque es un valor
inmutable per-serie; `ScanResult` es un agregado de salida en construcción.

### D-T7.3 — La nota de §5 se alinea; la tabla NO se toca
T7.2 pedía "verificar que §5 ya usa `distance_pct` + `bucket`" (sí, desde E6) y "alinear la **nota del
ejemplo**". Solo edité la prosa de la nota (línea 145); la tabla de campos y el JSON de ejemplo ya
eran correctos. Sin cambios de contrato en §5.

## Verificación de pureza (consideración técnica #1)

```
grep -nE "^(import|from).*(AlgorithmImports|QCAlgorithm)|self\.history"  features.py rules.py pipeline.py → VACÍO ✅
ScanResult() → rules_passed_count=0, sma_evidence={}, dict por-instancia (importlib standalone) ✅
```

## Estado de la Etapa 6B

**Todas las tareas T1–T7 ✅.** "Done when" medibles: **8 de 9 marcados**. El único sin marcar es el
de cierre — *"`features.py`/`rules.py` sin imports de QCAlgorithm/`self.history`; suite verde en
Docker. **Commit `[Etapa 6B] ...`**"* — cuya parte técnica (pureza + 141 passed) está **verificada**,
y solo falta el **commit** (gated por el usuario). El `Estado:` de la spec sigue `en progreso`: pasa a
`completada` al commitear, según el flujo spec-driven.

## Pendiente

- **Cierre de la etapa:** commit `[Etapa 6B]` + `Estado: completada`. Acumulado sin commitear:
  - T4 (`core/rules.py` `NotExtended` + tests), T5 (`config/strategies.json`), T6 (`core/pipeline.py`
    formateadores + tests), **T7** (`ScanResult` + tests), nota §5 de `PLAN.md`.
  - Ediciones de spec `etapa-06b.md` (checkboxes T4–T7 + preguntas abiertas) y bitácoras
    T4/T5/T6/T7.
  - De T3 (sin commitear aún): `docs/conceptos/buckets-y-simetria-largo-corto.md` (mod) y
    `docs/conceptos/factory-vs-composicion.md` (nuevo).
  - Sugerencia: commits por unidad (`[Etapa 6B] T4 ...`, `T5 ...`, `T6 ...`, `T7 ...`) o uno de cierre
    `[Etapa 6B] cerrar capa de reglas (T4–T7)`. `storage/` está gitignoreado.
- **Siguiente etapa: Etapa 7** (pipeline/orquestación real) — construye el snapshot por símbolo,
  ranking `top_n`, exclusión de fríos, `direction→side` desde config, llena `ScanResult` con la fila
  §5 completa y emite el log de embudo con los formateadores de T6.
