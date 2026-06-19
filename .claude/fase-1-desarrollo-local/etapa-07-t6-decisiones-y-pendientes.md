# T6 (Etapa 7) — Backtest de validación: reproducibilidad, evidencia y cierre de etapa (2026-06-19)

Verificación en **backtest** (no unit-testeable: schedule, working bar, emisión y reproducibilidad
requieren engine). Cierra Etapa 7 con la mecánica end-to-end demostrada en el harness dev y **difiere a
Etapa 9** el único criterio bloqueado por datos (backtest ≥3 meses con working bar intradía vivo).

## Decisión que gobierna T6 (usuario, 2026-06-19)

T6.1 pide "≥3 meses" + working bar, pero el harness dev solo tiene **~6 días de minute** (SPY 2013-10-04→11)
y **3** (AAPL 2014-06, no solapados); minute es obligatorio para el working_bar (D7.4). Stooq es solo daily
(confirmado). Minute multi-símbolo de ≥3 meses exige `lean data download` QC-pago (ADR-002), que es
**prerequisito de Etapa 9**. Plan internamente inconsistente (el spec asumió que dev tenía data suficiente —
cierto para daily Stooq de 30+ años, **falso** para minute). Per CLAUDE.md regla 6, me detuve y pregunté.

**Elección del usuario:** *"Diferir ≥3m a Etapa 9, cerrar E7 ahora"* — correr la demo dev enfocada (cosechar
≥1 `ScanResult` real + reproducibilidad), marcar el ≥3 meses como diferido-a-E9, y commitear Etapa 7.

## Resultado contra el criterio de aceptación (T6)

| Criterio T6 | Estado | Evidencia (backtest dev 2013-10-07..11, EXIT=0 ×2) |
|---|---|---|
| (a) Backtest sin errores; mecánica + emisión A.3 citada | ✅ | EXIT=0 en 2 corridas; A.3 resuelto en T5 (probe SPY working_bar=hoy vs close('D')=ayer) |
| (a) Ambas estrategias disparan + embudo logueado + `ScanResult`s generados | ✅ | 4 estrategias × 5 días disparan; embudo por rule; **5 candidatos** emitidos (todos IBM short) |
| (b) Watchlists **reproducibles** en fechas conocidas, con evidencia por candidato | ✅ | RUN1 vs RUN2: líneas de candidato **byte-idénticas** (`diff` vacío); evidencia por candidato (`sma_evidence` + `passed_rules`) logueada |
| (b) ≥2 fechas conocidas | ✅ | 10/09 y 10/10 (`market_close_short`+`swing_eod_short`), 10/11 (`market_close_short`) |
| (c) `run_tests.sh` verde + commit + bitácora | ✅ | **178 passed**; commit `[Etapa 7]`; esta bitácora |
| (T6.3) emisión A.3 | ✅ | resuelto en T5 |
| (T6.4) barra parcial + exclusión | ✅ (flag) / ⏳ (intradía vivo → E9) | `partial_bar=True` (`market_close_short`) / `False` (`swing_eod_short`) sobre IBM mismo día; FB excluido (gate B) |
| Backtest **≥3 meses** (PLAN DW#1, escala) | ⏭️ **DIFERIDO a Etapa 9** | data-limitado (ver decisión arriba) |

**Veredicto: ✅ Etapa 7 cerrada** con el ≥3 meses diferido explícitamente a Etapa 9.

## Cambios

**`main.py` (`_scan`):** se añade una línea de log **por candidato** con su evidencia
(`ticker direction price partial_bar passed=<rules> evidence=<sma_evidence JSON>`), para que la watchlist
sea **inspectable y reproducible desde el log**. La escritura a archivo/notificación sigue siendo Etapa 8
(aquí: memoria + log). Sin cambios en capas puras; `run_tests.sh` sigue 178 passed.

## Watchlist real (reproducible)

```
[market_close_short] candidato IBM short price=184.1123 partial_bar=True  passed=BelowSMA(20,W+M)|BelowSMA(20,D)|NotExtended(8,D)
[swing_eod_short]     candidato IBM short price=184.1123 partial_bar=False passed=BelowSMA(20,W+M)|BelowSMA(20,D)|NotExtended(8,D)
```
Evidencia (10/09): `D:8 below_mild (-0.52%)`, `D:20 below_mild (-2.53%)`, `W:20 below_strong (-4.63%)`,
`M:20 below_strong (-7.01%)` — IBM claramente bajo sus SMAs en las 3 escalas. Los buckets de D **evolucionan**
día a día (las SMAs reciben las barras diarias del feed); `W:20`/`M:20` quedan fijas en la ventana de 6 días.

## Hallazgos

### H-6 — El candidato IBM ejercita el FALLBACK de precio, no un working bar intradía vivo
`reference_price` = `working_bar.close` (si hay) o `close("D")`. IBM **no tiene minute** en el harness; su
feed diario llega **una sesión rezagado** (la barra de "hoy" no aparece hasta la sesión siguiente), así que
el `price` queda efectivamente en un cierre rancio: **184.1123 constante** en las 3 fechas, mientras las SMAs
sí evolucionan. El candidato es **válido** (IBM genuinamente bajo sus SMAs y pasa las 3 short rules) y el flag
`partial_bar` propaga correcto por estrategia, pero **no** demuestra un working bar intradía **vivo**.

El único símbolo con minute real (SPY) está **por encima** de sus SMAs (bull 2013) → pasa long, no short, y
en el ranking long no sobrevive la rule (`AboveSMA(20,W+M): 2 → 0`). ⇒ un candidato que ejercite el working
bar intradía vivo necesita minute multi-símbolo real → **Etapa 9** (misma limitación que difiere el ≥3 meses).

### H-7 — Corrección del falso "0 candidatos" de la bitácora T5
La bitácora T5 (H-4) afirmaba "0 candidatos en 18 corridas". **Falso**: artefacto del line-wrapping del log
(el `grep` perdió las líneas `final: 1`). La corrida real (T5 y T6) emite 5 candidatos. Corregido en la
bitácora T5. Lección: para conteos del log usar `grep -aE "final: [1-9]"` (o `-ao`), no patrones que
crucen saltos de línea.

### H-8 — Reproducibilidad confirmada byte a byte
Dos corridas idénticas (`lean backtest` ×2) → `diff` vacío de todas las líneas `candidato` (ticker, price,
buckets, distance_pct, passed_rules). El orden determinista (universo alfabético + tie-break ticker en el
ranking, consideración #8) se sostiene en el engine.

## Pendiente (todo → Etapa 9, ninguno bloquea el cierre de E7)

- **Backtest ≥3 meses** con watchlist poblada a escala + **candidato con working bar intradía vivo**
  (`partial_bar=True` sobre un símbolo con minute real). Bloqueado por datos: `lean data download` QC-pago
  (ADR-002). Diferido por decisión del usuario.
- **Coste minute a escala** (200 símbolos × minute): medir en E9 (consideración técnica #7).
- **Pulido opcional:** nombrar los ScheduledEvents por estrategia (warning benigno `"Already exists"`, H-5 de T5).
