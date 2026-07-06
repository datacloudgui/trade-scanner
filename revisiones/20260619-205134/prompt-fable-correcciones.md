# Prompt para Fable — Correcciones triaje E1–E8

**Generado:** 2026-07-05 · **Rama:** `feature/etapa-6-features-rules`
**Entrada:** `revisiones/20260619-205134/triaje-E1-E8.md` (26 hallazgos consolidados, 20 VIGENTE)

---

/goal Corregir los 20 hallazgos VIGENTE del triaje Codex E1–E8 en orden de criticidad, validando tests en cada paso.

## Contexto

Estás en el workspace de un screener multi-estrategia sobre LEAN (QuantConnect, Python 3.11).
- CLAUDE.md = reglas duras del proyecto (restricciones de capas, cero órdenes, portabilidad local↔cloud, no resampling manual).
- PLAN.md > SPECS.md > CLAUDE.md en caso de conflicto.
- Los tests corren SOLO dentro de Docker: `bash scripts/run_tests.sh`. Nunca ejecutes `pytest` directamente.

## Triaje ya completado

El archivo `revisiones/20260619-205134/triaje-E1-E8.md` contiene 26 hallazgos del análisis Codex ya clasificados y verificados contra el código actual. Lee ese archivo completo primero.

**NO TOCAR** (6 hallazgos):
- #1, #3 → YA CORREGIDO en código actual
- #4, #26 → DECISIÓN CONSCIENTE (diseño intencional)
- #5, #10 → solo documentar la decisión con una nota en el archivo correspondiente

**SEPARAR para discusión** (no implementar en este ciclo):
- #12 → "Requiere decisión de diseño / posible ADR nuevo" (cruce de universos entre estrategias). Propón el diseño en texto antes de escribir código y detente; no implementes sin aprobación.

## Paso 1 — Re-validación rápida (antes de tocar código)

Para cada uno de los 20 hallazgos VIGENTE (#2, #6, #7, #8, #9, #11, #13, #14, #15, #16, #17, #18, #19, #20, #21, #22, #23, #24, #25 + nota de #12):

1. Lee el archivo:línea que cita el triaje.
2. Confirma si la condición sigue presente en el código actual.
3. Si fue corregido desde el triaje (2026-06-20): márcalo y saltea.

Produce una tabla corta de validación antes de continuar.

## Paso 2 — Implementación por grupos de criticidad

Ejecuta en este orden. Después de cada grupo: corre `bash scripts/run_tests.sh` y no avances si hay fallos.

**Grupo A — ALTO (corrompen el universo o la persistencia):**
- #7: `scripts/seed_object_store.sh` — corregir selección de CSV más reciente (parsear fecha `MM-DD-YYYY` → `YYYYMMDD` para ordenar; añadir test con `12-31-2025` vs `01-02-2026`)
- #21: `core/output.py` — persistir el archivo incondicionalmente (fuera de la lista de canales `["file"]`)
- #20: `main.py`/`core/pipeline.py` — validar en `initialize()` que las series referenciadas por rules ⊆ `plan.included`; fallar con `ValueError` claro, no `KeyError` en runtime
- #2: `README.md` — reescribir Setup/Config/Universo/Salida al contrato real de E2–E8; eliminar instrucciones de `lean init`/`lean login` y referencias a claves Alpaca en `lean.json`

**Grupo B — MEDIO (robustez y guards):**
- #11: `core/universe.py` — guardrail `min(max_tickers, 200)` o validación en `__init__`
- #18: `core/rules.py` — `if not tfs: raise ValueError` en constructor de `SMAPositionRule` + test
- #19: `core/features.py` — validar mapping, castear a `float`, rechazar bool/NaN/inf en `resolve_bucket_thresholds` + tests
- #17: `scripts/seed_sample_data.sh` — corregir incoherencia fuente↔factor (zips LEAN vs factores neutros)
- #8: `scripts/explore_universe.py` — detectar footer por patrón Barchart; reportar el resto como no estándar

**Grupo C — BAJO (tests, doc, config):**
- #14: `tests/test_universe.py` — añadir test de tope absoluto 200 y alias map completo
- #25: `tests/test_pipeline.py` — test L5 con ObjectStore mock y universos long/short disjuntos
- #24: `tests/test_output.py` — test del wiring `notification_groups` → schedule → `_scan_group` → exactamente un `emit`
- #6: tests — test unitario de `_time_rule_for` (mapeo schedule→time-rule)
- #22: `core/output.py` — comprobar retorno de `save`/`email`; loguear error si `False`
- #23: `config/notifications.json` — añadir env `cloud` con `["file","qc_notify"]` o documentar el cambio
- #13: `core/universe.py` — envolver errores de `df.query` con contexto; nota sobre columnas requeridas
- #9: `scripts/explore_universe.py` — aplicar guard `if valid:` a columnas `PERCENT`
- #15/#16: `tests/` — fixtures mínimos versionados o preflight que falle si faltan los datos de E5

## Restricciones duras (no violar)

- Cero `self.market_order` ni similares.
- Portabilidad local↔cloud: el switch de entorno vive SOLO en `core/output.py`.
- L3/L4 no usan `AlgorithmImports`; L5 (main.py) es el único que usa `self.schedule`, `self.history`, etc.
- No hardcodear timeframes ni umbrales; vienen de ObjectStore.
- Cada grupo de cambios: un commit con mensaje `[Etapa 9B] #N, #N — descripción`.

## Entrega esperada

Al final: lista de hallazgos resueltos, skipped, y propuesta de diseño para #12.
