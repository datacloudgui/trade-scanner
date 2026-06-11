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
  "strategies": {
    "swing_eod":    { "universe": "swing", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "after_close", "top_n": 50, "max_extension_pct": 0.10 },
    "market_close": { "universe": "swing", "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
                      "schedule": "before_close_30m", "top_n": 50, "max_extension_pct": 0.10 }
  }
}
```

- **Por qué ObjectStore y no `get_parameter`:** `self.get_parameter` solo devuelve strings planos y no expresa el mapa anidado `timeframes`; la UI de parámetros de QC cloud es plana. ObjectStore es el único mecanismo portable local↔cloud que soporta estructura anidada y mantiene la config fuera del código (mismo canal que los universos CSV). El `config.json` del proyecto queda solo como archivo de LEAN (algorithm-language, etc.).
- `timeframes` = mapa timeframe → periodos de SMA requeridos.
- Por símbolo, L5 calcula la **unión** de timeframes/periodos de todas las estrategias que lo incluyen y crea solo esos consolidators/indicadores.
- **Warmup derivado**: barras diarias necesarias = `max` sobre lo declarado. Regla: `D:n → n+5` barras; `W:n → n*5+10`; `M:n → n*21+21`. Ej.: `M:[20]` → ~441 barras diarias. Nada de "504 fijo".
- `working_bar` del consolidator diario expone el OHLC parcial del día en curso para scans intradía (suscripción `Resolution.MINUTE`).
- SMAs estables intradía: los indicadores solo se actualizan al cierre de su barra; el scan intradía compara precio actual (working bar) vs medias del último cierre.

## 5. Contratos de datos EN DEFINICION

**CSV de universo** (mínimo; columnas extra se ignoran salvo que el filtro las use):
```csv
ticker,price,avg_dollar_volume
AAPL,232.5,1.2e10
```
Filtro simple declarativo en config: ej. `"universe_filter": "price > 5 and avg_dollar_volume > 5e6"`. Tope duro: 200 tickers post-filtro.

**ScanResult** (una fila por candidato, serializa a CSV y JSON):
```
strategy, as_of (UTC), ticker, partial_bar (bool), day_change_pct,
sma_evidence (valor y distancia % por cada SMA evaluada), passed_rules (lista)
```

## 6. Estrategia de referencia

**`swing_eod`** (tras el cierre): universo `swing` filtrado → top N por `day_change_pct` → regla `AboveSMA(20, D∧W∧M)` → regla `NotExtended(sma=8 D, max 10%)` → ScanResult.
**`market_close`** (15:30 ET): mismas reglas; precio/OHLC desde working bar; resultado marcado `partial_bar=True`.
Variante losers: top N negativos, reglas propias (placeholder, sin reglas en V1).

---

## 7. FASE 1 — Etapas (spec-driven; no avanzar a una etapa sin cerrar el Done when de la anterior)

## Etapa 0 — Entorno de desarrollo
**Estado:** pendiente
**Objetivo:** máquina lista para correr LEAN CLI (válido para cualquier PC)
**Depende de:** nada
**Alcance:**
- Instalar Docker Desktop; verificar con `docker run hello-world`.
- Instalar pyenv; instalar Python 3.11 (`pyenv install 3.11.9`); fijar versión local en el repo (`pyenv local 3.11.9` → genera `.python-version`).
- Crear virtualenv del proyecto (`python -m venv .venv`); añadir `.venv/` a `.gitignore`.
- Instalar LEAN CLI dentro del venv: `pip install lean`; verificar `lean --version`.
**Done when:**
- [ ] `docker run hello-world` pasa sin errores
- [ ] `python --version` dentro del venv muestra `3.11.x`
- [ ] `lean --version` pasa sin errores
- [ ] `.venv/` en `.gitignore`; `.python-version` en el repo

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
**Estado:** pendiente
**Objetivo:** CSV de universo real perfilado, contratos fijados y CSV sembrado en ObjectStore
**Depende de:** Etapa 2
**Alcance:**
- `scripts/explore_universe.py` sobre el CSV real: columnas, tipos, nulos, duplicados, tickers inválidos/no-US, rangos de price y volumen, conteo post-filtro.
- Confirmar o ajustar los contratos de datos borrador (abajo) con base en lo observado; actualizar este archivo.
- `scripts/seed_object_store.sh`: copiar CSV validado a `storage/universes/swing.csv`.

**Contrato CSV de universo — BORRADOR (confirmar en esta etapa):**
```
ticker,price,avg_dollar_volume,[columnas_extra_ignoradas]
AAPL,232.5,1200000000
```
- Columnas mínimas requeridas: `ticker`, `price`, `avg_dollar_volume`.
- Columnas extra permitidas; se ignoran salvo que `universe_filter` las referencie.
- Filtro declarativo en `config/strategies.json` (ObjectStore): string evaluable, ej. `"price > 5 and avg_dollar_volume > 5e6"`.
- Tope duro: 200 tickers post-filtro.

**Contrato ScanResult — BORRADOR (confirmar en esta etapa):**
```
strategy, as_of (UTC), ticker, partial_bar (bool), day_change_pct,
sma_evidence (valor + distancia % por cada SMA evaluada), passed_rules (lista separada por |)
```

**Done when:**
- [ ] Reporte de exploración del CSV generado y revisado
- [ ] Contratos de datos actualizados y aprobados (columnas reales, no borrador)
- [ ] CSV validado y sembrado en ObjectStore local

## Etapa 4 — UniverseSpec
**Estado:** pendiente
**Objetivo:** carga de universos por estrategia desde ObjectStore con filtro declarativo
**Depende de:** Etapa 3
**Alcance:**
- `core/universe.py`: lee CSV desde `self.object_store`, aplica `universe_filter` declarativo, valida tope 200, expone símbolos por estrategia (variantes por clave de universo), `refresh_universe()` no-op documentado.
- Tests: filtro, tope, CSV malformado.
**Done when:**
- [ ] Backtest loguea el universo cargado por estrategia con su conteo (≤200)
- [ ] Tests de filtro, tope y CSV malformado verdes

## Etapa 5 — TimeframeSpec + SymbolData + warmup (etapa crítica)
**Estado:** pendiente
**Objetivo:** consolidators e indicadores construidos dinámicamente según los timeframes declarados por estrategia, con warmup derivado y preciso
**Depende de:** Etapa 4
**Alcance:**
- `core/timeframes.py`: mapeo D/W/M → consolidator LEAN (`TradeBarConsolidator` diario, `Calendar.WEEKLY`, `Calendar.MONTHLY`) + fórmula de warmup §4.
- `core/symbol_data.py`: construye consolidators e indicadores SOLO para la unión de timeframes requeridos; `register_indicator`; expone `working_bar`; warmup empujando `self.history` (batch, no por símbolo en loop) a los consolidators.
- Tests unitarios: consolidators e indicadores standalone alimentados con TradeBars sintéticos (semana que cierra viernes, mes calendario, SMA con valores conocidos a mano).
- Validación de precisión: para 5 símbolos de muestra, comparar SMA20 D/W/M post-warmup contra valores de referencia de la plataforma de charting acordada; tolerancia documentada.
**Done when:**
- [ ] Tests unitarios de consolidators/indicadores con barras sintéticas verdes
- [ ] Solo se crean los consolidators/indicadores de la unión de timeframes declarados (verificado por test)
- [ ] Profundidad de warmup derivada por fórmula §4, no fija (verificado por test)
- [ ] Validación de precisión de SMAs contra plataforma de referencia registrada en `tests/` (criterio nº1 del SPECS)

## Etapa 6 — Features y Rules
**Estado:** pendiente
**Objetivo:** features reutilizables y reglas parametrizadas con evidencia, respetando capas
**Depende de:** Etapa 5
**Alcance:**
- `core/features.py`: `position_vs_sma(n, tf)`, `extension_pct(n, tf)`, `day_change_pct()` (con y sin working bar), `is_ready()` (indicadores calientes).
- `core/rules.py`: `AboveSMA(n, tfs)`, `NotExtended(n, max_pct)`, combinadores AND/NOT; cada regla devuelve pasa/no-pasa + evidencia (valores usados).
- Tests por feature y regla con SymbolData sintético.
**Done when:**
- [ ] Tests de cada feature y regla verdes
- [ ] Ninguna feature/regla importa nada fuera de SymbolData (revisión de respeto de capas)

## Etapa 7 — ScanPipeline + estrategias + schedule
**Estado:** pendiente
**Objetivo:** las dos estrategias V1 corriendo end-to-end en un solo nodo y produciendo ScanResults
**Depende de:** Etapa 6
**Alcance:**
- `core/pipeline.py`: ejecuta universo → ranking top_n → reglas → `ScanResult`.
- `strategies/swing_eod.py` y `strategies/market_close.py` como `StrategyConfig` declarativos (sin lógica nueva, solo composición).
- `main.py` completo: una instancia de pipeline por estrategia, ScheduledEvents desde config, símbolos no listos (warmup incompleto) excluidos y logueados.
**Done when:**
- [ ] `lean backtest` sobre ≥3 meses genera ScanResults reproducibles en fechas conocidas
- [ ] `market_close` reporta OHLC parcial del día con `partial_bar=True`
- [ ] Símbolos con warmup incompleto quedan excluidos y logueados

## Etapa 8 — OutputSink y notificación por entorno
**Estado:** pendiente
**Objetivo:** salida CSV/JSON y notificación seleccionadas por entorno, aisladas en un módulo
**Depende de:** Etapa 7
**Alcance:**
- `core/output.py`: serialización CSV+JSON del ScanResult; destino según entorno: local → archivo en ObjectStore/carpeta de resultados + log; QC cloud live → `self.notify` (NotificationManager). Detección vía `self.live_mode` + parámetro de entorno.
**Done when:**
- [ ] Backtest produce archivos CSV/JSON legibles del ScanResult
- [ ] El switch de destino por entorno está aislado en `output.py`, sin ramas de negocio fuera (criterio nº6 del SPECS)

## Etapa 9 — Validación integral Fase 1
**Estado:** pendiente
**Objetivo:** Fase 1 cerrada con los 6 criterios DONE WHEN del SPECS verificados
**Depende de:** Etapa 8

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


---

## 8. Definition of Done global de Fase 1
1. Warmup preciso: SMAs por timeframe declarado cuadran con referencia.
2. Watchlists reproducibles con evidencia por candidato.
3. Schedules disparan según calendario de mercado en un solo nodo.
4. Working bar funcional en scan intradía (`partial_bar=True`).
5. Cambio de fuente de datos = solo `lean.json`.
6. Salida/notificación por entorno aislada en `output.py`.
