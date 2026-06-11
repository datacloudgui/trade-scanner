# Etapa 5B — Decisiones y pendientes

## T1.1 — `universes/sample_dev.csv` (2026-06-11)

**Estado:** ✅ completada (criterio de T1.1 verificado por ejecución).

### Decisiones tomadas

- **Ubicación: `universes/` en la raíz del workspace (directorio versionado nuevo).**
  El plan dicta el path `universes/sample_dev.csv`. Se eligió un dir versionado propio
  para distinguir este fixture estático de:
  - `data/object-store/*.csv` → movers Barchart efímeros (gitignoreados, fuente de los swing).
  - `storage/universes/*.csv` → copia runtime regenerable (gitignoreada).
  `sample_dev.csv` es un fixture de harness de validación → debe versionarse.
- **Formato:** header Barchart §5 idéntico al de `swing_advances.csv` (columnas con comillas).
  Se incluyó la línea footer `"Downloaded from Barchart.com…"` a propósito, para ejercitar
  el footer strip de `UniverseSpec` (`_TICKER_RE`).
- **Valores SPY (2026-06-05):** `Latest=595.27`, `5D Avg Vol=72184500`.
  Pasan el filtro dev `avg_vol_5d > 1e6 and price > 5` con holgura.
- **Solo SPY:** AAPL/IBM se añaden en T5.2 (Fase 2), fuera del alcance de hoy.

### Verificación

`UniverseSpec("universes/sample_dev.csv", "avg_vol_5d > 1e6 and price > 5").load(store)`
→ `["SPY"]`. Footer descartado, alias map aplicado, filtro OK.
(Ejecutado en host venv; `core/universe.py` no importa `AlgorithmImports`.)

## T1.2 — overrides `environments.dev` en `strategies.json` (2026-06-11)

**Estado:** ✅ completada.

- Añadidos a `environments.dev`: `universe: "sample_dev"`,
  `timeframes: {D:[8,20,200], W:[8,20,200], M:[8,20,200]}` (incluye M:200, que prod NO usa),
  `warmup_budget: {"daily": 4300}`.
- `top_n:2` / `max_universe:2` conservados (cambio 5→2 / 10→2 intencional, per T1.2).
- Prod sin tocar (su SMA 200 / budget bajo es T7.1).
- JSON validado (`json.load` OK).

## T1.3 — wiring del seed para fixtures estáticos (2026-06-11)

**Estado:** ✅ completada.

### Decisión

- En `seed_object_store.sh` agregué una **rama §4 genérica**: copia *todos* los `universes/*.csv`
  (no solo `sample_dev`) a `storage/universes/` con `cp` directo, idempotente, **sin** la lógica
  de `processed/` de los movers. Razón: son fixtures versionados estáticos, no movers Barchart
  efímeros con fecha en el nombre. Generalizar a glob evita tocar el script al añadir más fixtures.
- `shopt -s nullglob` para que el `for` no falle si `universes/` está vacío.

### Verificación (criterio AGREGADO de T1 — ahora cumplido)

- `bash scripts/seed_object_store.sh` → loguea `sample_dev.csv → universes/sample_dev.csv
  (fixture estático)` y deja `storage/universes/sample_dev.csv` (244 B).
- `UniverseSpec("universes/sample_dev.csv", "<filtro dev>", max_tickers=2)` leído **desde storage**
  → `["SPY"]`.

### Pendiente (siguientes tareas de Fase 1, fuera de hoy)

- **T2** — integración del warmup en `main.py`: leer estos overrides dev (`universe`, `timeframes`,
  `warmup_budget`), construir `SymbolData` por símbolo, `set_warm_up`-primero con rollback manual.
  Hoy nada en `main.py` lee aún estos campos → sin impacto en runtime todavía.
- No corrí `run_tests.sh` (Docker): T1.2/T1.3 no cambian código en `core/`; la validación de T1 es
  seed + parse, ejecutada en host. Los tests de `test_universe.py` no se ven afectados.

## T2.1 — suscripción DAILY + SymbolData + wiring consolidator en `main.py` (2026-06-11)

**Estado:** ✅ completada (criterio verificado por ejecución: backtest + tests).

### Decisiones tomadas

- **Pregunta abierta nº4 del spec RESUELTA — mecanismo del override `timeframes`:** se adoptó
  la propuesta escrita: si `environment.timeframes` existe, **reemplaza** la unión de estrategias
  para construir `requirements` (`_build_requirements` en `main.py`); sin override (prod) se usa
  la **unión global** de los `timeframes` de todas las estrategias.
- **Unión global, no por símbolo (simplificación deliberada):** `requirements` es compartido por
  todos los símbolos en vez de "unión de las estrategias que usan ese símbolo" (CLAUDE.md). Hoy es
  equivalente: las 4 estrategias prod declaran timeframes idénticos, y dev fuerza un solo universo.
  Además habilita `plan_warmup` global una sola vez (R4, requirements idénticos entre símbolos).
  Si en el futuro las estrategias divergen en timeframes, refinar a unión por símbolo.
- **Ancla de calendario SPY pasa de MINUTE a DAILY (D5):** la minute data local solo cubre
  2013-10 y la ventana 5B exige `start ≥ 2016`. El ancla **reusa la suscripción del universo** si
  SPY está suscrito (dev); fallback a `add_equity("SPY", DAILY)` propio (prod sin SPY). El reloj
  avanza con barras diarias y los `ScheduledEvents` disparan por exchange hours (consideración #4
  del spec, **confirmada empíricamente**: scans a las 15:30 y 16:01 cada día hábil de la ventana).
- **Ventana:** `2016-01-04 → 2016-01-15` (10 días hábiles, cruza el cierre semanal del vie 08).
  SPY-zip arranca 1998-01-02 → ~4530 barras diarias previas al start ≥ 4221 (M:200 viable, T2.2).
- **`add_equity(..., Resolution.DAILY, DataNormalizationMode.SPLIT_ADJUSTED)`** per D5/T2.1.
  Ojo (consideración #5): el SPY-zip trae factors REALES → este símbolo sí ejercita el wiring del
  modo; la data convertida en F3 (factors neutros) será insensible al modo.
- **Evidencia 1:1 con contadores de instrumentación:** `on_data` cuenta barras diarias entregadas
  por la suscripción; un handler extra sobre `data_consolidated` cuenta emisiones del consolidator;
  `on_end_of_algorithm` cruza: `recibidas == consolidadas + working` (emisión perezosa, hallazgo #1
  de 5A, ahora confirmado también en runtime con feed del engine).
- **SymbolData construye las 9 series del override** (`D/W/M × 8/20/200`). El filtrado de series
  `excluded` por presupuesto llega con `plan_warmup` en T2.2 (con budget dev 4300 hoy no se
  excluiría nada de todos modos).

### Verificación (criterio de T2.1)

- `lean backtest "trade-scanner"` (env=dev) corre sin errores. Log:
  - `[swing_eod] universe loaded: 1 tickers (env=dev, max=2, key=universes/sample_dev.csv)` ×4
    estrategias → override `universe` operativo.
  - `[SPY] SymbolData listo (series: D:8, D:20, D:200, M:8, M:20, M:200, W:8, W:20, W:200)` →
    override `timeframes` operativo (9 series, incluye M:200).
  - **`[SPY] feed daily→consolidator 1:1 OK: 10 recibidas, 9 consolidadas, working hasta
    2016-01-16 00:00:00`** → la suscripción daily alimenta el consolidator diario 1:1 (la décima
    barra retenida como working bar = emisión perezosa esperada).
- Único data request fallido: `/alternative/interest-rate/usa/interest-rate.csv` — interno del
  engine (risk-free rate para estadísticas), no relacionado con nuestra suscripción. Benigno.
- `bash scripts/run_tests.sh` → **31 passed** (sin cambios en `core/`; main.py no se unit-testea,
  es boundary del engine — su verificación es el backtest).

### Pendiente (T2.2–T2.3, fuera de hoy)

- **T2.2** — warmup: `set_warm_up` primero (los consolidators YA quedan añadidos antes de
  cualquier warmup, requisito cumplido por construcción en `initialize`), gate de cross-check
  contra fixture T4, rollback manual (`history[TradeBar]` + `scan()` de cierre) si diverge;
  guard `if self.is_warming_up: return` en `on_data`/scans; series `plan.excluded` → warning
  y no construirlas (hoy SymbolData construye todo el override).
- **T2.3** — logs de evidencia: profundidad con driver (W:200→1010, M:200→4221), duración del
  warmup, conteo ready/no-ready, decisión de estrategia de warmup.
- Los **contadores 1:1 son instrumentación de T2.1**: decidir en T2.3 si se conservan como
  evidencia permanente del wiring o se retiran al cerrar F1.
- Las SMAs siguen **frías** (sin warmup todavía): `is_ready` no se validó hoy — es exactamente
  lo que T2.2 resuelve.

## T2.2 — warmup `set_warm_up` con gate de cross-check; ADOPTADO sin rollback (2026-06-11)

**Estado:** ✅ completada (gate verificado por ejecución; pregunta abierta nº1 del spec RESUELTA).

### Decisión principal: Estrategia A (engine-managed) ADOPTADA

`self.set_warm_up(4221, Resolution.DAILY)` con los consolidators ya cableados a la suscripción
(T2.1). El gate de D4 corrió en `on_warmup_finished` y dio **9/9 series exactas** contra la ruta
manual (igualdad estricta de `current.value` + `is_ready`): **no hay rollback**. Log:
`[warmup] gate dev OK: set_warm_up ADOPTADO — 9/9 series exactas vs ruta manual (4221 filas vía
history[TradeBar], 1 llamada batch)`.

### Decisiones de diseño del gate

- **La ruta manual B no es código muerto:** vive en `_run_warmup_gate()` — calienta `SymbolData`
  *sombra* (no cableados al engine) con `self.history[TradeBar](symbols, depth, DAILY)` tipado en
  **una** llamada batch + `update(bar)` por barra + `scan()` de cierre, y compara serie a serie.
  El gate corre en **cada backtest dev** (en prod no): re-valida la equivalencia continuamente y
  mantiene la ruta B lista como rollback si una versión futura del engine divergiera.
- **El flush de ambas rutas se hace al MISMO instante (`self.time`)**: comparar estados flusheados
  a tiempos distintos produce falsos mismatches W/M (periodos que vencen entre `last_bar.end_time`
  y el start date).

### Hallazgo nuevo (refina D4): la emisión perezosa al cierre del warmup solo se resuelve sola en el consolidator RAÍZ

- Al llegar a `on_warmup_finished`, el working bar **diario** ya estaba emitido (`flush scan(...)
  emitió 0 working bar(s) retenidas`): el engine escanea los consolidators registrados en
  `subscription_manager` al avanzar el frontier.
- Pero los consolidators **W/M encadenados son invisibles para el engine** (viven dentro de
  `SymbolData`, alimentados por `_feed_chained`): la barra M de diciembre y la W de la última
  semana seguían en working al instante del fin de warmup — un `update()` con la barra diaria
  del 12-31 no dispara emisión (la barra pertenece al periodo en curso, no al siguiente).
- Conclusión: **el `sd.scan(self.time)` en `on_warmup_finished` es NECESARIO** para que las SMAs
  W/M estén al día justo cuando T3 escriba el archivo de validación. La frase de D4 "sin `scan()`
  de cierre" vale para el flujo continuo daily, no para el instante de cierre del warmup en la
  cadena W/M. Es el hallazgo #1 de 5A manifestándose en la ruta A.

### Otras decisiones

- **Guard de warmup:** los ScheduledEvents SÍ disparan durante warmup → callback movido a
  `_scan_stub()` con `if self.is_warming_up: return` (sin él: ~4200 días × 4 estrategias de spam).
  `on_data` cuenta barras SIEMPRE (la instrumentación 1:1 ahora cubre warmup + runtime) y el guard
  protege solo la lógica de runtime futura.
- **`plan_warmup` global cableado:** series `excluded` → warning por cada una + `SymbolData` se
  construye con el requirements **filtrado** (la serie no existe). En dev (budget 4300) no se
  excluye nada por diseño; el disparo real del warning se verifica en T7.1 con budget prod.
- **Driver y profundidades en el log** (adelanta parte de T2.3):
  `[warmup] plan(daily): depth=4221 (driver M:200) | D:200→205, M:200→4221, W:200→1010`.

### Verificación (criterio de aceptación de T2)

| Criterio | Evidencia (backtest 2026-06-11_18-34-00) |
|---|---|
| Backtest dev corre sin errores | ✓ `Successfully ran 'trade-scanner'` |
| Profundidad coherente con fórmula (W:200→1010, M:200→4221) | ✓ línea `[warmup] plan(daily)` |
| Duración | ✓ `4221 barras stremeadas en 0.82s` (baseline SPECS §11) |
| SPY `ready` | ✓ `[warmup] ready: 1/1 símbolos` (las 9 series, M:200 incluida) |
| Decisión de warmup documentada con cross-check | ✓ `gate dev OK: set_warm_up ADOPTADO — 9/9 exactas` |
| Ruta manual con `history[TradeBar]` tipado, 1 llamada por resolución | ✓ en el gate (4221 filas, 1 batch) |
| `run_tests.sh` | ✓ 31 passed (sin cambios en `core/`) |
| 1:1 suscripción→consolidator (extendido a warmup+runtime) | ✓ `4231 recibidas, 4230 consolidadas` + 1 working |

El engine entregó **exactamente** las 4221 barras pedidas (rebobina por trading days con
resolución DAILY) — sin déficit que comprometa M:200.

### Observaciones (no bloquean)

- `Skip Dividend during warmup` (TRACE del engine, ~70 líneas): con SPLIT_ADJUSTED el feed
  entrega los dividendos crudos y el engine los omite durante warmup. Ruido esperado, no error.
- **Boundary del end-date:** los eventos `after_market_close` del ÚLTIMO día del backtest no
  disparan (el frontier termina a las 16:00 del end date con data daily) — preexistente (38
  scans también en el run de T2.1), solo artefacto de backtest, irrelevante en live. Nota para
  Etapa 7 al validar schedules.

### Pendiente

- **T2.3** — los logs exigidos ya se emiten (driver, duración, ready/no-ready, decisión);
  queda cotejarlos formalmente contra el criterio, y decidir si los contadores 1:1 y el gate
  dev se conservan tras F1 (el gate duplica el warmup en dev: +4221 filas de history por run).
- Warning de exclusión por presupuesto: cableado pero sin disparar en dev — verificación real
  en T7.1 (budget prod bajo).
- **T3** — archivo de validación: escribirlo en `on_warmup_finished` después del flush
  (las SMAs quedan al día gracias al hallazgo de arriba).

## T2.3 — logs de evidencia + gate detrás de flag `validate_warmup` (2026-06-11)

**Estado:** ✅ completada (los cinco logs del criterio verificados por ejecución).

### Decisiones tomadas (instrucción del usuario + cierre de la pendiente de T2.2)

- **Gate de cross-check detrás de flag, apagado por defecto:** nueva key
  `environments.dev.validate_warmup: false` en `strategies.json`. `main.py` lo lee con
  `env_cfg.get("validate_warmup", False)` — cualquier environment puede activarlo, ninguno lo
  hereda por defecto. Razón: el gate duplica el warmup (+depth filas de `history` por símbolo);
  como herramienta de re-validación se enciende a demanda (upgrades de imagen LEAN, debugging).
- **Contadores 1:1 se conservan** (decisión del usuario): costo ~cero y detectan regresiones
  silenciosas de wiring hasta que el fixture T4 cubra esa regresión por valores congelados.
- **La decisión de estrategia de warmup se loguea SIEMPRE** (antes solo aparecía vía gate):
  `[warmup] estrategia: set_warm_up engine-managed (A, adoptada en T2.2 con gate 9/9 exactas);
  gate cross-check ON|OFF (flag validate_warmup)` — el log de cada run documenta qué ruta corre
  y si el cross-check estuvo activo.

### Verificación (criterio de T2.3: logs de evidencia, env=dev)

| Log exigido | Evidencia (runs 2026-06-11_18-44-15 flag off / _18-44-35 flag on) |
|---|---|
| Profundidad derivada con driver | ✓ `[warmup] plan(daily): depth=4221 (driver M:200) \| D:200→205, M:200→4221, W:200→1010` |
| Duración (filas + tiempo, baseline §11) | ✓ `4221 barras stremeadas en 1.00s` (~0.8–1.0 s/símbolo a depth 4221 — baseline para el riesgo de warmup de 200 símbolos de SPECS §11) |
| Conteo ready/no-ready por símbolo | ✓ `[warmup] ready: 1/1 símbolos` + `WARNING ... series frías: ...` por símbolo no-ready (rama verificada en tests de 5A; no dispara con SPY) |
| Warning por serie excluida del presupuesto | ⚠️ cableado (warning + serie no construida); en dev no dispara por diseño (budget 4300) — verificación real en T7.1 |
| Estrategia de warmup usada | ✓ incondicional; con flag ON además: `gate dev OK: set_warm_up ADOPTADO — 9/9 series exactas` |

- Flag verificado en ambos estados: OFF → sin líneas de gate; ON → gate corre y da 9/9.
  Revertido a `false` y re-seeded al terminar.
- `bash scripts/run_tests.sh` → 31 passed.

### Pendiente

- **T3** (siguiente): archivo `validation/sma_validation_<fecha>.csv` en `on_warmup_finished`
  tras el flush, solo dev, K=5 filas/serie.
- Retiro de los contadores 1:1: re-evaluar recién cuando T4 congele el fixture (hasta entonces
  se quedan — decisión del usuario).
- Warning de exclusión: disparo real pendiente de T7.1 (budget prod).

## T3 — archivo de validación de SMAs, K=5 por serie (2026-06-11)

**Estado:** ✅ completada (criterio verificado por ejecución: archivo + contenido + tests).

### Decisiones tomadas

- **Flag de config `sma_validation`** (la "(flag de config)" que pedía el spec): nueva key
  `environments.dev.sma_validation: true`; prod no la define → default `False` → ni recorder
  ni archivo. Mismo patrón que `validate_warmup`.
- **Captura por observer, no por snapshot:** las SMAs de LEAN solo guardan el valor actual, así
  que los "últimos 5 puntos" se capturan con un handler extra sobre `data_consolidated` de cada
  consolidator (deque `maxlen=5` por serie), alimentado en streaming durante el warmup. Costo
  ~cero y sin tocar la matemática.
- **Nuevo accessor `SymbolData.consolidator(tf)`** (L2): expone el consolidator construido por
  timeframe ('D' = raíz; KeyError con los construidos si no existe). Necesario porque los W/M
  encadenados eran privados. Cubierto por test nuevo que además fija la **garantía de orden**
  de la que depende el recorder: un handler añadido DESPUÉS de construir `SymbolData` ve la SMA
  ya actualizada (orden de handlers .NET = orden de suscripción) — `32 passed`.
- **Escritura en `on_warmup_finished` DESPUÉS del flush** (tal como anticipó T2.2): así el
  archivo incluye la barra M de diciembre (end `2016-01-01`) y la W de la última semana
  (end `2016-01-04`), que sin flush quedarían retenidas.
- **`<fecha>` = fecha del algoritmo** (`self.time`, no wallclock): el nombre refleja el "as of"
  de la data (`sma_validation_20160104.csv`), que es lo que el usuario alineará en TradingView
  (T7.2 usará data Stooq reciente → fecha actual).
- El recorder sigue capturando en runtime tras el warmup (inofensivo: el archivo ya se escribió);
  los puntos de runtime quedarían en los deques si en el futuro se quisiera re-escribir al cierre.

### Verificación (criterio de T3)

- `storage/validation/sma_validation_20160104.csv` existe y es legible (CSV plano, 2.3 KB),
  escrito vía `self.object_store.save()`. Log:
  `[validation] validation/sma_validation_20160104.csv: 9 series, 45 filas`.
- **5 filas × 9 series** (D/W/M × 8/20/200) con valores no nulos para SPY; `bars_consumed`
  exacto (D: 4217→4221; W: 872→876; M: 198→202 — M:200 ready con margen 2).
- **Convención de fechas verificada en el contenido** (C4: `bar_end_time` = inicio del periodo
  siguiente):
  - D: medianoche del día siguiente a la sesión, con huecos correctos de festivos
    (12-24→`12-25`, salta Navidad+finde a 12-28→`12-29`).
  - W: todos lunes (`12-07/12-14/12-21/12-28/01-04`) = lunes→domingo, cierre efectivo viernes.
  - M: primeros de mes (`09-01…01-01`) = mes calendario.
  - Cross-consistencia: close W de la semana al 12-28 (205.65) == close D de la sesión 12-24 ✓.
- `bash scripts/run_tests.sh` → **32 passed** (test nuevo del accessor + orden de handlers).

### Pendiente

- **T4** (siguiente, cierra F1): congelar las SMAs de SPY-zip como fixture de regresión
  interino en `tests/` — los valores del archivo de hoy (p. ej. D:8@2016-01-01 = 204.925,
  W:200@2016-01-04 = 177.5696, M:200@2016-01-01 = 133.415) son los candidatos a congelar.
- La interpretación de fechas para el usuario en T7.2 (ej. fila D end `2016-01-01` = sesión
  del 12-31 en TradingView) quedó documentada en el docstring de `_write_validation_file`.
