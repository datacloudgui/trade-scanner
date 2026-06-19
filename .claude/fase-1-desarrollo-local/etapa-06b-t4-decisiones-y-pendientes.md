# T4 (Etapa 6B) — `NotExtended` rediseñada (preset sin `max_pct`) (2026-06-18)

L4, `core/rules.py` + `tests/test_rules.py`. **Supersede D4** de `etapa-06.md`: `NotExtended` deja
de tener umbral propio (`max_pct`) y pasa a ser un **constructor con nombre (preset)** de
`SMAPositionRule` que excluye el bucket favorable-extremo. El corte que define "extremo" lo fija el
`bucket_thresholds.extended` **único** de la estrategia (ya aplicado al bucketizar el snapshot),
no la rule.

> **Redacción (sugerencia del usuario aplicada):** en código y bitácora se evita la palabra
> *"factory"* — se usa **"constructor con nombre / preset"**. Así la coherencia con D-T3.2.1
> (eliminar `AboveSMA`) es obvia *a primera vista*: `AboveSMA` se eliminó por ser un **alias vacío**
> (solo precargaba `side="above"`); `NotExtended` se conserva porque **encapsula un concepto**
> (qué buckets son "extendido"). Mismo patrón ("favorece composición"), distinto veredicto, y el
> vocabulario ya no sugiere que sean el mismo caso.

## Resultado contra el criterio de aceptación (T4, criterios a–d)

| Criterio T4 | Estado | Evidencia (test en `test_rules.py`) |
|---|---|---|
| (a) Largo: falla en `extended_above`; pasa en `above_strong` bajo el corte | ✅ | `test_notextended_long_fails_extended_passes_strong` + `…_allows_all_but_extended_above` |
| (b) Corto (`side="below"`): el mirror excluye `extended_below`; falla ahí, pasa en `below_strong` | ✅ | `test_notextended_short_mirrors_to_exclude_extended_below` |
| (c) Un segundo `bucket_thresholds.extended` **mueve el corte** (reemplaza el viejo test de `max_pct`) | ✅ | `test_notextended_cut_driven_by_strategy_extended_threshold` |
| (d) `evidence` con la misma forma `{tf:{period:{value,distance_pct,bucket}}}` | ✅ | `test_notextended_evidence_shape` |
| `bash scripts/run_tests.sh` verde | ✅ | **135 passed, 13 warnings in 4.03s** (Docker) |

**Veredicto: ✅ T4 cerrado** (a–d). "Done when" #4 marcado `[x]`.

## Cambios

**`core/rules.py`:**
- Añadida `NotExtended(period, tf, side, required=True) -> SMAPositionRule`: retorna
  `SMAPositionRule(period, [tf], buckets_allowed=set(BUCKETS) - {"extended_above"}, side, required,
  label="NotExtended")`. **Sin `max_pct`.** Docstring explica que es composición (no subclase ni
  alias) y que el corte lo fija el `extended` del snapshot, no la rule.
- No es una clase: `grep "^class " core/rules.py` sigue devolviendo solo `RuleResult` y
  `SMAPositionRule` (un único símbolo de clase de regla, coherente con T3.2).

**`tests/test_rules.py`:**
- +6 tests T4 (a–d + flag `required`): `129 → 135 passed`.
- Helper local `_snapshot_at(tf, period, value, distance_pct, thresholds)`: arma un snapshot de 1
  serie bucketizado por el `_bucketize` **real** al `thresholds` dado (constantes locales
  `THRESHOLDS_LOOSE`/`THRESHOLDS_TIGHT`). Import añadido: `_bucketize` desde `core.features`.

**`.claude/fase-1-desarrollo-local/etapa-06b.md`:**
- D6B.6 y T4.1: "factory" → "constructor con nombre (preset)" (solo redacción, diseño idéntico);
  T4.1 marcada `✅`; "Done when" de `NotExtended` marcado `[x]`.

## Decisiones tomadas

### D-T4.1 — `NotExtended` es función (preset), no clase
Tal cual D6B.6 / T4.1: una función que arma y devuelve un `SMAPositionRule` configurado. Mantiene
**un solo símbolo de clase de regla** (`SMAPositionRule`) y expresa la variante por configuración,
no por herencia. El nombre `NotExtended` (PascalCase, "constructor con nombre") lee como un
constructor para el call site: `NotExtended(8, "D", side="above")`.

### D-T4.2 — Redacción "preset / constructor con nombre", no "factory" (sugerencia del usuario)
Diseño = D6B.6 sin cambios; solo el vocabulario. Motivo: `AboveSMA` se eliminó (D-T3.2.1) por ser
un *alias*; si a `NotExtended` se le llama también "factory", un lector que hojea ve dos "factories"
con veredictos opuestos y se confunde. "Preset / constructor con nombre" deja claro que `NotExtended`
**encapsula un concepto** (la aritmética `BUCKETS − {extended_above}`), que es justo lo que un alias
NO hace. La cápsula de estudio `docs/conceptos/factory-vs-composicion.md` ya argumenta esta línea.

### D-T4.3 — Criterio (c) con `_bucketize` real, sin stub ni import cross-test (desvío menor del spec)
El spec (c) dice "vía el snapshot construido con otro `thresholds`". El snapshot de producción
(`build_position_snapshot`) necesita un `SymbolData` (stub). Dos opciones evaluadas:
- **Importar `MultiSeriesStub` de `test_features`** → **falla**: con `python -m pytest /Project/tests`
  el dir de tests no queda importable como módulo top-level (`ModuleNotFoundError: test_features`).
  No hay `conftest.py` y `tests/` no es paquete. Forzarlo sería frágil.
- **Duplicar un stub en `test_rules.py`** → reintroduce el duplicado que D-T3.2.2 borró
  (`StubSymbolData`). Rechazado.

**Elegido:** construir el snapshot con `_bucketize` (el componente sensible al threshold, el mismo que
usa `position_vs_sma`/`build_position_snapshot`), a dos `extended` distintos. Demuestra exactamente lo
que pide (c) — el `extended` del snapshot mueve el corte de `NotExtended`, no un `max_pct` per-regla —
sin stub, sin import cross-test, autocontenido. `test_features.py` ya usa `_bucketize` directo, así que
es patrón establecido. El wiring `sd → distance → _bucketize` ya está cubierto end-to-end en
`test_features.py` (T1.1, `test_each_series_computed_exactly_once`; T1.3,
`test_second_threshold_set_moves_the_cuts`).

## Cero código muerto (verificación)

```
grep -in "factory" core/rules.py                         → VACÍO ✅ (mi código usa "preset")
grep "^class " core/rules.py                              → RuleResult, SMAPositionRule (un símbolo de regla) ✅
grep -rn "max_pct" --include=*.py                         → solo prosa que documenta su retiro (cero parámetro/consumidor) ✅
grep -nE "evaluate\(sd|position_vs_sma" core/rules.py     → VACÍO ✅ (T3 sigue limpio)
```

## Pendiente

- **T5** — Retirar `max_extension_pct` de `config/strategies.json` (4 bloques) + reseed +
  round-trip (`diff config/ storage/` vacío) + `resolve_bucket_thresholds` intacto. (Cierra
  también la parte de config del "Done when" #7, cero código muerto.)
- **T6** — Formateador de log (`format_filter_line`/`format_final_line`); decidir `rules.py` vs
  `pipeline.py` (preferencia `pipeline.py`).
- **T7** — `ScanResult` (contrato mínimo en `core/pipeline.py`) + alinear nota §5 de PLAN.md.
- **Done when:** marcados #1 (T1), #2 (T2), #3 (T3), **#4 (T4)**. Faltan #5 (T5), #6 (T6), #7 (cero
  código muerto — parte de config pendiente de T5), y el contrato de `ScanResult` (T7).
- **Cápsula de estudio `docs/conceptos/factory-vs-composicion.md`** (sin commitear, de T3): se
  **conserva** como el explicador canónico del patrón. Retiene "factory" porque ES el término que
  enseña, y ya hace explícita la distinción `AboveSMA`-alias vs `NotExtended`-preset. No se reescribe.
  Si prefieres alinear también su título/énfasis a "preset", es un cambio aparte trivial — avísame.
- **Commit:** acumulado sin commitear desde T3 (dd44dfb): T4 (rules + tests) + ediciones de spec +
  esta bitácora + (de antes) `docs/conceptos/buckets-y-simetria-largo-corto.md` (mod) y
  `docs/conceptos/factory-vs-composicion.md` (nuevo). Sugerencia: commit `[Etapa 6B] T4 NotExtended
  como preset (sin max_pct)` para el código+spec+bitácora, y los docs de conceptos aparte si quieres
  separarlos.
