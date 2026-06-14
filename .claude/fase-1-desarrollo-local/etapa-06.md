# Etapa 6 — Features y Rules

**Estado:** completada (fundamentos) — **la aplicación de reglas se rediseñó en Etapa 6B**
**Depende de:** Etapa 5B (`core/symbol_data.py` con SMAs registradas + `is_ready` + `working_bar`; warmup integrado en `main.py`)
**Estimado:** 4–6 h (L3 + L4 aisladas, sin pipeline)
**Contexto:** primera capa de negocio puro. 5A/5B entregaron `SymbolData` caliente y validado. Aquí se construyen los cómputos de lectura (L3) y los predicados parametrizados con evidencia (L4) como unidades **aisladas y testeables a mano**, sin ensamblar el pipeline (Etapa 7) ni la salida (Etapa 8). Todo el umbralado vive en `config/strategies.json` (ObjectStore), nunca en código.

---

> ## ⚠️ Reorganización (2026-06-14) — ver [Etapa 6B](etapa-06b.md) y [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md)
>
> Esta etapa se **dividió**. Lo entregado y **conservado** queda aquí (T1, T2 — fundamentos de L3/L4). Lo entregado y **cambiado** (T3: `AboveSMA`/firma de `evaluate`) y lo **no realizado** (T4, T5, T6) se rediseñó o trasladó a **Etapa 6B**, bajo el ADR-005 (snapshot único + reglas como filtros puros, simétricas long/short).
>
> | Tarea original | Estado | Destino |
> |---|---|---|
> | T1 (`PositionResult`, `position_vs_sma`, `_bucketize`, `FeatureNotReady`) | ✅ hecho, **conservado** | se queda en E6 |
> | T2 (`bucket_thresholds`, `resolve_bucket_thresholds`) | ✅ hecho, **conservado** | se queda en E6 |
> | T3 (`AboveSMA`, `RuleResult`) | ✅ hecho, **DEPRECADO parcial** | `evaluate(snapshot)` + `SMAPositionRule` → 6B/T3 |
> | T4 (`NotExtended` con `max_pct`) | ❌ no hecho, **SUPERSEDED (D4)** | rediseñado sin `max_pct` → 6B/T4 |
> | T5 (formateador de log) | ❌ no hecho | portado sin cambios → 6B/T6 |
> | T6 (`ScanResult` campos) | ❌ no hecho | portado → 6B/T7 |
>
> Las secciones de T4/T5/T6 de abajo se eliminaron (su contenido vive en 6B). T3 y D4 quedan anotados como deprecados in situ.

---

## Decisiones de diseño

### D1 — `position_vs_sma` = función pura en `core/features.py` (Opción A)

Función sin estado `position_vs_sma(sd, tf, period, thresholds) -> PositionResult` en vez de clase `Feature`. Razón (una línea): una función pura es trivial de testear con `SymbolData` sintético, no introduce jerarquía que L3 no necesita, y hace explícito que solo lee estado — la extensibilidad futura (más features) se cubre con más funciones, no con una taxonomía de clases.

### D2 — Umbrales en `strategies.json`: sección global `bucket_thresholds` + override por estrategia (Opción A)

Los cortes (`near`, `mild`, `extended`) viven en una clave global `bucket_thresholds` dentro de `config/strategies.json`, con override opcional dentro del bloque de cada estrategia. Razón (una línea): es el mismo objeto ObjectStore ya versionado y portable local↔cloud — un segundo archivo (`thresholds.json`) duplica el seam de carga sin ganancia. Valores por defecto **placeholder** (calibración real en Etapa 9): `{near: 0.005, mild: 0.03, extended: 0.10}`.

```json
// config/strategies.json — añadir a nivel raíz (global)
"bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 }
// y, opcionalmente, dentro de un bloque de estrategia para override:
"swing_eod": { ..., "bucket_thresholds": { "extended": 0.08 } }
```

La resolución es **merge poco profundo**: el override de la estrategia reemplaza solo las claves presentes; las ausentes caen al global; el global ausente cae a los defaults del código.

### D3 — API real de `SymbolData` (corrección sobre el pre-spec) — accesor `close(tf)` a añadir en L2

La firma real es **`sd.sma(tf, period)`** (orden `tf, period`, NO `period, tf`) y **devuelve el objeto indicador de LEAN, no un float** → la feature lee `sd.sma(tf, period).current.value`. Además **`SymbolData` hoy NO expone `close(tf)`**. Para que L3 hable solo con `SymbolData` (regla de capas) y no alcance internals de LEAN, esta etapa añade un accesor de lectura mínimo en L2:

```python
def close(self, tf: str) -> float:
    """Cierre de la última barra consolidada del timeframe (lectura para L3)."""
    return self.consolidator(tf).consolidated.close
```

Es la única modificación permitida a L2 en esta etapa y es de pura lectura (no toca el wiring de consolidators/indicadores). La feature usa `sd.close(tf)` y `sd.sma(tf, period).current.value`; nunca alcanza `consolidator()` ni `.consolidated` por su cuenta.

### D4 — `NotExtended` = composición sobre `AboveSMA` (no subclase) — ⚠️ DEPRECADO (ADR-005)

> **DEPRECADO 2026-06-14 — superseded por [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) / [Etapa 6B](etapa-06b.md) D6B.6.** Lo **obsoleto:** el parámetro `max_pct` y su inyección como `thresholds["extended"]` por-regla (rompía "un solo set de buckets por estrategia"). Lo **conservado:** que `NotExtended` es composición (no subclase). En 6B, `NotExtended(period, tf, side)` es una factory de `SMAPositionRule` con `buckets_allowed = BUCKETS − {extended_above}` y **sin umbral propio**: el corte "extendido" es el `bucket_thresholds.extended` único de la estrategia. Texto original abajo (histórico).

`NotExtended(period, tf, max_pct)` delega en `AboveSMA(period, [tf], buckets_allowed=<todos menos extended_above>)`. Es la forma más simple: reutiliza la maquinaria de evidencia y el AND-sobre-tfs sin herencia, y mantiene `max_pct` como el `extended` efectivo de esa evaluación (se inyecta como override de `thresholds["extended"]` para esa rule). Razón (una línea): "no extendido" es exactamente "el bucket no es `extended_above`", así que es una restricción de `buckets_allowed`, no lógica nueva.

---

## Tareas

> `(FABLE xhigh)` en subtareas con semántica de buckets/fronteras o capas. Resto `high`; CSV/seed/commits `medium`.

### T1 — `PositionResult` + `position_vs_sma` (L3, núcleo de la feature)

- **T1.1 (FABLE xhigh)** — `PositionResult` (dataclass `frozen=True` en `core/features.py`): campos `value: float` (valor de la SMA usada), `distance_pct: float` (`(close - sma) / sma`), `side: str` (`"above"`/`"below"`, derivado del signo de `distance_pct`; `>= 0 → "above"`), `bucket: str`. Comparable por igualdad para asserts directos en tests.
- **T1.2 (FABLE xhigh)** — `position_vs_sma(sd, tf, period, thresholds) -> PositionResult`: lee `sma = sd.sma(tf, period).current.value` y `close = sd.close(tf)` (D3); calcula `distance_pct`; delega el bucket en `_bucketize`. **Contrato de fríos:** si `not sd.is_ready(tf, period)` o `sma == 0`, lanza `FeatureNotReady` (excepción tipada en `core/features.py`) — el manejo de fríos (exclusión del scan) es del pipeline en Etapa 7; aquí solo se define y lanza la excepción.
- **T1.3 (FABLE xhigh)** — `_bucketize(distance_pct, thresholds) -> str`: implementa la tabla de 7 buckets con los cortes `near < mild < extended` leídos de `thresholds`; sin números mágicos en el cuerpo. Lado `below` espeja a `above`.

Tabla (intervalos; `t = thresholds`):

| bucket | condición |
|---|---|
| `extended_above` | `distance_pct >= t.extended` |
| `above_strong` | `t.mild <= distance_pct < t.extended` |
| `above_mild` | `t.near <= distance_pct < t.mild` |
| `near` | `-t.near < distance_pct < t.near` |
| `below_mild` | `-t.mild < distance_pct <= -t.near` |
| `below_strong` | `-t.extended < distance_pct <= -t.mild` |
| `extended_below` | `distance_pct <= -t.extended` |

**Criterio de aceptación:** test parametrizado con `SymbolData` sintético (o stub mínimo con `.sma().current.value`/`.close()`/`.is_ready()`) que cubre los **7 buckets** y los **6 cortes exactos** (`+near`, `+mild`, `+extended` y sus negativos) verificando la inclusión/exclusión de la tabla (`>=` en extended/strong/mild-low, `<` en el límite superior); `distance_pct` con tolerancia `1e-9`; un segundo set de `thresholds` (ej. `extended=0.08`) mueve los cortes (demuestra no-hardcodeo). Un caso con SMA fría levanta `FeatureNotReady`.

### T2 — Carga y resolución de `bucket_thresholds` (config → código)

- **T2.1** — `config/strategies.json`: añadir `bucket_thresholds` global (D2). No tocar timeframes ni universos.
- **T2.2 (FABLE xhigh)** — `resolve_bucket_thresholds(full_config, strategy_name) -> dict` en `core/features.py`: merge poco profundo override-de-estrategia → global → defaults del código. Retorna `{near, mild, extended}` siempre completo y valida `0 < near < mild < extended` sobre el resultado (única puerta de control de orden; fuera del hot path `_bucketize`). El primer parámetro es el `strategies.json` parseado **completo** (objeto raíz), nombrado `full_config` para no colisionar con la variable local `strategies_config = full_config["strategies"]` de `main.py:37` — pasar ese sub-dict caería a defaults en silencio (no lanza). **Convención Etapa 7:** resolver una vez por estrategia en `initialize()` desde `full_config` y guardar el dict resuelto; el scan recibe los thresholds ya resueltos y nunca llama esta función.
- **T2.3** — `scripts/seed_object_store.sh` ya siembra `strategies.json`; verificar que el nuevo campo viaja a `storage/config/strategies.json` (sin cambio de script si el glob ya lo cubre).

**Criterio de aceptación:** test con `MockObjectStore`/dict que verifica las tres rutas — (a) solo global presente → usa global; (b) override de estrategia gana clave-a-clave sobre global; (c) ausencia total de `bucket_thresholds` → defaults `{0.005, 0.03, 0.10}`. El dict resuelto siempre trae las 3 claves. Un set desordenado (`near ≤ 0`, `near ≥ mild` o `mild ≥ extended`), incluido cuando lo provoca el override tras el merge, levanta `ValueError`.

### T3 — `AboveSMA` (L4) — ⚠️ DEPRECADO parcial (ADR-005)

> **DEPRECADO 2026-06-14 (firma/clase) — ver [Etapa 6B](etapa-06b.md) T3.** Lo entregado funciona, pero el **contrato cambia**: `evaluate(sd, thresholds)` → `evaluate(snapshot)` (la rule ya no recibe `sd` ni `thresholds`), y `AboveSMA` se generaliza a `SMAPositionRule` side-aware (largos/cortos por mirror). **Se conserva** la lógica de fondo: AND estricto sobre tfs, fail-fast de `buckets_allowed`, `RuleResult`, evidencia anidada. Los 8 tests de T3 se **migran** en 6B. Texto original abajo (histórico).

- **T3.1 (FABLE xhigh)** — `AboveSMA(period, tfs, buckets_allowed, required=True)` en `core/rules.py`. `evaluate(sd, thresholds) -> RuleResult`: para **todos** los `tf` en `tfs` evalúa `position_vs_sma(sd, tf, period, thresholds)`; **pasa si el bucket de cada tf ∈ buckets_allowed** (AND estricto). Valida `buckets_allowed` contra el set de 7 buckets conocido **en el constructor** (fail-fast si la config trae un bucket inexistente).
- **T3.2** — `RuleResult` (dataclass): `passed: bool`, `evidence: dict` con forma `{tf: {period: {value, distance_pct, bucket}}}`, `name: str` (ej. `AboveSMA(20,W+M)`), `required: bool`.

**Criterio de aceptación:** tests con `SymbolData` sintético multi-tf — (a) todos los tf en buckets permitidos → `passed=True`; (b) **un** tf fuera de rango → `passed=False` (verifica el AND, no el OR); (c) la estructura de `evidence` coincide exactamente con `{tf:{period:{value,distance_pct,bucket}}}` para todos los tf evaluados (también cuando falla). Construir con un `buckets_allowed` inválido lanza error.

### T4 / T5 / T6 — ➡️ Trasladadas a [Etapa 6B](etapa-06b.md)

> **Eliminadas de E6 (2026-06-14).** No se habían realizado; bajo [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) se rediseñan o portan a 6B:
> - **T4 — `NotExtended`:** rediseñada **sin `max_pct`** (factory de `SMAPositionRule`, excluye `extended_above`; corte = `bucket_thresholds.extended` único). → **6B/T4**.
> - **T5 — Formateador de log de filtrado:** portado sin cambios de diseño. → **6B/T6**.
> - **T6 — Campos de `ScanResult` (`rules_passed_count`, `sma_evidence`):** portado; `sma_evidence` ahora documentado como proyección del snapshot. → **6B/T7**. (La reconciliación `dist_pct→distance_pct`+`bucket` de §5 de PLAN.md **ya se aplicó** en E6.)

---

## Scope (lo efectivamente cerrado en E6 — T1 + T2)

✅ Entra: `core/features.py` (`PositionResult`, `position_vs_sma`, `_bucketize`, `FeatureNotReady`, `BUCKETS`, `DEFAULT_BUCKET_THRESHOLDS`, `resolve_bucket_thresholds`); accesor de lectura `SymbolData.close(tf)` (L2, solo lectura); `bucket_thresholds` en `strategies.json`; `core/rules.py` (`AboveSMA`, `RuleResult` — **firma de `evaluate` redefinida en 6B**); tests sintéticos de T1–T3.

➡️ Rediseñado/portado a **Etapa 6B**: snapshot único (`build_position_snapshot`), `mirror_buckets`, `SMAPositionRule`, `NotExtended` sin `max_pct`, `snapshot_evidence`, formateador de log, contrato de `ScanResult`, retiro de `max_extension_pct`.

❌ No entra (igual que antes):
- **Pipeline de filtrado en cascada / orquestación real** — Etapa 7.
- **`working_bar` / `partial_bar` / precio intradía en features** — Etapa 7 / Fase 2.
- **Ranking / `top_n` / `main_timeframe` / exclusión de fríos del scan** — Etapa 7 (aquí solo se define y lanza `FeatureNotReady`).
- **`OutputSink` / serialización CSV-JSON de `ScanResult`** — Etapa 8.
- **Calibración de umbrales** — placeholders ahora; Etapa 9.
- **Cualquier import de `QCAlgorithm` / `self.history` / datos** en L3/L4.

---

## Consideraciones técnicas específicas al stack

1. **`sma()` devuelve indicador, no float (D3):** leer siempre `sd.sma(tf, period).current.value`. La firma real es `sma(tf, period)` — orden invertido respecto al pre-spec; no confundir.
2. **`close(tf)` no existía:** se añade como accesor de lectura en `SymbolData` (`consolidator(tf).consolidated.close`). Es la única vía permitida para que L3 obtenga el cierre — la feature **no** debe llamar `consolidator()` ni tocar `.consolidated` directamente (rompería la regla "L3 solo habla con SymbolData").
3. **Fronteras de buckets:** definir los cortes una sola vez y derivar los 7 buckets; documentar qué borde es inclusivo (la tabla: `>=` en extended/strong y en el piso de mild; `<` en el techo de mild/near). Los tests de frontera exacta son el seguro contra off-by-epsilon.
4. **`buckets_allowed` validado en construcción:** fallar al construir la rule si trae un bucket inexistente, no en caliente durante el scan — evita errores silenciosos en runtime.
5. **Evidencia anidada `tf → period → {...}`** (no plana): soporta futuras rules multi-period sobre el mismo tf sin romper el esquema de `sma_evidence`.
6. **`FeatureNotReady` tipada:** el contrato de fríos se define aquí pero el manejo (exclusión + log) es de Etapa 7; los tests de esta etapa solo verifican que se lanza.
7. **Pureza de capa:** `core/features.py` y `core/rules.py` importables **sin CLR** — testeables con `SymbolData` real-sin-engine o stub mínimo. Cero `AlgorithmImports` salvo tipos si fueran imprescindibles (no deberían serlo en L3/L4).

---

## Done when (medible)

- [x] `position_vs_sma` clasifica los 7 buckets y los 6 cortes exactos; test de frontera verde con `thresholds` por defecto y con un segundo set (no-hardcodeo) — `bash scripts/run_tests.sh`. (2026-06-12: 82 passed; T1.1+T1.2+T1.3)
- [x] `resolve_bucket_thresholds` verifica las 3 rutas (global / override-estrategia / defaults) con mock. (2026-06-13: 95 passed; T2.2 — incl. validación `0 < near < mild < extended` y always-3-keys)
- [x] `AboveSMA` aplica AND sobre todos los `tf` y emite `evidence` `{tf:{period:{value,distance_pct,bucket}}}`; tests pasa/falla + `buckets_allowed` inválido verdes. (2026-06-13: 103 passed; T3 — 8 tests, `core/rules.py` puro) — ⚠️ firma `evaluate` redefinida en [Etapa 6B](etapa-06b.md).
- [x] §5 de PLAN.md reconciliada (`dist_pct`→`distance_pct` + `bucket`). (E6)
- [x] `core/features.py` y `core/rules.py` sin imports de `QCAlgorithm`/`self.history` (T1–T3). Commit `[Etapa 6] ...`.
- ➡️ `NotExtended`, formateador de log y campos de `ScanResult`: **trasladados a [Etapa 6B](etapa-06b.md)** (T4/T6/T7) bajo ADR-005.

---

## Preguntas abiertas (resueltas/trasladadas a Etapa 6B)

- [x] **Ubicación del dataclass `ScanResult`** — resuelto en 6B/T7: dataclass mínimo (solo contrato) en `core/pipeline.py`; lógica de llenado en Etapa 7.
- [ ] **`required=false` en V1** — sigue abierta; se trata a nivel rule en 6B y su efecto en cascada se ejercita en Etapa 7. ¿Alguna rule opcional planeada para V1, o queda como capacidad latente?
