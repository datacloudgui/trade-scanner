# Bitácora — Segundo archivo de salida: medidas de todos los tickers evaluados

Diseño (sin implementar todavía). Feature **nuevo**, aún no asignado a una etapa de `PLAN.md`.
Fecha: 2026-06-21.

---

## Contexto

Tras la primera corrida real (semana del 2026-06-17), `latest.json` solo contiene los candidatos
que **pasaron** las reglas (la watchlist). El requerimiento: emitir un **segundo archivo, opcional y
configurable**, con las **medidas** (`sma_evidence`) de **todos los tickers evaluados** — hayan
pasado o no las reglas — para poder analizar por qué un ticker no entró a la watchlist.

El archivo actual (`results/<base>/<ts>.json|csv` + `latest.json`) queda **intacto**. El nuevo es
**aditivo** y está **off por defecto**.

---

## Cómo fluye hoy la salida (estado verificado)

Embudo en [pipeline.py:86-170](../../trade-scanner/core/pipeline.py):

1. **Gate** por warmup — excluye series frías (`is_ready`).
2. **Ranking** por `day_change_pct` → corte `top_n`.
3. **Snapshot + evaluación de TODAS las reglas** (sin short-circuit) — **solo para el `top_n`**.
   Aquí vive la lista `evaluated` ([pipeline.py:132-140](../../trade-scanner/core/pipeline.py)): cada
   entrada es `(sd, snapshot, results)` con `results: list[RuleResult]` (`.name`, `.passed`,
   `.required`). **Ya tiene snapshot completo + verdicto de cada regla por ticker.**
4. **Cascada** de reglas → solo `surviving`.
5. `ScanResult` **solo para sobrevivientes** → eso llega a `OutputSink` y se serializa.

**Clave del diseño:** el corte `top_n` ocurre **antes** del snapshot. Por eso las medidas SMA solo
existen para el `top_n` (prod: 50 de 200). Los tickers fuera del `top_n` nunca obtienen
`sma_evidence`.

---

## Decisiones de producto (respondidas por Guillermo, 2026-06-21)

| Eje | Decisión | Implicación |
|-----|----------|-------------|
| **Alcance** | Solo el `top_n` evaluado | El dato YA está en `evaluated`; cambio mínimo, no reordena el embudo. Los ~150 fuera del `top_n` NO estarán (documentar en log/archivo). |
| **Contenido** | Medidas + verdicto por regla | `sma_evidence` + `passed_rules` + `failed_rules` + `rules_passed_count` + `made_watchlist`. Todo derivable de `results`. |
| **Formato** | CSV + JSON | CSV plano (analítica/BigQuery) + JSON anidado (consistente con el actual). |
| **Flag** | Por entorno en `notifications.json` | `environments.<env>.emit_full_measures`. Coherente con el switch local/cloud que ya vive en `OutputSink`. |

---

## Decisiones de diseño

### D1 — Sin dataclass nuevo, sin tocar `ScanResult` (dict plano)

El primer borrador proponía un dataclass `EvaluatedSymbol` o agregar campos a `ScanResult`. **Ambos
descartados:**

- **Agregar campos a `ScanResult`** (`made_watchlist`, `failed_rules`): el serializer del archivo
  actual itera *todos* los campos del dataclass —
  `{f.name: getattr(result, f.name) for f in dataclasses.fields(result)}`
  ([output.py:58](../../trade-scanner/core/output.py)). Cualquier campo nuevo **aparecería en
  `latest.json`**, rompiendo "archivo actual intacto". ✗

- **Dataclass nuevo `EvaluatedSymbol`**: aísla el contrato pero agrega un tipo + su serialización +
  duplica datos ya calculados. Código de más. ✗

**Adoptado:** `output.py` **ya habla en `dict`** (los envelopes y `sections` son dicts, no
dataclasses). El set evaluado se expone como **lista de dicts planos**. Resultado:

- `ScanResult` **intacto** → `latest.json` byte-idéntico.
- Cero tipos nuevos.
- El retorno de `scan` **no cambia** (sigue devolviendo sobrevivientes) → los 10 call-sites en
  `test_pipeline.py` no se tocan.

### D2 — `scan` gana un out-param opcional, no un retorno nuevo

`scan(...)` recibe `evaluated_out: list | None = None`. Si se pasa, hace `append` de un dict por
ticker evaluado dentro del loop que ya existe. Si es `None` (default), comportamiento idéntico al
actual. Aditivo y retrocompatible.

Dict por ticker:
```python
{
  "ticker", "direction", "price", "sma_evidence",   # medidas (mismo snapshot, sin recompute)
  "passed_rules", "failed_rules", "rules_passed_count",
  "made_watchlist",                                  # True si el ticker quedó en `surviving`
}
```
`made_watchlist` se calcula con un `set` de tickers sobrevivientes (los demás campos salen de
`results` y `snapshot`, ya calculados).

### D3 — El flag se lee del envelope, sin plumbing nuevo de `env`

`_emit_file` no conoce `env` hoy, pero el envelope sí (`envelope["env"]`). El handler busca
`self._environments[env].get("emit_full_measures", False)`. Si está activo, escribe los archivos
extra; si no, no cambia nada. `emit(...)` recibe `measures` como **parámetro opcional** (default
`None`), igual patrón que `evaluated_out`.

### D4 — Nombres de archivo y aislamiento

Archivos nuevos junto a los actuales pero con sufijo propio, para no colisionar:
`results/<base>/<ts>.measures.json`, `results/<base>/<ts>.measures.csv`,
`results/<base>/measures-latest.json`. El puntero `latest.json` original no se toca.

### Invariantes de capa respetadas

- Todo sigue siendo **lectura** sobre `SymbolData`; **cero recompute** (las medidas salen del mismo
  snapshot único, D6B.7).
- El switch local/cloud sigue **solo** en `output.py`.
- `pipeline.py` y `output.py` siguen sin `AlgorithmImports` (negocio puro, testeable sin CLR).

---

## Cambios concretos (mínimos)

1. **`core/pipeline.py`** — `scan(...)` + param `evaluated_out: list | None = None`; dentro del loop
   sobre `evaluated`, append del dict plano (con `made_watchlist` vía set de sobrevivientes). Sin
   dataclass nuevo. Retorno sin cambios.

2. **`core/output.py`**
   - `serialize_measures_csv(measures)` → CSV plano: fila por ticker, columnas aplanadas por serie
     (`D_8_value`, `D_8_distance_pct`, `D_8_bucket`, …) + `passed_rules` / `failed_rules` /
     `made_watchlist`.
   - `serialize_measures_json(...)` → envelope JSON anidado análogo al actual.
   - `emit(...)` + param opcional `measures`; `_emit_file` escribe los `.measures.*` si
     `emit_full_measures` del entorno está activo.

3. **`main.py` `_scan_group`** — pasar `evaluated_out=[]` a cada `pipeline.scan(...)`, acumular por
   dirección, y pasar el dict resultante a `output.emit(...)`.

4. **`storage/config/notifications.json`** — `environments.prod.emit_full_measures: true` (y `dev`
   si se quiere). Ausente = `false` → opcional, off por defecto. Recordar que la fuente versionada
   vive en `config/` (el `storage/` es copia regenerable, gitignoreada).

5. **Tests** (`bash scripts/run_tests.sh`, dentro de la imagen LEAN):
   - `test_pipeline`: `evaluated_out` captura **todos** los `top_n` incl. los que fallan reglas, con
     `made_watchlist` correcto y `failed_rules` no vacío para los que no pasaron.
   - `test` de output: serializers nuevos (CSV plano + JSON); con flag **off** NO se escribe el
     archivo extra; `latest.json` sin cambios.

---

## Pendientes / preguntas abiertas

- **¿Formalizar como etapa en `PLAN.md`?** Guillermo eligió "solo el plan, sin codear" — falta
  decidir número de etapa y redactar el spec antes de implementar (flujo spec-driven).
- **Columnas exactas del CSV plano**: confirmar el orden y si se incluye `as_of`/`strategy`/`price`
  por fila (autocontenida) o solo en metadata.
- **`measures-latest.json` vs solo timestamped**: confirmar si el script host necesita un puntero
  fijo también para este archivo o basta con el timestamped.
