# ADR-005 — Snapshot único de posición precio↔SMA y reglas como filtros puros

**Estado:** aceptado (2026-06-14) — implementación en [Etapa 6B](../fase-1-desarrollo-local/etapa-06b.md)
**Fecha:** 2026-06-13 (propuesto) · 2026-06-14 (aceptado)
**Ámbito:** Etapa 6 (L3 features / L4 rules), preparación intradía (Fase 2+)
**Supersede a:** D4 de `etapa-06.md` (parcial — ver §"Conserva/Modifica/Elimina") y el override de umbral por-regla (`max_pct` de `NotExtended`).
**Relacionado:** [ADR-004](ADR-004-cadencia-evaluacion-intradia.md) (CUÁNDO se evalúa; este ADR es el QUÉ se calcula).

---

## 1. Contexto

Hoy cada rule llama `position_vs_sma(sd, tf, period, thresholds)` por cada `(tf, period)` dentro de su `evaluate`. Consecuencias del estado actual ([core/rules.py](../../trade-scanner/core/rules.py), [core/features.py](../../trade-scanner/core/features.py)):

- **Recomputación latente:** si dos rules comparten un `(tf, period)` (p. ej. `AboveSMA(20,D)` y otra regla sobre `D:20`), la distancia y el bucket se calculan dos veces. En V1 no se solapan, pero el contrato lo permite.
- **El umbral entra por rule, no por estrategia:** `NotExtended` (D4) inyecta `max_pct` como `thresholds["extended"]` propio → dos reglas de la misma estrategia pueden bucketizar con cortes distintos. Esto contradice la decisión ya tomada de **un solo set de buckets por estrategia**.
- **La rule tiene `sd` en la mano:** nada le impide re-medir o re-bucketizar; la pureza ("solo lee lo precalculado") es por convención, no estructural.

El rediseño hace **una sola evaluación** de posición por símbolo·scan, bucketiza **una vez** con el set resuelto de la estrategia, y convierte las rules en **filtros que solo leen** buckets ya asignados. Válido para largos y cortos sin duplicar reglas, y barato de reconstruir por barra de 2-min (intradía futuro).

**Decisiones de entrada (no se relitigan, se integran):**
- Un único set de `bucket_thresholds` por estrategia, compartido por todas sus rules. Se conserva `resolve_bucket_thresholds` (T2.2).
- Cadencia event-driven en cierre de barra del marco de decisión (ADR-004). Este ADR no toca el *trigger*.

---

## 2. Diseño final

### 2.1 Snapshot único (L3, `core/features.py`)

Estructura: **dict anidado plano** `{tf: {period: PositionResult}}` — misma forma que la evidencia, sin clase envolvente.

```python
def build_position_snapshot(
    sd: "SymbolData",
    series: Iterable[tuple[str, int]],
    thresholds: dict[str, float],
) -> dict[str, dict[int, PositionResult]]:
    """Posición precio↔SMA de un símbolo para cada (tf, period) en `series`, calculada
    una sola vez. Bucketiza con el set ya resuelto de la estrategia (D2/T2.2).

    `series` = unión de los (tf, period) que referencian las rules de la estrategia
    (NO todas las SMAs declaradas: ver §2.2). Frío: la primera serie con
    `FeatureNotReady` se propaga — el pipeline (Etapa 7) excluye el símbolo y loguea.
    """
```

- Reutiliza `position_vs_sma` tal cual como primitivo per-serie (loop fino sobre él): conserva el contrato de fríos, la normalización `float()` en la frontera L2→L3 y `_bucketize`.
- **Quién lo construye:** el pipeline (L4, Etapa 7), una vez por `(símbolo, estrategia, scan)`, antes de evaluar ninguna rule.
- **Costo:** `|series|` lecturas O(1) (`sma.current.value` + `close` + resta/división + cascada de bucket). Para 200 símbolos × ~7 series = ~1400 ops O(1) por scan. Trivial; reconstruible por barra (§7).

### 2.2 `series` = lo que las rules referencian, no lo declarado

El snapshot cubre **la unión de `(tf, period)` que usan las rules de la estrategia**, no todo `sd.declared` (que es la unión de *todas* las estrategias que comparten el símbolo). Razón doble:

1. **No malgastar:** una estrategia que declara `M:[8,20,200]` pero cuyas rules solo miran `M:20` no debe computar `M:8`/`M:200`.
2. **No sobre-excluir por frío:** si `M:200` está fría pero ninguna rule la usa, el símbolo no debe quedar fuera del scan. Construir solo lo referenciado acota la propagación de `FeatureNotReady` a lo que de verdad importa.

Esta unión se resuelve **una vez en `initialize()`** (junto a los thresholds), no por scan.

### 2.3 Firma de `Rule.evaluate` — el cambio de contrato central

```python
# Antes:  def evaluate(self, sd, thresholds) -> RuleResult
# Ahora:  def evaluate(self, snapshot) -> RuleResult
```

La rule **pierde el acceso a `sd` y a `thresholds`**. Estructuralmente ya no puede re-medir (no tiene `SymbolData`) ni re-bucketizar (no tiene cortes): solo lee `snapshot[tf][period].bucket`. La pureza pasa de convención a invariante de tipo.

### 2.4 Evidencia como proyección del snapshot

```python
def snapshot_evidence(
    snapshot: dict[str, dict[int, PositionResult]],
    series: Iterable[tuple[str, int]],
) -> dict:
    """Proyecta el snapshot al esquema de evidencia {tf:{period:{value,distance_pct,bucket}}}.
    Pura proyección — cero recompute."""
```

- `RuleResult.evidence` = proyección sobre las series de *esa* rule (se conserva el contrato T3, útil para "por qué falló esta rule").
- `ScanResult.sma_evidence` = proyección sobre la **unión** de series (Etapa 8). Ambas salen del mismo snapshot; ninguna recomputa.

---

## 3. Modelo long/short (simétrico, declarativo desde `direction`)

`PositionResult` ya es simétrico: `distance_pct` con signo, `side` derivado, y los 7 buckets espejan around `near`. La dirección **no entra en el cálculo** — entra solo en el **filtro** (qué buckets son "buenos").

**Opción elegida (la más simple): vocabulario canónico "above" + mirror en construcción.**

Las rules se autoran en vocabulario **largo/above** (canónico). `direction` → `side` (`long→"above"`, `short→"below"`) aplica `mirror_buckets` **una sola vez al construir la rule**. El `evaluate` resultante es **byte-idéntico** para largo y corto: solo cambia el set concreto de buckets permitidos.

```python
_MIRROR = {
    "extended_above": "extended_below",
    "above_strong":   "below_strong",
    "above_mild":     "below_mild",
    "near":           "near",            # autoespejo
    "below_mild":     "above_mild",
    "below_strong":   "above_strong",
    "extended_below": "extended_above",
}

def mirror_buckets(buckets: Iterable[str], side: str) -> frozenset[str]:
    """side=='above' → identidad; side=='below' → espejo. Biyección sobre los 7 buckets,
    así el resultado siempre ⊆ BUCKETS sin re-validar."""
```

Como `mirror_buckets` es biyección sobre los 7, funciona para cualquier subconjunto:
- `AboveSMA`: canónico `{above_mild, above_strong, extended_above}` → short `{below_mild, below_strong, extended_below}`.
- `NotExtended`: canónico `BUCKETS − {extended_above}` → short `BUCKETS − {extended_below}`.

**Descartado:** un parámetro `side` que la rule interprete en caliente (mete una rama por lado en el hot path), y duplicar `AboveSMA`/`BelowSMA` (la consigna pide simetría *sin* duplicar). El mirror-en-construcción no añade ramas al scan y mantiene una sola clase.

---

## 4. Reglas como filtros puros

Una sola clase genérica reemplaza `AboveSMA` y sirve de base a `NotExtended`:

```python
class SMAPositionRule:
    """Pasa si el bucket de CADA tf en `tfs` ∈ buckets_allowed (AND estricto)."""
    def __init__(self, period, tfs, buckets_allowed, side, required=True, label="SMA"):
        # 1) valida buckets_allowed canónicos ⊆ BUCKETS (fail-fast, como hoy T3)
        # 2) self.buckets_allowed = mirror_buckets(buckets_allowed, side)   # 1 vez
        ...
    @property
    def name(self) -> str:
        # label + side → "AboveSMA(20,W+M)" | "BelowSMA(20,W+M)" | "NotExtended(8,D)"
    def evaluate(self, snapshot) -> RuleResult:
        # for tf in self.tfs: pos = snapshot[tf][self.period]
        #   passed AND= pos.bucket in self.buckets_allowed
        # evidence = snapshot_evidence(snapshot, [(tf, self.period) for tf in self.tfs])
```

- **`AboveSMA`** queda como un caso de `SMAPositionRule` (`label="SMA"`, render `AboveSMA`/`BelowSMA` por `side`).
- **`NotExtended`** = **factory** que construye `SMAPositionRule(period, [tf], buckets_allowed=BUCKETS − {extended_above}, side, label="NotExtended")`. **Sin `max_pct`, sin threshold propio.** "No extendido" = "el bucket favorable-extremo está excluido"; el corte que define "extremo" es `bucket_thresholds.extended` de la estrategia (ya aplicado al bucketizar el snapshot). Esto es exactamente la propuesta 2 del rediseño ("excluir los buckets más alejados, no recalcular con otro umbral") y **supersede D4**.
- **Futuras rules** se expresan igual: un subconjunto canónico de buckets + el mirror. Sin recompute, sin `sd`.

`buckets_allowed` (qué buckets acepta una rule) **no es un threshold** — es composición de la rule, y se mantiene per-rule. Lo que se elimina es el override de *valores de corte* (`near/mild/extended`) por rule.

---

## 5. Tabla de análisis de cambios

| Cambio propuesto | ¿Merece? | Por qué | Impacto (archivos/tests) |
|---|---|---|---|
| Snapshot único `{tf:{period:PositionResult}}` 1×/símbolo·scan | **Sí** | Elimina recompute cuando ≥2 rules comparten `(tf,period)`; centraliza el seam de fríos en un punto en vez de disperso por rule | +`build_position_snapshot` en `features.py`; el pipeline (E7) lo construye. +tests de builder |
| `evaluate(snapshot)` en vez de `evaluate(sd, thresholds)` | **Sí** | Hace **estructuralmente imposible** re-medir/re-bucketizar (la rule ya no tiene `sd` ni cortes) | `rules.py` firma; migrar los 8 tests T3 (construir snapshot del stub y pasarlo) |
| Generalizar `AboveSMA` a `SMAPositionRule` side-aware con mirror en construcción | **Sí** | Simetría long/short sin duplicar reglas; `evaluate` idéntico ambos lados; cero ramas en hot path | rename de clase en `rules.py`; tests T3 añaden `side="above"` |
| `NotExtended` = factory que excluye bucket favorable-extremo, **sin `max_pct`** | **Sí** (supersede D4) | Unifica bajo el filtro genérico; elimina el override de umbral por-regla; "no extendido" = exclusión de bucket | T4 se implementa así (aún no escrito → sin migración, solo nueva forma) |
| Eliminar `max_extension_pct` de `strategies.json` | **Sí** | Redundante con `bucket_thresholds.extended` (hoy ambos = 0.10); el corte "extendido" es único y compartido | −1 línea × 4 estrategias en `config/strategies.json`; ningún consumidor aún |
| `mirror_buckets(side)` + mapa `_MIRROR` | **Sí** | Una función concentra toda la simetría; biyección ⇒ no re-valida | +pequeña en `features.py`; +test de simetría (near autoespejo, doble-mirror = identidad) |
| `series` del snapshot = referenciadas por rules, no `sd.declared` | **Sí** | Evita computar SMAs que ninguna rule usa y evita sobre-excluir por frío en ellas | el builder recibe `series` explícito; se resuelve 1× en `initialize()` |
| Evidencia per-rule = proyección del snapshot | **Sí** | Mantiene el contrato `RuleResult` (T3) con cero recompute | `rules.py` usa `snapshot_evidence` |
| Wrapper `PositionSnapshot` (clase) vs dict plano | **No** | El dict anidado basta y es la misma forma que la evidencia; un wrapper añade ceremonia. La validación `series ⊆ declared` va al pipeline (config-time, fail-fast), no al hot path | Se recomienda **dict plano**; sin archivo nuevo |
| Compartir un snapshot entre estrategias del mismo símbolo | **No** (en V1) | Requiere `thresholds` + `series` idénticos; en V1 long/short usan universos disjuntos (`swing_advances` vs `swing_declines`) → sin solape de símbolos. Optimización prematura | Ninguno ahora; nota para Fase 2 |
| Pasar `direction`/`side` por rule en caliente | **No** | Mete una rama por lado en el scan; el mirror-en-construcción lo evita | — |

---

## 6. Conserva / Modifica / Elimina (por componente)

**Conserva tal cual (sin tocar):**
- `PositionResult` (frozen, `side` derivado) — ya simétrico, sirve a ambos lados sin cambios.
- `_bucketize` + tabla de 7 buckets + invariante de frontera (T1.3).
- `position_vs_sma` — primitivo per-serie; el builder lo envuelve en un loop.
- `FeatureNotReady` — contrato de fríos (ahora aflora en el builder, un solo punto).
- `resolve_bucket_thresholds` (T2.2), `BUCKETS`, `DEFAULT_BUCKET_THRESHOLDS`.
- `RuleResult` (campos `passed/evidence/name/required`; no-frozen por D-T3.4).
- Plan de `ScanResult` (T6: `rules_passed_count`, `sma_evidence`) — sigue válido sin cambios.

**Modifica:**
- `AboveSMA` → `SMAPositionRule` genérica side-aware; firma `evaluate(snapshot)`.
- Evidencia: proyección del snapshot (`snapshot_evidence`), ya no recompute vía `position_vs_sma`.
- `config/strategies.json`: quita `max_extension_pct`; `direction` (ya presente) pasa a gobernar el mirror.

**Añade:**
- `build_position_snapshot` (L3).
- `mirror_buckets` + `_MIRROR` (L3).
- `snapshot_evidence` (L3).

**Elimina:**
- `NotExtended` como **clase con `max_pct`** (D4) → factory sin threshold.
- `max_extension_pct` de la config.
- El concepto de **override de umbral por-regla** (D4 queda obsoleto en esa parte).

### Qué de D4 queda obsoleto (explícito)

D4 decía: *"`NotExtended(period, tf, max_pct)` … mantiene `max_pct` como el `extended` efectivo de esa evaluación (se inyecta como override de `thresholds["extended"]` para esa rule)."*
→ **Obsoleto:** el parámetro `max_pct` y la inyección de `thresholds["extended"]` por-regla. **Se conserva** de D4 la idea de que `NotExtended` es *composición* sobre el filtro de buckets (no subclase) — solo que ahora sin umbral propio: excluye el bucket favorable-extremo, cuyo corte es el `extended` único de la estrategia.

---

## 7. Impacto en V1 (swing/EOD) y migración de tests

**Equivalencia observable — sí, con una condición que hoy se cumple:**

| Aspecto | Antes | Después | ¿Equivalente? |
|---|---|---|---|
| Corte de `NotExtended(8,D)` | `max_extension_pct=0.10` | `bucket_thresholds.extended=0.10` (excluye `extended_above` ≥ 0.10) | **Sí** — mismo corte 0.10 |
| Filtrado de `AboveSMA` | `buckets_allowed` | igual `buckets_allowed` (canónico) | **Sí** |
| Esquema de `evidence` | `{value,distance_pct,bucket}` | idéntico (proyección) | **Sí** |
| `ScanResult` | `rules_passed_count` + `sma_evidence` | sin cambios | **Sí** |

⚠️ **Condición:** la equivalencia se sostiene porque en la config actual `max_extension_pct == bucket_thresholds.extended` (ambos 0.10) en las 4 estrategias. Si alguna tuviera `max_extension_pct ≠ extended`, unificarlos **sería** un cambio semántico que requeriría decisión explícita. **Ninguna lo tiene** → migración limpia.

**Migración de tests:**
- **T3 (`AboveSMA`, 8 tests):** cambio mecánico — construir el snapshot desde el stub (`build_position_snapshot(stub, series, thresholds)`) y llamar `evaluate(snapshot)` en vez de `evaluate(sd, thresholds)`; añadir `side="above"`. El stub multi-tf de `test_rules.py` (D-T3.5) sirve igual.
- **T4 (`NotExtended`):** aún no escrito → se implementa directamente contra la factory nueva (sin `max_pct`). El criterio de aceptación de T4 cambia: "falla en `extended_above`, pasa en `above_strong`" sigue válido, pero el "caso con `max_pct` distinto del global" **se elimina** (ya no existe `max_pct`); se reemplaza por "un segundo `bucket_thresholds.extended` mueve el corte de NotExtended" (demuestra que el único umbral manda).
- **Tests nuevos:** `build_position_snapshot` (cálculo único, propagación de frío, `series` ⊊ declared no sobre-excluye), `mirror_buckets` (near autoespejo, doble-mirror = identidad), rule short (el mirror produce los buckets `below_*` correctos), `snapshot_evidence` (proyección exacta).

**Done-when de Etapa 6 afectados:** la línea de `NotExtended` y la de "AboveSMA/NotExtended con evidencia" se reinterpretan bajo este diseño; el formateador de log (T5) y `ScanResult` (T6) no cambian.

---

## 8. Preparación intradía (2-min, Fase 2+) — confirma que escala

El diseño **no se rediseña** para intradía; escala por construcción:

- **Costo por barra:** reconstruir el snapshot es `|series|` lecturas O(1). Aun con 200 símbolos × ~7 series por cierre de barra de 2-min (~195 barras/día regular), el cuello no es CPU (coincide con ADR-004 §"Costo"). El snapshot se reconstruye fresco en cada trigger (las SMAs solo cambian al cierre de barra de todos modos).
- **`evaluate(snapshot)` no cambia:** mismas rules, mismos filtros; solo habrá más `series` y posiblemente un snapshot que lea la barra en curso.

**Pendiente para activarlo (NO ahora, fuera de alcance):**
1. **Variante "precio vivo":** un `build_position_snapshot(..., use_working_bar=True)` o un `position_vs_sma_live` que lea `working_bar` en vez de la barra cerrada (ADR-004 §2). El builder actual lee la barra consolidada cerrada — correcto para swing.
2. **Timeframes intradía en L2:** `SymbolData` hoy solo soporta la cadena daily→W/M (lanza para `source_resolution != "daily"`, ver [symbol_data.py:38](../../trade-scanner/core/symbol_data.py#L38)). Añadir consolidators 1/5/15-min es el bloqueante real — **no las rules**.
3. **Trigger en L5:** handler del consolidator del marco de decisión (ya cubierto por ADR-004).

Las rules y el snapshot quedan listos; lo intradía es L2 (timeframes) + L5 (trigger) + una feature que lea la barra parcial.

---

## 9. Riesgos y decisiones abiertas

1. **Dónde vive la composición de rules** (lista de rules + `buckets_allowed` por rule por estrategia): ¿bloque en `strategies.json` o módulo declarativo en `strategies/`? Este ADR no lo fija (es Etapa 7), pero exige que **el `direction`→`side` se resuelva en un solo punto central** (el pipeline en `initialize()`), no esparcido. Recomendación: módulo `strategies/` que lee `direction` de config.
2. **Inclusión de `near` en `AboveSMA`:** ¿"above" incluye el bucket `near` (banda ±near alrededor de la SMA) o exige estar estrictamente por encima? Es parámetro de composición (`buckets_allowed`) — decidir en Etapa 7 / calibrar en Etapa 9. No afecta a este diseño.
3. **Rename de clase `AboveSMA` → `SMAPositionRule`:** churn en los 8 tests T3. Alternativa de menor cambio: conservar el nombre `AboveSMA` como clase y solo añadir `side` + render `BelowSMA` en `name`. Recomendación: renombrar (la clase ya no es "above"), pero es reversible si se prefiere minimizar diff.
4. **Snapshot per (símbolo, estrategia) vs per símbolo:** lógicamente per-estrategia (thresholds/series pueden diferir). "Una evaluación por símbolo y scan" se cumple *dentro* de una estrategia. Compartir entre estrategias es optimización futura gateada en `(thresholds, series)` idénticos — innecesaria en V1 (universos disjuntos).

---

## 10. Decisión (aprobada 2026-06-14)

Aprobado en bloque; se implementa en [Etapa 6B](../fase-1-desarrollo-local/etapa-06b.md):
- [x] Snapshot único `{tf:{period:PositionResult}}` + `build_position_snapshot` (L3). → 6B/T1
- [x] `evaluate(snapshot)` (rules sin `sd` ni `thresholds`). → 6B/T3
- [x] `SMAPositionRule` genérica + `mirror_buckets` (long/short canónico-above). → 6B/T2,T3
- [x] `NotExtended` sin `max_pct` (excluye bucket favorable-extremo) — **supersede D4**. → 6B/T4
- [x] Eliminar `max_extension_pct` de `config/strategies.json`. → 6B/T5
- [x] **Rename aprobado** `AboveSMA`→`SMAPositionRule` (conservando `AboveSMA` como factory `side="above"`, decisión final en 6B/T3.2). Ubicación de la composición de rules → Etapa 7.
