# PLAN — Screener de Acciones sobre LEAN

Archivo principal de trabajo. Complementa a `SPECS.md` (contexto de producto). Ante conflicto, gana este archivo.

**Qué se construye:** screener multi-estrategia sobre LEAN. Carga universos desde CSV (≤200 tickers), mantiene indicadores en los marcos de tiempo que cada estrategia declare, evalúa reglas en horarios programados y emite watchlist con evidencia. **Solo escanea: cero órdenes en V1.**

---

## 1. Reglas no negociables

1. El código solo habla con la API de `QCAlgorithm`. Sin SDKs de brokers/datos embebidos.
2. Portable local ↔ QuantConnect cloud sin cambios de código: fuente de datos y broker viven en `lean.json`; config de negocio y archivos (universos, `strategies.json`) vía ObjectStore. `self.get_parameter` solo para escalares sueltos si hiciera falta — no para la config anidada de estrategias (ver §4).
3. Un solo algoritmo/nodo ejecuta TODAS las estrategias vía `self.schedule.on(...)`.
4. **Los marcos de tiempo NO son fijos: cada estrategia declara los suyos.** Los consolidators creados y la profundidad del warmup se derivan de esas declaraciones (ver §4).
5. Desarrollo solo con LEAN CLI (`lean backtest` / `lean live`), engine en Docker `quantconnect/lean`.
6. Indicadores y barras W/M/etc. siempre con consolidators e indicadores de LEAN (`Calendar.WEEKLY`, `Calendar.MONTHLY`, `register_indicator`). Prohibido resampling manual con pandas en el algoritmo.
7. Parámetros de estrategias (umbrales, horarios, timeframes, archivo de universo) en `config/strategies.json` (ObjectStore), nunca hardcodeados ni en `config.json` del proyecto (ver §4).

## 2. Capas y restricciones entre capas

```
L6 Ejecución      lean backtest | lean live (Docker quantconnect/lean) — boundary de runtime/deploy
L5 Orquestación   main.py (QCAlgorithm): config → universos → SymbolData+warmup → schedule → OutputSink
L4 Estrategias    ScanPipeline = universo + Rules + ScheduleSpec → ScanResult
L3 Features       cómputos reutilizables sobre SymbolData (posición vs SMA(n,tf), extensión, % día)
L2 Datos derivados SymbolData: consolidators por timeframe + indicadores + working bar + warmup
L1 Config externa lean.json · CSVs en ObjectStore · parámetros
```

- L3/L4 **nunca** consultan datos: leen estado de `SymbolData`. El scan es lectura, no cómputo.
- L4 no calcula indicadores; solo evalúa predicados (Rules) y arma evidencia.
- Solo L5 usa `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify`.
- Un símbolo = un `SymbolData` compartido entre estrategias (unión de sus timeframes requeridos).

## 3. Árbol de directorios

```
trade-scanner/              # lean init aquí (workspace)
├── lean.json                    # provider de datos/broker: ÚNICO lugar que cambia entre fuentes
├── data/                        # data folder LEAN (gestionado por CLI; no versionar contenido pesado)
├── storage/                     # ObjectStore local REAL del CLI (montado en /Storage); copia
│                                #   sembrada y gitignoreada — fuente versionada vive en config/
├── trade-scanner/               # lean project-create "trade-scanner" --language python
│   ├── main.py                  # L5: única clase QCAlgorithm
│   ├── config.json              # archivo de proyecto LEAN (algorithm-language, etc.) — NO config de negocio
│   ├── research.ipynb           # exploración (generado por CLI)
│   ├── core/                    # paquete: incluye __init__.py (portable local↔cloud)
│   │   ├── timeframes.py        # TimeframeSpec: "D"|"W"|"M" → consolidator + barras de warmup necesarias
│   │   ├── symbol_data.py       # SymbolData (L2)
│   │   ├── features.py          # Features (L3)
│   │   ├── rules.py             # Rules componibles con evidencia (L4)
│   │   ├── pipeline.py          # ScanPipeline, ScanResult (L4)
│   │   ├── universe.py          # UniverseSpec: CSV ObjectStore + filtro simple + refresh_universe() no-op
│   │   └── output.py            # OutputSink: CSV/JSON local | NotificationManager cloud (selección por entorno)
│   ├── strategies/              # paquete: incluye __init__.py
│   │   ├── base.py              # StrategyConfig: declara timeframes requeridos, rules, schedule, universo
│   │   ├── swing_eod.py
│   │   └── market_close.py
│   └── tests/                   # pytest con TradeBars sintéticos (correr dentro de imagen LEAN)
├── config/                      # config de negocio versionada (se siembra a ObjectStore)
│   └── strategies.json          # estrategias, timeframes, umbrales, horarios, top_n (ver §4)
├── universes/                   # CSVs fuente versionados (se siembran a ObjectStore con script)
│   └── swing.csv
├── data/equity/usa/             # sample data libre (SPY 2013) p/ que el reloj del backtest avance — ver Etapa 2
├── scripts/
│   ├── explore_universe.py      # perfilado del CSV de entrada (Etapa 3)
│   ├── seed_object_store.sh     # copia config/*.json + universes/*.csv → storage/
│   ├── seed_sample_data.sh      # baja sample data libre del repo público LEAN → data/ (Etapa 2)
│   └── run_tests.sh             # pytest dentro de la imagen quantconnect/lean
└── README.md
```

## 4. Diseño clave: timeframes por estrategia

Cada estrategia declara qué necesita; el orquestador construye lo mínimo. La config de estrategias vive en un **JSON en ObjectStore** (`config/strategies.json`), leído por `main.py` vía `self.object_store` + `json.loads` — **no** en `config.json` del proyecto ni vía `self.get_parameter`:

```json
// config/strategies.json  (sembrado a ObjectStore; versionado en config/ del repo)
{
  "bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 },
  "strategies": {
    "swing_eod":    { "universe": "swing", "direction": "long", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "after_close", "top_n": 50 },
    "market_close": { "universe": "swing", "direction": "long", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "before_close_30m", "top_n": 50 }
  }
}
```

- **Umbrales de posición (Etapa 6/6B):** los cortes `near/mild/extended` viven en `bucket_thresholds` (global + override opcional por estrategia), **un solo set por estrategia** compartido por todas sus rules. El antiguo `max_extension_pct` por estrategia quedó **retirado** (ADR-005): "no extendido" = excluir el bucket extremo, cuyo corte es el `extended` único. Ver [ADR-005](.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).

- **Por qué ObjectStore y no `get_parameter`:** `self.get_parameter` solo devuelve strings planos y no expresa el mapa anidado `timeframes`; la UI de parámetros de QC cloud es plana. ObjectStore es el único mecanismo portable local↔cloud que soporta estructura anidada y mantiene la config fuera del código (mismo canal que los universos CSV). El `config.json` del proyecto queda como archivo de LEAN + parámetros escalares sueltos (`env`, etc.) — **no** config de negocio anidada.
- **D-E4 — `get_parameter` lee de `config.json`, no de `lean.json`:** `self.get_parameter("env")` lee desde `trade-scanner/config.json["parameters"]`. El campo `"parameters"` en `lean.json` (raíz del workspace) es para el engine LEAN y es ignorado por `get_parameter`. Parámetros escalares del algoritmo → `trade-scanner/config.json["parameters"]`. Config de negocio anidada → ObjectStore.
- `timeframes` = mapa timeframe → periodos de SMA requeridos.
- Por símbolo, L5 calcula la **unión** de timeframes/periodos de todas las estrategias que lo incluyen y crea solo esos consolidators/indicadores.
- **Warmup derivado**: barras diarias necesarias = `max` sobre lo declarado. Regla: `D:n → n+5` barras; `W:n → n*5+10`; `M:n → n*21+21`. Ej.: `M:[20]` → ~441 barras diarias. Nada de "504 fijo".
- `working_bar` del consolidator diario expone el OHLC parcial del día en curso para scans intradía (suscripción `Resolution.MINUTE`).
- SMAs estables intradía: los indicadores solo se actualizan al cierre de su barra; el scan intradía compara precio actual (working bar) vs medias del último cierre.

## 5. Contratos de datos (definitivos — ratificados en Etapa 3)

### Contrato de entrada: CSV Barchart

Fuente: Barchart.com, exportado manualmente. Formato de nombre: `5-day-all-us-exchanges-percent-change-{tipo}-{MM-DD-YYYY}.csv`.
Claves ObjectStore: `universes/swing_advances.csv` (advances/longs) y `universes/swing_declines.csv` (declines/shorts).

| Campo original | Alias normalizado | Tipo   | Notas de parsing                            |
|----------------|-------------------|--------|---------------------------------------------|
| `Symbol`       | `ticker`          | string | Validar `^[A-Z]{1,5}$`; footer → descartar  |
| `Name`         | `name`            | string | Informativo; no usado en reglas             |
| `5D %Chg`      | `pct_chg_5d`      | float  | Strip `+`/`%`; dividir / 100               |
| `Latest`       | `price`           | float  | Precio de cierre del último día del período |
| `Change`       | `chg_1d`          | float  | Cambio absoluto 1D                          |
| `%Change`      | `pct_chg_1d`      | float  | Strip `+`/`%`; dividir / 100               |
| `5D Chg`       | `chg_5d`          | float  | Cambio absoluto 5D                          |
| `5D High`      | `high_5d`         | float  | Máximo del período                          |
| `5D Low`       | `low_5d`          | float  | Mínimo del período                          |
| `5D Avg Vol`   | `avg_vol_5d`      | float  | Ya numérico (sin comas)                     |
| `Time`         | `date`            | string | Fecha de exportación (`YYYY-MM-DD`)         |

Reglas de parsing:
- Footer strip: fila con `Symbol` no coincidente con `^[A-Z]{1,5}$` → descartar siempre.
- Columnas extra futuras: ignoradas si no están en el alias map.
- Filtro declarativo usa **alias normalizados**: `"avg_vol_5d > 1e6 and price > 5"`.
- Normalización (rename de columnas) ocurre en `UniverseSpec` (Etapa 4); el CSV en ObjectStore se guarda tal cual (con footer incluido).
- Tope duro: 200 tickers post-filtro.

### Contrato de salida: `ScanResult`

Una fila/objeto por candidato; serializa a CSV y JSON.

| Campo                   | Tipo CSV        | Tipo JSON        | Descripción                                                      |
|-------------------------|-----------------|------------------|------------------------------------------------------------------|
| `strategy`              | string          | string           | Nombre de la estrategia (ej. `swing_eod`)                       |
| `as_of`                 | ISO 8601 UTC    | ISO 8601 UTC     | Timestamp del scan                                               |
| `ticker`                | string          | string           | Símbolo (de `Symbol` del CSV)                                   |
| `direction`             | `long`/`short`  | string           | Dirección de la estrategia                                       |
| `partial_bar`           | `True`/`False`  | bool             | `True` si el precio viene del working bar (intraday)            |
| `price`                 | float           | float            | Precio usado: close o working_bar.close                         |
| `time_frames_evaluated` | `D,W,M`         | `["D","W","M"]`  | Timeframes evaluados por esta estrategia                        |
| `sma_evidence`          | JSON string     | object           | `{tf: {period: {value, distance_pct, bucket}}}` — proyección del snapshot único (Etapa 6/6B); ver ejemplo |
| `passed_rules`          | pipe-separated  | array of string  | Reglas que pasaron (ej. `AboveSMA20\|NotExtended`)               |
| `rules_passed_count`    | int             | int              | Conteo de reglas que pasaron; usado como score de ranking        |

Ejemplo `sma_evidence` — proyección del snapshot único (Etapa 6B), no un recompute; `distance_pct` y `bucket` se añadieron en Etapa 6 y `distance_pct` es fracción, no porcentaje:
```json
{
  "D": {"20": {"value": 150.20, "distance_pct": 0.0231, "bucket": "above_mild"}},
  "W": {"20": {"value": 148.50, "distance_pct": 0.0352, "bucket": "above_strong"}},
  "M": {"20": {"value": 145.00, "distance_pct": 0.0586, "bucket": "above_strong"}}
}
```

## 6. Estrategia de referencia

**`swing_eod`** (tras el cierre): universo `swing` filtrado → top N por `day_change_pct` → regla `AboveSMA(20, D∧W∧M)` → regla `NotExtended(8, D)` → ScanResult.
**`market_close`** (15:30 ET): mismas reglas; precio/OHLC desde working bar; resultado marcado `partial_bar=True`.
Variante shorts (`*_short`): universo `swing_declines`, `direction: short` → las mismas reglas con `side="below"` por mirror (ADR-005): `AboveSMA` filtra `below_*`, `NotExtended` excluye `extended_below`. Sin reglas nuevas.

> **Reglas (Etapa 6/6B):** una sola evaluación de posición precio↔SMA por símbolo·scan (snapshot único); las rules son filtros puros sobre buckets ya asignados. `NotExtended` no lleva umbral propio: excluye el bucket extremo, cuyo corte es el `bucket_thresholds.extended` único de la estrategia. Largos/cortos: mirror del set de buckets desde `direction`. Ver [ADR-005](.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md).

---

## 7. FASE 1 — Etapas (spec-driven)

### Secuencia del ciclo 2026-09 (fija el orden de ejecución)

Roadmap del ciclo: [roadmap-definitivo-2026-09.md](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md). **La etapa activa es la primera fila de esta tabla
cuyo Estado no es `completada`**; se trabaja solo esa (CLAUDE.md, flujo, paso 1). El orden del documento de abajo
es histórico, no de ejecución. `pausada` = etapa abierta cuyo trabajo restante está asignado a una fila posterior.

| Orden | Etapa | Unidad del roadmap | Forma | Estado |
|---|---|---|---|---|
| 1 | **12** — Base estable + adopción de OpenSpec | U0 | [etapa-12.md](.claude/fase-1-desarrollo-local/etapa-12.md) | en progreso |
| 2 | **13** — Cobertura de datos | U1 | change `add-data-coverage-gate` | pendiente |
| 3 | **5B** — cierre de F3 | U1b | change `close-5b-reference-fixture` | pausada |
| 4 | **11** — Rango del backtest derivado del universo (re-scope) | U2 | change `derive-backtest-range-from-universe` | pendiente |
| 5 | **14** — Scan acotado al universo de cada estrategia (#12) | U3a | change `partition-scan-universe-per-strategy` + ADR-006 | pendiente |
| 6 | **15** — Lado corto habilitado | U3b | change `enable-short-side` + enmienda a ADR-005 | pendiente |
| 7 | **9** — Validación integral (+ 9A T7/T8) | U4 | tarea de PLAN, sin change | pendiente |

Desde la Etapa 13, cada unidad se especifica como change de OpenSpec (`openspec/changes/<id>/`); la Etapa 12 es el
último spec en formato `etapa-NN.md`. Una rama por etapa: `feature/etapa-NN-<change-id>` (modelo de ramas en
[etapa-12.md §Manejo de ramas](.claude/fase-1-desarrollo-local/etapa-12.md)).

## Etapa 0 — Entorno de desarrollo
**Estado:** completada (verificada 2026-09-23 en Etapa 12 T1; el entorno funcionaba desde Etapa 1 pero el Estado nunca se actualizó)
**Objetivo:** máquina lista para correr LEAN CLI (válido para cualquier PC)
**Depende de:** nada
**Alcance:**
- Instalar Docker Desktop; verificar con `docker run hello-world`.
- Instalar pyenv; instalar Python 3.11 (`pyenv install 3.11.9`); fijar versión local en el repo (`pyenv local 3.11.9` → genera `.python-version`).
- Crear virtualenv del proyecto (`python -m venv .venv`); añadir `.venv/` a `.gitignore`.
- Instalar LEAN CLI dentro del venv: `pip install lean`; verificar `lean --version`.
**Done when:**
- [x] `docker run hello-world` pasa sin errores *(2026-09-23)*
- [x] `python --version` dentro del venv muestra `3.11.x` *(3.11.11)*
- [x] `lean --version` pasa sin errores *(lean 1.0.225)*
- [x] `.venv/` en `.gitignore`; `.python-version` en el repo *(`3.11.11`)*

## Etapa 1 — Workspace LEAN, cuentas y credenciales
**Estado:** completada
**Objetivo:** entorno local LEAN corriendo en Docker con credenciales listas
**Depende de:** Etapa 0
**Alcance:**
- Alpaca paper (API key/secret) en `.env` (gitignoreado); `lean login` QC no requerido para Fase 1.
- `lean.json` generado desde template público de LEAN (sin `lean init` — requiere QC pago); `organization-id` placeholder para satisfacer check del CLI.
- Smoke test: `lean project-create "trade-scanner" --language python` y `lean backtest "trade-scanner"`.
**Done when:**
- [x] `lean backtest "trade-scanner"` corre en Docker sin errores con el algoritmo de ejemplo
- [x] Credenciales Alpaca en `.env` (gitignoreado); `lean.json` sin valores reales
- [x] `lean.json`, `.gitignore` y proyecto commiteados con `[Etapa 1] ...`

## Etapa 2 — Esqueleto del proyecto (walking skeleton)
**Estado:** completada
**Objetivo:** plumbing end-to-end validado temprano: paquetes importables, carga de config desde ObjectStore, un ScheduledEvent por estrategia disparando a su hora real, y pytest verde dentro de la imagen LEAN. Sin lógica de negocio (eso son Etapas 4+).
**Depende de:** Etapa 1

> **Hallazgo que define el alcance (verificado en log de Etapa 1):** un backtest **sin datos no avanza el reloj** — el motor procesa "1 data point" y dispara `On End Of Algorithm` de inmediato; los `ScheduledEvents` nunca corren. Doc QC: *"in backtests, the algorithm clock only advances when new data arrives."* Por eso esta etapa siembra sample data libre y ancla las time-rules a un símbolo de referencia. Además, la config de negocio NO va en `config.json`/`get_parameter` (no portable a cloud para estructura anidada) sino en JSON en ObjectStore (ver §4).

**Alcance:**
- **Estructura mínima (no stubs muertos):** crear `core/`, `strategies/`, `tests/` como paquetes con `__init__.py`, y solo los archivos que esta etapa ejercita. Cada etapa posterior añade su módulo. `config/`, `universes/`, `scripts/` en la raíz del workspace (fuera del proyecto pusheable).
- **`scripts/seed_sample_data.sh`:** baja la sample data libre de SPY (~2013, `Resolution.MINUTE`) del repo público de LEAN a `data/equity/usa/` (sin auth QC — ver ADR-002). Hace avanzar el reloj del backtest.
- **`config/strategies.json` + seed a ObjectStore:** estructura mínima de §4 (dos estrategias con `schedule` y `universe`; resto de campos pueden ir vacíos/placeholder en esta etapa). `scripts/seed_object_store.sh` lo copia a `storage/config/` (el ObjectStore real del CLI; **no** `data/object-store/`). Key de lectura: `config/strategies.json`.
- **`main.py` esqueleto (L5):** `add_equity("SPY", Resolution.MINUTE)` como ancla de calendario; lee `config/strategies.json` vía `self.object_store` + `json.loads`; mapea los strings de schedule (`after_close` → `time_rules.after_market_close(SPY, …)`, `before_close_30m` → `time_rules.before_market_close(SPY, 30)`, `date_rules.every_day(SPY)`); registra un `ScheduledEvent` por estrategia que solo loguea `"scan <nombre> @ <hora>"`.
- **`scripts/run_tests.sh`:** pytest dentro de `quantconnect/lean` (montando el proyecto). El test no es trivial: **importa `AlgorithmImports` y construye un objeto LEAN** (p. ej. un `TradeBar`) — así de-riesga que el puente pythonnet funciona en Docker, que es el verdadero unknown.

**Done when:**
- [x] `lean backtest` recorre la ventana con sample data y loguea cada `scan <estrategia> @ <hora>` a la hora correcta según el calendario del mercado (after_close, before_close_30m) — verificado por timestamps en el log, no asumido
- [x] `main.py` carga `strategies.json` desde ObjectStore (no desde `config.json` ni `get_parameter`); cero config de negocio hardcodeada
- [x] `scripts/run_tests.sh` corre pytest dentro de la imagen LEAN con un test verde que importa `AlgorithmImports` y construye un objeto LEAN
- [x] `core/`, `strategies/`, `tests/` son paquetes importables (`__init__.py`); el árbol coincide con §3 para los archivos creados en esta etapa
- [x] Commit `[Etapa 2] ...`; sample data (`data/equity/`) gitignoreada

> **Cierre (commit `[Etapa 2]`):** `market_close` dispara 15:30 y `swing_eod` 16:01 (verificado en log); config leída de `storage/config/strategies.json`; `run_tests.sh` verde (`1 passed`). Hallazgos y decisiones reversibles en [.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-02-decisiones-y-pendientes.md).

## Etapa 3 — Exploración y contrato del archivo de entrada
**Estado:** completada
**Objetivo:** CSV de universo real perfilado, contratos fijados y CSV sembrado en ObjectStore
**Depende de:** Etapa 2
**Alcance:**
- `scripts/explore_universe.py` sobre el CSV real: columnas, tipos, nulos, duplicados, tickers inválidos/no-US, rangos de price y volumen, conteo post-filtro.
- Confirmar o ajustar los contratos de datos borrador con base en lo observado; actualizar este archivo.
- `config/strategies.json`: sección `environments`, 4 estrategias con `direction`, `main_timeframe`, `timeframes`, `universe_filter`, `max_extension_pct` *(esta última retirada luego en 6B/T5 — ADR-005, redundante con `bucket_thresholds.extended`)*.
- `lean.json`: agregar `"parameters": {"env": "dev"}`.
- `scripts/seed_object_store.sh`: soporte para CSVs datados + archivo a `processed/`.

**Contratos de datos:** ver §5 (ratificados en esta etapa — el borrador quedó reemplazado por las tablas definitivas).

**Done when:**
- [x] `python scripts/explore_universe.py <path>` produce reporte completo para ambos CSVs sin errores
- [x] Reporte revisado y aprobado (hallazgos sin sorpresas que rompan el contrato)
- [x] PLAN.md §5 actualizado: contrato de entrada definitivo (alias map, parsing, footer, dos claves)
- [x] PLAN.md §5 actualizado: contrato de salida `ScanResult` definitivo (campos, tipos, ejemplo)
- [x] `config/strategies.json` tiene `environments` + 4 estrategias con `direction` y `universe_filter` correcto
- [x] `lean.json` tiene `"parameters": {"env": "dev"}`
- [x] `bash scripts/seed_object_store.sh` siembra `strategies.json` + `swing_advances.csv` + `swing_declines.csv`; mueve fuentes a `processed/`
- [x] `storage/universes/swing_advances.csv` y `swing_declines.csv` existen con ~200 filas; archivos movidos a `data/object-store/processed/`
- [x] `lean backtest "trade-scanner"` corre sin errores; las 4 estrategias loguearon a sus horas (15:30 y 16:01)

> **Cierre (commit `[Etapa 3]`):** perfilado confirma contrato sin sorpresas (200 datos + 1 footer, 11 columnas, mediana vol ~995K); filtro combinado `avg_vol_5d > 1M AND price > 5` deja 74 advances / 68 declines. Contratos definitivos en §5. 4 estrategias en `strategies.json` (2 long + 2 short placeholder) + `environments` dev/prod. `seed_object_store.sh` actualizado con glob datado y archivo a `processed/`. Backtest confirma las 4 estrategias disparando. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-03-decisiones-y-pendientes.md).

## Etapa 4 — UniverseSpec
**Estado:** completada
**Objetivo:** carga de universos por estrategia desde ObjectStore con filtro declarativo
**Depende de:** Etapa 3
**Alcance:**
- `core/universe.py`: lee CSV desde `self.object_store`, aplica `universe_filter` declarativo, valida tope 200, expone símbolos por estrategia (variantes por clave de universo), `refresh_universe()` no-op documentado.
- Tests: filtro, tope, CSV malformado.
**Done when:**
- [x] Backtest loguea el universo cargado por estrategia con su conteo (≤200)
- [x] Tests de filtro, tope y CSV malformado verdes

> **Cierre (commit `[Etapa 4]`):** `core/universe.py` implementado con `COLUMN_ALIASES`, footer strip (`^[A-Z]{1,5}$`), filtro declarativo vía `df.query()`, orden alfabético y tope duro. Sin imports de `AlgorithmImports`. `main.py` integrado: 4 líneas `universe loaded: N tickers (env=..., max=..., key=...)` en `initialize()`; conteos 74 advances / 68 declines en prod, 2 en dev. 6 tests verdes en Docker (`bash scripts/run_tests.sh`). **Hallazgo D-E4:** `self.get_parameter()` lee parámetros escalares desde `trade-scanner/config.json["parameters"]`, NO desde `lean.json["parameters"]` (el campo en `lean.json` es configuración del engine, no del algoritmo). El parámetro `env` vive en `trade-scanner/config.json`. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-04-decisiones-y-pendientes.md).

## Etapa 5A — TimeframeSpec + SymbolData (lógica y tests sintéticos)
**Estado:** completada
**Objetivo:** consolidators e indicadores construidos dinámicamente según los timeframes declarados, con fórmula de warmup generalizada (registro extensible, no D/W/M hardcodeado) y plan de warmup con presupuesto — verificable 100% por tests en Docker
**Depende de:** Etapa 4
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-05a.md](.claude/fase-1-desarrollo-local/etapa-05a.md)
**Alcance:**
- `core/timeframes.py`: registro declarativo `TimeframeSpec` (resolución fuente, barras por periodo, buffer, factory de consolidator) + `warmup_bars(n)` generalizada (§4) + `plan_warmup()` con presupuesto por resolución (`warmup_budget`): series sobre presupuesto quedan excluidas con warning — habilita SMA 200 condicional en el marco mayor según proveedor de datos.
- `core/symbol_data.py`: construye consolidators e indicadores SOLO para la unión de timeframes requeridos; SMAs cableadas al evento `data_consolidated` del consolidator (mismo mecanismo interno de `register_indicator`, sin instancia del algorithm — compatible QC cloud, decisión D3 del spec); cadena minute→daily→W/M con un solo punto de entrada `update(bar)`; expone `working_bar` e `is_ready`.
- Tests unitarios con TradeBars sintéticos: semana que cierra viernes, mes calendario, SMA con valores a mano, primera barra parcial, unión exacta, profundidades D/W/M × {8, 20, 200}, timeframe intradía nuevo sin tocar la fórmula, equivalencia de rutas de alimentación (warmup daily vs runtime minute), working bar, presupuesto.
**Done when:**
- [x] Tests unitarios de consolidators/indicadores con barras sintéticas verdes (`bash scripts/run_tests.sh`)
- [x] Solo se crean los consolidators/indicadores de la unión de timeframes declarados (verificado por test)
- [x] Profundidad de warmup derivada por fórmula generalizada; un timeframe nuevo se registra sin tocar la fórmula (verificado por test)
- [x] `plan_warmup()` excluye series sobre presupuesto con warning (exclusión y profundidad verificadas por test — T3.3; el warning lo emite `main.py` al leer el plan, cableado en 5B según D2 del spec)
- [x] Equivalencia de rutas de alimentación daily directo vs minute encadenado (verificado por test)
- [x] `core/symbol_data.py` no referencia la instancia de `QCAlgorithm` (tipos de `AlgorithmImports` sí permitidos)

> **Cierre (commits `[Etapa 5A]`, 2026-06-11):** `core/timeframes.py` (registro declarativo `TimeframeSpec`, fórmula de warmup generalizada, `plan_warmup` con presupuesto por resolución) y `core/symbol_data.py` (cadena minute→daily→W/M sin instancia del algorithm, `working_bar`, `is_ready`, `scan(time)`). 31 tests verdes en Docker (T3.1–T3.11 + previos). **Hallazgos D-E5A:** (1) la emisión del consolidator es perezosa incluso con barras diarias exactas y el lag se encadena a W/M → el warmup de 5B debe cerrar con `SymbolData.scan(...)`; (2) `scan()` también emite en consolidators de calendario → 5B puede refrescar SMAs W/M el mismo día del cierre de periodo; (3) equivalencia EXACTA de rutas warmup-daily vs runtime-minute verificada (T3.9) — sin asimetrías en LEAN. Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-05a-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-05a-decisiones-y-pendientes.md).

## Etapa 5B — Warmup integrado + datos de muestra + validación de precisión
**Estado:** pausada — F1/F2 cerradas; F3 (T6.3 + T6.4) se reanuda en el **orden 3** del ciclo como change `close-5b-reference-fixture`. Re-scope ([roadmap U1b](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md)): 27 series (SPY/AAPL/IBM × SMA 8/20/200 × D/W/M) sobre `data/stooq_lean/` con corte 2026-06-11, split-only; **no** refrescar `data/equity/usa/daily/{spy,aapl,ibm}.zip` (lo lee el fixture INTERINO)
**Objetivo:** warmup batch real en `main.py`, datos diarios de muestra multi-símbolo, y SMAs validadas manualmente contra plataforma de referencia (criterio DONE nº1 del SPECS)
**Depende de:** Etapa 5A
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-05b.md](.claude/fase-1-desarrollo-local/etapa-05b.md)
**Alcance (slice-vertical SPY primero; 4 fases):**
- **F1 — slice vertical SPY (datos cero):** `main.py` construye `SymbolData` por símbolo, warmup batch `self.history` agrupado por resolución **cerrando con `sd.scan()`** (hallazgo #1 de 5A), `plan_warmup` global, suscripción `Resolution.DAILY` con `SPLIT_ADJUSTED`, wiring `subscription_manager.add_consolidator`. Entorno `dev` como harness: overrides `universe`/`timeframes`/`warmup_budget` a nivel environment (universo `sample_dev` = SPY/AAPL/IBM; `D/W/M:[8,20,200]` con M:200 solo en dev). Archivo `validation/sma_validation_<fecha>.csv` (solo dev, **K=5 filas/serie**) + fixture de regresión interino. Hito: *pipeline verde*.
- **F2 — ampliar data:** extender `seed_sample_data.sh` con AAPL/IBM (zips LEAN, baseline) → 3 símbolos; ejercita el batch multi-símbolo.
- **F3 — data reciente + precisión:** converter host-side agnóstico a fuente (`requests` crudo, formato LEAN, factor_files neutros) + fetcher Stooq (recent, 30+ a, M:200 viable); cross-check converter==zip; config prod `D:[8,20,200]`/`W:[8,20,200]` (M:200 excluida por presupuesto → warning); validación manual del usuario (TradingView/IBKR, ≤0,25%) congelada como fixture + test de regresión.
- **F4 — de-risk Etapa 9:** smoke-test de la API de datos de Alpaca (conectividad/keys; NO valida `lean live` — ADR-002).
- Datos: triple fuente complementaria (zips LEAN + converter Stooq + smoke-test Alpaca); proceso agnóstico a la fuente (todo escribe formato LEAN en `data/`; `main.py` solo lee el feed). `working_bar`/minute/`partial_bar` quedan para Etapa 7.
**Done when:**
- [x] **F1:** `lean backtest` dev con SPY completa el warmup y loguea profundidad derivada con driver (W:200→1010, M:200→4221), duración y ready/no-ready; `storage/validation/sma_validation_*.csv` con K=5 filas/serie; regresión interina de SPY verde (2026-06-11: `set_warm_up` adoptado con gate 9/9 vs ruta manual; detalle en [etapa-05b-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-05b-decisiones-y-pendientes.md))
- [x] **F2:** 4 símbolos (SPY/AAPL/IBM/FB) ready en batch; 1 llamada warmup (set_warm_up ADOPTADO); log gate: `36/36 series × ruta manual (13574 filas, 1 batch)`; FB M:200 y W:200 cold (esperado); main.py sin cambios (2026-06-12, T6.1)
- [ ] **F3 (parcial — T6.3 y T6.4 pendientes):** ✅ converter Stooq (split-only adjusted) produce zips válidos (SPY/AAPL/IBM); ✅ cross-check CSV→zip fidelidad (±1 unidad ×10000) + SMAs coherentes vía SymbolData; ✅ prod `warmup_budget=1100` con D:200/W:200 incluidos y warning de exclusión de M:200 verificado; ⏳ validación manual ≤0,25% usuario en TradingView (T6.3); ⏳ fixture autoritativo + test de regresión (T6.4)
- [~] **F4:** smoke-test Alpaca diferido a Etapa 9 (ADR-003) — fuera de scope de 5B
- [x] Viabilidad de SMA 200 por marco/proveedor documentada: M:200 viable en Stooq/zip (budget=4300 dev), excluida en prod (budget=1100 < 4221) con warning automático. Guardrail operativo (2026-06-12, T6.2)

## Etapa 6 — Features y Rules (fundamentos L3/L4)
**Estado:** completada (fundamentos) — **aplicación de reglas rediseñada en Etapa 6B**
**Objetivo:** feature `position_vs_sma` (clasificación en 7 buckets configurables), umbralado en ObjectStore (`bucket_thresholds` + `resolve_bucket_thresholds`), y primera rule (`AboveSMA`/`RuleResult`) — capa de negocio puro, aislada y testeada a mano
**Depende de:** Etapa 5B
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-06.md](.claude/fase-1-desarrollo-local/etapa-06.md)
**Entregado y conservado:**
- `core/features.py`: `PositionResult`, `position_vs_sma(sd, tf, period, thresholds)` (D1), `_bucketize` (7 buckets, fronteras exactas), `FeatureNotReady`, `BUCKETS`, `resolve_bucket_thresholds` (merge override-estrategia → global → defaults + validación de orden).
- `core/symbol_data.py` (L2, solo lectura): accesor `close(tf)` (D3).
- `config/strategies.json`: `bucket_thresholds` global placeholder (calibración en Etapa 9).
- `core/rules.py`: `AboveSMA` + `RuleResult` (T3) — **firma de `evaluate` y generalización rediseñadas en 6B**.
**Done when:**
- [x] `position_vs_sma` clasifica los 7 buckets y los 6 cortes exactos; no-hardcodeo con dos sets de thresholds (2026-06-12, T1.3: 82 passed)
- [x] `resolve_bucket_thresholds` verifica global / override-estrategia / defaults con mock (2026-06-13, T2.2: 95 passed)
- [x] `AboveSMA` (AND sobre tfs) + `RuleResult` con evidencia `{tf:{period:{value,distance_pct,bucket}}}`; tests verdes (2026-06-13, T3: 103 passed) — contrato `evaluate` redefinido en 6B
- [x] §5 reconciliada (`dist_pct`→`distance_pct` + `bucket`); features/rules sin imports de `QCAlgorithm`/`self.history`
- ➡️ `NotExtended`, formateador de log y campos de `ScanResult`: **trasladados a Etapa 6B** (no se realizaron en E6)

## Etapa 6B — Snapshot único + reglas como filtros puros
**Estado:** completada (T1–T7 — 141 passed; commits `dd44dfb` 2026-06-14 y `03880f2` 2026-06-18. El Estado se actualizó en la resincronización de Etapa 12 T3, 2026-09-23)
**Objetivo:** una sola evaluación de posición precio↔SMA por símbolo·scan (snapshot único), reglas convertidas en filtros puros sobre buckets ya asignados, simétricas long/short sin duplicar reglas; cerrar las piezas pendientes de la capa de reglas
**Depende de:** Etapa 6
**Autoridad de diseño:** [ADR-005](.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) (aprobado). Supersede D4 de E6.
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-06b.md](.claude/fase-1-desarrollo-local/etapa-06b.md)
**Alcance:**
- `core/features.py`: `build_position_snapshot(sd, series, thresholds)` (snapshot `{tf:{period:PositionResult}}`, 1×/símbolo·scan, frío en un punto), `snapshot_evidence` (proyección), `mirror_buckets`+`_MIRROR`+`SIDE_BY_DIRECTION` (simetría long/short).
- `core/rules.py`: `SMAPositionRule` genérica side-aware con `evaluate(snapshot)` (sin `sd` ni `thresholds`), reemplaza a `AboveSMA` (eliminado — un solo símbolo de clase); `NotExtended(period, tf, side)` preset (constructor con nombre) **sin `max_pct`** (excluye `extended_above`; corte = `bucket_thresholds.extended` único) — supersede D4.
- `config/strategies.json`: retirar `max_extension_pct` (redundante; sembrado en E3, sin consumidor).
- `core/pipeline.py`: contrato mínimo de `ScanResult` (`rules_passed_count`, `sma_evidence` como proyección) + formateadores del log de filtrado (`format_filter_line`/`format_final_line`).
- Tests: snapshot (cálculo único, frío, series no-referenciadas), mirror (involución, `near` autoespejo), rule long/short, `NotExtended`, log literal.
**Done when:**
- [x] `build_position_snapshot` computa cada serie 1×, propaga `FeatureNotReady`, ignora series declaradas-no-referenciadas; `snapshot_evidence` proyecta exacto *(T1)*
- [x] `mirror_buckets`: identidad/`near` autoespejo/involución/above→below/⊆BUCKETS/`side` inválido → error *(T2)*
- [x] `SMAPositionRule.evaluate(snapshot)`: 8 tests de T3 migrados + casos short; evidencia completa al fallar; `buckets_allowed` inválido revienta en construcción *(T3 — `AboveSMA` eliminado)*
- [x] `NotExtended` sin `max_pct` excluye el bucket favorable-extremo (ambos lados); segundo `extended` mueve el corte *(T4)*
- [x] `max_extension_pct` retirado de config + `storage/`; `grep` `.py` limpio; round-trip idéntico *(T5)*
- [x] Formateador reproduce literalmente las 4 líneas; `ScanResult` con campos nuevos; suite verde (141 passed) — T6+T7 commiteados en `03880f2`

## Etapa 7 — ScanPipeline + estrategias + schedule
**Estado:** completada (T1–T6, 2026-06-19) — 178 passed; backtest dev verificado (EXIT=0 ×2). Mecánica end-to-end demostrada: minute subscription + 4 pipelines + schedule + gate B + ranking + embudo + `ScanResult` con evidencia + reproducibilidad (watchlist IBM short byte-idéntica entre 2 corridas). **El literal "backtest ≥3 meses" se DIFIERE a Etapa 9** (decisión usuario): el harness dev solo tiene ~6 días de minute (SPY) y ≥3 meses multi-símbolo exige `lean data download` QC-pago (ADR-002, prerequisito de E9).
**Objetivo:** las dos estrategias V1 corriendo end-to-end en un solo nodo y produciendo ScanResults
**Depende de:** Etapa 6B
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-07.md](.claude/fase-1-desarrollo-local/etapa-07.md)
**Alcance:**
- `core/pipeline.py`: por símbolo construye el **snapshot único** (`build_position_snapshot`, 6B) con la unión de `series` de la estrategia y los thresholds resueltos en `initialize()`; luego universo → ranking top_n → reglas (filtros sobre el snapshot) → `ScanResult`. Resuelve `direction`→`side` (vía `SIDE_BY_DIRECTION`) en un solo punto al componer las rules.
- `strategies/swing_eod.py` y `strategies/market_close.py` como `StrategyConfig` declarativos (sin lógica nueva, solo composición de rules con su `buckets_allowed` canónico y `side`).
- `main.py` completo: una instancia de pipeline por estrategia, ScheduledEvents desde config, símbolos no listos (warmup incompleto) o con serie fría excluidos y logueados (la exclusión por frío usa el `FeatureNotReady` que aflora en el builder).
**Done when:**
- [~] `lean backtest` genera ScanResults **reproducibles** con evidencia por candidato (watchlist IBM short byte-idéntica entre 2 corridas, 2026-06-19). **El alcance ≥3 meses se difiere a Etapa 9** (data-limitado: ~6 días de minute en dev; ≥3 meses multi-símbolo = `lean data download` QC-pago, ADR-002)
- [x] `market_close` reporta `partial_bar=True` (`market_close_short` True / `swing_eod_short` False sobre IBM, mismo símbolo·fecha); working bar **intradía vivo** sobre un candidato → Etapa 9 (IBM sin minute; SPY con minute está sobre SMAs, no pasa short)
- [x] Símbolos con warmup incompleto (serie referenciada fría) quedan excluidos y logueados (FB por `M:20 fría`, gate B)

## Etapa 8 — OutputSink y notificación por entorno
**Estado:** completada (T1–T7, 2026-06-19) — 225 passed; backtest dev verificado; switch por canal demostrado config-only. Diferido a E9: envío real Gmail + `qc_notify` cloud live.
**Objetivo:** salida CSV/JSON y notificación seleccionadas por entorno, aisladas en un módulo
**Depende de:** Etapa 7
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-08.md](.claude/fase-1-desarrollo-local/etapa-08.md)
**Alcance (lo construido):**
- `core/output.py`: serialización CSV+JSON + **envelope por estrategia base** (D8.2: long+short en un solo envelope, ordenado por `rules_passed_count`) + `OutputSink` con **dispatch por tabla de canales leída de `config/notifications.json`** (`file`/`qc_notify`/`host_email`, D8.4) — el switch local/cloud vive SOLO aquí, sin ramas `if env ==`. `JsonSubscriberSource` (lookup de suscriptores por estrategia base, swappable a DB, D8.5).
- `core/email_render.py`: `render_email(envelope) -> EmailDoc` **puro y SDK-free**, compartido por el algoritmo (`qc_notify`) y el script host (D8.1); bloques LONG/SHORT (tickers uno-por-línea) + tabla de detalle humanizada.
- `config/notifications.json`: `notification_groups` (estrategia base → variantes, D8.7), canales/`notify_empty` por entorno, suscriptores por base, `email.from`/`subject_prefix`. Sin secretos (token Gmail en `.env`).
- `main.py`: schedule **por estrategia base** (un `ScheduledEvent` por grupo, D8.7) → `_scan_group` corre los pipelines miembro (long/short) y llama `OutputSink.emit` una vez. Invariante (miembros comparten schedule/`partial_bar`) validado en `initialize()`.
- `scripts/notify_email.py`: transporte host-side de Gmail (fuera del algoritmo), `--dry-run` por defecto; `send_gmail` aislado y mockeado (envío real → E9). `scripts/run_tests.sh` monta `scripts/` para testearlo en Docker.
**Done when:**
- [x] Backtest produce archivos CSV/JSON legibles del ScanResult (envelope por base + CSV con columna `direction`; evidencia: `storage/results/swing_eod/latest.json`, IBM short)
- [x] El switch de destino por entorno está aislado en `output.py`, sin ramas de negocio fuera (criterio nº6 del SPECS) — grep limpio + demo config-only (`channels` cambia comportamiento sin tocar `.py`)

> **Cierre (commit `[Etapa 8]`):** salida materializada — envelope por estrategia base persistido a `storage/results/<base>/` (JSON+CSV+`latest.json`), correo híbrido (render puro compartido + canal por config), script host `notify_email.py` con dry-run. Hallazgo: `dataclasses.asdict()` deepcopia el `as_of` tz-aware (`GMT` de LEAN, no deep-copiable) → copia superficial en `_scanresult_to_dict`. Diferido a E9: envío real Gmail (token/app GCP) + `qc_notify` cloud live (ADR-002). Decisiones y pendientes en [.claude/fase-1-desarrollo-local/etapa-08-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-08-decisiones-y-pendientes.md).

## Etapa 9 — Validación integral Fase 1
**Estado:** pendiente
**Objetivo:** Fase 1 cerrada con los 6 criterios DONE WHEN del SPECS verificados
**Depende de:** Etapa 8
**Notas y deferrals acumulados:** [.claude/fase-1-desarrollo-local/etapa-09.md](.claude/fase-1-desarrollo-local/etapa-09.md) (incluye D9-1: optimización del batching de historia en live con Alpaca, diferido desde 5B)
**Ciclo 2026-09 (orden 7):** el prerrequisito de datos quedó resuelto con la **Opción C** (Etapa 9A); `lean live` sigue bloqueado (ADR-002) → DoD nº4 diferido y justificado. Absorbe 9A T7 (portabilidad) y T8 (matriz de proveedor), #23 (`qc_notify` en cloud, vía `[config]`) y #5 (anchor SPY: `spy.zip` termina en 2021, prod lo usa solo por market hours). **Toda evidencia de DoD debe salir de corridas posteriores a la Etapa 15** ([roadmap U4](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md)).

> ⚠️ **Prerrequisito bloqueante — resolver ANTES de iniciar esta etapa**
>
> `lean live "trade-scanner"` con Alpaca y `lean data download` requieren credenciales QC
> y una org con licencia `AlpacaBrokerage` (plan Researcher mínimo). Sin esto, ambos
> comandos fallan al intentar instalar el módulo NuGet del brokerage.
>
> Opciones documentadas en [ADR-002](.claude/decisions/ADR-002-qc-module-auth-constraint.md):
> - **A** — Suscripción QC Researcher (pago, flujo estándar)
> - **B** — Compilar módulo Alpaca desde su repo open source y montarlo en Docker ($0, más frágil)
> - **C** — Script de descarga directa desde API REST de Alpaca para datos históricos ($0, solo resuelve datos, no `lean live`)
>
> Elegir y documentar la opción antes de arrancar.

**Alcance:**
- Backtest 6–12 meses; revisar watchlists de fechas conocidas manualmente.
- `lean live "trade-scanner"` paper local con Alpaca: una sesión completa, verificar ambos scans, working bar real, salida y logs.
- Verificar portabilidad de fuente: cambiar provider en `lean.json` (Alpaca ↔ QC) sin tocar código.
**Done when:**
- [ ] Backtest 6–12 meses con watchlists revisadas manualmente
- [ ] Una sesión live paper completa con ambos scans, working bar real y salida correcta
- [ ] Cambio de provider en `lean.json` sin tocar código verificado
- [ ] Checklist de los 6 criterios DONE WHEN del SPECS (§8 de este plan) firmado → Fase 1 cerrada; sigue Fase 2 (deploy VPS, fuera de este plan)

## Etapa 9A — Datos reales D/W/M vía Alpaca REST (Opción C de ADR-002)
**Estado:** pausada — T1–T6 cerradas; T7 (portabilidad local↔cloud) y T8 (matriz de proveedor) se cierran dentro de la **Etapa 9**; T9 (live paper) diferida por QC pago (ADR-002)
**Objetivo:** datos diarios reales multi-símbolo en formato LEAN, descargados host-side (`scripts/alpaca_to_lean.py`), sin tocar el algoritmo
**Depende de:** Etapa 8
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-09a-conexion-alpaca.md](.claude/fase-1-desarrollo-local/etapa-09a-conexion-alpaca.md) · bitácora [etapa-09a-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-09a-decisiones-y-pendientes.md)
**Done when:**
- [x] T1–T6 (commit `5d1c429`, 2026-07-05): descarga Alpaca→LEAN, cross-check de fidelidad Alpaca↔Stooq ≤0,25 % (máx. 0,2259 % AAPL M:20), fixture SPY-Alpaca — 238 passed
- [ ] T7 — portabilidad local↔cloud (→ Etapa 9)
- [ ] T8 — matriz de proveedor (→ Etapa 9)
- [~] T9 — sesión live paper: diferida (ADR-002)

## Etapa 9B — Correcciones del triaje Codex E1–E8
**Estado:** completada (2026-07-05) — 19 de 20 hallazgos VIGENTES corregidos; suite A: 253 → B: 270 → C: 284 passed; smoke backtest dev sin errores
**Depende de:** Etapa 8
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-09b-correcciones-triaje-E1-E8.md](.claude/fase-1-desarrollo-local/etapa-09b-correcciones-triaje-E1-E8.md) · triaje [revisiones/20260619-205134/triaje-E1-E8.md](revisiones/20260619-205134/triaje-E1-E8.md)
**Done when:**
- [x] Grupo A (ALTO) `b5294bb`, Grupo B (MEDIO) `9acf292`, Grupo C (BAJO) `53be8bd`
- ➡️ **#12 (ALTO, el scan cruza universos entre estrategias) NO corregido** → Etapa 14. Está **activo** cuando `swing_eod_short` está habilitado (roadmap H1: 500/1163 candidatos short cruzados en el backtest prod del 2026-09-20). Propuesta: [propuesta-diseno-12.md](revisiones/20260619-205134/propuesta-diseno-12.md)

## Etapa 10 — Refinamiento post-9B (`enabled` por estrategia + `filters` por TF:periodo)
**Estado:** completada (2026-07-09, commit `8b0afc2` "add: some improvements" — sin el tag `[Etapa 10]` en el mensaje)
**Depende de:** Etapa 9B
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-10-refinamiento.md](.claude/fase-1-desarrollo-local/etapa-10-refinamiento.md)
**Done when:**
- [x] R1: `enabled` por estrategia en `config/strategies.json` (ausente ⇒ `true`), leído en `initialize()`
- [x] R2: bloque `filters` `{"TF:period": [buckets]}` + `resolve_filters` con validación; SMA20 D/W/M dividida en una rule por TF; tests
- ⚠️ Hallazgos posteriores (roadmap H2b/H2c) → Etapa 15: `filters["W:8"]` no tiene rule consumidora; `filters["D:8"]` alimenta una rule `required=False`; el vocabulario canónico "above" invierte en silencio un short escrito en vocabulario natural

## Etapa 11 — Rango del backtest derivado del universo + resultados por fecha (re-scope)
**Estado:** pendiente — **orden 4** del ciclo; se ejecuta como change `derive-backtest-range-from-universe`
**Depende de:** Etapa 13 (`session_date` y preflight de cobertura)
**Spec original:** [.claude/fase-1-desarrollo-local/etapa-11-fecha-desde-universo.md](.claude/fase-1-desarrollo-local/etapa-11-fecha-desde-universo.md) — **superseded en parte**: la premisa `end_date = asof` y la prioridad del footer quedaron refutadas (roadmap H4/H4b: con `end_date` = último día hábil la sesión no se escanea; el footer es la fecha de descarga). Re-scope en [roadmap U2](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md).
**Done when:**
- [ ] Spike documentado en `design.md` con el extracto de log de la opción elegida (candidata o plan B)
- [ ] Con los CSV del 09-19: log `asof=2026-09-18`, y `latest.json.as_of` corresponde a la **sesión 2026-09-18** (el `price` de un candidato = cierre del 09-18 en su zip); exactamente **un** scan por sesión
- [ ] **Test**: dos CSV de sesiones distintas → `ValueError` en la reconciliación de fechas
- [ ] `results/{base}/{YYYYMMDD}/` y `results/{base}/latest.json` coexisten; `notify_email.py --base swing_eod` sin cambios funciona
- [ ] `main.py` sin fechas prod hardcodeadas; dev inalterado; README sin el paso 4 manual
- [ ] Al cerrar: DEVLOG/ROADMAP con una entrada por etapa

## Etapa 12 — Base estable + adopción de OpenSpec (bootstrap del ciclo 2026-09)
**Estado:** en progreso (desde 2026-09-23) — **orden 1**
**Objetivo:** config sembrada == versionada (short apagado), PLAN resincronizado, OpenSpec instalado y validado sin contradecir CLAUDE.md, baseline reproducible de la watchlist long para el gate G4
**Depende de:** ninguna etapa de código
**Rama:** `feature/etapa-12-bootstrap-openspec`
**Spec detallado:** [.claude/fase-1-desarrollo-local/etapa-12.md](.claude/fase-1-desarrollo-local/etapa-12.md) · bitácora [etapa-12-decisiones-y-pendientes.md](.claude/fase-1-desarrollo-local/etapa-12-decisiones-y-pendientes.md)
**Done when:** (detalle y criterios de aceptación en el spec)
- [x] Fase A — `develop`/`main` fast-forward a `f8ded63` y pusheados; tag `scan/v2026.09.23-pre-ciclo`; rama de etapa con la spec como primer commit
- [x] T1 — `run_tests.sh` verde: **304 passed** (2026-09-23); `docker run hello-world` OK
- [x] T2 — ObjectStore resembrado: config sembrada == versionada, `swing_eod_short.enabled = false` en `storage/`
- [x] T3 — PLAN §7 resincronizado + CLAUDE.md flujo paso 1 + nota de supersesión en etapa-11 *(2026-09-23)*
- [x] T4/T5 — Node + OpenSpec instalados; `openspec init` solo Claude Code; `openspec validate --all --strict` exit 0 *(2026-09-23: Node 26.9.0, openspec 1.13.1, perfil custom core+verify, delivery commands, `config.yaml` verificado)*
- [ ] T6/T7 — `AGENTS.md` de solo lectura retirado; `run_review.sh` opcional (Codex no disponible) y apuntando a la ruta nueva; CLAUDE.md con reglas OpenSpec + modelo de ramas + disposición de la documentación + revisión por defecto `/opsx:verify` + `/code-review`
- [ ] T8 — spike `chore-openspec-smoke`: ciclo completo con `/opsx:*` (validate antes de archive, Purpose, retiro manual) sin flags prohibidos ni requisitos duplicados
- [ ] T9 — baseline `baselines/scan-vYYYY.MM.DD-baseline/` (resultados + manifiesto), tarball fuera del repo, 0 tickers fuera de `swing_advances`, tag
- [ ] T10 — merge `--no-ff` a `develop`, `main` == `develop`, tags en `origin`, ramas integradas borradas
- [ ] T11 — decisión Finnhub escrita en `docs/ROADMAP.md` (bajo `# Post V1`; se ejecuta antes de T10)

## Etapa 13 — Cobertura de datos del ciclo semanal
**Estado:** pendiente — **orden 2**; primer change de OpenSpec: `add-data-coverage-gate`
**Objetivo:** preflight host-side de frescura y profundidad de historia + cobertura (`universe_size`, `ready`, excluidos con motivo) y `config_sha256` en el envelope, para que ninguna watchlist oculte qué parte del universo no se evaluó
**Depende de:** Etapa 12
**Detalle:** [roadmap U1](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md)
**Done when:**
- [ ] `session_date` sobre los CSV del 09-19 → `2026-09-18`; CSV sin columna `Time` → `ValueError` (tests)
- [ ] Preflight sobre los CSV del 09-19: 76/49 con zip, 0 desactualizados, exit 0. Con un zip borrado o truncado antes de la sesión → exit ≠ 0
- [ ] Coherencia preflight ↔ engine: el conjunto "historia corta" del preflight == `coverage.excluded` del envelope del último scan de la ventana; diferencias explicadas en `design.md`
- [ ] `latest.json` de un backtest prod trae `coverage` por miembro y `config_sha256`; el hash coincide con `sha256sum storage/config/strategies.json`
- [ ] G4: candidatos idénticos al baseline; solo cambian los campos nuevos
- [ ] Test: miembro con universo vacío post-filtro → sección vacía, `WARNING` en el log y `coverage.universe_size = 0`
- [ ] README con el runbook de 3 pasos (refresh → preflight → backtest)

## Etapa 14 — Scan acotado al universo declarado de cada estrategia (#12)
**Estado:** pendiente — **orden 5**; change `partition-scan-universe-per-strategy` + ADR-006
**Objetivo:** cada pipeline escanea exactamente el mapa de su universo; la unión global solo decide suscripción y warmup. Precondición de un rollback limpio del lado corto
**Depende de:** Etapa 11
**Detalle:** [roadmap U3a](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md) · [propuesta-diseno-12.md](revisiones/20260619-205134/propuesta-diseno-12.md)
**Done when:**
- [ ] Tests: mapas disjuntos por miembro + partición L5-style (cierra #25) + unión > 200 → `ValueError`
- [ ] Test unitario de invariancia: `run_group_scan` con un FakePipeline long produce la misma sección long con y sin el miembro short
- [ ] G4 con short activo en la rama: `check_watchlist_universe.py` exit 0 sobre toda la ventana
- [ ] Invariancia del long en backtest: para cada `results/swing_eod/**/2026*.json`, `jq -S .sections.long` idéntico al del baseline
- [ ] ADR-006 aceptado; en el log, cada pipeline solo lista exclusiones de su propio universo

## Etapa 15 — Lado corto habilitado (`swing_eod_short`)
**Estado:** pendiente — **orden 6**; change `enable-short-side` + enmienda a ADR-005
**Objetivo:** encender el short con `filters` explícitos en vocabulario absoluto (el de la evidencia), validación de claves muertas, log del conjunto efectivo por rule, anotación `ssr_likely`, y rollback por `enabled: false` ensayado
**Depende de:** Etapa 14 (archivada). Precondiciones: decisión del trader sobre el setup short (espejo del pullback long vs tendencia) y aprobación de la enmienda a ADR-005
**Detalle:** [roadmap U3b](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md) (incluye §Rollback)
**Done when:**
- [ ] Decisión de setup short registrada en `design.md`; enmienda a ADR-005 aceptada
- [ ] Tests: short con `"W:20": ["near","below_mild"]` → rule permite exactamente `{near, below_mild}`; long sin cambios; clave muerta → `ValueError`
- [ ] G4 específico completo (5 checks del roadmap), con la revisión del trader (≥3 corridas semanales reales) registrada en `design.md` y por encima del umbral fijado
- [ ] `ssr_likely` visible en CSV/JSON/correo; decisión HTB escrita
- [ ] Docs corregidos: §6 de este plan ya no afirma el espejo implícito; SPECS §6, `pipeline.py`, `swing_eod.py`
- [ ] Promoción: `enabled: true` commiteado, tag creado, rollback ensayado una vez en la rama (flag → reseed → backtest → long idéntico)

---

## 8. Definition of Done global de Fase 1
1. Warmup preciso: SMAs por timeframe declarado cuadran con referencia.
2. Watchlists reproducibles con evidencia por candidato.
3. Schedules disparan según calendario de mercado en un solo nodo.
4. Working bar funcional en scan intradía (`partial_bar=True`).
5. Cambio de fuente de datos = solo `lean.json`.
6. Salida/notificación por entorno aislada en `output.py`.
