# Etapa 9A — Test run end-to-end (T5 + T6) con datos reales

**Fecha:** 2026-06-21
**Contexto:** primera corrida del pipeline completo en `env=prod` sobre **datos Alpaca reales**
(descargados con `alpaca_to_lean.py`, T3) y **universo Barchart real** (`swing_advances`/`declines`).
Complementa [etapa-09a-conexion-alpaca.md](etapa-09a-conexion-alpaca.md) y
[etapa-09a-decisiones-y-pendientes.md](etapa-09a-decisiones-y-pendientes.md).

---

## Resultado: watchlist real (env=prod, semana 2026-06-12 → 06-18)

**swing_eod** (after close, `partial_bar=False`, as_of 2026-06-17):
- **LONG (4):** BEAM, CGEM, NUVB, OPTX
- **SHORT (8):** ACI, ACN, BAH, CTSH, EPAM, GLOB, LDOS, ODD

**market_close** (15:30 ET, `partial_bar=True`, as_of 2026-06-18):
- **LONG (4):** BEAM, CGEM, NUVB, OPTX
- **SHORT (8):** ACI, ACN, BAH, CTSH, EPAM, GLOB, LDOS, ODD

Materializado en `storage/results/<base>/`: un JSON+CSV por scan/día + `latest.json`, con evidencia
por candidato (bucket, `distance_pct`, valor SMA en D/W/M). Regla activa (cambio del usuario):
`AboveSMA(20,D+W+M)` y su espejo short `BelowSMA(20,D+W+M)`.

Scans disparados en la corrida (todos los días de trading del rango):
```
[market_close]       final: 13 candidatos   (long)
[market_close_short] final:  9 candidatos   (short)
[swing_eod]          final: 17 candidatos   (long)
[swing_eod_short]    final:  7 candidatos   (short)
```
(El conteo de `latest.json` es del último día tras ranking `top_n`; los `final` de arriba son del
scan del 06-12 antes del recorte por día.)

---

## Evidencia de T5 — warmup real del universo

Del log del backtest prod (`trade-scanner/backtests/2026-06-21_21-16-55/`):

- **Plan:** `plan(daily): depth=1010 (driver W:200) | D:200→205, M:20→441, W:200→1010`
- **Filas + duración:** `set_warm_up(1010, DAILY) completado: 122669 barras streameadas en 8.69s`
- **Ready/no-ready:** `ready: 112/141 símbolos` + WARNING por símbolo con series frías
  (2 totalmente fríos: AADX, QNT — listados muy recientes; gate B los excluye del scan).
- **Universos:** `swing_eod`/`market_close` (advances) → 81 tickers; `*_short` (declines) → 60.
  Unión = 141 SymbolData (env=prod, max=200).

### Hallazgo de budget (corrige la expectativa del spec)
En **prod las estrategias solo declaran hasta W:200 y M:20** (no M:200), así que el plan (depth
1010) **cabe entero en budget 1100 → no hay exclusión en prod**. El límite de historia de Alpaca
(~2020 para muchos tickers) **no** se manifiesta como exclusión de M:200, sino como **W:200 fría por
símbolo** (W:200 necesita ~1010 barras ≈ 4 años; los listados posteriores a ~2021 quedan cold). El
guardrail "M:200 excluida con warning" sigue válido pero es del **superset dev** (5B), no de prod.

---

## Cambios aplicados para habilitar la corrida (env-condicional, dev intacto)

1. **`main.py` — rango por entorno.** dev mantiene la ventana 2013-10 (ancla SPY-minute); prod usa
   `2026-06-12..2026-06-19` (datos Alpaca reales 2020+, con runway para el warmup DAILY).
2. **`main.py` — resolución de feed por entorno.** dev = `MINUTE` (working_bar intradía con SPY
   sample); **prod = `DAILY`** porque los datos Alpaca de 9A son diarios. Con `MINUTE` el reloj no
   avanzaba (sin minute) y los `ScheduledEvents` no disparaban ("Sequence contains no elements"). El
   `working_bar` minute real queda como rebanada live (T9), por diseño (D9A.2).
3. **`core/universe.py` — separador de miles de Barchart.** `_parse_pct` y las columnas numéricas
   (`avg_vol_5d`, `price`) ahora quitan comas antes de `float()`/`to_numeric`. Datos reales traen
   `"+1,153.11%"` y volúmenes `"101,584,617"`; `sample_dev` (valores chicos) nunca lo expuso.
   Reventaba `initialize` con "could not convert string to float". Test de regresión añadido en
   `test_universe.py`.
4. **`trade-scanner/config.json`** — `parameters.env` cambiado a `"prod"` para esta corrida.

> Nota: los `ERROR` de `InterestRateProvider` (sin archivo de tasas) y `SendFinalResult: Sequence
> contains no elements` (sin órdenes/benchmark → stats finales) son **benignos**: no afectan ni el
> warmup ni la emisión de watchlists.

---

## Estado vs. cierre formal de T5/T6

| Ítem | Estado |
|---|---|
| **T5** warmup real (filas/duración/ready/no-ready) | ✅ verificado |
| **T6** pipeline produce watchlists reproducibles con evidencia | ⏳ corre y produce resultado real; falta reproducibilidad byte-idéntica |
| Suite de tests verde | ❌ **4 tests rojos** por el cambio de regla del usuario (esperan `W+M`, ahora `D+W+M`) |

### Pendiente para cerrar (bloqueante por la def. de "verificado" de CLAUDE.md)
1. **Actualizar 4 tests** a la nueva regla `D+W+M` (cambio del usuario en `swing_eod.py`):
   - `test_strategies.py::test_swing_eod_above_rule_names`
   - `test_strategies.py::test_swing_eod_below_rule_names_and_mirror`
   - `test_pipeline.py::test_only_symbols_passing_all_required_become_results`
   - `test_pipeline.py::test_funnel_cascade_lines`
   Causa raíz: el nombre de la rule pasó de `AboveSMA(20,W+M)` a `AboveSMA(20,D+W+M)`.
2. **Reproducibilidad T6:** dos corridas → watchlist byte-idéntica (como en Etapa 7).
3. **Recongelar fixture T4** (`FROZEN_SPY_ALPACA`) si se re-descarga SPY desde 2016 (cambia samples).
4. **Decisión de diseño abierta:** confirmar si la regla `D+W+M` es la intención final o se revierte a
   `W+M`. De ello dependen los valores esperados de los tests.

---

## Cómo reproducir esta corrida

```bash
# 1. Universo Barchart (advances/declines) en data/object-store/ → ObjectStore
bash scripts/seed_object_store.sh

# 2. Datos diarios Alpaca del universo (host-side, $0)
python scripts/alpaca_to_lean.py --universe storage/universes/swing_advances.csv --start 2016-01-01 --out data/equity/usa/daily
python scripts/alpaca_to_lean.py --universe storage/universes/swing_declines.csv --start 2016-01-01 --out data/equity/usa/daily

# 3. Backtest prod (env=prod en trade-scanner/config.json)
lean backtest "trade-scanner"

# 4. Watchlist materializada
cat storage/results/swing_eod/latest.json
cat storage/results/market_close/latest.json
```
