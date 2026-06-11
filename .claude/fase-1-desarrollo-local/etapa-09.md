# Etapa 9 — Validación integral Fase 1 (notas y deferrals acumulados)

**Estado:** pendiente (spec formal se escribe al cerrar Etapa 8)
**Depende de:** Etapa 8
**Rol de este documento:** buzón de deferrals que las etapas previas mandan a Etapa 9. **No** es el spec formal todavía; complementa PLAN.md §Etapa 9 y el [ADR-002](../decisions/ADR-002-qc-module-auth-constraint.md). Cada entrada cita su origen.

> ⚠️ **Prerrequisito bloqueante (de PLAN §9):** `lean live` con Alpaca y `lean data download` requieren credenciales QC + org con licencia `AlpacaBrokerage` (plan Researcher mínimo). Elegir y documentar opción A/B/C de [ADR-002](../decisions/ADR-002-qc-module-auth-constraint.md) antes de arrancar.

---

## Deferral D9-1 — Optimización del batching de historia en live (Alpaca)

**Origen:** Etapa 5B (T8 / discusión de optimización de warmup, 2026-06-11). En 5B el warmup lee **archivos locales** (sin red, sin rate limit), así que el batching no es un lever; en live sí.

### Contexto verificado
- **Alpaca free (Basic): 200 requests/min** para market data, feed **IEX** únicamente (~2,5% del volumen US → usar volumen relativo, no absoluto). Historia desde **2016-01-01** (~10 a → M:200 NO viable en Alpaca; sí en Stooq/zips). Fuentes: [Alpaca rate limit](https://alpaca.markets/support/usage-limit-api-calls), [About Market Data API](https://docs.alpaca.markets/us/docs/about-market-data-api).
- El **endpoint v2 de bars acepta multi-símbolo** (`symbols=AAPL,IBM,...`) en una request, con tope de URL ~16 KB (≈ miles de tickers). Universo del proyecto: tope duro **200 tickers** → caben de sobra en una request multi-símbolo.

### Principio de diseño (NO romper la portabilidad)
El algoritmo se queda **agnóstico a la fuente**: `main.py` llama `self.history(symbols_list, depth, resolution)` (una por resolución). **Cómo** eso se mapea a requests batcheadas, paginación o throttle es trabajo del **history provider del brokerage**, configurado en `lean.json`. No meter lógica de chunking/rate-limit en `main.py` — violaría la regla "fuente de datos solo en `lean.json`, portable local↔cloud".

### Qué verificar/decidir en Etapa 9
- [ ] ¿El history provider de Alpaca en LEAN usa el endpoint **multi-símbolo** (1 request para los ≤200) o itera **por símbolo** (≤200 requests = ~1 min de warmup a 200/min)? Ambos son viables; medir el real.
- [ ] Si itera por símbolo y el rate limit aprieta: chunking + throttle a 200/min en la capa de provider, **no** en el algoritmo.
- [ ] El guardrail `warmup_budget` (5B) ya acota la profundidad por símbolo (excluye M:200 en prod) → mantiene el payload/paginación bajo control. Confirmar que el budget de prod es coherente con la profundidad real que Alpaca puede servir (~10 a).
- [ ] Baseline de performance del warmup live (filas + duración + nº de requests) — pedido por SPECS §11.

### Lo que ya está resuelto y NO hay que rehacer
- El batching que controla el algoritmo (una llamada con la lista completa, agrupada por resolución, profundidad mínima vía budget, `history[TradeBar]` tipado) ya está en el diseño de 5B (T2.2). En backtest es óptimo; en live se hereda igual.

---

## (placeholder) Otros deferrals hacia Etapa 9

- Medición seria de memoria/CPU con **200 símbolos suscritos en `Resolution.MINUTE`** (riesgo conocido C6 de Etapa 5; en 5B solo corren ≤3 símbolos a DAILY).
- Verificación de portabilidad de fuente: cambiar provider en `lean.json` (Alpaca ↔ QC) sin tocar código (Done-when de PLAN §9).
- Sesión live paper completa: ambos scans, `working_bar` real, salida y logs.
