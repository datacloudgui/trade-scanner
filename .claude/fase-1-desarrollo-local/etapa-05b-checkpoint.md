# Etapa 5B — Checkpoint de diseño (refinamiento del pre-spec)

**Estado:** borrador de diseño / pre-spec refinado — NO es el spec final ni se ha implementado nada.
**Fecha:** 2026-06-11 (sesión de refinamiento; guardado a 97% de usage antes de posible corte).
**Origen:** conversación de validación "¿hay que refinar el pre-spec de 5B con los resultados de 5A?".
**Insumos revisados:** PLAN.md §5B, [etapa-05.md](etapa-05.md) (análisis T4–T7), [etapa-05a.md](etapa-05a.md), [etapa-05a-decisiones-y-pendientes.md](etapa-05a-decisiones-y-pendientes.md), y el código real de 5A (`core/symbol_data.py`, `core/timeframes.py`, `trade-scanner/main.py`, `scripts/seed_sample_data.sh`, `config/strategies.json`, universos en `storage/`).

> **✅ SUPERADO (2026-06-11):** este checkpoint se formalizó en el spec **[etapa-05b.md](etapa-05b.md)** (reordenado a slice-vertical SPY por fases, tareas T1–T8 listas para desarrollo) y PLAN.md §5B quedó en `en progreso`. Este archivo queda como referencia del razonamiento; la fuente operativa es `etapa-05b.md`.

---

## 1. Decisiones cerradas en esta sesión (4 preguntas + fuente de datos)

| Tema | Decisión |
|---|---|
| **Símbolos de validación** | **Solo SPY + AAPL + IBM** (3, no 5). |
| **Granularidad del archivo de validación** | **K=5 filas por serie** (últimos 5 puntos de cada SMA), no 1 — detecta off-by-one de fechas. |
| **M:200 en dev** | **Sí, validar M:200** en el marco mayor (la data lo permite con fuentes profundas). |
| **Fuente de datos** | **Las tres**, complementarias (ver §3): Stooq (primaria) + sample data LEAN (baseline) + Alpaca free (smoke-test de conectividad). |
| **`plan_warmup` global vs por símbolo** | **Global** (todos los símbolos comparten estrategias → requirements idénticos → un `WarmupPlan` por conjunto de estrategias). Resuelve pregunta abierta de 5A. |

Decisiones heredadas ya firmes (de etapa-05.md / 5A): plataforma de referencia TradingView **o** IBKR (manual, sin APIs); tolerancia **≤0,25%** relativa; `SPLIT_ADJUSTED` (o equivalente, ver §3.4); prod → `D:[8,20,200]`, `W:[8,20,200]`; cableado manual de SMAs (D3); presupuesto vía `plan_warmup(budget=...)`.

---

## 2. Refinamientos al pre-spec por hallazgos de 5A (qué cambia vs etapa-05.md / PLAN §5B)

- **R1 — Universo ↔ data (era bloqueante; resuelto por §3).** El borrador asumía "un `SymbolData` por símbolo del universo", pero los CSV de universo son movers Barchart 2026 (`STI`, `STAK`…) **sin data local**. Solución: el backtest de validación de 5B usa un **universo dev con SPY/AAPL/IBM** (los símbolos que sí tendrán data sembrada). Crear `universes/sample_dev.csv` (o equivalente) y apuntar `env=dev` a él; prod sigue intacto. Ejercita el pipeline `UniverseSpec→SymbolData` real.
- **R2 — El warmup DEBE cerrar con `scan()` (hallazgo #1 de 5A).** `SymbolData` **no tiene método `warmup(bars)`** (esa línea del T2 original se descartó). El loop de warmup en `main.py` es: por símbolo, `sd.update(bar)` por cada barra histórica diaria, y **cerrar con `sd.scan(last_bar.end_time)`** o las SMAs quedan un periodo frías. `buffer_bars` absorbe el +1 en producción.
- **R3 — La verificación de equivalencia daily↔minute se ELIMINA de 5B (5A T3.9).** Ya se probó identidad exacta (`==`). 5B la hereda gratis; no re-verificar.
- **R4 — Forma del presupuesto.** El borrador escribió `warmup_budget_days` (escalar). El `plan_warmup` **implementado** recibe `budget: dict[str,int]` **por resolución fuente** (`{"daily": 1200}`). La key en `environments` de `strategies.json` debe matchear esa forma: `"warmup_budget": {"daily": N}`. El presupuesto es **dependiente del proveedor** (no constante): en dev/local con data profunda se sube para habilitar M:200; en prod/Alpaca-free se capa más bajo.
- **R5 — Ventana + suscripción (mecánico).** `main.py` hoy es 2013-10-07..11 SPY-only. 5B necesita: ventana donde los 3 símbolos tengan data + ≥ profundidad de warmup previa; suscripción daily/minute por símbolo con `SPLIT_ADJUSTED`; wiring de cada `sd.daily_consolidator` vía `self.subscription_manager.add_consolidator(symbol, sd.daily_consolidator)`.
- **R6 — `plan_warmup` global** (ver §1).

Interfaz real de 5A disponible para `main.py` (verificada en código):
`SymbolData(symbol, requirements)` · `.update(bar)` · `.scan(time)` · `.daily_consolidator` (prop) · `.working_bar` (prop) · `.declared` / `.timeframes` (introspección para logs) · `.sma(tf,n)` · `.is_ready(tf?,n?)`.
`timeframes.py`: `TIMEFRAMES`, `TimeframeSpec.warmup_bars(n)`, `plan_warmup(requirements, budget=None, registry=None) -> WarmupPlan(depth_by_resolution, included, excluded)`.

---

## 3. Diseño de datos: triple fuente complementaria

### 3.0 Por qué tres (y por qué no añade mucho)
El **converter a formato LEAN es la única pieza de trabajo real** y es compartido. Sobre él, las tres fuentes son adiciones pequeñas con roles distintos:

| Fuente | Rol | Profundidad | Esfuerzo extra | M:200 |
|---|---|---|---|---|
| **Stooq** | **Primaria** — validación recent contra TradingView | 30+ años, hasta hoy | el converter (~50-60 líneas) | ✅ |
| **Sample data LEAN** | Baseline garantizado-compatible + cross-check del converter | AAPL/IBM ~1998–2014 | ~6 líneas en `seed_sample_data.sh` (curl) | ✅ (fecha vieja) |
| **Alpaca free (IEX)** | Smoke-test de conectividad (de-risk Etapa 9) | 2016-01-01+ (~10 a) | script standalone ~30 líneas | ❌ (solo ~10 a) |

**Cross-validación de regalo:** si Stooq y los zips LEAN dan la misma SMA en fechas solapadas, eso valida el converter por sí solo.

### 3.1 Formato LEAN daily (VERIFICADO inspeccionando `data/equity/usa/daily/spy.zip`)
- Zip `<sym>.zip` contiene `<sym>.csv` con filas: `YYYYMMDD 00:00,O,H,L,C,V`
- **Precios ×10000** (deci-cents): `973100` = $97.31. Volumen entero crudo.
- `factor_files/<sym>.csv`: `fecha,price_factor,split_factor,ref_price`.
- `map_files/<sym>.csv`: `fecha,symbol,exchange` (ej. `19980102,spy,P` … `20501231,spy,P`).
- El SPY local ya cubre **1998–2021** (no solo 2013): M:200 para SPY ya es viable localmente.

### 3.2 Converter host-side (núcleo compartido) — `scripts/`
- Lenguaje: Python 3.11 del `.venv`. **`requests` crudo, sin SDK de Alpaca/datos** (honra la regla "sin SDKs de datos"; es data-prep host-side, fuera del algoritmo, análogo a `seed_sample_data.sh`).
- Pasos: fetch → parsear fecha + `OHLC*10000` (int) → ordenar ascendente → escribir `<sym>.csv` dentro de `<sym>.zip` en `data/equity/usa/daily/`.
- **factor_files NEUTROS** (`<firstdate>,1,1,<ref>`): si la fuente entrega split-adjusted y los factors son 1, LEAN sirve los precios tal cual → **agnóstico al `data_normalization_mode`** (ADJUSTED/SPLIT_ADJUSTED/RAW dan lo mismo) y cuadra con TradingView. **Esto reemplaza** la tarea vieja de scrapear factor/map del repo LEAN.
- map_files de una línea (símbolo activo en rango amplio).

### 3.3 Fetchers por fuente
- **Stooq:** GET CSV directo, sin key. URL estilo `https://stooq.com/q/d/l/?s=spy.us&i=d`. Verificar al implementar: convención de ajuste (split-adjusted), orden de fechas, headers de columnas. **Confirmar el patrón de URL y el toggle split antes de codear.**
- **Sample data LEAN:** extender `seed_sample_data.sh` con `fetch daily/aapl.zip`, `daily/ibm.zip`, `factor_files/{aapl,ibm}.csv`, `map_files/{aapl,ibm}.csv` (mismo `BASE_URL` del repo público; cero conversión). **Confirmar que existen esos paths en el repo.**
- **Alpaca smoke-test (standalone, NO alimenta la validación):** GET `https://data.alpaca.markets/v2/stocks/SPY/bars?timeframe=1Day&adjustment=split&feed=iex&start=...` con headers `APCA-API-KEY-ID`/`APCA-API-SECRET-KEY` desde `.env`. Imprime N barras y confirma que las keys sirven. **Distinción clave: esto valida la API de DATOS de Alpaca, NO el path de `lean live` (que usa el módulo `AlpacaBrokerage` de QC — ADR-002, otra cosa).**

### 3.4 Modo de ajuste
Con factor files neutros + fuente split-adjusted, el resultado es agnóstico al modo. Aun así declarar `SPLIT_ADJUSTED` explícito en `add_equity` (decisión firme) para dejar la intención clara y robustez si en el futuro se usan factor files reales.

### 3.5 BLOQUEANTE pendiente
- **`.env` tiene las keys de Alpaca VACÍAS** (`ALPACA_KEY_ID=`, `ALPACA_SECRET_KEY=`). El smoke-test de Alpaca no corre hasta llenarlas. (El usuario dijo tenerlas listas; hay que pegarlas en `.env`, que está gitignoreado.)

---

## 4. Esquema de tareas propuesto para `etapa-05b.md` (a formalizar)

- **T-data1:** converter host-side compartido (formato §3.1) + fetcher Stooq → zips/factor/map de SPY/AAPL/IBM en `data/`. Cross-check vs sample LEAN.
- **T-data2:** extender `seed_sample_data.sh` con AAPL/IBM (zips LEAN, baseline).
- **T-data3:** smoke-test Alpaca standalone (conectividad + keys). Requiere `.env` lleno.
- **T-univ:** `universes/sample_dev.csv` con SPY/AAPL/IBM; `env=dev` apunta a él (R1).
- **T-config:** `strategies.json` → prod `D:[8,20,200]`, `W:[8,20,200]`; `environments[*].warmup_budget = {"daily": N}` (R4); presupuesto dev alto (M:200 on), prod/Alpaca bajo.
- **T-main:** integración `main.py` — `SymbolData` por símbolo (unión), warmup batch por resolución (`self.history`), **cierre con `sd.scan(last_end_time)`** (R2), wiring `subscription_manager.add_consolidator` (R5), `plan_warmup` global (R6), logs (profundidad derivada + driver, duración, ready/no-ready, warning por serie excluida del presupuesto).
- **T-valid:** archivo `validation/sma_validation_<fecha>.csv` vía ObjectStore (solo `env=dev`), **K=5 filas/serie**, columnas `ticker,timeframe,period,bar_end_time,bar_close,sma_value,bars_consumed`.
- **T-regr:** validación manual del usuario (TradingView/IBKR, ≤0,25%) → congelar valores como fixture + test de regresión en `tests/`.

Done-when (heredan de PLAN §5B, ajustados): warmup completo con log de profundidad/duración/ready; archivo de validación con SMA 8/20/200 en D/W/M (M:200 incluido) para los 3 símbolos; desviaciones ≤0,25% como fixture+regresión; viabilidad M:200 documentada por proveedor + guardrail del presupuesto operativo; prod con SMA 200 y backtest sin errores; smoke-test Alpaca documentado.

---

## 5. Verificaciones pendientes antes/durante implementación (NO confirmadas aún)
- Patrón de URL y convención de ajuste de **Stooq** (split-adjusted, orden, headers).
- Existencia de `daily/aapl.zip`, `daily/ibm.zip` + factor/map en el repo público de LEAN.
- Endpoint y parámetros exactos del **smoke-test de Alpaca** (v2 bars, feed=iex, adjustment=split).
- Llenar keys de Alpaca en `.env`.
- Ventana de backtest concreta que cubra warmup (W:200 ≈ 4 años; M:200 ≈ 17 años de historia previa al start).

## 6. Pendientes de higiene heredados de 5A (decisión del usuario, fuera de scope técnico)
- `config/strategies.json` sin commitear desde antes (dev: `top_n` 5→2, `max_universe` 10→2) — **confirmar si es intencional** (el cambio de R4/T-config lo va a tocar igual).
- `.DS_Store` modificado — candidato a `.gitignore`.
- `etapa-04-decisiones-y-pendientes-md` sin extensión `.md` — renombrar.

---

## Fuentes consultadas
- Alpaca free / IEX desde 2016-01-01: https://docs.alpaca.markets/us/docs/market-data-faq · https://forum.alpaca.markets/t/iex-feed-historical-data/13681
- Stooq CSV gratis, 30+ años, split-adjusted: https://stooq.com/db/h/ · https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/
