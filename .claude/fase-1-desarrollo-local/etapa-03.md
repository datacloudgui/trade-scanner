# Etapa 3 — Exploración y contrato del archivo de entrada

**Estado:** pendiente
**Depende de:** Etapa 2 (walking skeleton con ObjectStore operativo, `scripts/seed_object_store.sh` existente)
**Estimado:** 3–5 horas

---

## Objetivo

Al cerrar la etapa existe un contrato de datos verificado contra los CSVs reales de Barchart, los archivos fuente están sembrados en ObjectStore con claves estables, `strategies.json` incorpora la sección de ambientes (dev/prod) y las cuatro estrategias (2 longs + 2 shorts placeholder), y el script de siembra archiva los CSVs procesados. A partir de aquí, Etapa 4 puede implementar `UniverseSpec` con contratos firmes.

---

## Contexto: los archivos de entrada

**Fuente:** Barchart.com — exportados manualmente.
**Ubicación de entrada:** `data/object-store/` (gitignoreado; no versionar CSVs de datos).
**Formato de nombre (sin modificar):** `5-day-all-us-exchanges-percent-change-{tipo}-{MM-DD-YYYY}.csv`

```
5-day-all-us-exchanges-percent-change-advances-06-05-2026.csv   # longs (gainers)
5-day-all-us-exchanges-percent-change-declines-06-05-2026.csv   # shorts (losers)
```

**Hallazgos del perfilado previo (verificar en T1):**
- Columnas (11): `Symbol, Name, 5D %Chg, Latest, Change, %Change, 5D Chg, 5D High, 5D Low, 5D Avg Vol, Time`
- 200 filas de datos + 1 fila footer de Barchart (`Downloaded from Barchart.com as of ...`) detectada por símbolo inválido.
- `5D Avg Vol`: ya numérico (sin comas). Mediana ~995K, máximo ~125M. Con filtro `> 1M`: ~98–99 filas pasan.
- `5D %Chg` y `%Change`: strings con prefijo `+`/`-` y sufijo `%` (ej. `+668.17%`). Requieren parsing.
- `Latest`: precio numérico. `5D High`, `5D Low`, `5D Chg`: numéricos.

---

## Diseño: longs y shorts

**Decisión:** dos universos separados, no inversión de reglas. Ver razonamiento completo en [etapa-03-decisiones-y-pendientes.md](etapa-03-decisiones-y-pendientes.md) (D1).

| Dirección | Barchart type | Clave ObjectStore            | Universo en config   |
|-----------|---------------|------------------------------|----------------------|
| Long      | advances      | `universes/swing_advances.csv` | `swing_advances`   |
| Short     | declines      | `universes/swing_declines.csv` | `swing_declines`   |

Cada estrategia declara `"direction": "long"` o `"short"`. Las estrategias short son **placeholders** en V1 (config lista, reglas se definen en Etapa 6).

---

## Tareas

### T1 — `scripts/explore_universe.py`: perfilado del CSV real

Script de línea de comandos (host Python 3.11, sin dependencia de LEAN/Docker) que recibe una ruta de CSV Barchart y emite un reporte en consola.

**Criterio de aceptación:**
```bash
python scripts/explore_universe.py "data/object-store/5-day-all-us-exchanges-percent-change-advances-06-05-2026.csv"
```
Produce reporte que incluye:
- Filas totales, filas de datos (post-footer), columnas presentes vs. esperadas.
- Footer detectado y descartado (mostrar valor completo).
- Por columna: tipo inferido, nulos/blancos, rango (mín/máx para numéricas), muestras de formato para columnas con parsing especial (`5D %Chg`, `%Change`).
- Tabla de simulación de filtros: para umbrales de `5D Avg Vol` (100K, 500K, 1M, 5M, 10M), cuántos tickers pasan; y con el filtro combinado `avg_vol_5d > 1e6 and price > 5`, cuántos pasan.
- Tickers con símbolo no-estándar (no `^[A-Z]{1,5}$`), listados.
- Corre sin errores con ambos archivos (advances y declines).

**Notas técnicas:**
- Usar `csv.DictReader` o `pandas` (host tiene acceso libre a pip).
- Detectar footer: fila donde `Symbol` no matchee `^[A-Z]{1,5}$`.
- Parsing de porcentajes: strip `+`, `%`; convertir a `float` y dividir por 100.
- El script **solo lee y reporta**: no escribe, no siembra, no filtra el universo final (eso es Etapa 4).

---

### T2 — Contrato del CSV ratificado y documentado en PLAN.md

Actualizar la sección "Contratos de datos EN DEFINICIÓN" del PLAN.md con los contratos definitivos post-perfilado.

**Criterio de aceptación:** el PLAN.md refleja exactamente:

#### Contrato de entrada (CSV Barchart)

| Campo original | Alias normalizado | Tipo   | Notas de parsing                           |
|----------------|-------------------|--------|--------------------------------------------|
| `Symbol`       | `ticker`          | string | Validar `^[A-Z]{1,5}$`; footer → descartar |
| `Name`         | `name`            | string | Informativo; no usado en reglas            |
| `5D %Chg`      | `pct_chg_5d`      | float  | Strip `+`/`%`; dividir / 100              |
| `Latest`       | `price`           | float  | Precio de cierre del último día del período |
| `Change`       | `chg_1d`          | float  | Cambio absoluto 1D                         |
| `%Change`      | `pct_chg_1d`      | float  | Strip `+`/`%`; dividir / 100              |
| `5D Chg`       | `chg_5d`          | float  | Cambio absoluto 5D                         |
| `5D High`      | `high_5d`         | float  | Máximo del período                         |
| `5D Low`       | `low_5d`          | float  | Mínimo del período                         |
| `5D Avg Vol`   | `avg_vol_5d`      | float  | Ya numérico (sin comas)                    |
| `Time`         | `date`            | string | Fecha de exportación (`YYYY-MM-DD`)        |

- Footer strip: fila con `Symbol` inválido → descartar siempre.
- Columnas extra futuras: ignoradas si no están en el alias map.
- Filtro declarativo usa **alias normalizados**: `"avg_vol_5d > 1e6 and price > 5"`.
- Normalización ocurre en `UniverseSpec` (Etapa 4); el CSV en ObjectStore se guarda tal cual.

#### Contrato de salida `ScanResult`

| Campo                  | Tipo CSV        | Tipo JSON       | Descripción                                              |
|------------------------|-----------------|-----------------|----------------------------------------------------------|
| `strategy`             | string          | string          | Nombre de la estrategia (ej. `swing_eod`)               |
| `as_of`                | ISO 8601 UTC    | ISO 8601 UTC    | Timestamp del scan                                       |
| `ticker`               | string          | string          | Símbolo (de `Symbol` del CSV)                           |
| `direction`            | `long`/`short`  | string          | Dirección de la estrategia                              |
| `partial_bar`          | `True`/`False`  | bool            | `True` si el precio viene del working bar (intraday)    |
| `price`                | float           | float           | Precio usado: close o working_bar.close                 |
| `time_frames_evaluated`| `D,W,M`         | `["D","W","M"]` | Timeframes evaluados por esta estrategia                |
| `sma_evidence`         | JSON string     | object          | `{tf: {period: {value, dist_pct}}}` — ver ejemplo      |
| `passed_rules`         | pipe-separated  | array of string | Reglas que pasaron (ej. `AboveSMA20\|NotExtended`)      |
| `rules_passed_count`   | int             | int             | Conteo de reglas que pasaron; usado como score de ranking. Las reglas obligatorias deben pasar todas; las opcionales suman al score. |

Ejemplo `sma_evidence`:
```json
{
  "D": {"20": {"value": 150.20, "dist_pct": 2.31}},
  "W": {"20": {"value": 148.50, "dist_pct": 3.52}},
  "M": {"20": {"value": 145.00, "dist_pct": 5.86}}
}
```

---

### T3 — `strategies.json` con `environments` + 4 estrategias (2 long, 2 short)

**Criterio de aceptación:** `config/strategies.json` queda exactamente así:

```json
{
  "environments": {
    "dev":  { "top_n": 5, "max_universe": 10 },
    "prod": { "top_n": 50, "max_universe": 200 }
  },
  "strategies": {
    "swing_eod": {
      "universe": "swing_advances",
      "direction": "long",
      "main_timeframe": "W",
      "timeframes": { "D": [8, 20], "W": [8, 20], "M": [8, 20] },
      "schedule": "after_close",
      "universe_filter": "avg_vol_5d > 1e6 and price > 5",
      "max_extension_pct": 0.10
    },
    "swing_eod_short": {
      "universe": "swing_declines",
      "direction": "short",
      "main_timeframe": "W",
      "timeframes": { "D": [8, 20], "W": [8, 20], "M": [8, 20] },
      "schedule": "after_close",
      "universe_filter": "avg_vol_5d > 1e6 and price > 5",
      "max_extension_pct": 0.10
    },
    "market_close": {
      "universe": "swing_advances",
      "direction": "long",
      "main_timeframe": "W",
      "timeframes": { "D": [8, 20], "W": [8, 20], "M": [8, 20] },
      "schedule": "before_close_30m",
      "universe_filter": "avg_vol_5d > 1e6 and price > 5",
      "max_extension_pct": 0.10
    },
    "market_close_short": {
      "universe": "swing_declines",
      "direction": "short",
      "main_timeframe": "W",
      "timeframes": { "D": [8, 20], "W": [8, 20], "M": [8, 20] },
      "schedule": "before_close_30m",
      "universe_filter": "avg_vol_5d > 1e6 and price > 5",
      "max_extension_pct": 0.10
    }
  }
}
```

- `top_n` y `max_universe` viven en `environments`, no en cada estrategia.
- `direction` es metadata de la estrategia: lo usan las Rules (Etapa 6) y el `ScanResult`.
- `main_timeframe` es el timeframe de referencia principal de la estrategia (ej. `"W"` para swing). Lo usa el pipeline (Etapa 7) para ordenar la `sma_evidence` en el output y para futuras reglas de prioridad. No afecta qué consolidators se crean (eso lo define `timeframes`).
- Las estrategias `*_short` son **placeholders** — el skeleton de Etapa 2 las procesa igual (registra ScheduledEvent que solo loguea); las reglas short se definen en Etapa 6.
- `max_extension_pct` aplica a ambas direcciones; la interpretación (extensión long vs. short) la define la Rule en Etapa 6.

**Cómo `main.py` lee el ambiente (en Etapa 4, no ahora):**
```python
env = self.get_parameter("env", "prod")
env_cfg = strategies_config["environments"][env]
top_n = env_cfg["top_n"]
max_universe = env_cfg["max_universe"]
```

**`lean.json` — agregar `parameters`:**
```json
"parameters": { "env": "dev" }
```
En QC cloud: parámetro `env=prod` desde la UI. Sin tocar código.

---

### T4 — `scripts/seed_object_store.sh`: soporte para CSVs datados + archivo de procesados

Actualizar el script para:
1. Encontrar el CSV más reciente de cada tipo en `data/object-store/` (no procesados).
2. Copiar a `storage/universes/` con clave estable.
3. Mover el archivo fuente a `data/object-store/processed/` (carpeta de historial).

**Flujo operativo esperado:**
```
data/object-store/
  5-day-...-advances-06-05-2026.csv      ← nuevo archivo descargado de Barchart
  5-day-...-declines-06-05-2026.csv      ← nuevo archivo descargado de Barchart
  processed/
    5-day-...-advances-06-03-2026.csv    ← ya procesado, archivado
    5-day-...-declines-06-03-2026.csv    ← ya procesado, archivado
```

Después de correr el script:
```
data/object-store/
  processed/
    5-day-...-advances-06-05-2026.csv    ← movido
    5-day-...-declines-06-05-2026.csv    ← movido
    ... (anteriores)
storage/universes/
  swing_advances.csv                     ← copia estable del más reciente
  swing_declines.csv                     ← copia estable del más reciente
```

**Criterio de aceptación:**
```bash
bash scripts/seed_object_store.sh
```
- Copia `config/strategies.json` → `storage/config/strategies.json` (existente).
- Encuentra `data/object-store/*-advances-*.csv` más reciente (no en `processed/`) → `storage/universes/swing_advances.csv`.
- Mueve ese archivo a `data/object-store/processed/`.
- Ídem para `*-declines-*.csv` → `swing_declines.csv`.
- Loguea: qué archivo usó, fecha en el nombre, cuántas líneas tiene.
- Si no hay archivos nuevos (todos ya en `processed/`): mensaje de advertencia, no error fatal. El archivo previo en `storage/universes/` permanece intacto.
- Crea `data/object-store/processed/` si no existe.

**Notas técnicas:**
```bash
# Bash puro — seleccionar el más reciente por nombre (el date stamp en el nombre es ordenable)
ADVANCES=$(ls data/object-store/*-advances-*.csv 2>/dev/null | sort | tail -1)
```
- `processed/` vive dentro de `data/`, que está gitignoreado. No necesita entry extra en `.gitignore`.
- No hay re-procesamiento automático: si el usuario quiere re-sembrar un archivo ya archivado, lo mueve manualmente de vuelta a `data/object-store/`.

---

## Scope

✅ Entra en esta etapa:
- `scripts/explore_universe.py`: perfilado, reporte en consola
- Contrato de entrada definitivo (alias map, parsing, footer rule, dos claves ObjectStore)
- Contrato de salida `ScanResult` definitivo (campos, tipos CSV y JSON)
- `config/strategies.json`: sección `environments`, 4 estrategias, `direction`, `universe_filter` con price > 5
- `lean.json`: agregar `"parameters": {"env": "dev"}`
- `scripts/seed_object_store.sh`: glob datado + lógica de archivo a `processed/`

❌ No entra en esta etapa:
- Implementar `UniverseSpec` (`core/universe.py`) — Etapa 4
- Aplicar `universe_filter` en runtime — Etapa 4
- Implementar merge de `environments[env]` en `main.py` — Etapa 4 (cuando `top_n` se use por primera vez)
- Reglas específicas para shorts (`BelowSMA`, etc.) — Etapa 6
- Descargar CSVs automáticamente de Barchart — fuera de scope V1
- Descargar datos de precios de Alpaca — Etapa 5+
- Tests pytest dentro de Docker — no aplica (no hay código LEAN nuevo en esta etapa)
- Cualquier cambio a `main.py` (el skeleton actual procesa las 4 estrategias igual: solo loguea)

---

## Consideraciones técnicas específicas al stack

1. **Alias normalizados vs. pandas eval**: los nombres originales (`5D %Chg`, `5D Avg Vol`) contienen espacios y caracteres especiales que quiebran `eval()` sin quoting. La normalización ocurre en `UniverseSpec` (Etapa 4) al leer el CSV. El contrato de filtro en `strategies.json` **ya usa alias normalizados** para que Etapa 4 pueda implementarlo sin cambiar la config.

2. **`get_parameter("env", "prod")` es el único escalar suelto permitido**: encaja con PLAN.md §1 regla 2. Es portable a QC cloud UI. El default `"prod"` protege de runs accidentales en dev contra datos reales.

3. **4 estrategias en el skeleton**: el `main.py` actual registra un `ScheduledEvent` por cada entrada en `strategies.json`. Con 4 estrategias, se loguearán 4 mensajes por día de backtest — comportamiento correcto y esperado.

4. **Short placeholders no rompen nada**: `swing_eod_short` y `market_close_short` tienen el mismo `schedule` que sus contrapartes long. El skeleton los trata igual. Las reglas vacías no están en el JSON; simplemente no hay `rules` key todavía.

5. **ObjectStore key = ruta relativa estable**: `self.object_store.read("universes/swing_advances.csv")` mapea a `storage/universes/swing_advances.csv` local. El nombre datado del archivo original no llega al algoritmo — solo lo conoce el script de siembra.

6. **Footer en ObjectStore**: el CSV se siembra tal cual (con footer). `UniverseSpec` (Etapa 4) es responsable de filtrarlo al parsear. Esto permite auditar el archivo sembrado e inspeccionar qué se cargó.

7. **`processed/` no necesita gitignore explícito**: vive dentro de `data/`, que ya tiene `data/*` en `.gitignore`. Verificar con `git check-ignore data/object-store/processed/`.

---

## Done when

- [ ] `python scripts/explore_universe.py <path>` produce reporte completo para ambos CSVs (advances y declines), sin errores
- [ ] Reporte revisado y aprobado (hallazgos sin sorpresas que rompan el contrato borrador)
- [ ] PLAN.md actualizado: contrato de entrada definitivo (alias map, parsing, footer, dos claves)
- [ ] PLAN.md actualizado: contrato de salida `ScanResult` definitivo (campos, tipos, ejemplo)
- [ ] `config/strategies.json` tiene `environments` + 4 estrategias con `direction` y `universe_filter` correcto
- [ ] `lean.json` tiene `"parameters": {"env": "dev"}`
- [ ] `bash scripts/seed_object_store.sh` siembra `strategies.json` + `swing_advances.csv` + `swing_declines.csv` a `storage/`, y mueve los fuentes a `processed/`
- [ ] Verificar manualmente: `storage/universes/swing_advances.csv` y `swing_declines.csv` existen con ~200 filas; archivos movidos a `data/object-store/processed/`
- [ ] `lean backtest "trade-scanner"` corre sin errores con las 4 estrategias (skeleton loguea los 4 nombres)
- [ ] Commit `[Etapa 3] ...`
