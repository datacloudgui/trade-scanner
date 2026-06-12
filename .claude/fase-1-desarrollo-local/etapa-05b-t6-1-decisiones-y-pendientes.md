# T6.1 — Batch multi-símbolo + backtest dev 4 símbolos (2026-06-12)

## Resultado contra el criterio de aceptación

| Criterio T6.1 | Estado | Evidencia |
|---|---|---|
| 4 símbolos listos (AAPL/IBM/SPY ready; FB M:200, W:200 cold) | ✅ | Log: `ready: 3/4 símbolos`; `WARNING [warmup] FB series frías: M:200, W:200` |
| Batch de warmup: UNA llamada por resolución (no loop por símbolo) | ✅ | Log: `36/36 series exactas vs ruta manual (13574 filas vía history[TradeBar], 1 llamada batch)` |
| Driver M:200 y profundidad coherente | ✅ | `depth=4221 (driver M:200) | D:200→205, M:200→4221, W:200→1010` |
| `main.py` sin cambios al añadir AAPL/IBM (agnosticidad) | ✅ | Zips regenerados → backtest funciona sin tocar main.py |
| Archivo de validación generado | ✅ | `validation/sma_validation_20160104.csv: 36 series, 180 filas (K=5 × 36)` |
| Feed 1:1 OK para los 4 símbolos | ✅ | AAPL: 4231/4230; FB: 921/920; IBM: 4231/4230; SPY: 4231/4230 |
| `run_tests.sh` verde | ✅ | 35 passed (sin cambios en tests) |
| Backtest sin errores | ✅ | Completado en 1.88s, 31,549 data points, 0 errores |

**Veredicto: ✅ T6.1 cumplido.**

---

## Log de warmup completo (evidencia)

```
1999-03-25 00:00:00 Algorithm starting warm up...
2016-01-04 00:00:00 [swing_eod] universe loaded: 4 tickers (env=dev, max=4, key=universes/sample_dev.csv)
...×4 estrategias...
2016-01-04 00:00:00 [AAPL] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)
2016-01-04 00:00:00 [FB] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)
2016-01-04 00:00:00 [IBM] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)
2016-01-04 00:00:00 [SPY] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)
2016-01-04 00:00:00 [warmup] plan(daily): depth=4221 (driver M:200) | D:200→205, M:200→4221, W:200→1010
...warmup engine stremea 4221 barras × 4 símbolos...
2016-01-04 00:00:00 Algorithm finished warming up.
2016-01-04 00:00:00 [warmup] set_warm_up(4221, DAILY) completado: 13574 barras stremeadas en 1.29s; 
                              flush scan(2016-01-04 00:00:00) emitió 0 working bar(s) retenidas
2016-01-04 00:00:00 [warmup] ready: 3/4 símbolos
2016-01-04 00:00:00 WARNING [warmup] FB series frías: M:200, W:200
2016-01-04 00:00:00 [warmup] estrategia: set_warm_up engine-managed (A, adoptada en T2.2 con gate 9/9 exactas); gate cross-check ON
2016-01-04 00:00:00 [warmup] gate dev OK: set_warm_up ADOPTADO — 36/36 series exactas vs ruta manual 
                              (13574 filas vía history[TradeBar], 1 llamada batch)
2016-01-04 00:00:00 [validation] validation/sma_validation_20160104.csv: 36 series, 180 filas (K=5 últimos puntos por serie)
```

## Decisiones tomadas

### D-T6.1.1 — Conversión de CSV a split-only adjusted (re-descarga con "skip dividends")

El usuario re-descargó los CSV de Stooq marcando "skip dividends" (y otros rights) pero SIN marcar "skip splits". Resultado: **precios split-only adjusted** (los splits se aplican toward atrás desde hoy, los dividendos no se ajustan).

Impacto:
- AAPL close dic-2015 en CSV: ~$26-27 (nominal ~$105 dividido por el 4:1 split de 2020)
- IBM close dic-2015 en CSV: ~$130-140 (IBM no tuvo splits recientes → precio ≈ nominal)
- SPY close dic-2015 en CSV: ~$197-201 (SPY sin splits → precio = nominal)

Los zips LEAN se regeneraron con estos nuevos valores. Los factor files neutros (=1) siguen siendo correctos (evitan el doble ajuste con los factores reales del repo LEAN).

### D-T6.1.2 — validate_warmup=true en dev (evidence de batch)

Se habilitó `validate_warmup: true` en el environment dev para que el log muestre explícitamente la evidencia de la "1 llamada batch". El gate duplica el warmup (usa `history[TradeBar](symbols, depth, DAILY)` con todos los símbolos en un solo batch). Para T6.1 es la evidencia más clara del criterio. Se queda habilitado en dev como guardrail de cross-check.

### D-T6.1.3 — FB cold: M:200 Y W:200 (más de lo esperado)

El spec mencionaba FB M:200 como caso de "not-ready". En la ejecución también se verificó que W:200 está frío (921 barras disponibles < 1010 requeridas para W:200). Es esperado y correcto:
- FB IPO: 2012-05-18 → ~921 barras diarias al 2016-01-04
- W:200 necesita: 1010 barras → not ready ✅
- M:200 necesita: 4221 barras → not ready ✅

La lógica `is_ready()` excluye FB de series W:200 y M:200 correctamente.

### D-T6.1.4 — Convención de precios actualizada (total-return → split-only)

El hallazgo T5.3 documentaba "Stooq = total-return adjusted". Tras la re-descarga con "skip dividends", la convención es ahora **split-only adjusted**. Impacto en T6.3:

| Aspecto | Antes (total-return) | Ahora (split-only) |
|---|---|---|
| Ajuste Stooq | splits + dividendos | solo splits |
| Vista TradingView para ≤0.25% | "Adjusted" (total-return checkbox) | "Adjusted" (split-only, default de TradingView) |
| Factor files AAPL/IBM | neutros (=1) | neutros (=1) — sin cambios |

Para T6.3, usar la vista "Adjusted" de TradingView (el toggle estándar, NO el modo "Dividends Adjusted" o similar). TradingView split-adjusted = Stooq split-only = coherente.

---

## Muestra de valores de validación (sma_validation_20160104.csv)

```
ticker  tf  period  bar_end_time          bar_close   sma_value     bars_consumed
AAPL    D   200     2016-01-01 00:00:00   26.319      30.014451     4221
AAPL    W   200     2016-01-04 00:00:00   26.319      22.8649565    876
AAPL    M   8       2016-01-01 00:00:00   26.319      29.4721625    202
IBM     D   200     (ver csv)             ...         ...           4221
SPY     D   200     (ver csv)             ...         ...           4221
FB      D   8       2016-01-01 00:00:00   107.18      ...           907   ← ready
FB      M   200     — no aparece en sma ready set —                       ← cold, excluida
```

Los valores de AAPL muestran el efecto del split-only adjusted (M:200 promedia barras desde 1999 cuando AAPL cotizaba mucho más bajo antes del crecimiento + splits → valor ~$8.16, numéricamente correcto).

---

## Pendiente (T6.2, T6.3, T6.4)

- **T6.2** (siguiente): `config/strategies.json` prod → `D:[8,20,200]`, `W:[8,20,200]` (M queda `[8,20]`); `warmup_budget` prod bajo que excluya M:200 → verificar warning de exclusión en log. Backtest prod sin errores.
- **T6.3**: validación manual del usuario en TradingView con vista **"Adjusted"** (split-only) — comparar SMA 8/20/200 en D/W/M para SPY/AAPL/IBM. Tolerancia ≤0,25% relativa. SPY sin splits → comparación directa (precios Stooq = precios nominales SPY). AAPL/IBM: ajuste backward por splits → usar TradingView Adjusted.
- **T6.4**: congelar valores confirmados como fixture autoritativo + test de regresión en `tests/`.
