# ADR-003 — Stooq como fuente de datos (validación y candidato a feed primario V1)

**Estado:** investigación — decisión de feed live diferida a Etapa 9
**Fecha:** 2026-06-11
**Supersede a:** —
**Supersedido por:** —
**Relacionado:** [ADR-002](ADR-002-qc-module-auth-constraint.md) (constraint QC para brokerage Alpaca), [etapa-05b.md](../fase-1-desarrollo-local/etapa-05b.md) (F3 usa Stooq como fuente de validación)

---

## Contexto

Durante Etapa 5B surgió la pregunta de si **Stooq** podría usarse como fuente de datos primaria para la primera versión (V1) del screener, en vez de **Alpaca**, dado que:

- El screener V1 corre a EOD / swing lento y **no coloca órdenes**.
- El delay de Stooq (intradía 15–20 min; daily final tras el cierre) es **irrelevante** para un scan EOD.
- Alpaca free entrega datos IEX (un solo venue, volumen subestimado) y su path live choca con [ADR-002](ADR-002-qc-module-auth-constraint.md) (módulo de brokerage = QC paid).

Esta nota documenta la investigación. **No cierra la decisión del feed live** (eso es Etapa 9); sí fija el rol de Stooq dentro de 5B y el hallazgo arquitectónico que reabre el cálculo Alpaca-vs-Stooq.

---

## Hallazgos de la investigación

### Calidad de dato (eje: SMAs EOD)

- **Stooq EOD** es consolidado, split/dividend-adjusted, cuadra mejor con TradingView; historia 30+ años → **M:200 viable**.
- **Alpaca free = IEX**: un solo exchange, volumen subestimado (ya en CLAUDE.md); arranca **2016** → **M:200 imposible** (~17 años requeridos).
- **Veredicto de dato:** para SMAs sobre cierres en un screener EOD, **Stooq > Alpaca free**. El delay de Stooq no afecta a un scan post-cierre.

### Reframe arquitectónico (el hallazgo importante)

La razón por la que el plan arrastra Alpaca es su **integración nativa de LEAN**, que es un *brokerage* (con datos incluidos) → de ahí el bloqueo de ADR-002 (módulo NuGet `installs: true`, QC paid).

Pero **V1 no coloca órdenes → no necesita brokerage**, solo un *feed de datos*. LEAN ofrece un mecanismo sancionado que **no es un SDK de broker**: custom data vía `PythonData` (`get_source` + `reader`). El algoritmo entrega una URL (el CSV de Stooq), **LEAN hace el fetch**, el `reader` parsea cada línea. Propiedades:

- **Dentro de la API de `QCAlgorithm`** (`add_data`) → no viola "el código solo habla con QCAlgorithm; sin SDKs de datos".
- **Portable local ↔ cloud** (misma URL) → respeta la regla de portabilidad.
- **Esquiva ADR-002 por completo** — sin módulo de brokerage, sin QC paid.
- `is_live` permite zips locales en backtest y la URL de Stooq en vivo, con la misma clase.

Consecuencia: **Stooq-como-custom-data es un candidato a feed live de V1 potencialmente más limpio que Alpaca**, precisamente porque evita el brokerage.

### Límites de Stooq (todos de fiabilidad de producción, no de dato)

- **Sin API oficial** — solo interfaz CSV (`https://stooq.com/q/d/l/?s=<sym>.us&i=d`). Sin contrato, SLA ni soporte.
- **Rate limit agresivo y opaco** — devuelve "Exceeded the daily hits limit". A ~200 tickers/día hay que batchear; comportamiento **no verificado a esa escala**.
- **Fragilidad de fuente gratuita** — formato/URL puede cambiar o desaparecer sin aviso (patrón "Bye Yahoo").
- **ToS** — gratis para uso personal; scraping sistemático para producción puede violar términos.
- **Sin profundidad intradía real** (solo barras 5/60-min delayed) → insuficiente si una estrategia futura pide timeframes intradía.

Alpaca, por contraste: API formal con términos claros, rate limit documentado (100/min), y camino natural cuando V2 coloque órdenes (broker + datos integrados).

---

## Ventajas y desventajas (Stooq como feed primario V1)

**Ventajas**
- Calidad EOD superior (consolidado, ajustado, cuadra con TradingView).
- M:200 viable (historia profunda).
- Esquiva ADR-002 / QC paid vía custom `PythonData`.
- Sinergia con 5B: el fetcher/converter de F3 ya construye esta pieza → trabajo transferible.
- El feed live sería el mismo validado manualmente en F3 → confianza directa.

**Desventajas**
- Sin API oficial / SLA / soporte.
- Rate limit opaco; comportamiento a 200 símbolos sin verificar.
- Fragilidad de fuente gratuita (drift de formato, caída sin aviso).
- Riesgo de ToS para uso sistemático.
- Sin profundidad intradía real (techo si aparecen timeframes intradía).

---

## Decisión

1. **Rol de Stooq en 5B (firme):** fuente de **validación** en F3 — converter host-side que escribe zips LEAN y valida SMAs ≤0,25% contra TradingView. Sin cambios al plan.

2. **Stooq como feed primario de V1 (diferido a Etapa 9):** decisión abierta. Antes de cerrarla hace falta **evidencia empírica de fiabilidad** — el único eje donde Stooq es dudoso.

---

## Acciones propuestas

- **F4 de Etapa 5B (adición pequeña):** junto al smoke-test de conectividad de Alpaca, agregar un **smoke-test de fiabilidad de Stooq a escala** — fetch de ~200 símbolos, medir si pega el quota, latencia y estabilidad del formato. Genera la evidencia dura para el ADR de Etapa 9.
- **Etapa 9:** decidir feed live de V1 entre:
  - **Stooq vía `PythonData` custom** (sin brokerage, sin QC paid; sujeto a fiabilidad).
  - **Alpaca** (ADR-002, Opción A/B/C) — natural cuando V2 coloque órdenes.
  Actualizar este ADR con la elección.

---

## Revisión futura

Reevaluar si aparece un timeframe intradía (Stooq queda corto), si Stooq formaliza una API/quota, o cuando V2 introduzca órdenes (empuja hacia Alpaca como broker+datos).

---

## Fuentes

- [QuantStart — Introduction to Stooq Pricing Data](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/)
- [Stooq — Free Market Data](https://stooq.com/db/)
- [AmiBroker forum — Stooq download limit violation](https://forum.amibroker.com/t/stooq-download-range-control-and-download-limit-violation/1167)
- [The Financial Hacker — Bye Yahoo](https://financial-hacker.com/bye-yahoo-and-thank-you-for-the-fish/)
- [QuantConnect — Importing Custom Data (Key Concepts)](https://www.quantconnect.com/docs/v2/writing-algorithms/importing-data/key-concepts)
- [Alpaca — Market Data](https://alpaca.markets/data)
