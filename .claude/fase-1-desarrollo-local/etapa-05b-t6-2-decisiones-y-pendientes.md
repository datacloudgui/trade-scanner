# T6.2 — Config prod: SMA 200 en D/W + guardrail warmup_budget (2026-06-12)

## Resultado contra el criterio de aceptación

| Criterio T6.2 | Estado | Evidencia |
|---|---|---|
| Estrategias prod: `D:[8,20,200]`, `W:[8,20,200]` | ✅ | Ya estaban en las 4 estrategias (correcto desde F1); no se modificaron |
| Estrategias prod: `M` queda `[8,20]` | ✅ | Confirmado; sin M:200 en prod |
| `environments.prod.warmup_budget = {"daily": 1100}` | ✅ | Añadido a `config/strategies.json`; profundidad resultante: 1010 (driver W:200) |
| Warning de exclusión M:200 verificado en log | ✅ | Run de demo con override temporal M:[8,20,200]: `WARNING [warmup] serie M:200 excluida del plan: necesita 4221 barras (daily), presupuesto 1100` |
| Backtest prod sin errores (config final) | ✅ | `Algorithm completed in 1.24 seconds`; plan: `depth=1010 (driver W:200) | D:200→205, M:20→441, W:200→1010`; sin warning de M:200 |
| `run_tests.sh` verde | ✅ | 35 passed |

**Veredicto: ✅ T6.2 cumplido.**

---

## Logs clave

### Run de demo (override M:[8,20,200] + budget=1100) — warning disparado

```
2016-01-04 00:00:00 [swing_eod] universe loaded: 74 tickers (env=prod, max=200, ...)
2016-01-04 00:00:00 WARNING [warmup] serie M:200 excluida del plan: necesita 4221 barras (daily), presupuesto 1100
2016-01-04 00:00:00 [warmup] plan(daily): depth=1010 (driver W:200) | D:200→205, M:20→441, W:200→1010
2016-01-04 00:00:00 [warmup] ready: 0/142 símbolos  (esperado: prod tickers sin data local)
```

### Run final (sin override — unión de estrategias = M:[8,20]) — sin warning

```
2016-01-04 00:00:00 [warmup] plan(daily): depth=1010 (driver W:200) | D:200→205, M:20→441, W:200→1010
2016-01-04 00:00:00 [warmup] set_warm_up(1010, DAILY) completado: 0 barras stremeadas en 1.30s
2016-01-04 00:00:00 [warmup] ready: 0/142 símbolos
Algorithm completed in 1.24 seconds
```

---

## Decisiones tomadas

### D-T6.2.1 — budget=1100 como valor canónico de prod

- W:200 warmup = 200×5+10 = **1010 barras** → entra (< 1100)
- M:200 warmup = 200×21+21 = **4221 barras** → excluida (> 1100) si se añadiera
- M:20 warmup = 20×21+21 = **441 barras** → entra (< 1100)
- Margen sobre el driver: 1100 - 1010 = 90 barras ≈ 4 semanas de colchón

El valor 1100 es suficientemente alto para cubrir W:200 con holgura pero suficientemente bajo para excluir M:200 (necesitaría 4221). Candidato natural para ajustar si prod necesita más M periods.

### D-T6.2.2 — Prod usa unión de estrategias (sin override de timeframes en env)

Las 4 estrategias ya tenían `D:[8,20,200]`, `W:[8,20,200]`, `M:[8,20]` desde F1. No se necesita override de timeframes en `environments.prod` — la unión natural da el resultado correcto. El override de `timeframes` en `environments.dev` sigue siendo el harness de validación (incluye M:200 a propósito para T6.3).

### D-T6.2.3 — Warning de M:200 en prod: mecánica verificada, no log de producción

El warning se disparó en un run de demo (timeframes override temporal con M:200). En el run de prod final, el warning NO aparece (correcto: M:200 no está en los requirements de prod). La mecánica está probada y el guardrail está operativo: si alguien añade M:200 a las estrategias de prod sin aumentar el budget, el warning dispara automáticamente.

### D-T6.2.4 — 0/142 símbolos ready en prod (esperado)

Los tickers de prod (`swing_advances.csv`, `swing_declines.csv`) son movers de Barchart 2026 sin data local. En backtest, 0 barras stremeadas → todos cold. Este es el comportamiento correcto en dev local (el objetivo del backtest prod es verificar la infraestructura, no SMAs reales). El paso "ready con data real" llega cuando se tenga data live (Etapa 9).

---

## Estado final de config/strategies.json (extracto)

```json
"environments": {
  "dev": {
    "top_n": 2,
    "max_universe": 4,
    "universe": "sample_dev",
    "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20, 200] },
    "warmup_budget": { "daily": 4300 },
    "validate_warmup": true,
    "sma_validation": true
  },
  "prod": {
    "top_n": 50,
    "max_universe": 200,
    "warmup_budget": { "daily": 1100 }
  }
},
"strategies": {
  "swing_eod":        { ..., "timeframes": { "D": [8,20,200], "W": [8,20,200], "M": [8,20] }, ... },
  "swing_eod_short":  { ..., "timeframes": { "D": [8,20,200], "W": [8,20,200], "M": [8,20] }, ... },
  "market_close":     { ..., "timeframes": { "D": [8,20,200], "W": [8,20,200], "M": [8,20] }, ... },
  "market_close_short": { ..., "timeframes": { "D": [8,20,200], "W": [8,20,200], "M": [8,20] }, ... }
}
```

---

## Pendiente (T6.3, T6.4)

- **T6.3** (usuario): validación manual en TradingView con vista **"Adjusted"** (split-only).
  Comparar `storage/validation/sma_validation_20160104.csv` vs TradingView:
  - SPY D:8/20/200, W:8/20/200, M:8/20/200 en 2016-01-04
  - AAPL D:8/20/200, W:8/20/200, M:8/20 en 2016-01-04
  - IBM D:8/20/200, W:8/20/200, M:8/20 en 2016-01-04
  - Tolerancia ≤0,25% relativa
  - Nota: `bar_end_time` = inicio del SIGUIENTE periodo (W → lunes siguiente, M → primer día del mes siguiente)
- **T6.4**: congelar valores confirmados (T6.3) como fixture autoritativo + test de regresión en Docker.
