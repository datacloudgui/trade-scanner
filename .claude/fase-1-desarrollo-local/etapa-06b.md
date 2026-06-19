# Etapa 6B — Snapshot único de posición y reglas como filtros puros

**Estado:** en progreso
**Depende de:** Etapa 6 (T1+T2+T3: `PositionResult`, `position_vs_sma`, `_bucketize`, `FeatureNotReady`, `resolve_bucket_thresholds`, `BUCKETS`, `RuleResult`, `AboveSMA`).
**Autoridad de diseño:** [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) (aprobado 2026-06-14). **Supersede:** D4 de [etapa-06.md](etapa-06.md) (parcial — ver §"Qué cambia respecto a Etapa 6").
**Estimado:** 3–5 h (L3 + L4, sin pipeline).

**Contexto.** Etapa 6 entregó los fundamentos de L3/L4 con un contrato per-serie: cada rule llamaba `position_vs_sma(sd, tf, period, thresholds)` por su cuenta dentro de `evaluate(sd, thresholds)`. El ADR-005 (aprobado) rediseña la **aplicación** de las reglas: **una sola evaluación** de posición precio↔SMA por símbolo·scan (snapshot único), bucketizada **una vez** con el set resuelto de la estrategia, y reglas convertidas en **filtros que solo leen** buckets ya asignados — simétricas para largos y cortos sin duplicar reglas, y baratas de reconstruir por barra de 2-min (intradía futuro, fuera de alcance). Esta etapa implementa ese rediseño y cierra las piezas pendientes de la capa de reglas (formateador de log, `ScanResult`) bajo el nuevo contrato. Sigue sin ensamblar el pipeline (Etapa 7) ni la salida (Etapa 8).

---

## Decisiones de diseño (aprobadas en ADR-005)

### D6B.1 — Snapshot único `{tf: {period: PositionResult}}` (dict anidado plano)

`build_position_snapshot(sd, series, thresholds)` construye, **una vez por símbolo·scan**, la posición precio↔SMA de cada `(tf, period)` que las reglas de la estrategia referencian. Estructura = dict anidado plano (misma forma que la evidencia), **sin clase envolvente** (ADR §5: el wrapper añade ceremonia; la validación `series ⊆ declared` va al pipeline en config-time, no al hot path). Reutiliza `position_vs_sma` como primitivo per-serie (loop fino): conserva el contrato de fríos, la normalización `float()` L2→L3 y `_bucketize`.

### D6B.2 — `series` = lo que referencian las rules, NO `sd.declared`

El snapshot cubre la **unión de `(tf, period)` que usan las rules de la estrategia**, no toda SMA declarada. Doble razón: (a) no malgastar cómputo en SMAs que ninguna rule mira; (b) **no sobre-excluir por frío** — una SMA fría que ninguna rule usa no debe sacar el símbolo del scan. La unión se resuelve **una vez en `initialize()`** (Etapa 7), junto a los thresholds; el builder la recibe como parámetro explícito `series`.

### D6B.3 — `evaluate(snapshot)` — la regla pierde `sd` y `thresholds`

Firma nueva: `evaluate(self, snapshot) -> RuleResult` (antes `evaluate(self, sd, thresholds)`). La regla ya **no tiene** `SymbolData` (no puede re-medir) ni cortes (no puede re-bucketizar): solo lee `snapshot[tf][period].bucket`. La pureza pasa de convención a invariante de tipo. **El contrato de fríos se traslada al builder**: `FeatureNotReady` aflora en `build_position_snapshot` (un solo punto), no en `evaluate` — la rule asume un snapshot ya construido sobre un símbolo caliente.

### D6B.4 — Long/short: vocabulario canónico "above" + mirror en construcción

Las rules se autoran en vocabulario **largo/above** (canónico). `direction` → `side` (`long→"above"`, `short→"below"`) aplica `mirror_buckets` **una sola vez al construir la rule**; el `evaluate` resultante es idéntico para ambos lados (solo cambia el set concreto permitido). `mirror_buckets` es biyección sobre los 7 buckets (`near` autoespejo) ⇒ el resultado siempre ⊆ `BUCKETS` sin re-validar. La resolución `direction→side` (lectura de config) es de Etapa 7; en 6B las rules reciben `side` directo (tests aislados). Se añade el mapa `SIDE_BY_DIRECTION = {"long": "above", "short": "below"}` como única fuente de esa traducción.

### D6B.5 — `AboveSMA` → `SMAPositionRule` genérica (rename aprobado)

Una sola clase `SMAPositionRule` reemplaza `AboveSMA` y sirve de base a `NotExtended`. `name` renderiza la etiqueta legible por `side`+`label`: `AboveSMA(20,W+M)` / `BelowSMA(20,W+M)` / `NotExtended(8,D)`. Se conserva del diseño de T3: validación fail-fast de `buckets_allowed ⊆ BUCKETS` en construcción, AND estricto sobre todos los tf, sin short-circuit (evidencia completa aun al fallar), `RuleResult` no-frozen.

### D6B.6 — `NotExtended` sin `max_pct` (supersede D4)

`NotExtended` deja de ser una clase con umbral propio: pasa a ser un **constructor con nombre (preset)** que arma `SMAPositionRule(period, [tf], buckets_allowed=BUCKETS − {extended_above}, side, label="NotExtended")`. (Redacción: se evita "factory" para que la coherencia con D-T3.2.1 sea obvia — `AboveSMA` se eliminó por ser un *alias* vacío; `NotExtended` se conserva porque **encapsula un concepto** (qué buckets son "extendido"), no porque precargue un argumento.) "No extendido" = "el bucket favorable-extremo está excluido"; el corte que define "extremo" es el `bucket_thresholds.extended` **único** de la estrategia (ya aplicado al bucketizar el snapshot). **Obsoleto de D4:** el parámetro `max_pct` y la inyección de `thresholds["extended"]` por-regla. **Se conserva de D4:** que `NotExtended` es composición (no subclase).

### D6B.7 — Evidencia como proyección del snapshot

`snapshot_evidence(snapshot, series)` proyecta al esquema `{tf:{period:{value,distance_pct,bucket}}}` (descarta `side`). `RuleResult.evidence` = proyección sobre las series de esa rule; `ScanResult.sma_evidence` (Etapa 8) = proyección sobre la unión. Pura proyección — cero recompute.

### D6B.8 — `max_extension_pct` se retira de la config

Redundante con `bucket_thresholds.extended` (hoy ambos `0.10` en las 4 estrategias). El corte "extendido" es único y compartido. Sembrado originalmente en Etapa 3 (`64a39cd`), **sin ningún consumidor en código** (`grep` limpio) → retiro limpio, sin regresión funcional. Se anota la trazabilidad (origen E3 → retiro 6B).

---

## Tareas

> `(FABLE xhigh)` en subtareas con semántica de buckets/fronteras/simetría o capas. Resto `high`; config/log/commits `medium`.

### T1 — `build_position_snapshot` + `snapshot_evidence` (L3, `core/features.py`)

- **T1.1 (FABLE xhigh)** ✅ *(implementada 2026-06-14 — ver `etapa-06b-t1-1-decisiones-y-pendientes.md`)* — `build_position_snapshot(sd, series: Iterable[tuple[str,int]], thresholds: dict) -> dict[str, dict[int, PositionResult]]`: itera `position_vs_sma(sd, tf, period, thresholds)` sobre cada `(tf, period)` en `series`, una sola vez, y los agrupa en el dict anidado. **Frío:** la primera serie que lance `FeatureNotReady` se propaga (no se captura) — el manejo (exclusión + log) es de Etapa 7. No cubre series fuera de `series` aunque estén declaradas en `sd` (D6B.2).
- **T1.2** ✅ *(implementada 2026-06-14 — ver `etapa-06b-t1-2-decisiones-y-pendientes.md`)* — `snapshot_evidence(snapshot, series) -> dict`: proyecta el subconjunto `series` del snapshot al esquema `{tf:{period:{value,distance_pct,bucket}}}` (sin `side`). Pura lectura del snapshot, sin `sd` ni recompute. **Es la ÚNICA fuente de evidencia** de aquí en adelante: T3 elimina la construcción inline del dict de evidencia que hoy vive en `AboveSMA.evaluate` (`rules.py:69-75`) y la reemplaza por una llamada a esta función.

**Criterio de aceptación:**
- (a) Snapshot de un stub multi-`(tf,period)` tiene la forma exacta `{tf:{period:PositionResult}}` con los `value/distance_pct/bucket` esperados; `position_vs_sma` se invoca **una vez por serie** con los args correctos (spy/monkeypatch que cuenta llamadas), nunca dos veces para la misma serie.
- (b) Una serie fría en `series` levanta `FeatureNotReady` y **detiene** la construcción (no se silencia); el mensaje identifica símbolo+serie.
- (c) `series` ⊊ `sd.declared`: una SMA declarada-pero-no-referenciada **no se computa** y su frialdad **no** excluye el símbolo (se construye el snapshot solo con `series`).
- (d) `snapshot_evidence` reproduce exactamente el esquema para un subconjunto de series; `distance_pct` con tolerancia `1e-9`; no incluye `side`.
- `bash scripts/run_tests.sh` verde.

### T2 — `mirror_buckets` + `_MIRROR` (L3, `core/features.py`)

- **T2.1 (FABLE xhigh)** ✅ *(implementada 2026-06-14 — ver `etapa-06b-t2-decisiones-y-pendientes.md`)* — `_MIRROR: dict[str,str]` (7 entradas; `above_*↔below_*`, `near→near`) y `mirror_buckets(buckets: Iterable[str], side: str) -> frozenset[str]`: `side=="above"` → identidad; `side=="below"` → espejo por `_MIRROR`. Valida `side ∈ {"above","below"}` (fail-fast). Añadir `SIDE_BY_DIRECTION = {"long":"above","short":"below"}` (D6B.4).

**Criterio de aceptación:**
- (a) `mirror_buckets(X, "above") == frozenset(X)` (identidad).
- (b) `near` es autoespejo: `mirror_buckets({"near"}, "below") == {"near"}`.
- (c) **Involución:** espejar dos veces devuelve el set original, para cualquier subconjunto de los 7.
- (d) `mirror_buckets({"above_mild","above_strong","extended_above"}, "below") == {"below_mild","below_strong","extended_below"}`.
- (e) El resultado siempre ⊆ `BUCKETS`; un `side` inválido levanta `ValueError`.
- `run_tests.sh` verde.

### T3 — `SMAPositionRule` (generaliza `AboveSMA`, `evaluate(snapshot)`) (L4, `core/rules.py`)

- **T3.1 (FABLE xhigh)** ✅ *(implementada 2026-06-14 — ver `etapa-06b-t3-1-decisiones-y-pendientes.md`; T3.2–T3.4 pendientes para cerrar T3)* — `SMAPositionRule(period, tfs, buckets_allowed, side, required=True, label="SMA")`: (1) valida `buckets_allowed` **canónicos** ⊆ `BUCKETS` en construcción (fail-fast, como T3); (2) almacena `self.buckets_allowed = mirror_buckets(buckets_allowed, side)` (una vez). `name` (property) renderiza por `side`+`label`: `label=="SMA"` → `AboveSMA(...)`/`BelowSMA(...)`; otro `label` → `<label>(period,tfs)`. `evaluate(snapshot) -> RuleResult`: para **todos** los tf en `tfs`, lee `snapshot[tf][period]`, baja `passed` si algún `bucket ∉ self.buckets_allowed` (AND, sin short-circuit), arma `evidence = snapshot_evidence(snapshot, [(tf,period) for tf in tfs])`.
- **T3.2** ✅ *(2026-06-14 — ver `etapa-06b-t3-2-decisiones-y-pendientes.md`)* — Migrar `AboveSMA` → `SMAPositionRule(label="SMA")`. **Decisión del usuario: `AboveSMA` ELIMINADO** (no se conserva como factory; un solo símbolo de clase). E7 compondrá long con `side="above"` explícito (que en la práctica saldrá de config vía `SIDE_BY_DIRECTION`).
- **T3.3 — Limpieza (cero código muerto en `rules.py`).** ✅ *(2026-06-14)* Al refactorizar:
  - **Eliminar** el cuerpo viejo `evaluate(sd, thresholds)` y su construcción **inline** de `evidence` (`rules.py:69-75`) — la evidencia sale de `snapshot_evidence` (T1.2).
  - **Eliminar el import huérfano** `position_vs_sma` de `rules.py` (línea 10): tras el refactor `rules.py` ya **no** lo llama (lo usa el builder en `features.py`). Dejar `from core.features import BUCKETS, mirror_buckets, snapshot_evidence` (+ `SIDE_BY_DIRECTION` si se usa aquí).
  - **Actualizar el docstring del módulo** (`rules.py:1-6`): hoy dice "evalúa `position_vs_sma` (L3)"; pasa a "filtra sobre el snapshot precalculado".
  - **Si `AboveSMA` deja de ser clase** (se vuelve factory o se elimina): no dejar la clase vieja y la nueva conviviendo — un solo símbolo.
- **T3.4 — Limpieza de tests (`test_rules.py`).** ✅ *(2026-06-14 — `StubSymbolData` ELIMINADO en vez de reubicado: el builder ya usa `MultiSeriesStub` (T1.1); el test de frío ya está cubierto por `test_cold_series_halts_and_propagates` en test_features.py. Los 8 tests de `AboveSMA` se borraron: los 11 de `SMAPositionRule` (T3.1) los superan bajo el nuevo contrato.)*
  - **Reubicar** `StubSymbolData` (lee `is_ready`/`sma`/`close`) a `test_features.py` (o `conftest.py`): tras la migración lo necesitan los tests del **builder** (T1), no las rules (que reciben snapshots). No dejar el stub huérfano en `test_rules.py`.
  - **Mover** `test_cold_series_propagates_feature_not_ready` (`test_rules.py:129`) a `test_features.py`: el frío ahora aflora en `build_position_snapshot`, no en `evaluate`. Borrarlo de `test_rules.py`.
  - **Reescribir** los 8 tests de T3 para construir el snapshot (`build_position_snapshot`/stub→dict) y llamar `evaluate(snapshot)`; eliminar las llamadas `.evaluate(sd, THRESHOLDS)` y el `THRESHOLDS` local si queda sin uso.

**Criterio de aceptación:**
- (a) Largo (`side="above"`): todos los tf en buckets permitidos → `passed=True`; un tf fuera → `passed=False` (AND, no OR). Migración de los 8 tests de T3 a `build_position_snapshot(...)` + `evaluate(snapshot)`.
- (b) Corto (`side="below"`): con los mismos buckets canónicos, el mirror produce el filtrado `below_*` correcto (un símbolo `extended_below` pasa un `AboveSMA` canónico mirrored a short; un `above_*` no).
- (c) `evidence` con forma exacta `{tf:{period:{value,distance_pct,bucket}}}` para **todos** los tf, también cuando la rule no pasa (sin short-circuit).
- (d) `buckets_allowed` inválido → `ValueError` **en construcción**.
- (e) `evaluate` **no** maneja fríos: con un snapshot ya construido nunca toca `FeatureNotReady` (el contrato de frío se prueba en T1, no aquí). `name` correcto para 1 y N tf en ambos lados.
- (f) **Cero código muerto:** `grep -n "evaluate(sd\|position_vs_sma" trade-scanner/core/rules.py` vacío; `grep "class AboveSMA\|class SMAPositionRule" rules.py` devuelve **un solo** símbolo de clase; sin imports ni `StubSymbolData`/`THRESHOLDS` huérfanos en `test_rules.py`.
- `run_tests.sh` verde.

### T4 — `NotExtended` rediseñada (factory sin `max_pct`) (L4, `core/rules.py`) — **supersede D4**

- **T4.1 (FABLE xhigh)** ✅ *(implementada 2026-06-18 — ver `etapa-06b-t4-decisiones-y-pendientes.md`)* — `NotExtended(period, tf, side, required=True)`: constructor con nombre (preset) que retorna `SMAPositionRule(period, [tf], buckets_allowed=BUCKETS − {"extended_above"}, side, required, label="NotExtended")`. **Sin `max_pct`.** `name == NotExtended(8,D)`.

**Criterio de aceptación:**
- (a) Largo: falla cuando el bucket es `extended_above` (`distance_pct ≥ bucket_thresholds.extended`); pasa en `above_strong` justo por debajo del corte `extended`.
- (b) Corto (`side="below"`): el mirror excluye `extended_below`; falla en `extended_below`, pasa en `below_strong`.
- (c) Un **segundo** `bucket_thresholds.extended` (vía el snapshot construido con otro `thresholds`) **mueve el corte** de `NotExtended` — demuestra que el único umbral de la estrategia manda (reemplaza al viejo test de "`max_pct` distinto del global", que ya no existe).
- (d) `evidence` con la misma forma que `SMAPositionRule`.
- `run_tests.sh` verde.

### T5 — Retirar `max_extension_pct` de la config (`config/strategies.json`)

- **T5.1** ✅ *(implementada 2026-06-18 — ver `etapa-06b-t5-decisiones-y-pendientes.md`)* — Eliminar la clave `max_extension_pct` de los 4 bloques de estrategia. Verificar que viaja (su ausencia) a `storage/config/strategies.json` vía `seed_object_store.sh` (sin cambio de script). Anotar trazabilidad: origen Etapa 3 (`64a39cd`), sin consumidor en código.

**Criterio de aceptación:**
- (a) `grep -rn "max_extension_pct" --include="*.py"` vacío (ya lo está) y la clave ausente en `config/strategies.json` y, tras el seed, en `storage/config/strategies.json`.
- (b) `diff config/strategies.json storage/config/strategies.json` vacío tras el seed (identidad round-trip).
- (c) `resolve_bucket_thresholds` sigue resolviendo `{near,mild,extended}` para las 4 estrategias desde el artefacto sembrado (la retirada no afecta la resolución de thresholds).

### T6 — Formateador del log de filtrado (portado de Etapa 6/T5, sin cambios de diseño)

- **T6.1** ✅ *(implementada 2026-06-18 — ver `etapa-06b-t6-decisiones-y-pendientes.md`)* — Función pura `format_filter_line(strategy, rule_name, n_in, n_out, kind) -> str` → `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)`; `format_final_line(strategy, n) -> str` → `[<strategy>] final: <n> candidatos`. `kind ∈ {"required","optional"}`. **No** ejecuta filtrado (Etapa 7); solo formatea contadores. **Ubicación decidida: `core/pipeline.py`** (el log de embudo es del orquestador, no de la rule; `rules.py` queda como L4 puro de filtros). Símbolos exactos: flecha U+2192, signo menos U+2212.

**Criterio de aceptación:** test que reproduce **literalmente** las 4 líneas a partir de contadores:
```
[swing_eod] AboveSMA(20,W+M): 50 → 38 (−12 required)
[swing_eod] AboveSMA(20,D): 38 → 29 (−9 required)
[swing_eod] NotExtended(8,D): 29 → 22 (−7 required)
[swing_eod] final: 22 candidatos
```

### T7 — `ScanResult`: campos nuevos + reconciliación §5 (portado de Etapa 6/T6)

- **T7.1** ✅ *(implementada 2026-06-18 — ver `etapa-06b-t7-decisiones-y-pendientes.md`)* — Crear el dataclass mínimo `ScanResult` en `core/pipeline.py` (solo contrato, sin lógica de llenado — eso es Etapa 7) con, al menos: `rules_passed_count: int = 0` y `sma_evidence: dict = field(default_factory=dict)`, forma `{tf:{period:{value,distance_pct,bucket}}}`. Documentar que `sma_evidence` es **proyección del snapshot** (`snapshot_evidence` sobre la unión de series), no un recompute. **Decisión: contrato mínimo (solo los 2 campos nuevos); E7 añade el resto de la fila de §5.**
- **T7.2** ✅ *(2026-06-18)* — Verificar que PLAN.md §5 ya usa `distance_pct` + `bucket` (reconciliado en E6: confirmado, línea 141 + ejemplo); alinear la nota del ejemplo a "proyección del snapshot único (Etapa 6B)".

**Criterio de aceptación:** test de construcción que confirma los campos nuevos con sus defaults; nota de §5 de PLAN.md alineada. `run_tests.sh` verde.

---

## Consideraciones técnicas específicas al stack

1. **Pureza de capa (dura):** `core/features.py` y `core/rules.py` siguen importables **sin CLR** — cero `AlgorithmImports` salvo tipos bajo `TYPE_CHECKING`. El snapshot y el mirror son negocio puro; se testean con `SymbolData` sintético / stub mínimo (mismo patrón que E6). `build_position_snapshot` solo habla con la API de `SymbolData` vía `position_vs_sma`.
2. **El snapshot no toca L2.** `build_position_snapshot` **no** modifica `SymbolData`: solo lee (`is_ready`/`sma`/`close` a través de `position_vs_sma`). El accesor `close(tf)` (E6/D3) ya existe; no se añade nada a L2 en esta etapa.
3. **Frío en un solo punto.** A diferencia de E6 (cada rule podía lanzar `FeatureNotReady`), ahora **solo el builder** lo lanza. Las rules asumen snapshot caliente. El test de propagación de frío migra de `test_rules.py` (E6, D-T3.1) a `test_features.py` (builder). `evaluate` ya no debe envolver nada en try/except.
4. **`series` como `Iterable[tuple[str,int]]`.** El builder no asume orden ni unicidad; si se pasa una serie repetida, `position_vs_sma` se llamaría dos veces — por eso E7 pasa un **set** (unión deduplicada). Documentar que el dedup es responsabilidad del call site (E7), coherente con D6B.2.
5. **Mirror como biyección.** `mirror_buckets` debe ser involutiva y total sobre los 7 buckets; `near` autoespejo es el caso de frontera a fijar con test (que nadie lo "optimice" a un `if side=='above'` que olvide `near`). El resultado ⊆ `BUCKETS` se garantiza por construcción (no re-validar en caliente).
6. **`buckets_allowed` canónico, validación antes del mirror.** La validación fail-fast de E6 (set ⊆ `BUCKETS`) se hace sobre los buckets **canónicos** (los que escribe la config, en vocabulario above), **antes** de espejar. El mirror de un set válido es válido.
7. **`distance_pct` es fracción, no porcentaje** (igual que E6): `0.0231`, no `2.31`. La evidencia y `sma_evidence` heredan esta convención (§5 de PLAN.md).
8. **Tests dentro de la imagen LEAN.** Como siempre, vía `scripts/run_tests.sh` (pythonnet/Docker). Los stubs de snapshot/rule no requieren CLR, pero la suite completa corre en Docker.
9. **Cero código muerto (regla de cierre de la etapa).** Este rediseño *reemplaza* contratos; cada tarea que renombra o supersede algo debe **borrar** lo viejo en el mismo commit, no dejarlo conviviendo:
   - `rules.py`: fuera el `evaluate(sd, thresholds)` viejo, la evidencia inline y el import `position_vs_sma` (T3.3).
   - `test_rules.py`: `StubSymbolData` y el test de frío se **reubican** a `test_features.py`; nada huérfano (T3.4).
   - `config`: `max_extension_pct` retirado, no comentado (T5).
   - Un solo símbolo de clase de regla (T3.2). Sin alias de transición que sobrevivan a la etapa salvo el `AboveSMA`-factory si se decide conservarlo (decisión explícita, no residuo).
   Verificación: `grep` de las firmas/símbolos viejos vacío (criterios T3.f, T5.a) + suite verde **sin** tests saltados o stubs sin uso.

---

## Qué NO hacer en esta etapa (fuera de scope)

- **Pipeline / orquestación real** (construir el snapshot por símbolo en el scan, ranking `top_n`, exclusión de fríos, `main_timeframe`, lectura de `direction`→`side` desde config) — **Etapa 7**. Aquí las rules reciben `side` directo y el snapshot se construye en tests.
- **Composición declarativa de estrategias** (qué rules, con qué `buckets_allowed`, por estrategia; dónde vive: `strategies/` vs config) — **Etapa 7** (ADR-005 §9.1).
- **Inclusión o no del bucket `near` en `AboveSMA`** ("above" estricto vs banda) — decisión de composición de **Etapa 7** / calibración **Etapa 9** (ADR-005 §9.2). No condiciona este diseño.
- **`working_bar` / precio vivo / variante intradía del snapshot** (`use_working_bar`, `position_vs_sma_live`) — **Fase 2** (ADR-004, ADR-005 §8). El builder lee la barra consolidada cerrada.
- **Timeframes intradía (1/5/15-min) en `SymbolData`** — **Fase 2** (el bloqueante real, L2).
- **`OutputSink` / serialización CSV-JSON de `ScanResult`** — **Etapa 8**. Aquí solo el contrato del dataclass.
- **Compartir un snapshot entre estrategias del mismo símbolo** — optimización futura, gateada en `(thresholds, series)` idénticos; en V1 los universos long/short son disjuntos (ADR-005 §9.4).
- **Calibración de `bucket_thresholds`** — placeholders; **Etapa 9**.
- **Cualquier import de `QCAlgorithm`/`self.history`/datos** en L3/L4.

---

## Done when (medible)

- [x] `build_position_snapshot` computa cada serie **una sola vez**, propaga `FeatureNotReady` en la primera serie fría, y **no** computa ni excluye por series declaradas-pero-no-referenciadas; `snapshot_evidence` proyecta el esquema exacto. Tests verdes — `bash scripts/run_tests.sh`. *(T1.1+T1.2 — 112 passed, 2026-06-14)*
- [x] `mirror_buckets` verifica identidad (above), `near` autoespejo, involución, above→below, resultado ⊆ `BUCKETS`, `side` inválido → `ValueError`. Tests verdes. *(T2.1 — 126 passed, 2026-06-14)*
- [x] `SMAPositionRule` con `evaluate(snapshot)`: los 8 tests de T3 migrados + casos short (mirror) verdes; evidencia completa aun al fallar; `buckets_allowed` inválido revienta en construcción; `evaluate` no toca `FeatureNotReady`. *(T3.1–T3.4 — `AboveSMA` eliminado; 129 passed, 2026-06-14)*
- [x] `NotExtended` (sin `max_pct`) excluye el bucket favorable-extremo en ambos lados; un segundo `bucket_thresholds.extended` mueve el corte; evidencia coherente. Tests verdes. *(T4.1 — 135 passed, 2026-06-18)*
- [x] `max_extension_pct` retirado de `config/strategies.json` y de `storage/` tras el seed; `grep` en `.py` limpio; round-trip idéntico; `resolve_bucket_thresholds` intacto. *(T5.1 — grep vacío en `.py`/config/storage, diff round-trip vacío, las 4 estrategias resuelven {near,mild,extended}, 2026-06-18)*
- [x] Formateador reproduce **literalmente** las 4 líneas del ejemplo. *(T6.1 — `core/pipeline.py` + `tests/test_pipeline.py`; 138 passed, 2026-06-18)*
- [x] `ScanResult` (contrato mínimo en `core/pipeline.py`) con `rules_passed_count` + `sma_evidence` (documentado como proyección del snapshot); §5 de PLAN.md alineada. *(T7 — construible sin args con defaults, acepta la proyección, default_factory por-instancia; nota §5 alineada; 141 passed, 2026-06-18)*
- [x] **Cero código muerto:** `grep` de `evaluate(sd`, `position_vs_sma` (en `rules.py`), `max_extension_pct` (en `.py`/config) y de un segundo símbolo de clase de regla → todos vacíos; `StubSymbolData`/test de frío reubicados a `test_features.py`; sin tests saltados ni stubs sin uso. *(cerrado al completar T5: la parte de `rules.py`/tests venía de T3, la de `max_extension_pct` la cierra T5, 2026-06-18)*
- [ ] `core/features.py` y `core/rules.py` sin imports de `QCAlgorithm`/`self.history`; suite completa verde en Docker. Commit `[Etapa 6B] ...`.

---

## Preguntas abiertas

- [x] **¿Conservar el símbolo `AboveSMA`** (como alias/factory `side="above"` de `SMAPositionRule`) o eliminarlo del namespace? **RESUELTO (2026-06-14): ELIMINADO.** Tras el rediseño no hay semántica "above-específica" — es `SMAPositionRule(side="above")`; una factory reintroduciría la dualidad que el rediseño quitó y forzaría simétricos `BelowSMA`/etc. E7 apunta a composición config-driven (`direction→side` vía `SIDE_BY_DIRECTION`), así que `side` no se teclea a mano: la factory aportaba poco. El `name` sigue renderizando `AboveSMA(...)`/`BelowSMA(...)` como etiqueta legible. Reintroducir factory es trivial si E7 muestra fricción real.
- [x] **Ubicación del formateador de log** (`rules.py` vs `pipeline.py`): **RESUELTO (2026-06-18, T6): `core/pipeline.py`.** El log de embudo describe contadores del filtrado en cascada (un concepto del orquestador/E7), no el veredicto de una rule individual; ponerlo en `rules.py` mezclaría observabilidad del pipeline con la lógica de filtro pura. `pipeline.py` ya es donde vivirá su único caller (la cascada de E7) y el `ScanResult` (T7). `rules.py` se mantiene como L4 puro de filtros. Se creó `pipeline.py` en esta tarea (T7 le añade `ScanResult`).
