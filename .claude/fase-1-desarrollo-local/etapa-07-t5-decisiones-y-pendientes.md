# T5 (Etapa 7) — Integración en `main.py` (L5): minute subscription + pipelines + schedule (2026-06-19)

L5, `main.py`. Cablea el embudo real: suscripción `Resolution.MINUTE` (working bar), un `ScanPipeline`
por estrategia construido en `initialize()` (config=datos × `STRATEGIES`=composición), y el callback real
reemplazando `_scan_stub`. Primer paso de la etapa cuya verificación es el **backtest** (no unit tests:
`main.py` no lo cubre `run_tests.sh`).

## Resultado contra el criterio de aceptación (T5 — verificable en backtest)

| Criterio T5 | Estado | Evidencia (backtest dev 2013-10-07..11) |
|---|---|---|
| (a) `main.py` sin composición de rules ni umbrales hardcodeados; todo de config + `strategies/` | ✅ | pipelines construidos desde `STRATEGIES[name]` + `resolve_bucket_thresholds(config,name)` + `SIDE_BY_DIRECTION[cfg["direction"]]` + `top_n` de environment |
| (b) Suscripción minute; warmup completa igual que 5B; probe confirma `close("D")`=ayer | ✅ | `add_equity(..., MINUTE, SPLIT_ADJUSTED)`; `gate dev OK` (set_warm_up DAILY bajo minute == ruta manual daily); probe A.3: working_bar=167.94 (hoy) vs close('D')=168.89 (ayer) |
| (c) Un `ScheduledEvent` por estrategia dispara a su hora y ejecuta el pipeline real | ✅ | scans: market_close=5 + market_close_short=5 (15:30 ET), swing_eod=4 + swing_eod_short=4 (16:01 ET); las 4 corren el pipeline real |
| Capas puras intactas | ✅ | `run_tests.sh` **178 passed** (solo cambió `main.py`, no testeado por pytest) |

**Veredicto: ✅ T5 cerrada y verificada en backtest.** Cierra el wiring `direction→side` del Done-when #2
(ahora `[x]`), demuestra el gate B (Done-when #6 `[x]`) y resuelve la pregunta abierta A.3 (RESUELTA).

## Cambios en `main.py`

- **Imports:** `from core.features import SIDE_BY_DIRECTION, resolve_bucket_thresholds`; `from core.pipeline import ScanPipeline`.
- **Ventana:** `set_start_date/end` → **2013-10-07..11** (única con minute: SPY sample del repo LEAN).
- **Suscripción:** `Resolution.DAILY` → `Resolution.MINUTE` (mantiene `SPLIT_ADJUSTED` + `add_consolidator`); warmup intacto (`set_warm_up(depth, DAILY)`).
- **`initialize()`:** dict `self.pipelines` — por estrategia: `composition = STRATEGIES.get(name)` (omite+loguea si falta), `side = SIDE_BY_DIRECTION[cfg["direction"]]`, `ScanPipeline(...)` con rules/series de la composición y thresholds/top_n de config. ScheduledEvent con callback real `self._scan(name)`.
- **`_scan_stub` → `_scan`:** corre `pipeline.scan(self.symbol_data, self.utc_time, self.log)`, loguea nº de candidatos; dispara `_emit_probe()` (A.3) solo en el primer scan. Nuevo `_emit_probe(ticker="SPY")`.
- **`on_end_of_algorithm`:** la instrumentación 1:1 daily de 5B se reformula a conteo informativo (con minute la relación barras→consolidador es N:1, no 1:1 → evita un MISMATCH falso).

## Decisiones tomadas

### D-T5.a — Config JSON INTACTO (no cambié su forma)
`strategies.json` ya tenía todo lo que T5 lee: `direction`, `schedule`, `universe`, `universe_filter`,
`timeframes`, `bucket_thresholds` (global) y `top_n` (environment). Las 4 claves coinciden con `STRATEGIES`.
`main.py` solo **lee** el JSON; la composición (rules) vive en `strategies/` (D7.2, decidido antes). El
contrato sigue siendo el archivo configurable que en el futuro podría venir de un frontend (requisito del
usuario): cero datos de negocio movidos a código.

### D-T5.b — Ventana 2013-10 + SPY-minute (decisión de datos, con el usuario)
SPY (minute 2013-10) y AAPL (minute 2014-06) **no se solapan** y SPY es el ancla del calendario → la
ventana es 2013-10. SPY ejercita `working_bar`; AAPL/IBM/FB caen al fallback `close("D")` (C2). FB (IPO
2012, historia corta) tiene `M:20` referenciada **fría** → el gate B lo excluye (demostración limpia de B).
Una sola corrida cubre los 3 caminos: working_bar, fallback y exclusión.

### D-T5.c — Logging por callable inyectado (`self.log`), no acoplar el pipeline
`pipeline.scan(self.symbol_data, self.utc_time, self.log)` — el pipeline (L4 puro) recibe `self.log` como
callable; mantiene la pureza de capas (decidido en T4, ahora cableado).

### D-T5.d — Instrumentación 1:1 de 5B reformulada (no eliminada)
Con minute, `on_data` cuenta barras-minuto (no daily) → el chequeo 1:1 daily de 5B daría MISMATCH falso.
Se conserva el conteo como observabilidad informativa (barras recibidas vs diarias consolidadas + working
bar), sin el veredicto 1:1. El warmup en sí no regresó (gate dev OK lo confirma).

## Hallazgos del backtest (relevantes para T6 y diseño)

### H-1 — A.3 RESUELTO: hoy NO está consolidado al scan ✅
Probe SPY @ 15:30 ET (19:30 UTC) del 10-07: `working_bar.close=167.94` (hoy, end_time 2013-10-08 00:00)
vs `close('D')=168.89` (ayer, 10-04). Comportamiento esperado de `timedelta(days=1)`: la diaria de hoy no
se emite hasta la sesión siguiente. ⇒ `day_change` compara hoy vs ayer correctamente; la SMA de `swing_eod`
**excluye hoy** (off-by-one vs chart, aceptado); **NO se activa la contingencia D7.6**.

### H-2 — Gate B confirmado en el engine
`ready: 0/4` global (todos con M:200 fría; FB también M:20/W:200) — si usáramos `is_ready()` global se
excluirían los 4. El gate B (series **referenciadas**) excluye solo a FB (`serie M:20 fría`) y escanea
SPY/AAPL/IBM. Demostración exacta de D7.7 (B ≠ global).

### H-3 — `set_warm_up(DAILY)` bajo suscripción minute == ruta manual daily (gate dev OK)
Despeja la consideración técnica #6 (riesgo de implementación): minute no altera el warmup daily.

### H-4 — ~~0 candidatos~~ **CORRECCIÓN (T6, 2026-06-19): la corrida SÍ emite candidatos**
> ⚠️ La afirmación original ("18 corridas → 0 candidatos") era **falsa**: artefacto del mismo
> line-wrapping del log que ya había confundido el conteo de `market_close_short` (el `grep` de la
> bitácora T5 perdió las líneas `final: 1`). La corrida real emite **5 candidatos** (todos `*_short`):
> `market_close_short`+`swing_eod_short` en 10/09 y 10/10, y `market_close_short` en 10/11 — todos = **IBM**.
> Verificado en T6 con `grep -aE "final: [1-9]"`. Ver `etapa-07-t6-decisiones-y-pendientes.md`.

Lo que sí es cierto del análisis original: (i) SPY (único con minute) está **por encima** de sus SMAs en
2013 → pasa las rules "above" pero no las "below", así que **no** aparece como candidato short; (ii) en el
lado long, el embudo loguea `AboveSMA(20,W+M): 2 → 0` (los top_n long no superan la rule). El candidato que
sí pasa (IBM, short) ejercita el **fallback** de precio (IBM sin minute → feed diario rezagado), no un
working bar intradía vivo. **Para una watchlist con working bar intradía vivo hace falta data minute
multi-símbolo → Etapa 9.**

### H-5 — `"Already exists"` (warning benigno de ScheduledEvent)
Dos estrategias con el mismo schedule auto-generan el mismo hash de nombre → LEAN avisa, pero **ambas
disparan** (conteos 5/5 y 4/4 lo confirman). Posible pulido: nombrar los eventos por estrategia (no
bloqueante; la API nombrada cambia la firma del callback, se evaluaría aparte).

## Pendiente

- **T6 — backtest de validación (lo que falta de la etapa):**
  - **T6.1/T6.2 (≥3 meses + reproducibilidad con evidencia por candidato):** bloqueado por datos — el
    harness dev solo tiene ~1 semana de minute (SPY) y produce 0 candidatos (H-4). Necesita data minute
    multi-símbolo (Stooq es solo daily; LEAN sample = SPY 2013; minute amplio → probablemente QC pago,
    Etapa 9). **Decisión pendiente del usuario** sobre cómo conseguir esa data.
  - **T6.3 (emisión A.3):** ✅ ya resuelto en T5 (H-1).
  - **T6.4 (barra parcial + exclusión):** exclusión ✅ (H-2); `partial_bar=True` en un `ScanResult` real
    pendiente (0 candidatos).
- **Pulido opcional:** nombrar los ScheduledEvents por estrategia (H-5).
- **Commit:** gated por el usuario. Acumulado sin commitear (T1–T5): `core/features.py`, `core/pipeline.py`,
  `strategies/*.py`, `main.py`, `tests/test_*.py`, `etapa-07.md`, `PLAN.md`, `SPECS.md`, bitácoras
  `etapa-07-t1..t5-…`.
