# Fuentes de datos programáticas: top movers + earnings calendar

**Fecha:** 2026-07-09
**Objetivo:** evaluar alternativas gratuitas o casi gratuitas para obtener, de forma programática (API/librería), tres listas de acciones:

1. **Top movers % multi-periodo** (1D, 5D, 1M, 3M — estilo Barchart) con volumen.
2. **Top movers % intradía** (en cualquier momento del día) con volumen.
3. **Earnings** con fecha, hora **BMO/AMC** y volumen (hoy resuelto con Finviz: filtro volumen + AMC/BMO + próxima semana).

> **Contexto del proyecto.** El screener ya corre sobre **Alpaca free (datos IEX)** vía LEAN. Eso pesa en la recomendación: reutilizar Alpaca no añade dependencias ni credenciales nuevas. La contra conocida (ver `CLAUDE.md`): **el volumen IEX está subestimado** → usar **volumen relativo**, no absoluto.

---

## TL;DR — recomendación por caso

| Caso | Recomendación primaria | Alternativa | Por qué |
|------|------------------------|-------------|---------|
| **1. Movers 1D/5D/1M/3M + vol** | **Finviz** (`finvizfinance`, columnas *Perf Week/Month/Quarter*) | Calcular desde **EOD histórico** (yfinance / EODHD / Tiingo) | Ningún endpoint de "movers" da 5D/1M/3M; Finviz ya trae esas columnas + volumen + rel-volume, igual que Barchart. |
| **2. Movers intradía + vol** | **Alpaca Screener** (`movers` + `most-actives`) — ya integrado | **Yahoo** `day_gainers` (yfinance/yahooquery), sin API key | Alpaca ya está en el stack; near-real-time. Yahoo es el fallback gratis y sin credenciales. |
| **3. Earnings BMO/AMC + vol** | **Finnhub** `/calendar/earnings` (free, US, campo `hour` = bmo/amc/dmh) | **Nasdaq** earnings calendar (no oficial) o seguir con **Finviz** | Finnhub free cubre US con hora BMO/AMC; el volumen se hace *join* con la fuente de quotes. |

**Regla general sobre "volumen":** casi ninguna API de *earnings* trae volumen; se obtiene por *join* con una fuente de quotes/screener. En movers, Alpaca free da volumen **IEX** (subestimado → relativo); Finviz y Yahoo dan volumen **consolidado**.

---

## Nota transversal: por qué "movers multi-periodo" es un caso distinto

Los endpoints etiquetados *"top gainers/losers"* (Alpaca, Alpha Vantage, Yahoo `day_gainers`, FMP) son **de un solo día** (% vs. cierre anterior). **No existe** un endpoint gratuito estándar de "top movers a 5D / 1M / 3M". Para el caso 1 hay dos caminos:

- **A) Screener con columnas de performance ya calculadas.** Finviz expone *Perf Week (5D), Perf Month (1M), Perf Quarter (3M), Perf Half, Perf Year*. Yahoo Screener permite queries por rango pero con menos granularidad de performance. → **camino más rápido y el que más se parece a Barchart.**
- **B) Calcular uno mismo desde barras EOD.** Descargar OHLCV diario del universo y computar `pct_change` a 5/21/63 sesiones. Más control y sin depender de scraping, pero hay que mantener el histórico. Encaja natural con la arquitectura LEAN (consolidators + features).

---

## Caso 1 — Top movers % (1D / 5D / 1M / 3M) con volumen

| Fuente | Coste | Multi-periodo (5D/1M/3M) | Volumen | Acceso programático | Notas |
|--------|-------|--------------------------|---------|---------------------|-------|
| **Finviz** (no-Elite) | Gratis | ✅ Perf Week/Month/Quarter como columnas de screener | ✅ Volume + Rel Volume (consolidado) | `finvizfinance` / `pyfinviz` (scraping HTML) | Igual a lo que ya usas. Sin API oficial en free → rate-limit/ToS de scraping; añade *sleeps*. |
| **Finviz Elite** | ~US$39.5/mes | ✅ igual + export oficial | ✅ | Export CSV/Excel + snippets Python/Sheets oficiales | Casi-gratis con export soportado y datos ~real-time (sin delay). La vía "limpia" si Finviz es el core. |
| **yfinance (EOD)** | Gratis | ⚙️ se calcula desde histórico diario | ✅ consolidado | `yf.download(universe, period=...)` | No da ranking listo; tú computas % y ordenas. Sin API key. No oficial (Yahoo). |
| **EODHD** | Free tier / ~US$20/mes | ⚙️ desde EOD | ✅ | REST | Free tier corto; bulk EOD barato para el universo ≤200. |
| **Tiingo** | Free (limitado) | ⚙️ desde EOD | ✅ | REST | EOD gratis sólido para históricos; sin ranking de movers. |
| **Alpha Vantage** `TOP_GAINERS_LOSERS` | Gratis (25 req/día) | ❌ sólo 1D | ✅ (snapshot) | REST | Sólo día. 25 req/día lo hace inviable como fuente principal. |

**Recomendación caso 1:** **Finviz** (mantener `finvizfinance`; si molesta el scraping/ToS, **Elite ~US$39.5/mes** por export oficial y datos real-time). Si prefieres cero dependencia de Finviz y control total, **camino B**: bajar EOD con **yfinance/Tiingo** y calcular Perf 5D/1M/3M en `core/features.py`.

---

## Caso 2 — Top movers % intradía (cualquier momento) con volumen

| Fuente | Coste | Intradía | Volumen | Acceso | Notas |
|--------|-------|----------|---------|--------|-------|
| **Alpaca Screener** (`/v1beta1/screener/stocks/movers` + `most-actives`) | Gratis (plan basic) | ✅ near-real-time; resetea en el open | ⚠️ IEX (subestimado) → usar **relativo** | `alpaca-py` `ScreenerClient` o REST | **Ya en el stack.** `movers` = top gainers/losers %; `most-actives` = por volumen/trades. Verifica en tu cuenta que devuelve datos en el plan free. |
| **Yahoo** `day_gainers`/`day_losers`/`most_actives` | Gratis, **sin API key** | ✅ ~real-time (con delay Yahoo) | ✅ consolidado | `yfinance` (`EquityQuery`+`yf.screen`) o `yahooquery` `Screener` | Mejor fallback gratis. No oficial → puede romperse (issues recurrentes en yfinance). |
| **Finviz** screener (Change + Rel Volume) | Gratis / Elite | ✅ (~15 min delay en free) | ✅ | `finvizfinance` | Ordena por `Change`; filtra por rel-volume. Delay en free. |
| **Alpha Vantage** `TOP_GAINERS_LOSERS` | Gratis 25/día | ✅ snapshot US | ✅ | REST | Snapshot único del mercado; 25 req/día limita polling intradía. |
| **Financial Modeling Prep** gainers/losers | Free 250 req/día | ✅ 1D | ✅ | REST | Movers sí en free; earnings calendar **no** (ver caso 3). |

**Recomendación caso 2:** **Alpaca Screener** por reutilización de credenciales/stack y latencia. Recordatorio duro del proyecto: **volumen IEX subestimado → volumen relativo**. Mantener **Yahoo `day_gainers`** como fallback gratuito sin API key.

---

## Caso 3 — Earnings calendar (fecha + BMO/AMC) con volumen

| Fuente | Coste | Fecha + hora BMO/AMC | Volumen | Acceso | Notas |
|--------|-------|----------------------|---------|--------|-------|
| **Finnhub** `/calendar/earnings` | **Gratis** (60 req/min, US) | ✅ campo `hour`: `bmo`/`amc`/`dmh` | ❌ (join aparte) | REST / SDK | **Mejor free.** Rango de fechas `from`/`to` (tu filtro "próxima semana"). US en free; internacional es premium. |
| **Finviz** (tu setup actual) | Gratis / Elite | ✅ columna Earnings con `/a` (AMC) `/b` (BMO) + filtro | ✅ (mismo screener) | `finvizfinance` filtro `Earnings Date` | Ventaja única: **earnings + volumen en la misma query**. Es lo que ya haces. |
| **Nasdaq earnings calendar** (no oficial) | Gratis | ✅ `time`: pre/after/time-not-supplied | ❌ | `api.nasdaq.com/.../earnings` (JSON) | Buena cobertura y hora; endpoint no oficial, headers/UA sensibles. |
| **Alpha Vantage** `EARNINGS_CALENDAR` | Gratis 25/día | ⚠️ fecha sí, **BMO/AMC no** | ❌ | REST (CSV, horizon 3/6/12m) | Da fecha estimada pero **no** la hora del día → no cubre tu requisito clave. |
| **FMP** earnings calendar | **Premium** (ya no en free) | ✅ `time` + BMO/AMC | ❌ | REST | Antes free; en 2025 el earnings calendar quedó detrás de plan de pago. Descartado como "gratis". |
| **API Ninjas** earnings calendar | Free (limitado) | Parcial | ❌ | REST | Cobertura/actualidad menor; útil sólo como cruce. |

**Recomendación caso 3:** **Finnhub free** para la fecha + BMO/AMC programática (rango de fechas = tu "próxima semana"), y **join con volumen** desde Alpaca/Yahoo por ticker. Si valoras tener *earnings + volumen en una sola llamada*, **seguir con Finviz** es perfectamente válido (Elite si quieres export oficial). El volumen casi nunca viene en la fuente de earnings: se cruza por símbolo.

---

## Síntesis de decisión

- **Ecosistema mínimo (0 credenciales nuevas):** Alpaca (intradía) + Finviz (multi-periodo y earnings, como hoy) + Yahoo como fallback. Coste **US$0** (o ~US$39.5/mes si pasas Finviz a Elite por export oficial + real-time).
- **Ecosistema "API-first" (menos scraping):** Alpaca (intradía) + **cálculo EOD propio** con yfinance/Tiingo (multi-periodo) + **Finnhub** (earnings). Coste **US$0**, más código pero sin depender del HTML de Finviz.

### Encaje con la arquitectura LEAN del proyecto
- Todas estas fuentes son **externas al algoritmo LEAN**: por las reglas duras del repo, el código del algoritmo sólo habla con `QCAlgorithm`. Estas APIs encajan como **pre-procesado fuera del engine** (scripts del host / capa de universo) que **producen el CSV de universo ≤200 tickers**, no como llamadas dentro de `main.py`.
- El camino B (calcular Perf 5D/1M/3M desde EOD) es el más afín: se puede expresar como *features* si algún día entran esos datos al `SymbolData`, pero para *rankear el universo* conviene resolverlo en un script host que emita el CSV.

---

## Fuentes

- Alpaca — [Top market movers](https://docs.alpaca.markets/reference/movers-1) · [Most active stocks](https://docs.alpaca.markets/reference/mostactives-1) · [Screener API (alpaca-py)](https://alpaca.markets/sdks/python/api_reference/data/stock/screener.html) · [Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- Finviz — [Elite/Export](https://finviz.com/elite) · [Screener help](https://finviz.com/help/screener) · [`finvizfinance` docs](https://finvizfinance.readthedocs.io/) · [`finvizfinance` GitHub](https://github.com/lit26/finvizfinance) · [`pyfinviz`](https://pypi.org/project/pyfinviz/)
- Yahoo — [Day Gainers screener](https://finance.yahoo.com/research-hub/screener/gainers/) · [yahooquery Screener](https://yahooquery.dpguthrie.com/guide/screener/) · [yfinance screener issue](https://github.com/ranaroussi/yfinance/issues/2419)
- Finnhub — [Earnings Calendar API](https://finnhub.io/docs/api/earnings-calendar) · [Pricing](https://finnhub.io/pricing)
- Financial Modeling Prep — [Earnings Calendar API](https://site.financialmodelingprep.com/developer/docs/stable/earnings-calendar) · [Pricing](https://site.financialmodelingprep.com/pricing-plans)
- Alpha Vantage — [API docs (TOP_GAINERS_LOSERS, EARNINGS_CALENDAR)](https://www.alphavantage.co/documentation/) · [Premium/limits](https://www.alphavantage.co/premium/)
- EODHD / Tiingo / comparativas — [Free stock API comparison 2026 (qveris)](https://qveris.ai/guides/stock-api-free-comparison/) · [Best free APIs 2026 (dev.to)](https://dev.to/nexgendata/best-free-stock-market-apis-and-data-tools-in-2026-a-developers-honest-comparison-1926)
