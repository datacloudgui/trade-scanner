# Etapa 6 — Features y Rules

**Estado:** pendiente
**Depende de:** Etapa 5B (`core/symbol_data.py` con SMAs registradas + `is_ready` + `working_bar`; warmup integrado en `main.py`)
**Estimado:** 4–6 h (L3 + L4 aisladas, sin pipeline)
**Contexto:** primera capa de negocio puro. 5A/5B entregaron `SymbolData` caliente y validado. Aquí se construyen los cómputos de lectura (L3) y los predicados parametrizados con evidencia (L4) como unidades **aisladas y testeables a mano**, sin ensamblar el pipeline (Etapa 7) ni la salida (Etapa 8). Todo el umbralado vive en `config/strategies.json` (ObjectStore), nunca en código.

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

### D4 — `NotExtended` = composición sobre `AboveSMA` (no subclase)

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
- **T2.2 (FABLE xhigh)** — `resolve_bucket_thresholds(strategies_config, strategy_name) -> dict` (en `core/features.py` o helper de config): merge poco profundo override-de-estrategia → global → defaults del código. Retorna `{near, mild, extended}` siempre completo.
- **T2.3** — `scripts/seed_object_store.sh` ya siembra `strategies.json`; verificar que el nuevo campo viaja a `storage/config/strategies.json` (sin cambio de script si el glob ya lo cubre).

**Criterio de aceptación:** test con `MockObjectStore`/dict que verifica las tres rutas — (a) solo global presente → usa global; (b) override de estrategia gana clave-a-clave sobre global; (c) ausencia total de `bucket_thresholds` → defaults `{0.005, 0.03, 0.10}`. El dict resuelto siempre trae las 3 claves.

### T3 — `AboveSMA` (L4)

- **T3.1 (FABLE xhigh)** — `AboveSMA(period, tfs, buckets_allowed, required=True)` en `core/rules.py`. `evaluate(sd, thresholds) -> RuleResult`: para **todos** los `tf` en `tfs` evalúa `position_vs_sma(sd, tf, period, thresholds)`; **pasa si el bucket de cada tf ∈ buckets_allowed** (AND estricto). Valida `buckets_allowed` contra el set de 7 buckets conocido **en el constructor** (fail-fast si la config trae un bucket inexistente).
- **T3.2** — `RuleResult` (dataclass): `passed: bool`, `evidence: dict` con forma `{tf: {period: {value, distance_pct, bucket}}}`, `name: str` (ej. `AboveSMA(20,W+M)`), `required: bool`.

**Criterio de aceptación:** tests con `SymbolData` sintético multi-tf — (a) todos los tf en buckets permitidos → `passed=True`; (b) **un** tf fuera de rango → `passed=False` (verifica el AND, no el OR); (c) la estructura de `evidence` coincide exactamente con `{tf:{period:{value,distance_pct,bucket}}}` para todos los tf evaluados (también cuando falla). Construir con un `buckets_allowed` inválido lanza error.

### T4 — `NotExtended` (L4, composición sobre `AboveSMA`)

- **T4.1 (FABLE xhigh)** — `NotExtended(period, tf, max_pct, required=True)`: delega en `AboveSMA(period, [tf], buckets_allowed=<7 buckets menos extended_above>)`, inyectando `max_pct` como `thresholds["extended"]` efectivo de esa evaluación (D4). `name = NotExtended(8,D)`.

**Criterio de aceptación:** test — falla cuando `distance_pct >= max_pct` (bucket `extended_above`) y pasa en `above_strong` justo por debajo de `max_pct`; `evidence` con la misma forma que `AboveSMA`. Un caso con `max_pct` distinto del `extended` global demuestra que `max_pct` manda en esta rule.

### T5 — Formateador del log de filtrado (sin pipeline)

- **T5.1** — Función pura `format_filter_line(strategy, rule_name, n_in, n_out, kind) -> str` que produce `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)` y `format_final_line(strategy, n) -> str` → `[<strategy>] final: <n> candidatos`. `kind ∈ {"required","optional"}`. **No** ejecuta el filtrado (eso es Etapa 7); solo formatea contadores.

**Criterio de aceptación:** test que reproduce **literalmente** las líneas del ejemplo a partir de contadores:
```
[swing_eod] AboveSMA(20,W+M): 50 → 38 (−12 required)
[swing_eod] AboveSMA(20,D): 38 → 29 (−9 required)
[swing_eod] NotExtended(8,D): 29 → 22 (−7 required)
[swing_eod] final: 22 candidatos
```

### T6 — Extensión de `ScanResult` + esquema de evidencia (contrato)

- **T6.1** — Añadir a `ScanResult` (donde viva su definición; hoy solo en PLAN.md §5 — crear el dataclass si aún no existe, o anotar el contrato si su construcción es Etapa 7): `rules_passed_count: int = 0` y `sma_evidence: dict = field(default_factory=dict)` con forma `{tf: {period: {value, distance_pct, bucket}}}`.
- **T6.2** — Reconciliar §5 de PLAN.md: el ejemplo de `sma_evidence` usa la clave `dist_pct` y no incluye `bucket`. Esta etapa estandariza la clave en **`distance_pct`** y **añade `bucket`** (seguro: ningún consumidor existe aún — la serialización es Etapa 8). Actualizar el ejemplo de §5.

**Criterio de aceptación:** test de construcción que confirma los campos nuevos con sus defaults; nota en §5 de PLAN.md alineada con `{value, distance_pct, bucket}`. (La regla `required=false` que pasa suma a `rules_passed_count` sin filtrar — esto se verifica en el test unitario de la rule, no del pipeline, que es Etapa 7.)

---

## Scope

✅ Entra: `core/features.py` (`PositionResult`, `position_vs_sma`, `_bucketize`, `FeatureNotReady`, `resolve_bucket_thresholds`); accesor de lectura `SymbolData.close(tf)` (L2, solo lectura); `core/rules.py` (`AboveSMA`, `NotExtended`, `RuleResult`); formateador de log de filtrado; `bucket_thresholds` en `strategies.json`; campos nuevos de `ScanResult` + reconciliación de §5; tests sintéticos de cada feature/rule.

❌ No entra:
- **Pipeline de filtrado en cascada / orquestación real** — Etapa 7 (aquí solo el formateador de log y rules aisladas).
- **`working_bar` / `partial_bar` / precio intradía en features** — Etapa 7.
- **Ranking / `top_n` / `main_timeframe` / exclusión de fríos del scan** — Etapa 7 (aquí solo se define y lanza `FeatureNotReady`).
- **`OutputSink` / serialización CSV-JSON de `ScanResult`** — Etapa 8.
- **Otras rules** además de `AboveSMA` y `NotExtended`.
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

- [ ] `position_vs_sma` clasifica los 7 buckets y los 6 cortes exactos; test de frontera verde con `thresholds` por defecto y con un segundo set (no-hardcodeo) — `bash scripts/run_tests.sh`.
- [ ] `resolve_bucket_thresholds` verifica las 3 rutas (global / override-estrategia / defaults) con mock.
- [ ] `AboveSMA` aplica AND sobre todos los `tf` y emite `evidence` `{tf:{period:{value,distance_pct,bucket}}}`; tests pasa/falla + `buckets_allowed` inválido verdes.
- [ ] `NotExtended` reutiliza `AboveSMA`, corta en `max_pct`, evidencia coherente.
- [ ] Formateador reproduce **literalmente** las 4 líneas del ejemplo (incl. `final: N candidatos`).
- [ ] `core/features.py` y `core/rules.py` sin imports de `QCAlgorithm`/`self.history`; `ScanResult` con `rules_passed_count` + `sma_evidence`; §5 de PLAN.md reconciliada. Commit `[Etapa 6] ...`.

---

## Preguntas abiertas

- [ ] **Ubicación del dataclass `ScanResult`** — ¿se crea en `core/pipeline.py` ya en esta etapa (solo el contrato, sin lógica) o se difiere a Etapa 7 anotando los campos? Propuesta: crear el dataclass mínimo aquí para que las rules/tests lo referencien; la lógica de llenado es Etapa 7.
- [ ] **`required=false` en V1** — la config de referencia tiene las 3 rules `required=true`. El conteo `rules_passed_count` y el no-filtrado de opcionales se especifican y testean a nivel rule, pero su efecto en cascada se ejercita en Etapa 7. ¿Alguna rule opcional planeada para V1, o queda como capacidad latente?
