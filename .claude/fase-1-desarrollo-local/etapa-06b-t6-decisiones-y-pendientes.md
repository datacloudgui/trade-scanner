# T6 (Etapa 6B) — Formateador del log de filtrado (2026-06-18)

L4, **nuevo** `core/pipeline.py` + `tests/test_pipeline.py`. Portado de Etapa 6/T5 sin cambios de
diseño. Dos funciones **puras** que dan formato a contadores del embudo de filtrado en cascada —
**no ejecutan filtrado** (eso es Etapa 7); solo formatean números ya calculados.

## Resultado contra el criterio de aceptación (T6)

| Criterio T6 | Estado | Evidencia |
|---|---|---|
| Test reproduce **literalmente** las 4 líneas del ejemplo desde contadores | ✅ | `test_filter_log_reproduces_example_lines_literally` (igualdad exacta de las 4 strings) |
| `dropped = n_in − n_out`; `kind` se renderiza (required/optional) | ✅ | `test_filter_line_computes_dropped_and_renders_optional` (incl. dropped=0, optional) |
| Símbolos exactos (flecha U+2192, signo menos U+2212, no ASCII) | ✅ | `test_filter_line_uses_exact_unicode_symbols` (`→`/`−` presentes; `->`/`-7` ausentes) |
| `run_tests.sh` verde | ✅ | **138 passed, 13 warnings in 4.48s** (Docker) — 135 (T4/T5) + 3 de T6 |

**Veredicto: ✅ T6 cerrado.** "Done when" #6 marcado `[x]`.

## Cambios

**`core/pipeline.py` (NUEVO):**
- `format_filter_line(strategy, rule_name, n_in, n_out, kind) -> str` →
  `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)`, `dropped = n_in - n_out`.
- `format_final_line(strategy, n) -> str` → `[<strategy>] final: <n> candidatos`.
- Negocio puro, sin AlgorithmImports (patrón features/rules). Docstring del módulo documenta que la
  cascada real y `ScanResult` llegan en E7/T7.

**`tests/test_pipeline.py` (NUEVO):** 3 tests (líneas literales + dropped/optional + símbolos exactos).

**`.claude/fase-1-desarrollo-local/etapa-06b.md`:** T6.1 marcada `✅`; "Done when" #6 `[x]`;
pregunta abierta de ubicación marcada `[x]` (resuelta a `pipeline.py`).

## Decisiones tomadas

### D-T6.1 — Ubicación: `core/pipeline.py`, no `core/rules.py` (resuelve la pregunta abierta)
El log de embudo describe **contadores del filtrado en cascada** — un concepto del orquestador
(Etapa 7), no el veredicto pasa/no-pasa de una rule individual. Ponerlo en `rules.py` mezclaría
observabilidad del pipeline con la lógica de filtro pura de L4. `pipeline.py` es donde vivirá su
**único caller** (la cascada de E7) y el `ScanResult` (T7), así que es su hogar natural. Coincide
con la preferencia que ya anotaba la spec. Se **crea** `pipeline.py` en esta tarea (vacío salvo los
formateadores); T7 le añadirá el dataclass `ScanResult`.

### D-T6.2 — Símbolos Unicode exactos congelados con test (flecha U+2192, menos U+2212)
El ejemplo de la spec usa `→` (U+2192) y `−` (U+2212), **no** `->` ni el guion ASCII `-`. Verifiqué
los codepoints en la spec antes de implementar y los blindé con un test dedicado
(`…uses_exact_unicode_symbols`): un refactor que "normalice" a ASCII rompería el contrato literal.

### D-T6.3 — Formateador sin validación de `kind` (se mantiene formateador puro)
`kind` se interpola tal cual (`required`/`optional`). No se valida fail-fast: el criterio pide solo
reproducir las líneas, el caller es E7 (controla el valor), y validar añadiría una rama sin cobertura
real en 6B. Es coherente con "**No** ejecuta filtrado; solo formatea contadores".

## Pendiente (Etapa 6B)

- **T7** (única tarea restante) — `ScanResult` (dataclass mínimo en `core/pipeline.py`:
  `rules_passed_count: int = 0`, `sma_evidence: dict = field(default_factory=dict)`, documentado como
  **proyección del snapshot**, no recompute) + alinear la nota de §5 de PLAN.md a "proyección del
  snapshot único (Etapa 6B)". Se añade al `pipeline.py` ya creado aquí.
- **Done when:** marcados #1 (T1), #2 (T2), #3 (T3), #4 (T4), #5 (T5), **#6 (T6)**, #7 (cero código
  muerto). Falta solo el contrato de `ScanResult` (T7) para cerrar la etapa.
- **Commit:** acumulado sin commitear: T4 (rules+tests) + T5 (config) + T6 (pipeline+tests) +
  ediciones de spec + bitácoras T4/T5/T6 + (de T3) los dos docs de conceptos. T6 es commiteable como
  unidad (`[Etapa 6B] T6 formateador del log de filtrado en pipeline.py`).
