# Etapa 5B — Warmup integrado + datos de muestra + validación de precisión

**Estado:** en progreso (2026-06-11)
**Depende de:** Etapa 5A (`core/timeframes.py` + `core/symbol_data.py`, 31 tests verdes)
**Estimado:** 8–11 h, repartidas por fase (F1 ~3–4 h ✅ · F2 ~5–7 h). El smoke-test de Alpaca salió de 5B (ver [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md))
**Contexto:** segunda mitad de la antigua Etapa 5. 5A entregó la lógica de consolidación/registro/warmup verificada por tests sintéticos; aquí se integra en `main.py` con datos reales, se valida la precisión de las SMAs contra una plataforma de referencia (criterio DONE nº1 del SPECS) usando data reciente de Stooq. El de-risk del path de datos live (Stooq custom-data vs Alpaca) se difirió a Etapa 9 — [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md). Refinamiento del pre-spec en [etapa-05b-checkpoint.md](etapa-05b-checkpoint.md); análisis original en [etapa-05.md](etapa-05.md).

---

## Objetivo

`main.py` construye un `SymbolData` por símbolo, ejecuta el warmup real (evaluando primero el `set_warm_up` nativo del engine, con rollback al push manual `self.history`+`scan()` de 5A si falla), y produce un archivo de validación con las SMAs por timeframe declarado. Las SMAs se validan manualmente contra TradingView/IBKR con tolerancia ≤0,25% y se congelan como test de regresión. La integración se construye primero como **slice vertical con SPY** (datos ya presentes, cero trabajo de datos) para obtener un *pipeline verde* temprano, y luego se amplían las fuentes manteniendo el proceso **agnóstico a la fuente de datos**.

---

## Decisiones de diseño

### D1 — Slice vertical SPY primero (orden de construcción)

Se construye el camino completo de `main.py` con **un solo símbolo (SPY)** antes de invertir en datos. Razón: el `spy.zip` local ya cubre **1998–2021** (23 años → M:200 viable) → cero trabajo de datos para el primer output; SPY solo ejercita todo el integration path (SymbolData, warmup, wiring de suscripción, `plan_warmup` global, logs, archivo de validación). El converter de datos —la única pieza de trabajo real— se difiere a F2 sin bloquear la integración. Alineado con el *walking skeleton* de Etapa 2 y con el ethos spec-driven (hito verificable antes de la inversión grande).

**El hito de F1 es "pipeline verde" (backtest corre + archivo escrito + regresión interina), NO el Done-when de precisión** (ese exige data reciente de F2).

### D2 — Entorno `dev` como harness de validación (overrides a nivel environment)

Los CSV de universo de prod son movers Barchart 2026 (`STI`, `STAK`…) **sin data local**. En vez de ensuciar la config de estrategias, `dev` actúa como harness controlado con overrides opcionales a nivel `environment` en `strategies.json`, leídos por `main.py` solo si existen (prod queda intacto):

- `universe` → fuerza el universo de TODAS las estrategias a `sample_dev` (SPY/AAPL/IBM).
- `timeframes` → fuerza el superset a validar: `{D:[8,20,200], W:[8,20,200], M:[8,20,200]}` (incluye M:200, que prod NO usa).
- `warmup_budget` → `{"daily": N}` por resolución fuente (forma que ya consume `plan_warmup`, R4): en dev alto (≥4221, habilita M:200); en prod bajo (excluye M:200 → warning).

Patrón coherente: "dev = arnés que sobreescribe universo y timeframes a un set conocido para validar la misma maquinaria que usará prod".

### D3 — Agnosticidad a la fuente: el converter escribe formato LEAN; `main.py` solo lee el feed

Boundary explícito: **todo lo que produce datos escribe archivos en formato LEAN dentro de `data/equity/usa/`; `main.py` solo lee vía `self.history`/feed y nunca sabe de dónde vino el zip.** El slice SPY prueba el lado consumidor; el converter prueba el lado productor. Añadir AAPL/IBM (zips LEAN) o Stooq/Alpaca-convertidos es "más archivos en `data/`", cero cambios en `main.py`. Converter host-side (`scripts/`, `requests` crudo, sin SDK de datos — data-prep fuera del algoritmo, análogo a `seed_sample_data.sh`). **factor_files neutros** (`factor=1`) → con fuente split-adjusted LEAN sirve los precios tal cual → agnóstico al `data_normalization_mode` y cuadra con TradingView. Reemplaza la tarea vieja de scrapear factor/map del repo LEAN.

### D4 — Estrategia de warmup: `set_warm_up` (engine) primero, manual como rollback; `plan_warmup` global

Se **evalúa primero** el warmup nativo del engine (`set_warm_up`): suscribir DAILY + `add_consolidator(sym, sd.daily_consolidator)` y dejar que el engine stremee la historia por la suscripción → consolidator diario → cadena W/M → SMAs. Ventajas: sin loop manual, **sin `scan()` de cierre** (el flujo natural de barras resuelve la emisión perezosa), sin tocar pandas, y es el **path idiomático de live** (Etapa 9). **Gate:** al terminar (`is_warming_up==False`) las SMAs deben quedar `ready` y **coincidir con la ruta manual** (cross-check contra el cálculo de 5A / fixture T4). Si coinciden → se adopta.

Si `set_warm_up` falla o diverge → **rollback** a la ruta manual probada en 5A: `plan_warmup` global → `self.history[TradeBar]` (tipado) + `sd.update(bar)` por barra + **cierre con `sd.scan(last_end_time)`** (sin esto las SMAs quedan un periodo frías — hallazgo #1; `buffer_bars` absorbe el +1). `plan_warmup` se calcula una vez global (requirements idénticos entre símbolos). La equivalencia daily↔minute ya se probó en 5A T3.9 → no se re-verifica (R3).

### D5 — 5B corre a `Resolution.DAILY` (validación de barras cerradas)

Solo hay minute data de SPY para 2013-10; M:200 exige arrancar ~2016. Por eso 5B suscribe a **DAILY** y valida **barras cerradas** (las SMAs W/M no incluyen la barra en curso — comportamiento correcto y deseado). `working_bar`/minute/`partial_bar` pertenecen a `market_close` y se ejercitan en **Etapa 7**, no aquí. La suscripción daily alimenta el consolidator diario 1:1.

### D6 — Doble fuente complementaria + cross-validación (SPY-only)

| Fuente | Rol | Profundidad | M:200 | Fase |
|---|---|---|---|---|
| **Sample data LEAN** (solo SPY) | Baseline garantizado-compatible + cross-check del converter (solo SPY) | SPY 1998–2021 | ✅ (fecha vieja) | F1 |
| **Stooq** | **Primaria** — los 3 símbolos; validación *reciente* contra TradingView | 30+ años, hasta hoy, split-adjusted | ✅ | F2 |

Cross-validación de regalo: SMA de SPY vía converter Stooq == SMA de SPY-zip en fechas solapadas → valida el converter por sí solo (SPY es el único símbolo con zip de referencia local; AAPL/IBM se validan manualmente). El smoke-test de Alpaca (data API, de-risk Etapa 9) se difirió fuera de 5B — [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md).

---

## Tareas

> **Marca `(FABLE xhigh)`** en subtareas que razonan sobre semántica de LEAN no trivial (warmup/`set_warm_up`/`scan`, formato de datos y factor files). El resto: `high` por defecto; tareas mecánicas (CSV, seed, commits) pueden bajar a `medium`.

### FASE 1 — Slice vertical SPY (datos cero → "pipeline verde")

#### T1 — Harness dev: universo + config (sin código de algoritmo)

- **T1.1** — `universes/sample_dev.csv` en **formato Barchart §5** (columnas `Symbol,Name,5D %Chg,Latest,Change,%Change,5D Chg,5D High,5D Low,5D Avg Vol,Time`) con fila **SPY** y valores que pasen el filtro `avg_vol_5d > 1e6 and price > 5` (AAPL/IBM se añaden en T5.2). Debe parsear limpio con `UniverseSpec` (alias map + footer strip).
- **T1.2** — `config/strategies.json`: en `environments.dev` añadir `universe: "sample_dev"`, `timeframes: {D:[8,20,200], W:[8,20,200], M:[8,20,200]}`, `warmup_budget: {"daily": 4300}`. Prod sin tocar todavía (su SMA 200 es T6.2). *(Nota: el cambio previo de dev `top_n`/`max_universe` 5→2/10→2 es intencional — se conserva.)*
- **T1.3** — `scripts/seed_object_store.sh`: incluir `sample_dev.csv` en el glob sembrado a `storage/universes/`.

**Criterio de aceptación:** `bash scripts/seed_object_store.sh` deja `storage/universes/sample_dev.csv`; un `UniverseSpec` sobre esa clave con el filtro dev devuelve `["SPY"]`.

#### T2 — Integración del warmup en `main.py` (corazón de la etapa)

- **T2.1 (FABLE xhigh)** — Suscripción y construcción de SymbolData. Por cada símbolo del universo dev: construir `requirements` desde el override `timeframes` del environment (o unión de estrategias en prod); instanciar `SymbolData(symbol, requirements)`; `add_equity(ticker, Resolution.DAILY, data_normalization_mode=DataNormalizationMode.SPLIT_ADJUSTED)` (D5); wiring `self.subscription_manager.add_consolidator(symbol, sd.daily_consolidator)` (R5) **antes** de cualquier warmup. **`set_start_date` ≥ ~2016** para que existan ≥4221 barras diarias previas (M:200 ≈ 16,8 a; SPY desde 1998); ventana corta (días) basta — el valor está en el warmup, no en la duración. Validar que la suscripción daily alimenta el consolidator diario 1:1.

- **T2.2 (FABLE xhigh)** — Warmup: `set_warm_up` primero, rollback a manual (D4).
  - **Estrategia A (preferida) — engine-managed:** con los consolidators ya añadidos (T2.1), llamar `self.set_warm_up(depth_by_resolution["daily"], Resolution.DAILY)`; guardar `on_data` y los scans/escritura con `if self.is_warming_up: return`. El engine stremea la historia por la suscripción → consolidator → SMAs, sin loop ni `scan()` de cierre.
  - **Gate de validación:** al terminar (`is_warming_up==False`), las SMAs de SPY deben quedar `ready` y **coincidir con la ruta manual / cálculo a mano** (cross-check contra el fixture T4). Coinciden → se adopta A y se documenta.
  - **Estrategia B (rollback) — manual probado en 5A:** si A falla o diverge, `plan_warmup` global → **`self.history[TradeBar](symbols, depth, Resolution.DAILY)` tipado, NO el DataFrame de pandas** (más liviano y respeta la regla "nada de resampling con pandas"; evita tocar pandas del todo), batch agrupado por resolución; push `sd.update(bar)` por barra; **cerrar con `sd.scan(last_bar.end_time)`** (hallazgo #1). Documentar el rollback y su causa.
  - En ambas estrategias: las series en `plan.excluded` (sobre presupuesto) no se construyen → warning por cada una.

- **T2.3 (FABLE xhigh)** — Logs de evidencia (env=dev): profundidad derivada **con su driver** (ej. `warmup: 1010 daily bars (driver W:200)` y `4221 (driver M:200)`), duración del warmup (filas + tiempo, baseline SPECS §11), conteo `ready/no-ready` por símbolo, warning por cada serie excluida del presupuesto, y **qué estrategia de warmup se usó** (`set_warm_up` adoptado vs rollback manual).

**Criterio de aceptación:** `lean backtest "trade-scanner"` en `env=dev` con SPY corre sin errores; el log muestra la profundidad derivada coherente con la fórmula (W:200→1010, M:200→4221), la duración, SPY `ready`, y la decisión de warmup; queda documentado si se adoptó `set_warm_up` (con el cross-check) o se hizo rollback a manual y por qué; en la ruta manual el batch usa `history[TradeBar]` tipado, una llamada por resolución.

#### T3 — Archivo de validación de SMAs

`validation/sma_validation_<fecha>.csv` vía `self.object_store.save()` (aparece en `storage/validation/`), **solo `env=dev`** (flag de config), escrito tras completar el warmup (en A: cuando `is_warming_up` pasa a falso; en B: tras el `scan()` de cierre). **K=5 filas por serie** (últimos 5 puntos de cada SMA, detecta off-by-one de fechas). Columnas: `ticker, timeframe, period, bar_end_time, bar_close, sma_value, bars_consumed`.

**Criterio de aceptación:** el archivo existe en `storage/validation/`, es legible, contiene 5 filas por cada serie activa `(ticker, tf, period)` con valores no nulos para SPY, y `bar_end_time` refleja la convención de LEAN (W lunes→domingo cierre viernes; M mes calendario).

#### T4 — Fixture de regresión interino (protege la matemática)

Congelar las SMAs computadas sobre **SPY-zip** como test de regresión en `tests/` (recalcular con la misma data y comparar con `==`/tolerancia estrecha). **No es** la validación manual de precisión (esa es T6.3); su rol es evitar que los refactors de F2 rompan la matemática en silencio, y sirve de cross-check del gate de `set_warm_up` (T2.2).

**Criterio de aceptación:** `bash scripts/run_tests.sh` verde con el nuevo test de regresión de SPY.

> **★ Hito F1 — "pipeline verde":** backtest dev SPY corre, loguea warmup (con la decisión `set_warm_up`/manual), escribe el archivo de validación, regresión interina verde. La precisión contra charts recientes llega en F2.

---

### FASE 2 — Data reciente Stooq + batch multi-símbolo + validación de precisión (Done-when real)

> **Reorganización (2026-06-11):** la antigua F2 (zips LEAN de AAPL/IBM) se **eliminó**; los 3 símbolos provienen ahora del converter Stooq (una sola fuente productora, sin sembrar zips extra). El check de **batch multi-símbolo** se **pliega** aquí (T6.1). El cross-check converter-vs-zip se mantiene **solo en SPY** (único símbolo con `spy.zip` de referencia local); la precisión de AAPL/IBM se valida manualmente (T6.3). El antiguo smoke-test de Alpaca se retiró de 5B → ver [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md) y Etapa 9.

#### T5 — Universo dev a 3 símbolos + converter host-side agnóstico (Stooq)

- **T5.1** — ✅ 2026-06-11 (redefinida por instrucción del usuario: zips LEAN ya descargados en vez de Stooq para este paso; decisión: **4 símbolos SPY/AAPL/IBM/FB**). Filas **AAPL, IBM, FB** añadidas a `universes/sample_dev.csv` (formato Barchart §5, pasan el filtro `avg_vol_5d > 1e6 and price > 5`); `seed_sample_data.sh` extendido (daily+map+factor de aapl/ibm/fb, idempotente); `dev.max_universe` 2→4. `UniverseSpec` sobre `sample_dev` con el filtro dev devuelve `["AAPL","FB","IBM","SPY"]` (orden alfabético del parser). **FB: M:200 no-ready esperado** (IPO 2012, 2946 barras) → caso real de `is_ready=False`. Detalle en [etapa-05b-t5-checkpoint.md](etapa-05b-t5-checkpoint.md).
- **T5.2** — ✅ 2026-06-11. Núcleo del converter: `parsear fecha + OHLC×10000 (int) → ordenar ascendente → escribir <sym>.csv dentro de <sym>.zip`. Entregable [scripts/stooq_to_lean.py](../../scripts/stooq_to_lean.py) (stdlib `csv`+`zipfile`, sin SDK; D3). Verificado por **round-trip exacto** contra `spy.zip` (5849 filas byte-a-byte, entrada desordenada → salida ascendente) + edge cases (N/D, columnas extra, header faltante). **El `fetch` se separó del núcleo:** Stooq bloquea la descarga programática (proof-of-work anti-bot + cuota diaria `Access denied`) → por decisión del usuario el converter consume un **CSV manual** vía `--input` y el fetch automatizado se difiere a Etapa 9 (ADR-003). Detalle en [etapa-05b-t5-2-decisiones-y-pendientes.md](etapa-05b-t5-2-decisiones-y-pendientes.md).
- **T5.3 (FABLE xhigh)** — ✅ 2026-06-11; CSVs re-descargados 2026-06-12 con "skip dividends" → precios actualizados a **split-only adjusted**. factor_files neutros escritos para AAPL/IBM (`19840907,1,1,1` y `19620102,1,1,1`); map_files reutilizados del repo LEAN; zips Stooq AAPL/IBM reemplazaron los zips LEAN en `data/equity/usa/daily/`. Cross-check: fidelidad CSV→zip (20 fechas, ±1 unidad ×10000) + SMAs coherentes vía SymbolData. **T6.3: validar en TradingView con vista "Adjusted" (split-only)**. SPY `data/equity/usa/daily/spy.zip` conserva LEAN (T4 verde). Detalle en [etapa-05b-t5-3-decisiones-y-pendientes.md](etapa-05b-t5-3-decisiones-y-pendientes.md). run_tests.sh → 35 passed.
- **T5.4** — Fetcher Stooq: **confirmar patrón de URL** (`https://stooq.com/q/d/l/?s=spy.us&i=d`), toggle/convención split-adjusted, orden de fechas y headers de columnas antes de codear (pregunta abierta); bajar SPY/AAPL/IBM con historia hasta hoy.

**Criterio de aceptación:** el converter produce zips LEAN válidos para los 3 símbolos con data reciente; el cross-check **SPY** (converter vs zip) coincide dentro de tolerancia estrecha; `UniverseSpec` dev devuelve los 3 símbolos.

#### T6 — Batch multi-símbolo + config prod + validación manual + fixture autoritativo

- **T6.1** — ✅ 2026-06-12. CSVs Stooq re-descargados con "skip dividends" (split-only adjusted) → zips regenerados. Backtest dev con 4 símbolos (SPY/AAPL/IBM/FB): ready 3/4; FB frío en W:200 y M:200 (921 barras < 1010/4221); gate: `36/36 series exactas vs ruta manual (13574 filas vía history[TradeBar], 1 llamada batch)`; depth=4221 driver M:200; validation/sma_validation_20160104.csv (36 series, 180 filas); main.py sin cambios (agnosticidad ✅); 35 tests verdes. Detalle en [etapa-05b-t6-1-decisiones-y-pendientes.md](etapa-05b-t6-1-decisiones-y-pendientes.md).
- **T6.2** — ✅ 2026-06-12. `environments.prod.warmup_budget = {"daily": 1100}` añadido; prod usa unión de estrategias = `D:[8,20,200]`, `W:[8,20,200]`, `M:[8,20]` (sin override). Depth=1010 (driver W:200). Demo de warning con override temporal M:[8,20,200]: `WARNING [warmup] serie M:200 excluida del plan: necesita 4221 barras (daily), presupuesto 1100`. Config final sin override → plan limpio sin exclusiones, D:200 y W:200 incluidos. Backtest prod completa en 1.24s sin errores. Detalle en [etapa-05b-t6-2-decisiones-y-pendientes.md](etapa-05b-t6-2-decisiones-y-pendientes.md).
- **T6.3** — Validación manual del usuario (TradingView **o** IBKR, sin APIs): comparar los valores del archivo T3 (data Stooq reciente) para SPY/AAPL/IBM: SMA 8/20/200 en D y W; 8/20/200 en M (M:200 viable con Stooq). Tolerancia **≤0,25%** relativa; desviaciones mayores se explican (ajuste, convención de semana) o se corrigen.
- **T6.4** — Congelar los valores confirmados como **fixture autoritativo** + test de regresión en `tests/` (extiende/reemplaza el interino T4).

**Criterio de aceptación:** 3 símbolos `ready` con batch agrupado verificado en log y M:200 en los tres; agnosticidad demostrada (`main.py` sin cambios al añadir AAPL/IBM); desviaciones manuales ≤0,25% registradas; test de regresión verde en Docker; prod con SMA 200 en D/W corriendo y warning de exclusión de M:200 verificado.

> **★ Hito F2 — "Done-when real":** converter Stooq produce los 3 símbolos, batch agrupado verificado, validación manual ≤0,25% congelada como fixture autoritativo, prod con SMA 200 D/W + warning M:200. Cierra el criterio DONE nº1 de SPECS. El feed de datos para V1 (Stooq custom-data vs Alpaca) se decide en Etapa 9 — [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md).

---

## Scope

✅ Entra: integración warmup en `main.py` (DAILY, `set_warm_up`-primero con rollback manual), harness dev (overrides universe/timeframes/budget), archivo de validación K=5, doble fuente de datos (SPY-zip de baseline + converter Stooq para los 3 símbolos), validación manual ≤0,25% + fixtures de regresión, config prod con SMA 200 en D/W.

❌ No entra:
- **`working_bar`/minute/`partial_bar`** — Etapa 7 (D5: 5B valida barras cerradas a DAILY).
- **Features y Rules** (`position_vs_sma`, `extension_pct`) — Etapa 6.
- **Pipeline, ranking, ScanResult, exclusión de fríos del scan** — Etapa 7 (aquí solo se expone `is_ready` y se loguea).
- **OutputSink real** — Etapa 8 (el archivo de validación es artefacto temporal vía ObjectStore directo).
- **Consolidators intradía reales** (5m/15m/30m) — etapa futura.
- **Smoke-test de la API de datos de Alpaca** — retirado de 5B; de-risk de conectividad para Etapa 9 ([ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md)).
- **`lean live` / brokerage Alpaca / `lean data download` / feed de datos live de V1 (Stooq custom-data vs Alpaca) / optimización de batching de historia live** — ADR-002 + ADR-003 + Etapa 9 ([etapa-09.md](etapa-09.md)).
- **Medición de memoria de 200 símbolos en minute** — Etapa 9.

---

## Consideraciones técnicas específicas al stack

1. **Cierre con `scan()` (hallazgo #1 de 5A) — solo en la ruta manual (B):** sin `sd.scan(last_end_time)` al final del warmup las SMAs quedan un periodo frías. En la ruta `set_warm_up` (A) el flujo natural de barras lo resuelve solo. Si la validación manual muestra valores "casi correctos" desplazados, revisar esto (y `buffer_bars` expulsando la barra parcial inicial — T3.7 de 5A).
2. **Profundidad y memoria:** M:200 = 4221 barras diarias × 3 símbolos ≈ 12,6K filas — holgado. El presupuesto dev (`{"daily": 4300}`) la permite; el de prod la excluye a propósito (Alpaca free no tiene 17 a).
3. **Ventana de backtest:** la duración de la ventana es casi irrelevante (días); lo que importa es que la historia tenga ≥ profundidad de barras previas al `start_date`. Con SPY 1998–2021, `start ≥ ~2016` cubre M:200.
4. **Resolución DAILY (D5):** evita el hueco de minute data (solo 2013-10) y valida barras cerradas. Los `ScheduledEvents` disparan por exchange hours aunque la data sea daily; el reloj avanza con barras diarias 1998–2021.
5. **factor_files neutros (D3):** con fuente split-adjusted + factors=1, ADJUSTED/SPLIT_ADJUSTED/RAW dan lo mismo. **Ojo:** el `spy.zip` del repo LEAN trae factors REALES → SPY-zip SÍ es sensible al modo (úsalo como test del wiring del modo); la data convertida por nosotros no. No confundir ambos comportamientos en el cross-check.
6. **Convención de fechas (C4 de 5A):** `bar_end_time` cae al inicio del periodo siguiente (W lunes→domingo, cierre viernes; M mes calendario). Reportarlo tal cual en el archivo de validación y documentar la convención para que el usuario alinee fechas en TradingView.
7. **Stooq sin verificar:** patrón de URL, ajuste y orden de columnas se confirman empíricamente en T6.3 antes de codear el fetcher.
8. **`set_warm_up` (D4) — guards y orden:** los consolidators deben añadirse con `add_consolidator` **antes** de `set_warm_up`; durante el warmup `on_data` corre con data histórica → guardar scans/escritura con `if self.is_warming_up: return`; el engine emite las barras como flujo real, por lo que la emisión perezosa se resuelve sola (no hace falta `scan()` de cierre en este path). Incumplir esto es la causa típica de rollback a manual.
9. **Historia tipada en la ruta manual:** usar `self.history[TradeBar](...)` (overload tipado) en vez del DataFrame — más liviano, sin dependencia de pandas, y consistente con la regla de "no resampling manual con pandas".

---

## Done when (medible)

- [x] **F1:** `lean backtest` dev con SPY completa el warmup y loguea profundidad derivada con driver (W:200→1010, M:200→4221), duración, `ready/no-ready` y la **decisión de warmup** (`set_warm_up` adoptado con cross-check, o rollback a manual con causa); `storage/validation/sma_validation_*.csv` con K=5 filas/serie; regresión interina de SPY verde (`run_tests.sh`) ✅ 2026-06-11: set_warm_up ADOPTADO (gate 9/9), 9 series × 5 filas, 33 tests verdes
- [ ] **F2** *(ajustado 2026-06-11, decisión del usuario en T5.1: universo dev = 4 símbolos SPY/AAPL/IBM/FB; FB sin M:200 por IPO 2012)*: converter agnóstico produce zips válidos desde Stooq; cross-check **SPY** (converter == zip) dentro de tolerancia; los 4 símbolos `ready` con batch de historia/warmup agrupado por resolución (una llamada, no loop por símbolo) verificado en log; M:200 en SPY/AAPL/IBM y **FB documentado como M:200 no-ready** (caso real de `is_ready=False`, excluido y logueado); `main.py` sin cambios al añadir símbolos (agnosticidad); validación manual ≤0,25% para SPY/AAPL/IBM (D/W/M 8/20/200) registrada como fixture autoritativo + test de regresión; prod con SMA 200 en D/W corriendo y warning de exclusión de M:200 verificado
- [ ] Viabilidad de SMA 200 por marco/proveedor documentada (M:200 viable en Stooq/zip, no en Alpaca free) y guardrail `warmup_budget` con warning operativo
- [ ] Commit(s) `[Etapa 5B] ...` por fase

---

## Preguntas abiertas

- [x] **`set_warm_up` vs manual** — RESUELTA (T2.2, 2026-06-11): `set_warm_up` ADOPTADO; gate dev 9/9 series exactas vs ruta manual. Hallazgo: el flush `scan(self.time)` en `on_warmup_finished` sigue siendo necesario para la cadena W/M (el engine solo escanea el consolidator raíz registrado en `subscription_manager`). Detalle en [etapa-05b-decisiones-y-pendientes.md](etapa-05b-decisiones-y-pendientes.md).
- [x] **Patrón de URL y ajuste de Stooq** — CONFIRMADO empíricamente (T5.2, 2026-06-11): la descarga programática de `q/d/l/?s=<sym>.us&i=d` está **bloqueada** (proof-of-work JS anti-bot + cuota diaria `Access denied`). Formato confirmado: header `Date,Open,High,Low,Close,Volume`, fechas `YYYY-MM-DD`, decimales split-adjusted. Decisión: CSV manual + converter agnóstico; fetch automatizado → Etapa 9 (ADR-003).
- [ ] **Mecanismo del override de `timeframes` dev en `main.py`** — leerlo del environment vs derivarlo: se fija al implementar T2.1 (propuesta: si `environment.timeframes` existe, reemplaza la unión de estrategias para construir `requirements`).
- [ ] **Feed de datos live para V1 (Stooq custom-data vs Alpaca)** — decisión diferida a Etapa 9; evidencia de fiabilidad de Stooq a escala (~200 símbolos/quota) pendiente. Ver [ADR-003](../decisions/ADR-003-stooq-como-fuente-de-datos.md).
