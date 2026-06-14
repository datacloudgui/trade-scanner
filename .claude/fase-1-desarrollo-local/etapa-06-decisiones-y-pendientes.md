# Etapa 6 — Decisiones y pendientes

Bitácora acumulativa de la etapa (una sección por tarea).

> ## ⚠️ Cierre y reorganización (2026-06-14)
>
> Tras T3, la **aplicación de reglas** se rediseñó en [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) (aprobado) → nueva [Etapa 6B](etapa-06b.md). Esta bitácora es registro histórico de T1.1–T3 (no se reescribe). Qué sigue vigente y qué cambia:
> - **T1.1, T1.2, T1.3, T2.1, T2.2, T2.3 — vigentes sin cambios** (`PositionResult`, `position_vs_sma`, `_bucketize`, `FeatureNotReady`, `bucket_thresholds`, `resolve_bucket_thresholds`).
> - **T3 — vigente como lógica, DEPRECADO en contrato:** `evaluate(sd, thresholds)` → `evaluate(snapshot)` y `AboveSMA` → `SMAPositionRule` (ver nota en la sección T3 y 6B/T3). Las decisiones D-T3.1 (manejo de frío) y la firma cambian; D-T3.2/D-T3.3/D-T3.4/D-T3.5 se conservan en su mayoría.
> - **D4 (NotExtended con `max_pct`) — SUPERSEDED** (nunca se implementó como T4; rediseñado sin `max_pct` en 6B/T4).

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

- **T1.2** — `position_vs_sma(sd, tf, period, thresholds)` + `FeatureNotReady` (contrato de fríos). → ✅ hecho (ver sección T1.2)
- **T1.3** — `_bucketize` (7 buckets, 6 cortes exactos) + test parametrizado de fronteras con dos sets de thresholds. → ✅ hecho (ver sección T1.3)
- **T2** — `bucket_thresholds` en `config/strategies.json` + `resolve_bucket_thresholds` (3 rutas de merge).
- **T3** — `AboveSMA` + `RuleResult` en `core/rules.py`.
- **T4** — `NotExtended` (composición sobre `AboveSMA`).
- **T5** — Formateador del log de filtrado (4 líneas literales).
- **T6** — `ScanResult` (`rules_passed_count`, `sma_evidence`) + reconciliación §5 de PLAN.md.
- **Accesor `SymbolData.close(tf)`** (D3, única modificación permitida a L2) — necesario para T1.2. → ✅ hecho (ver sección T1.2)
- **Preguntas abiertas del spec sin resolver:** ubicación del dataclass `ScanResult` (¿`core/pipeline.py` ya en esta etapa?) y si habrá alguna rule `required=false` en V1 — decidir antes de T6.

---

## T1.2 — `position_vs_sma` + `FeatureNotReady` + accesor `close(tf)` (2026-06-12)

> Sesión interrumpida a mitad de tarea: la implementación (`features.py` + `symbol_data.py`) quedó aplicada sin commitear; al retomar se validó el working tree con `git diff`, se añadieron los tests, suite y bitácora. Sin pérdida de trabajo.

### Resultado contra el criterio de aceptación

Del criterio del bloque T1, lo que corresponde a T1.2:

| Criterio (parte T1.2) | Estado | Evidencia |
|---|---|---|
| `position_vs_sma(sd, tf, period, thresholds) -> PositionResult` | ✅ | `core/features.py`; firma y orden de args del spec (D3: `tf, period`) |
| Lee `sd.sma(tf, period).current.value` y `sd.close(tf)` — solo API de SymbolData | ✅ | `test_delegates_bucket_and_reads_declared_series`: el stub registra exactamente `[is_ready, sma, close]` con los args pedidos |
| Accesor `close(tf)` añadido en L2 (única modificación permitida, pura lectura) | ✅ | `SymbolData.close()`; `test_etapa6_close_reads_last_consolidated_close_per_timeframe` con cadena real D→W (W=20.0, D=99.0, KeyError en tf no construido) |
| Calcula `distance_pct = (close - sma) / sma` | ✅ | `test_distance_pct_formula` parametrizado (+0.05 / −0.05 / 0.0), tolerancia `1e-9` |
| Delega el bucket en `_bucketize` | ✅ | monkeypatch registra `(distance_pct, thresholds)` y su retorno aterriza en `result.bucket` sin recálculo |
| `FeatureNotReady` tipada en `core/features.py` | ✅ | Hereda de `Exception`; mensaje incluye símbolo y serie (`SPY: SMA W:20 fría`) para el log de exclusión de Etapa 7 |
| Fríos: `not is_ready` → raise | ✅ | `test_cold_series_raises_feature_not_ready` (y verifica que NO lee `close` tras el corte) |
| Fríos: `sma == 0` → raise | ✅ | `test_zero_sma_raises_feature_not_ready` |
| Sin imports CLR en `core/features.py` | ✅ | `SymbolData` solo bajo `TYPE_CHECKING`; tests corren sin CLR path |
| `run_tests.sh` verde | ✅ | 50 passed (43 previos + 7 nuevos) |
| Test parametrizado 7 buckets + 6 cortes exactos | ⏳ | Es T1.3: `_bucketize` real + fronteras con dos sets de thresholds |

**Veredicto: ✅ T1.2 cumplido** (la parte ⏳ pertenece a T1.3).

### Decisiones tomadas

#### D-T1.2.1 — `_bucketize` queda como placeholder `NotImplementedError` hasta T1.3

T1.2 "delega el bucket en `_bucketize`" pero la tabla de buckets es T1.3. Para no mezclar alcance (granularidad una-tarea-por-sesión), `_bucketize` existe con firma y docstring pero lanza `NotImplementedError`; los tests del camino caliente de T1.2 lo stubean con `monkeypatch` y verifican la **delegación** (args y retorno), no la clasificación. El propio criterio del spec avala el "stub mínimo". T1.3 lo sustituye por la tabla real + tests de frontera.

#### D-T1.2.2 — Normalización a `float` en la frontera L2→L3

`.current.value` y `.consolidated.close` son `decimal` de C# vía pythonnet. `close(tf)` castea `float()` (honra su hint `-> float`) y `position_vs_sma` castea la SMA antes de operar. Evita aritmética mixta decimal-C#/float y hace estables los asserts de igualdad. Es el mismo patrón que ya usaban los tests de 5A (`float(...)` en cada lectura).

#### D-T1.2.3 — `close(tf)` sin guard de `consolidated is None`

El accesor es mínimo, como dicta D3. El contrato de fríos vive en L3: `position_vs_sma` exige `is_ready` **antes** de leer (si una serie está ready, su consolidator ya emitió ≥ period barras → `consolidated` nunca es None por esa vía). Documentado en el docstring del accesor.

#### D-T1.2.4 — Orden de verificación: `is_ready` → leer SMA → `sma == 0` → leer close

El corte por frío ocurre antes de tocar cualquier estado caliente (testeado: con `ready=False` no se llama `close`). El caso `sma == 0` es defensa contra división degenerada, no un estado esperable de una SMA ready con precios reales.

### Pendiente tras T1.2

Sin pendientes propios de la tarea. Siguiente: **T1.3** (`_bucketize` real — al implementarla, el placeholder y su `NotImplementedError` desaparecen; los tests de delegación de T1.2 quedan como están porque stubean por monkeypatch).

---

## T1.3 — `_bucketize`: tabla de 7 buckets (2026-06-12)

### Resultado contra el criterio de aceptación

Cierra el criterio del bloque T1 completo (T1.1+T1.2+T1.3):

| Criterio T1 | Estado | Evidencia |
|---|---|---|
| `_bucketize(distance_pct, thresholds) -> str` con la tabla de 7 buckets | ✅ | Cascada de arriba hacia abajo en `core/features.py`; exhaustiva y sin solapes por construcción |
| Cortes `near < mild < extended` leídos de `thresholds`; sin números mágicos | ✅ | Los 3 cortes se leen una sola vez al inicio; el cuerpo solo usa esas variables |
| Lado `below` espeja a `above` | ✅ | `test_bucketize_mirror_symmetry`: `bucketize(-d) == espejo(bucketize(d))` para interiores Y cortes |
| Test parametrizado: 7 buckets cubiertos | ✅ | `test_seven_buckets_and_six_exact_cuts` (7 interiores, vía `position_vs_sma` + stub SMA=100) |
| 6 cortes exactos con inclusión/exclusión de la tabla (`>=` piso above, `<=` techo below) | ✅ | Mismo test (6 casos de corte exacto) + `test_bucketize_boundary_ownership_with_epsilon` (12 casos: cada corte y su vecino a `±1e-12` hacia el centro) |
| `distance_pct` con tolerancia `1e-9` | ✅ | Assert con `pytest.approx(abs=1e-9)` en los 13 casos |
| Segundo set de thresholds mueve los cortes (no-hardcodeo) | ✅ | `test_second_threshold_set_moves_the_cuts`: `{near:0.01, mild:0.05, extended:0.08}` — 6 casos donde default y custom clasifican distinto, incl. cortes exactos del set custom (±0.08) |
| Caso con SMA fría levanta `FeatureNotReady` | ✅ | Cubierto en T1.2 (`test_cold_series_raises_feature_not_ready`) |
| `run_tests.sh` verde | ✅ | 82 passed (50 previos + 32 nuevos) |

**Veredicto: ✅ T1.3 cumplido → bloque T1 completo.** Primer "Done when" de la etapa marcado `[x]` en etapa-06.md y PLAN.md.

### Decisiones tomadas

#### D-T1.3.1 — Cascada de extremos hacia el centro, fiel a la invariante de frontera

La tabla se implementa como cascada `extended_above → … → extended_below`. La invariante (un corte exacto pertenece al bucket más alejado de la SMA) queda expresada con `>=` en el lado above y `>` sobre el corte negado en el lado below (equivalente al `<=` de la tabla), documentada en el docstring. No se usa `abs()` ni duplicación de cortes: cada corte aparece una vez por lado.

#### D-T1.3.2 — Constante `BUCKETS` a nivel de módulo (set cerrado de 7)

Se define ya en `core/features.py` porque: (a) los tests de propiedad la usan para verificar que `_bucketize` solo emite buckets conocidos, y (b) T3.1 la necesita para el fail-fast de `buckets_allowed` en el constructor de `AboveSMA` — definir el set canónico junto a quien lo produce evita dos fuentes de verdad.

#### D-T1.3.3 — Doble batería de frontera: división real + epsilon directo

Los cortes exactos se testean por dos vías complementarias: (a) vía `position_vs_sma` con SMA=100 y cierres que producen el corte exacto tras la división (`(103-100)/100 == 0.03` en doble precisión); (b) directo sobre `_bucketize` con `corte ± 1e-12` — valores que la división real difícilmente produce pero que pinean el ownership de cada frontera contra off-by-epsilon (`<` vs `<=`) en refactors. La propiedad espejo cubre además la simetría completa en un solo test.

### Pendiente tras T1.3

Sin pendientes propios de la tarea. **Propuesta para T2.2** (decidir al empezar T2): `resolve_bucket_thresholds` debería validar `0 < near < mild < extended` al resolver la config — hoy nadie lo verifica y unos thresholds desordenados invertirían los intervalos en silencio. Validar una vez en la resolución (entrada de config) y no en `_bucketize` (hot path por símbolo×tf).

---

## T2.1 — `bucket_thresholds` global en `config/strategies.json` (2026-06-13)

### Resultado contra el criterio de aceptación

T2.1 no tiene criterio de aceptación propio (el criterio del bloque T2 cubre T2.2); la tarea es un cambio de config puro verificable directamente:

| Verificación | Estado | Evidencia |
|---|---|---|
| Campo `bucket_thresholds` añadido a nivel raíz de `config/strategies.json` | ✅ | Primera línea del objeto raíz: `{"near": 0.005, "mild": 0.03, "extended": 0.10}` |
| Valores placeholder del spec: `near=0.005`, `mild=0.03`, `extended=0.10` | ✅ | Confirmado por lectura directa del archivo |
| Sin toque a `timeframes` ni `universes` | ✅ | Solo se añadió la clave raíz nueva |
| Campo viaja a `storage/config/strategies.json` vía seed existente | ✅ | `seed_object_store.sh` lo propaga con su glob `config/*.json`; verificado con `python3 -c "json.load(...)"` → `{'near': 0.005, 'mild': 0.03, 'extended': 0.1}` |
| Sin cambio al script `seed_object_store.sh` (glob ya cubría el archivo) | ✅ | T2.3 válido sin modificación adicional |

**Veredicto: ✅ T2.1 cumplido.** T2.3 también verificado de paso (el glob ya cubre el archivo).

### Decisiones tomadas

#### D-T2.1.1 — `bucket_thresholds` como primera clave del objeto raíz

Se coloca antes de `environments` para que sea visible inmediatamente en cualquier editor. Orden elegido por legibilidad, no por restricción técnica (JSON no ordena semánticamente).

#### D-T2.1.2 — Sin override por estrategia en esta tarea

El spec D2 permite override por estrategia (merge poco profundo), pero en V1 ninguna estrategia lo usa. Los overrides se añadirán cuando una estrategia necesite cortes distintos. `resolve_bucket_thresholds` (T2.2) implementará el merge de todas formas.

### Pendiente tras T2.1

- **T2.2** — `resolve_bucket_thresholds(strategies_config, strategy_name) -> dict` (3 rutas: global / override-estrategia / defaults). Incorporar la validación `0 < near < mild < extended` propuesta en T1.3.
- **T2.3** — Ya verificado: el glob de `seed_object_store.sh` cubre el archivo sin cambios.

---

## T2.2 — `resolve_bucket_thresholds` (merge global/override/defaults) (2026-06-13)

### Resultado contra el criterio de aceptación

Cierra el criterio del bloque T2 (T2.1 sembró el campo; T2.3 ya verificado en sesión previa):

| Criterio T2 | Estado | Evidencia |
|---|---|---|
| `resolve_bucket_thresholds(strategies_config, strategy_name) -> dict` en `core/features.py` | ✅ | Función pura junto a `_bucketize`; type hints completos |
| Merge poco profundo: override-estrategia > global > defaults del código | ✅ | Comprehension per-clave `strategy_th.get(k, global_th.get(k, default))` sobre `DEFAULT_BUCKET_THRESHOLDS.items()` |
| Ruta (a) solo global presente → usa global | ✅ | `test_resolve_uses_global_when_no_strategy_override` |
| Ruta (b) override gana clave-a-clave sobre global | ✅ | `test_resolve_strategy_override_wins_key_by_key` (override `{extended:0.08}`; near/mild caen al global) |
| Ruta (c) ausencia total → defaults `{0.005, 0.03, 0.10}` | ✅ | `test_resolve_falls_back_to_code_defaults` (== defaults y NO alias del constante module-level) |
| El dict resuelto siempre trae las 3 claves | ✅ | `test_resolve_always_returns_three_keys` (3 casos: vacío, global parcial, override parcial) |
| `run_tests.sh` verde | ✅ | **95 passed** (82 previos + 13 nuevos) |
| *(extra)* Validación `0 < near < mild < extended` sobre el resultado | ✅ | `test_resolve_rejects_disordered_thresholds` (5 casos) + `test_resolve_override_can_trigger_validation` (override rompe el orden tras merge) |
| *(extra)* Estrategia inexistente → cae al global | ✅ | `test_resolve_unknown_strategy_uses_global` |

**Veredicto: ✅ T2.2 cumplido → bloque T2 completo** (T2.1 ✅ + T2.2 ✅ + T2.3 ✅). Segundo "Done when" de la etapa marcado `[x]`.

### Decisiones tomadas

#### D-T2.2.1 — el parámetro es el `strategies.json` parseado **completo** (raíz), nombrado `full_config`

El global `bucket_thresholds` vive en la **raíz** (T2.1/D2) y el override dentro del bloque de estrategia; para ver ambos, la función recibe el objeto raíz (`global` ← `full_config["bucket_thresholds"]`, `override` ← `full_config["strategies"][name]["bucket_thresholds"]`).

El spec nombró el parámetro `strategies_config`, pero ese nombre colisiona con la variable local de `main.py:37` (`strategies_config = full_config["strategies"]`, que es el **sub-dict**). En Etapa 7 la llamada refleja `resolve_bucket_thresholds(strategies_config, name)` pasaría el sub-dict → **no lanza error, cae a defaults en silencio** para todas las estrategias (anula la calibración de Etapa 9 sin avisar; los tests unitarios no lo atrapan porque el bug vive en el call site). **Decisión (2026-06-13, revisión post-análisis):** se renombra el parámetro a **`full_config`** para que coincida con la variable de `main.py:31` y pasar el sub-dict se lea como error evidente. Conserva la firma del spec (`(config, strategy_name)`), el `strategy_name` en el mensaje de validación y el schema en un solo lugar. Costo ~0: los tests llaman posicional → sin cambios (95 passed antes y después del rename). Opciones descartadas: dejar el nombre ambiguo (riesgo latente) y firma de dos dicts `(global, override)` (pierde `strategy_name`, reescribe los 7 tests).

**Convención para Etapa 7 (acordada, anotada aquí):** la config se carga una sola vez en `initialize()` y los thresholds no cambian por scan. Resolver los thresholds **una vez por estrategia en `initialize()` desde `full_config`** y guardar el `{near, mild, extended}` resuelto en el StrategyConfig/pipeline. El hot path del scan recibe el dict ya resuelto — `position_vs_sma(sd, tf, period, thresholds)` — y **nunca** llama `resolve_bucket_thresholds`. Así la única llamada queda confinada al punto donde `full_config` está en scope, donde pasar el dict correcto es natural.

#### D-T2.2.2 — Validación `0 < near < mild < extended` en la resolución (no en `_bucketize`)

Se incorpora la propuesta dejada por T1.3. Se valida el dict **resuelto** (post-merge), una sola vez en la entrada de config, con `ValueError`. Razón: `_bucketize` corre por símbolo×tf (hot path) y unos cortes desordenados invertirían los intervalos en silencio; el merge es el único punto donde un override puede romper el orden aunque el global sea válido (`test_resolve_override_can_trigger_validation` lo fija). Es estricto (`<`, no `<=`): cortes iguales colapsarían un bucket. No afecta a ninguna config real (default y `config/strategies.json` cumplen `0 < 0.005 < 0.03 < 0.10`).

#### D-T2.2.3 — `DEFAULT_BUCKET_THRESHOLDS` como constante module-level + copia en cada resolución

Los defaults viven en una constante junto a `BUCKETS` (fuente única; la comprehension itera sus `.items()` para derivar las 3 claves canónicas). `resolve_bucket_thresholds` construye un dict nuevo siempre — nunca retorna el alias mutable del constante (`test_resolve_falls_back_to_code_defaults` verifica `is not`), evitando que un consumidor mute los defaults globales por accidente.

#### D-T2.2.4 — Test con dict plano, sin `MockObjectStore`

El criterio admite "MockObjectStore/dict". La función opera sobre el config **ya parseado** (`main.py` hace `json.loads` antes), así que su entrada natural es un `dict` — `MockObjectStore` (que devuelve CSV/strings crudos) no aporta aquí. Los tests pasan dicts literales, fieles a la frontera real de la función.

### Pendiente tras T2.2

Sin pendientes propios. **Bloque T2 cerrado.** Siguiente: **T3** (`AboveSMA` + `RuleResult` en `core/rules.py`) — usará `BUCKETS` (fail-fast de `buckets_allowed`) y `position_vs_sma`. Nota: la integración de `resolve_bucket_thresholds` en `main.py` (con `full_config`, ver D-T2.2.1) es de Etapa 7, no de esta etapa.

---

## T2.3 — `bucket_thresholds` viaja al ObjectStore local (verificación) (2026-06-13)

### Resultado contra el criterio de aceptación

T2.3 es **verificación pura** (sin implementación): confirmar que el campo añadido en T2.1 llega a `storage/config/strategies.json` vía el seed, sin tocar el script si el glob ya lo cubre. Re-verificado **fresco** en esta sesión (no asumido del run de T2.1):

| Criterio T2.3 | Estado | Evidencia |
|---|---|---|
| `bucket_thresholds` presente en `storage/config/strategies.json` tras el seed | ✅ | `json.load(storage/...)` → `{'near': 0.005, 'mild': 0.03, 'extended': 0.1}` |
| Sin cambio al script (el glob `config/*.json` ya lo cubre) | ✅ | Línea del seed `for f in "$SRC_CONFIG"/*.json; do cp ...` — copia el archivo entero, no clave a clave; `strategies.json` entra por el glob |
| Identidad round-trip fuente → destino | ✅ | `diff config/strategies.json storage/config/strategies.json` vacío (el seed es `cp`) |
| Idempotente | ✅ | Re-seed sin error; `cp` sobrescribe |
| *(bonus end-to-end)* `resolve_bucket_thresholds` resuelve desde el artefacto sembrado | ✅ | Host (venv, sin CLR): las 4 estrategias de la config de referencia → `{0.005, 0.03, 0.10}`; `swing_eod` == global sembrado == `DEFAULT_BUCKET_THRESHOLDS`. Cierra la cadena T2.1+T2.2+T2.3 contra el archivo real, no contra un dict de test |

**Veredicto: ✅ T2.3 cumplido. Bloque T2 completo al 100% (T2.1 ✅ + T2.2 ✅ + T2.3 ✅).**

### ¿Era necesaria T2.3 como tarea aparte?

Como *acción*, mínima: ningún cambio de código ni de script (el glob ya cubría el archivo desde Etapa 2). Como *checkpoint*, sí aporta: garantiza explícitamente que el seam config→ObjectStore no se rompió al añadir la clave (un campo nuevo podría haber quedado fuera si el seed copiara claves selectivamente — no es el caso, copia el archivo entero). El bonus end-to-end es lo que de verdad agrega valor: prueba que `resolve_bucket_thresholds` lee el artefacto real, no solo dicts sintéticos. No hay checkbox propio de T2.3 en el "Done when" de etapa-06.md (T2 se cierra con la línea de `resolve_bucket_thresholds`, ya `[x]`).

### Pendiente tras T2.3

Sin pendientes. **Bloque T2 cerrado al 100%.** Siguiente: **T3** (`AboveSMA` + `RuleResult`).

---

## T3 — `AboveSMA` + `RuleResult` (L4, primera rule) (2026-06-13)

> **⚠️ Contrato deprecado 2026-06-14 (ADR-005 / [Etapa 6B](etapa-06b.md) T3).** La implementación de abajo es correcta y queda como histórico, pero `evaluate(sd, thresholds)` pasa a `evaluate(snapshot)` y `AboveSMA` se generaliza a `SMAPositionRule` (mirror long/short). Se conserva: AND estricto, fail-fast de `buckets_allowed`, sin short-circuit, `RuleResult`. El contrato de frío (D-T3.1, frío propagado en `evaluate`) se traslada al builder del snapshot. Los 8 tests se migran en 6B.

### Resultado contra el criterio de aceptación

| Criterio T3 | Estado | Evidencia |
|---|---|---|
| `AboveSMA(period, tfs, buckets_allowed, required=True)` en `core/rules.py` | ✅ | Clase con `evaluate(sd, thresholds) -> RuleResult` |
| `RuleResult` (dataclass): `passed`, `evidence`, `name`, `required` | ✅ | `core/rules.py`; `name` ej. `AboveSMA(20,W+M)` |
| AND estricto: pasa si el bucket de **cada** tf ∈ `buckets_allowed` | ✅ | `evaluate` recorre todos los tf; `passed=False` si alguno cae fuera |
| (a) todos los tf permitidos → `passed=True` | ✅ | `test_and_passes_when_all_tfs_in_allowed_buckets` (W above_strong + M above_mild) |
| (b) un tf fuera → `passed=False` (AND, no OR) | ✅ | `test_and_fails_when_one_tf_out_of_range` (W ∈, M near ∉ → no pasa) |
| (c) `evidence` con forma exacta `{tf:{period:{value,distance_pct,bucket}}}` para todos los tf, también al fallar | ✅ | `_assert_evidence` (claves exactas por nivel; value/bucket exactos, distance_pct `approx 1e-9`) en casos pasa y falla |
| Sin short-circuit: el primer tf que falla no aborta la evidencia | ✅ | `test_evidence_complete_even_when_first_tf_fails` (D falla primero, W sigue evaluándose) |
| (d) `buckets_allowed` inválido → revienta al **construir** (fail-fast) | ✅ | `test_invalid_buckets_allowed_raises_at_construction` (`ValueError`); `test_all_seven_buckets_allowed_is_valid` fija el set aceptado |
| `name` con un solo tf | ✅ | `test_name_single_tf` → `AboveSMA(20,D)` |
| `required` se propaga a `RuleResult` | ✅ | `test_required_flag_propagates_to_result` |
| `core/rules.py` sin imports CLR | ✅ | `grep` solo halla la mención en el docstring; importa `dataclasses`/`typing` + `core.features` |
| `run_tests.sh` verde | ✅ | **103 passed** (95 previos + 8 nuevos) |

**Veredicto: ✅ T3 cumplido.** "Done when" #3 marcado `[x]` en etapa-06.md (en PLAN.md el checkbox agrupa `AboveSMA`+`NotExtended`: anotado `AboveSMA` ✅, falta `NotExtended`/T4).

### Decisiones tomadas

#### D-T3.1 — Fríos se **propagan**, no se manejan en la rule

`evaluate` no envuelve `position_vs_sma` en try/except: si una serie está fría, `FeatureNotReady` sube al pipeline (Etapa 7), que excluye el símbolo y loguea. La rule asume símbolo ya validado (el pipeline excluye fríos **antes** de evaluar reglas). `test_cold_series_propagates_feature_not_ready` fija el contrato para que nadie añada un except que lo silencie. Coherente con la consideración técnica #6 del spec.

#### D-T3.2 — Evaluación de TODOS los tf antes de decidir (sin short-circuit)

Aunque para el AND bastaría cortar al primer bucket fuera de rango, `evaluate` recorre todos los tf y arma la evidencia completa primero; `passed` se baja a `False` sin romper el bucle. Razón: el criterio (c) exige evidencia de **todos** los tf también cuando la rule falla — la evidencia es para el output (Etapa 8), no solo para el veredicto. El costo (evaluar tf de más) es irrelevante: 2–3 tf por símbolo, lectura pura.

#### D-T3.3 — `name` como `@property` derivada; clave `period` de la evidencia es `int`

`name` se computa de `period`+`tfs` (no se almacena): una sola fuente. `NotExtended` (T4) producirá su propio `name` sin heredar el de `AboveSMA`. La evidencia usa `period` como clave **int** (natural desde `self.period`); la coerción a string es de la serialización JSON (Etapa 8), no del contrato en memoria.

#### D-T3.4 — `RuleResult` dataclass **no** frozen

A diferencia de `PositionResult` (frozen, campos escalares), `RuleResult` contiene `evidence: dict` (mutable): congelar solo el binding daría falsa sensación de inmutabilidad. Se deja como `@dataclass` plano (eq por valor para asserts). El spec pide "dataclass" sin exigir frozen.

#### D-T3.5 — Stub multi-tf propio en `test_rules.py`

El `StubSymbolData` de `test_features.py` tiene un único `(sma, close)` para todos los tf; las rules necesitan **distinto bucket por tf**. Se define un stub paralelo `{tf: (sma, close)}` en `test_rules.py` (mínimo: solo `is_ready`/`sma`/`close`). No se factoriza a un conftest compartido todavía — dos stubs pequeños y legibles > una abstracción prematura; si T4/T5 lo repiten, se promueve a `conftest.py`.

### Pendiente tras T3

Sin pendientes propios. Siguiente: **T4** (`NotExtended`, composición sobre `AboveSMA`, D4) — reutilizará `AboveSMA` con `buckets_allowed` = 7 menos `extended_above` e inyectará `max_pct` como `thresholds["extended"]` efectivo; `name` propio `NotExtended(8,D)` (ver D-T3.3: cada rule arma su nombre).
