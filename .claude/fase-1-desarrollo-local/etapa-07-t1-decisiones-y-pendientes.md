# T1.1 (Etapa 7) — `reference_price`: precio único "ahora" (2026-06-18)

L3, `core/features.py` + `tests/test_features.py`. Primer paso de T1 (decisión A.2): el helper
único del "precio ahora". **Solo T1.1**; el refactor de `position_vs_sma` (T1.2), `build_position_snapshot`
(T1.3) y la migración de tests E6 (T1.4) quedan pendientes en esta misma tarea T1.

## Resultado contra el criterio de aceptación

El único criterio de T1 que aplica a T1.1 es el (a) — los (b)/(c) son de T1.2/T1.3 y (d) es transversal:

| Criterio | Estado | Evidencia |
|---|---|---|
| (a) `reference_price` devuelve `working_bar.close` con working bar y `close("D")` sin él (stub) | ✅ | `test_reference_price_uses_working_bar_when_present`, `test_reference_price_falls_back_to_daily_close_without_working_bar` |
| Cast `float()` del decimal C# en working bar (frontera L2→L3) | ✅ | `test_reference_price_casts_working_bar_close_to_float` (int 99 → 99.0, `isinstance float`) |
| Con working bar NO consulta el cierre consolidado | ✅ | mismo test (a): `sd.calls == []` con working bar; `== ["D"]` en fallback |
| (d) `core/features.py` sin `AlgorithmImports` a nivel de módulo | ✅ | `grep AlgorithmImports` → solo el docstring (línea 3), cero imports |
| `run_tests.sh` verde | ✅ | **144 passed, 13 warnings in 6.12s** (Docker) — 141 previos + 3 de T1.1 |

**Veredicto: ✅ T1.1 cumplido.** Ningún "Done when" de la etapa se marca aún: el #1 (Precio único A.1)
exige también T1.2–T1.4.

## Cambios

**`core/features.py`:** nueva función pura `reference_price(sd) -> float` (antes de `position_vs_sma`):
`float(sd.working_bar.close)` si hay working bar, si no `sd.close("D")`. Docstring corto: por qué el
working bar (con minute, la diaria de hoy no se consolida hasta la sesión siguiente → "hoy" solo vive
ahí) y el fallback C2.

**`tests/test_features.py`:** import de `reference_price` + sección T1.1 con `ReferencePriceStub`
(stub mínimo `.working_bar`/`.close`) y 3 tests. `141 → 144 passed`.

**`.claude/fase-1-desarrollo-local/etapa-07.md`:** Estado `pendiente` → `en progreso`.

## Decisiones tomadas

### D-T1.1.a — El fallback devuelve `sd.close("D")` sin re-envolver en `float()`
`SymbolData.close()` ya normaliza a `float` en su frontera (`symbol_data.py:126`), así que el segundo
`float()` sería redundante. El cast explícito se reserva al working bar, cuyo `.close` es decimal C#
crudo. Coherente con la spec de T1.1 (`float(sd.working_bar.close)` … `si no sd.close("D")`).

### D-T1.1.b — El log del fallback C2 NO vive en `reference_price` (es del pipeline, T4)
C2 pide "loguear el fallback" cuando no hay working bar. L3 es negocio puro (sin `QCAlgorithm`, no
puede loguear): `reference_price` solo devuelve el precio. La observabilidad del fallback la añade el
**pipeline (T4)**, que es quien tiene el logger y arma el embudo. No es un hueco, es separación de capas.

### D-T1.1.c — `working_bar is None`, no truthiness
Se chequea `if working is not None` (no `if working`): un working bar válido con OHLC en cero sería
falsy y caería al fallback por error. `None` es el único sentinel de "sin barra" (antes de la primera
barra del día); cualquier objeto barra, aun degenerado, es un dato real.

### D-T1.1.d — Sin caller en producción todavía (esperado)
`reference_price` queda implementado y testeado pero **aún no se invoca** desde `build_position_snapshot`
ni el ranking: ese cableado es T1.3/T2/T4. Es deliberado por el alcance "solo T1.1 hoy"; no es código muerto.

## Pendiente

- **Resto de T1 (refactor A.1), no tocado hoy:**
  - **T1.2** — cambiar la firma de `position_vs_sma(sd, tf, period, thresholds, price)`: recibe el
    precio inyectado y deja de leer `sd.close(tf)`; conservar contrato de fríos (`is_ready`, `sma==0`).
  - **T1.3** — `build_position_snapshot` computa `price = reference_price(sd)` **una vez** y lo pasa a
    cada `position_vs_sma` (firma externa intacta).
  - **T1.4** — migrar los tests E6 de `position_vs_sma`/`_bucketize`/snapshot al contrato de precio
    inyectado (hoy siguen pasando porque `position_vs_sma` aún lee `sd.close(tf)`; ese contrato cambia
    en T1.2 y rompería estos tests si no se migran).
- **Caso degenerado documentado (no implementado):** si no hay working bar **ni** cierre consolidado
  (símbolo profundamente frío), `sd.close("D")` propaga el error de LEAN. El gate de exclusión por
  series referenciadas (B, T4) filtra esos símbolos antes; `reference_price` no necesita guard propio.
- **Commit:** gated por el usuario. Acumulado de hoy: `core/features.py`, `tests/test_features.py`,
  `etapa-07.md` (Estado), esta bitácora.
