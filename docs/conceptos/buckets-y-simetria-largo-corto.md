# Buckets, filtros y simetría largo/corto

**Tipo:** explicación (modelo mental). No es un how-to ni un ADR — para *decisiones* ver
[ADR-005](../../.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).
**Código:** `core/features.py` (`BUCKETS`, `_bucketize`, `mirror_buckets`, `_MIRROR`,
`SIDE_BY_DIRECTION`, `resolve_bucket_thresholds`, `DEFAULT_BUCKET_THRESHOLDS`),
`core/rules.py` (`SMAPositionRule`).
**Config:** `config/strategies.json` → `storage/config/strategies.json` (ObjectStore).
**Spec:** `.claude/fase-1-desarrollo-local/etapa-06b.md` (D6B.1, D6B.4).

Este documento aclara una confusión natural: en el screener hay **dos cosas distintas** que
ambas se llaman "buckets", y la simetría largo/corto opera sobre una, no sobre la otra.
Entenderlo explica por qué `mirror_buckets` se prueba de forma exhaustiva.

---

## La escalera de los 7 buckets

La posición del precio respecto a una SMA se clasifica en una de 7 categorías ordenadas, de más
arriba a más abajo de la media (`core/features.py: BUCKETS`):

```
        extended_above     ← muy por encima de la SMA (≥ corte "extended")
        above_strong
        above_mild
  SMA → near               ← pegado a la media (autoespejo)
        below_mild
        below_strong
        extended_below     ← muy por debajo de la SMA
```

Los cortes (`near < mild < extended`) salen de `bucket_thresholds` de la estrategia
(`resolve_bucket_thresholds`), y `_bucketize(distance_pct, thresholds)` asigna el bucket a partir
de la distancia relativa `(close - sma) / sma`.

---

## Dónde se configuran los límites (thresholds)

Los límites de los buckets son los 3 cortes `near < mild < extended`. Se resuelven con
**precedencia de 3 niveles** (override de estrategia > global > defaults del código):

**1. Global — `config/strategies.json` (raíz del objeto):**
```json
"bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 }
```
Es la fuente versionada. `seed_object_store.sh` lo copia a `storage/config/strategies.json`, que el
algoritmo lee en runtime vía `self.object_store` (ObjectStore). **Nunca** con `open()` ni hardcodeado.

**2. Override por estrategia (opcional) — mismo archivo:**
```
strategies.<nombre>.bucket_thresholds   # gana CLAVE POR CLAVE sobre el global (merge poco profundo)
```
Hoy ninguna de las 4 estrategias define override.

**3. Defaults del código (última red) — `core/features.py`:**
```python
DEFAULT_BUCKET_THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}
```
Solo aplican si una clave falta tanto en el override como en el global.

La resolución vive en `resolve_bucket_thresholds(full_config, strategy_name)`: aplica la precedencia,
devuelve siempre las 3 claves y valida `0 < near < mild < extended` (único punto de control — no el
hot path `_bucketize`). El dict resuelto viaja a `build_position_snapshot → position_vs_sma → _bucketize`.

> **Convenciones.** Son **fracciones, no porcentajes** (`0.10` = 10%, no `10`). Los valores actuales
> son **placeholders**; la calibración real es **Etapa 9**. No confundir con `max_extension_pct` (clave
> redundante retirada en 6B/T5, D6B.8): el corte "extendido" único es `bucket_thresholds.extended`.

---

## Las dos cosas que se llaman "bucket"

### 1. La posición de la acción = UN bucket

Para un `(timeframe, period)` concreto, una acción cae en **exactamente un** bucket. Es el campo
`PositionResult.bucket` que guarda el snapshot:

```
AAPL, W, SMA20 → cierre +5% sobre la media → distance_pct = 0.05 → bucket = "above_strong"
```

No es un conjunto. Es un valor único por serie.

### 2. El filtro de la regla = un SUBCONJUNTO de buckets

`buckets_allowed` es **qué buckets considera aceptables una regla**. *Eso* sí es un subconjunto de
los 7, y lo decide quien compone la estrategia (Etapa 7) o la calibra (Etapa 9). Ejemplos:

```
AboveSMA estricto    → {above_mild, above_strong, extended_above}        (3 de 7)
AboveSMA con banda   → {near, above_mild, above_strong, extended_above}  (4 de 7)
NotExtended          → BUCKETS − {extended_above}                        (6 de 7)
```

La evaluación de una regla es simplemente: *¿el único bucket de la acción está dentro del
subconjunto permitido?*

```python
passed = snapshot[tf][period].bucket in self.buckets_allowed
#            └── UN bucket (la acción) ──┘    └── SUBCONJUNTO (la regla) ──┘
```

---

## La simetría largo/corto: el espejo actúa sobre el FILTRO

Una regla se escribe **una sola vez**, en vocabulario canónico "above" (largo). Para usarla en
corto no se duplica: `mirror_buckets(buckets_allowed, side)` traduce el **filtro** al lado pedido,
una vez, en construcción (D6B.4). `_MIRROR` es el espejo `above_* ↔ below_*` con `near` autoespejo.

**Largo** — `AboveSMA(20, [W])`, `side="above"` → espejo = identidad:

```
buckets_allowed = {above_mild, above_strong, extended_above}
AAPL bucket "above_strong" ∈ permitido  → PASA ✅
```

**Corto** — la *misma* regla canónica, `side="below"`:

```
mirror_buckets({above_mild, above_strong, extended_above}, "below")
    = {below_mild, below_strong, extended_below}

TSLA cotiza −5% bajo su SMA20 → bucket "below_strong" ∈ permitido  → PASA ✅ (corto válido)
una acción por encima de su media → "above_strong" ∉ {below_*}     → NO PASA ✅
```

> El espejo transforma el **conjunto permitido de la regla**, no el bucket de la acción. La acción
> siempre tiene un solo bucket; lo que cambia entre largo y corto es contra qué conjunto se compara.

`SIDE_BY_DIRECTION = {"long": "above", "short": "below"}` es la única fuente de la traducción
`direction → side` que lee la config (su uso real es de Etapa 7).

---

## Por qué `mirror_buckets` se prueba con los 128 subconjuntos

`buckets_allowed` es un **parámetro libre**: aún no sabemos qué subconjuntos usarán las estrategias
futuras (composición en Etapa 7, calibración en Etapa 9 — incluido si `near` entra o no en la
banda). El espejo debe ser correcto para **cualquier filtro posible**, no solo los 2-3 de hoy.

El conjunto potencia de 7 elementos tiene **2⁷ = 128** subconjuntos (cada bucket *está* o *no está*;
7 decisiones binarias; incluye el vacío y el total). El test recorre los 128 × 2 lados y verifica:

- **identidad** en `"above"` (no toca el filtro canónico),
- **involución**: espejar dos veces devuelve el original (`below ∘ below = id`) → traducir
  largo↔corto es reversible y limpio,
- **cierre**: el filtro espejado siempre queda ⊆ `BUCKETS` → la regla nunca termina con un bucket
  imposible que ningún snapshot podría igualar.

Bugs típicos —*"optimicé el espejo a un `if` y olvidé `near`"*, o un espejo no biyectivo que saca un
bucket fuera de la escalera— **solo se manifiestan en ciertos subconjuntos**. Probar el espacio
completo (barato: 128×2 casos en milisegundos) los blinda contra refactors futuros.

---

## Resumen en una frase

> La acción cae en **un** bucket; la regla permite un **conjunto** de buckets; el espejo transforma
> ese conjunto para reusar la misma regla en corto. Como el conjunto puede ser cualquiera de los
> 128, lo verificamos entero.
