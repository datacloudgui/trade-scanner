# Etapa 3 — Decisiones y pendientes para etapas futuras

> **Propósito:** decisiones de diseño tomadas en Etapa 3 y pendientes que impactan etapas posteriores.
> No son ADRs; son notas operativas acotadas a las consecuencias de este diseño.
>
> Spec de la etapa: [etapa-03.md](etapa-03.md). Última actualización: 2026-06-11.

---

## Decisiones tomadas

### D1 — Longs y shorts: dos universos separados, no inversión de reglas

- **Opciones consideradas:**
  - A) Inversión: un solo universo, la estrategia short aplica las reglas "al revés" (BelowSMA en lugar de AboveSMA, etc.)
  - B) Dos universos separados: `swing_advances` (gainers) y `swing_declines` (losers), cada uno con su set de reglas.
- **Decisión:** Opción B (dos universos separados).
- **Por qué:**
  1. Los datos ya vienen pre-separados de Barchart (dos archivos distintos). No hay lógica de split que implementar.
  2. Las reglas short no son simétricas a las long: la extensión de un short candidate tiene distinto significado que para un long (ej. precio vs. SMA8 para un short puede checkear resistencia, no soporte). Una inversión mecánica simplifica incorrectamente la lógica.
  3. Permite que cada dirección tenga su `universe_filter`, `timeframes`, y reglas propias sin condicionales de dirección en el código de las Rules.
  4. Escala a estrategias futuras que tengan solo long o solo short, sin necesidad de un campo `direction` en el filtro.
- **Cómo revertir:** si en el futuro los datos vienen como un solo CSV con columna de dirección, `UniverseSpec` puede filtrar por esa columna; el contrato de config no cambia.

---

### D2 — `direction` como campo de metadata en la estrategia, no como filtro de universo

- **Qué:** `"direction": "long"` | `"short"` vive en `strategies.json` como metadata de la estrategia, no como condición del `universe_filter`.
- **Por qué:** el universo ya está pre-filtrado por dirección (advances vs. declines). El campo `direction` sirve para: (a) incluirlo en el `ScanResult` para que el consumidor final sepa qué dirección recomendar, y (b) orientar la interpretación de reglas en Etapa 6 si alguna rule necesita saber la dirección (ej. `NotExtended` en un short chequea el lado opuesto).
- **Impacto en Etapa 6:** las Rules que reciben `direction` como parámetro deben ser agnósticas de él si la lógica es idéntica, o parametrizadas si difiere. Evaluar caso a caso; el campo en config alcanza.

---

### D3 — Estrategias short como placeholders con config completa

- **Qué:** `swing_eod_short` y `market_close_short` tienen todos los campos en `strategies.json` (`universe`, `direction`, `timeframes`, `schedule`, `universe_filter`, `max_extension_pct`) pero sin reglas definidas todavía.
- **Por qué:** el contrato de config debe estar firme desde Etapa 3 para que el resto de la cadena (seed, UniverseSpec, SymbolData, pipeline) no tenga que cambiar cuando se activen en Etapas 6–7. Agregar la config ahora cuesta cero; agregarla después tiene riesgo de inconsistencias.
- **Impacto en el skeleton:** el `main.py` actual registra ScheduledEvents para las 4 estrategias (solo loguea). No hay diferencia de comportamiento hasta Etapa 7.
- **Reglas short a definir en Etapa 6:** `BelowSMA(20, D∧W∧M)`, `NotExtended_Short` (lógica a acordar). Son placeholder; la config no las lista todavía.

---

### D4 — Filtro default: `avg_vol_5d > 1e6 and price > 5`

- **Qué:** el `universe_filter` base de todas las estrategias V1 excluye penny stocks (`price > 5`) y tickers ilíquidos (`avg_vol_5d > 1e6`).
- **Por qué:** con el umbral de 1M de volumen, ~98–99 de 200 tickers pasan por archivo. El filtro de precio elimina micro-caps y securities con spreads amplios que distorsionan los indicadores. Filtro combinado real (Etapa 3): 74 advances / 68 declines.
- **Cómo ajustar:** editar `universe_filter` en `config/strategies.json` sin tocar código. Cada estrategia puede tener su propio filtro. Filtros adicionales opcionales: `pct_chg_5d > 0.05`, `high_5d > X`, etc.

---

### D5 — Lógica de archivo: `data/object-store/processed/` tras siembra

- **Qué:** `seed_object_store.sh` mueve el archivo fuente a `data/object-store/processed/` después de copiarlo a `storage/universes/`.
- **Por qué:** distingue "pendiente de procesar" (en `data/object-store/`) de "ya sembrado" (en `processed/`). Permite historial de archivos y evita sembrar el mismo archivo dos veces accidentalmente.
- **No se versiona:** `data/` está gitignoreado completo. `processed/` es historial local.
- **Flujo manual de re-siembra:** si el usuario necesita re-sembrar un archivo ya archivado, lo mueve manualmente de `processed/` a `data/object-store/` y corre el script.

---

## Estado de T1 — `scripts/explore_universe.py` (2026-06-11)

### Criterios de aceptación

| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | `python scripts/explore_universe.py <advances>` corre sin errores | ✅ | Exit 0, reporte completo |
| 2 | `python scripts/explore_universe.py <declines>` corre sin errores | ✅ | Exit 0, reporte completo |
| 3 | Filas totales + filas de datos (post-footer) reportadas | ✅ | 201 totales / 200 datos en ambos |
| 4 | Footer detectado y descartado (valor completo mostrado) | ✅ | Muestra el dict completo del footer de Barchart |
| 5 | Columnas presentes vs. esperadas | ✅ | 11/11 coinciden exactamente |
| 6 | Por columna: tipo, nulos, rango, muestras de formato | ✅ | Todas las columnas cubiertas |
| 7 | Muestras de formato para `5D %Chg` y `%Change` | ✅ | Muestra valores crudos como `+668.17%`, `-76.49%` |
| 8 | Tabla de simulación de filtros (5 umbrales de volumen) | ✅ | 100K/500K/1M/5M/10M |
| 9 | Filtro combinado `avg_vol_5d > 1M AND price > 5` | ✅ | advances: 74 / declines: 68 |
| 10 | Tickers con símbolo no estándar listados | ✅ | Ninguno en ambos archivos |

### Hallazgos del perfilado (sin sorpresas que rompan el contrato)

**Advances (gainers):**
- 200 filas de datos + 1 footer ✓
- `5D Avg Vol` rango: 1,620 – 125,139,875. Mediana: ~995K ✓
- Con `avg_vol_5d > 1M AND price > 5`: **74 tickers** (contrato decía ~98–99 solo por vol; el filtro de precio adicional reduce a 74)
- `5D %Chg` en formato `+668.17%` (parsing: strip `+`/`%`, /100) ✓
- `%Change`: puede ser positivo o negativo (`+57.29%` a `+123.94%` en este set) ✓

**Declines (losers):**
- 200 filas de datos + 1 footer ✓
- `5D Avg Vol` rango: 6,060 – 116,221,836. Mediana: ~929K ✓
- Con `avg_vol_5d > 1M AND price > 5`: **68 tickers**
- `5D %Chg` en formato `-76.49%` — los values negativos también parsean correctamente ✓
- `5D Chg` también negativo en declines (`-95.97` a `-0.52`) — contrato correcto como `float` ✓

**Confirmación del contrato de entrada:** ninguna sorpresa. El alias map, los tipos y las reglas de parsing documentados en el spec son correctos.

---

## Pendientes por etapa

### Etapa 4 — UniverseSpec

| # | Pendiente | Descripción |
|---|-----------|-------------|
| P1 | `UniverseSpec`: normalización de alias de columnas | Al leer el CSV, renombrar columnas según el alias map (contrato §5 de PLAN.md). El filtro declarativo usa alias; el CSV fuente usa nombres originales. `UniverseSpec` hace el rename antes de aplicar `eval()`. |
| P2 | `UniverseSpec`: footer strip | Descartar filas donde `ticker` no matchee `^[A-Z]{1,5}$`. El CSV en ObjectStore llega con footer de Barchart; la validación es responsabilidad de `UniverseSpec`, no del script de siembra. |
| P3 | `UniverseSpec`: `direction` no es campo de universo | El campo `direction` de la estrategia debe estar disponible para `ScanResult`, pero `UniverseSpec` no lo necesita (solo filtra tickers). El pipeline (Etapa 7) lo propaga. No diseñar `UniverseSpec` con ese acoplamiento. |
| P4 | `main.py`: leer `env_cfg["top_n"]` y `env_cfg["max_universe"]` | `main.py` debe leer `self.get_parameter("env", "prod")` y extraer `top_n`/`max_universe` del bloque `environments`. Estos valores se pasan al pipeline cuando se instancie en Etapa 7. En Etapa 4 ya se puede leer y loguear para verificar. |
| P7 | Actualizar spec Etapa 4 | El spec debe referenciar el contrato de alias de §5 (PLAN.md) y la regla de footer strip. `UniverseSpec` no necesita conocer `direction` ni `main_timeframe`; el pipeline (Etapa 7) los propaga al `ScanResult`. |

### Etapa 6 — Rules

| # | Pendiente | Descripción |
|---|-----------|-------------|
| P5 | Reglas short: `BelowSMA(20, D∧W∧M)` y lógica de `NotExtended` para shorts | Las reglas short son placeholder. Antes de Etapa 6 acordar: (a) `BelowSMA` = precio < SMA20 en los 3 timeframes; (b) `NotExtended` para short = precio no demasiado por debajo de SMA8 (¿mismo umbral que long pero en la dirección opuesta?). |
| P8 | Definir semántica de `rules_passed_count` para el ranking | Acordar qué reglas son obligatorias (todas deben pasar para que el ticker entre al resultado) y cuáles son opcionales (suman al score). El `ScanResult` reporta `rules_passed_count` = total de reglas que pasaron; el pipeline puede ordenar por ese valor. |

### Etapa 7 — Pipeline y ScanResult

| # | Pendiente | Descripción |
|---|-----------|-------------|
| P6 | `strategies/swing_eod_short.py` y `market_close_short.py` | Crear los módulos de estrategia short (análogo a `swing_eod.py`). En Etapa 3 no existen; la config ya está lista para cuando se creen. |

---

## Síntomas → causa probable

- **`Object with path 'universes/swing_advances.csv' was not found`** → falta correr `bash scripts/seed_object_store.sh`, o no había CSV en `data/object-store/` (todos ya en `processed/`).
- **El backtest solo loguea 2 estrategias en lugar de 4** → `strategies.json` no fue re-sembrado a `storage/config/` después de agregar las estrategias short. Correr `seed_object_store.sh`.
- **El ambiente es `prod` cuando esperás `dev`** → `lean.json` no tiene `"parameters": {"env": "dev"}` o el CLI lo sobrescribió. Verificar el campo en `lean.json` después de cualquier comando `lean`.
- **Filtro devuelve 0 tickers** → revisar que los nombres de columna en el `universe_filter` usan alias normalizados (`avg_vol_5d`), no los nombres originales del CSV (`5D Avg Vol`).
