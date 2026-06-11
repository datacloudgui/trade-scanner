# Etapa 5 — TimeframeSpec + SymbolData + warmup (etapa crítica)

**Estado:** fraccionada en 5A + 5B (aprobado 2026-06-11) — este documento queda como análisis de referencia
**Spec detallado 5A:** [etapa-05a.md](etapa-05a.md) · **Spec 5B:** pendiente (se escribe al cerrar 5A)
**Depende de:** Etapa 4 (UniverseSpec entrega tickers por estrategia)
**Estimado:** 8–12 horas total (4–6 h por sub-etapa)

---

## Objetivo

Al cerrar la etapa, cada símbolo del universo tiene un `SymbolData` que construye **solo** los consolidators e indicadores de la unión de timeframes declarados por las estrategias que lo usan, con profundidad de warmup **derivada por fórmula generalizada** (nunca fija), y las SMAs resultantes **validadas contra una plataforma de referencia** con tolerancia documentada (criterio DONE nº1 del SPECS).

El diseño debe soportar sin refactor los marcos futuros (ej. 5m/15m/30m como marcos principales): añadir un timeframe nuevo = añadir una entrada al registro de `TimeframeSpec`, no editar fórmulas ni `SymbolData`.

---

## Análisis previo (fundamenta las tareas)

### A1 — Fórmula de warmup generalizada y números con SMA 200

La fórmula de PLAN §4 (`D:n → n+5`, `W:n → n×5+10`, `M:n → n×21+21`) se generaliza así: cada timeframe declara una tupla y la profundidad se calcula uniformemente.

```
TimeframeSpec(code) declara:
  source_resolution   # Resolution.DAILY para D/W/M; Resolution.MINUTE para 5m/15m/30m futuros
  bars_per_period     # barras fuente por barra consolidada: D=1, W=5, M=21; (5m=5, 15m=15, 30m=30 min)
  buffer_bars         # colchón por barra parcial inicial + feriados: D=5, W=10, M=21
  consolidator_factory()  # TradeBarConsolidator: timedelta(1) | Calendar.WEEKLY | Calendar.MONTHLY

warmup_bars(n) = n * bars_per_period + buffer_bars   # en unidades de source_resolution
```

Por símbolo: `profundidad = max(warmup_bars(n))` sobre la unión de `(tf, n)` declarados, **agrupada por `source_resolution`** (una llamada `self.history` batch por resolución).

Profundidades resultantes (barras diarias):

| Timeframe | SMA 8 | SMA 20 | SMA 200 | SMA 200 en años |
|---|---|---|---|---|
| D | 13 | 25 | 205 | ~0,8 |
| W | 50 | 110 | 1.010 | ~4,0 |
| M | 189 | 441 | **4.221** | **~16,8** |

Marcos intradía futuros (barras de minuto, ~390/día de sesión):

| Timeframe | SMA 200 en barras minute | En días de sesión |
|---|---|---|
| 5m | 1.000 + buffer | ~2,6 |
| 15m | 3.000 + buffer | ~7,7 |
| 30m | 6.000 + buffer | ~15,4 |

### A2 — Viabilidad de SMA 200 por marco (requisito del usuario)

Requisito: SMA 200 visible en los **dos marcos menores**; en el **marco mayor**, validar viabilidad.

Con marcos actuales D/W/M (`main_timeframe: W`):

- **D:200 → viable** en cualquier fuente (205 barras ≈ 10 meses).
- **W:200 → viable**: 1.010 barras ≈ 4 años. Alpaca IEX tiene historia desde ~2016 (~10 años al 2026) ✅. La sample data de LEAN (1998–2014) también lo cubre para backtest ✅.
- **M:200 → NO viable por defecto**: 4.221 barras ≈ 16,8 años. Alpaca free no llega (~10 años). QC cloud sí (equities desde 1998), pero solo para tickers con 17+ años cotizando — en un universo de movers habrá muchos IPOs recientes. **Decisión propuesta:** el sistema no lo prohíbe, pero (a) emite warning al cargar config si la profundidad requerida supera un presupuesto configurable (`warmup_budget_days` en `environments`), y (b) los símbolos sin historia suficiente simplemente nunca alcanzan `is_ready` y quedan excluidos del scan con log (mecanismo ya previsto en SPECS).

Con marcos futuros 5m/15m/30m: SMA 200 viable en los tres (máx ~16 días de minutos); el cuello pasa a ser el rate limit de Alpaca en el warmup live, no la profundidad.

### A3 — Validación por usuario: archivo de valores, NO gráficas

`self.plot()` funciona en backtest, pero el LEAN CLI gratuito **no renderiza charts localmente**: los datos de chart quedan en el JSON de resultados del backtest y la UI que los grafica es QC cloud o Local Platform (pago). Visualizarlos = parsear JSON a mano o duplicar cómputo en un notebook de research (violaría además la prohibición de resampling manual). **Esfuerzo no bajo → descartado para esta etapa.**

En su lugar: **archivo de validación** escrito vía `self.object_store.save()` a la clave `validation/sma_validation_<fecha>.csv` (aparece en `storage/validation/`). Columnas propuestas:

```
ticker, timeframe, period, bar_end_time, bar_close, sma_value, bars_consumed
```

Opcional (decidir en revisión): emitir las últimas K (~5) filas por serie en vez de solo la final, para que el usuario compare varios puntos en la plataforma de referencia (hover sobre fechas pasadas) y no un solo valor.

### A4 — Datos para la validación (sin desbloquear ADR-002)

Hoy solo hay SPY (daily + minute, sample 2013). La validación de precisión necesita ~5 símbolos con historia diaria larga. El repo público de LEAN trae sample data diaria gratuita con historia ~1998–2014 para varios símbolos (AAPL, IBM, etc.) **incluyendo sus `factor_files` y `map_files`** (imprescindibles: sin ellos el ajuste de precios cambia y las SMAs no cuadran). Extender `seed_sample_data.sh` cubre la carga de datos de esta etapa sin credenciales QC ni descarga Alpaca. La validación manual se hace contra valores históricos de la plataforma de referencia en fechas 2013–2014.

---

## Tareas (preliminares — detalle fino al aprobar el spec)

### Bloque A — lógica pura, verificable por tests

#### T1 — `core/timeframes.py`: registro de `TimeframeSpec` + fórmula de warmup

Registro declarativo (dict de specs, no if/elif) según A1. Sin estado; `consolidator_factory` es lo único que toca LEAN (import perezoso o inyectado, para mantener el módulo testeable con mock como `universe.py` — decidir en detalle).

**Criterio de aceptación (preliminar):**
- `warmup_bars` reproduce exactamente la tabla A1 para D/W/M × {8, 20, 200}.
- Test demuestra extensibilidad: registrar un timeframe intradía sintético (ej. `"30T"`, `source_resolution=MINUTE`) en el test y obtener su warmup correcto **sin tocar código de la fórmula**.
- La profundidad por símbolo es el `max` de la unión de declaraciones, agrupado por `source_resolution` (test con dos estrategias que declaran timeframes distintos del mismo símbolo).

#### T2 — `core/symbol_data.py`: `SymbolData`

- Construye consolidators e indicadores **solo** para la unión de `(tf, periodo)` requeridos.
- SMAs registradas sobre cada consolidator (`register_indicator` o suscripción manual al evento del consolidator — decidir en detalle; ver C3).
- Expone `working_bar` (barra parcial del día desde el consolidator diario).
- Expone readiness: `is_ready(tf, n)` y agregado `is_ready()` (todos los indicadores calientes).
- Método `warmup(bars)` que recibe TradeBars históricos y los empuja a los consolidators (la llamada a `self.history` vive en `main.py`, L5).

**Criterio de aceptación (preliminar):**
- Test verifica que con `{D:[8,20], W:[20]}` declarados NO existen consolidator M ni SMA W:8 (unión exacta, nada de más).
- Tras `warmup()` con barras suficientes, `is_ready()` es `True`; con barras insuficientes, `False` y sin excepciones.

#### T3 — Tests unitarios con TradeBars sintéticos (en Docker)

- Semana que cierra viernes (`Calendar.WEEKLY` lunes→domingo): barras diarias de dos semanas → exactamente 2 barras W con OHLC verificable a mano.
- Mes calendario: barras de dos meses → 2 barras M correctas.
- SMA con valores conocidos calculados a mano (ej. SMA8 D sobre closes 1..10).
- Semana parcial al inicio del warmup: la primera barra W es parcial y la SMA converge al valor correcto cuando el buffer la expulsa de la ventana.
- Profundidad de warmup derivada, no fija (cubierto en T1).

**Criterio de aceptación:** `bash scripts/run_tests.sh` verde con todos los casos; los valores esperados están calculados a mano en el test (comentario con la aritmética).

### Bloque B — integración, datos y validación con humano en el loop

#### T4 — Datos de muestra multi-símbolo: extender `scripts/seed_sample_data.sh`

Descargar del repo público de LEAN data diaria (+ `factor_files` + `map_files`) para ~5 símbolos de muestra con historia larga (candidatos: SPY, AAPL, IBM + 2 a confirmar según disponibilidad en el repo).

**Criterio de aceptación:** `lean backtest` con los 5 símbolos suscritos no loguea datos faltantes; los consolidators W/M emiten barras durante la ventana del backtest.

#### T5 — Integración en `main.py`: SymbolData + warmup batch

- Por símbolo: unión de requerimientos de todas las estrategias que lo incluyen → un `SymbolData`.
- Warmup: `self.history(symbols, profundidad, resolución)` **en batch agrupado por resolución** (no por símbolo en loop), empujando a los consolidators de cada símbolo.
- Log de evidencia: profundidad pedida y su derivación (ej. `warmup: 1010 daily bars (driver W:200)`), duración del warmup, y conteo ready/no-ready por símbolo.
- Guardrail: warning si la profundidad requerida excede `warmup_budget_days` del environment (A2).

**Criterio de aceptación:** backtest en `env=dev` muestra en el log la profundidad derivada coherente con la fórmula, el tiempo de warmup y los símbolos excluidos por warmup incompleto.

#### T6 — Archivo de validación de SMAs

Según A3: tras completar el warmup (en `env=dev`), escribir `validation/sma_validation_<fecha>.csv` vía ObjectStore con todas las series `(ticker, tf, periodo)` activas. Activado por flag de config (no corre en prod).

**Criterio de aceptación:** el archivo existe en `storage/validation/`, es legible, y contiene una fila por serie (o K filas si se aprueba la variante multi-punto) con valores no nulos para los símbolos ready.

#### T7 — Validación manual de precisión + registro como test de regresión

- El usuario compara los valores del archivo T6 contra la plataforma de referencia (pendiente acordar, ver preguntas) en las mismas fechas, para los 5 símbolos de muestra: SMA 8/20/200 en D y W; SMA 8/20 en M (200 M solo si la historia alcanza — A2).
- Los valores confirmados se congelan en `tests/` como fixture de referencia (test de regresión: recalcular con la misma data y comparar dentro de la tolerancia acordada).
- Documentar tolerancia y modo de ajuste de precios usado (ver C1).

**Criterio de aceptación:** desviaciones ≤ tolerancia acordada documentadas en el spec/cierre; test de regresión verde en Docker; cualquier desviación mayor explicada (ajuste de precios, convención de semana) o corregida.

---

## Consideraciones técnicas específicas al stack

1. **C1 — Modo de ajuste de precios = primera causa de SMAs que no cuadran.** LEAN ajusta por defecto splits **y dividendos** (`DataNormalizationMode.ADJUSTED`); TradingView/Barchart suelen mostrar solo ajuste por splits (dividendos opcional). Antes de validar hay que fijar el modo en `add_equity(..., data_normalization_mode=...)` para que coincida con la plataforma de referencia, y documentarlo. Sin esto, la "imprecisión" observada será del ajuste, no del consolidator.
2. **C2 — Semana/mes parciales al inicio del warmup.** La historia pedida rara vez empieza en lunes o en día 1: la primera barra W/M consolidada es parcial. El `buffer_bars` existe para que esa barra salga de la ventana de la SMA antes del primer scan. Los tests T3 cubren la convergencia; la validación T7 ignora los primeros valores.
3. **C3 — Cadena de consolidators: warmup con daily, runtime con minute.** En warmup se empujan barras **diarias** de `self.history`; en runtime live la suscripción es `Resolution.MINUTE`. Diseño propuesto: el consolidator diario consume minute bars y sus barras consolidadas alimentan (encadenadas) a los consolidators W/M; en warmup, las barras diarias históricas se empujan directo a los tres. Hay que verificar que ambas rutas producen barras W/M idénticas (test o evidencia en log) — es el punto más fino de la etapa.
4. **C4 — `Calendar.WEEKLY` = lunes→domingo (cierre efectivo viernes); `Calendar.MONTHLY` = mes calendario; el `end_time` de la barra consolidada cae al inicio del período siguiente.** Cuidado con off-by-one al comparar fechas en tests y en el archivo de validación (reportar `bar_end_time` tal cual lo da LEAN y documentar la convención).
5. **C5 — Batch de historia y límites.** 200 símbolos × 1.010 barras (W:200) ≈ 200K filas: una sola llamada batch está bien. 200 × 4.221 (M:200) ≈ 850K filas: medir memoria antes de permitirlo (guardrail A2). En live, Alpaca free (100 calls/min) limita el warmup, no el scan — el batch por resolución minimiza llamadas. Registrar duración y filas en el log (baseline de performance pedido por SPECS §11).
6. **C6 — Suscripción `Resolution.MINUTE` para 200 símbolos es el riesgo de memoria/CPU conocido.** En esta etapa la validación corre en `env=dev` (2 tickers) y la medición seria de 200 símbolos queda para Etapa 9. No optimizar prematuramente aquí.
7. **C7 — Gráficas descartadas en esta etapa** (ver A3): `self.plot()` escribe al JSON de resultados pero no hay renderer local gratuito. Si más adelante se quiere visual, la vía barata sería un script del host que lea el CSV de validación y grafique con matplotlib — fuera del algoritmo, fuera de esta etapa.
8. **C8 — Testeabilidad de `timeframes.py`.** Seguir el patrón de `universe.py`: la lógica de fórmula/registro sin imports de `AlgorithmImports` (testeable sin CLR); solo la `consolidator_factory` toca LEAN. `symbol_data.py` sí depende de LEAN (consolidators/indicadores reales) — sus tests corren en Docker como los de Etapa 2.
9. **C9 — La config actual no declara SMA 200.** `strategies.json` declara `{D:[8,20], W:[8,20], M:[8,20]}`. La capacidad SMA 200 se valida vía config de `dev` (o entrada de validación) sin cambiar prod — el sistema debe soportarla, no activarla en V1 (decidir en preguntas abiertas).

---

## Qué NO hacer en esta etapa (fuera de scope)

- **Features y Rules** (`position_vs_sma`, `extension_pct`, etc.) — Etapa 6. Aquí solo se expone estado en `SymbolData`.
- **Pipeline, ranking, ScanResult** — Etapa 7. La exclusión de símbolos no-ready del *scan* se implementa allí; aquí solo se expone `is_ready` y se loguea.
- **OutputSink real** — Etapa 8. El archivo de validación T6 es un artefacto temporal de esta etapa vía ObjectStore directo, no el sink de producción.
- **Implementar timeframes intradía (5m/15m/30m)** — solo se prueba que el diseño los admite (T1); no se crean consolidators de minutos ni estrategias intradía.
- **Gráficas / charts** — descartado por esfuerzo (A3, C7).
- **Descarga de datos históricos de Alpaca / desbloqueo de `lean live`** — ADR-002, prerrequisito de Etapa 9.
- **Calibración de umbrales y definición de pullback** — pendientes de SPECS §11.
- **Optimización de memoria para 200 símbolos en minute** — medición seria en Etapa 9.

---

## Done when (medible)

- [ ] Tests unitarios de consolidators/indicadores con barras sintéticas verdes (`bash scripts/run_tests.sh`): semana cierra viernes, mes calendario, SMA a mano, barra parcial inicial
- [ ] Solo se crean los consolidators/indicadores de la unión de timeframes declarados (verificado por test)
- [ ] Profundidad de warmup derivada por fórmula generalizada, no fija; un timeframe nuevo se registra sin tocar la fórmula (verificado por test)
- [ ] `lean backtest` con ≥5 símbolos de muestra completa el warmup y loguea profundidad derivada, duración y símbolos ready/no-ready
- [ ] `storage/validation/sma_validation_*.csv` generado con SMA 8/20/200 en D y W, y 8/20 en M, para los símbolos de muestra
- [ ] Validación manual del usuario contra plataforma de referencia: desviaciones ≤ tolerancia acordada, registradas como fixture + test de regresión en `tests/` (criterio DONE nº1 del SPECS)
- [ ] Viabilidad de SMA 200 en el marco mayor documentada (A2) y guardrail `warmup_budget_days` con warning operativo
- [ ] Commit(s) `[Etapa 5] ...`

---

## Preguntas abiertas (resoluciones del 2026-06-11)

- [x] **¿Plataforma de referencia para validar?** Resuelto: TradingView **o** Interactive Brokers, a elección del usuario el día de la validación. Validación 100% manual — cero conexión a APIs externas.
- [x] **¿Modo de ajuste de precios?** Resuelto: `DataNormalizationMode.SPLIT_ADJUSTED` explícito en `add_equity` (5B). TradingView e IBKR muestran por defecto ajuste solo por splits (dividendos es toggle opcional en ambos); LEAN por defecto ajusta también dividendos — de ahí la necesidad de fijarlo.
- [x] **¿Tolerancia aceptable?** Resuelto: ampliada a **≤0,25%** de desviación relativa por valor de SMA (absorbe diferencias de feed IEX vs cinta consolidada); desviaciones mayores requieren explicación o corrección.
- [ ] **¿Símbolos de muestra?** Pendiente para 5B: depende de qué hay en el repo de sample data de LEAN con daily largo + factor files. Propuesta: SPY, AAPL, IBM + 2 según disponibilidad.
- [x] **¿SMA 200 en `strategies.json` de prod?** Resuelto: **must en los dos marcos menores** (`D:[8,20,200]`, `W:[8,20,200]`) y **activable en el marco mayor según proveedor de datos** vía presupuesto de warmup (`plan_warmup` + `warmup_budget`, diseño D2 de etapa-05a.md). El cambio de config se aplica en 5B.
- [ ] **¿Archivo de validación con 1 punto por serie o últimas K (~5) filas?** Pendiente para el spec de 5B. Propuesta: K filas — validar varios puntos detecta errores de alineación de fechas que un solo punto esconde.
- [x] **¿Fraccionar la etapa?** Resuelto: sí, 5A y 5B — PLAN.md §7 actualizado; spec detallado de 5A en [etapa-05a.md](etapa-05a.md).
- [x] **¿Cableado de SMAs?** (surgida al detallar 5A) Resuelto: suscripción manual al evento `data_consolidated` en vez de `register_indicator`, condicionado a compatibilidad QC cloud — verificada: son APIs del engine idénticas en cloud; justificación completa en D3 de etapa-05a.md.

---

## Propuesta: fraccionar en 5A y 5B

**Recomendación: fraccionar.** La etapa mezcla dos modos de verificación distintos y un riesgo de datos:

| | 5A — Lógica (T1–T3) | 5B — Integración y precisión (T4–T7) |
|---|---|---|
| Verificación | 100% automática (`run_tests.sh`) | Requiere backtest con data nueva **+ validación manual del usuario** |
| Riesgo principal | Convenciones de Calendar/consolidators | Disponibilidad de sample data, ajuste de precios (C1), cadena daily↔minute (C3) |
| Bloqueos externos | Ninguno | Plataforma de referencia y tolerancia por acordar |

Razones:
1. El flujo spec-driven exige Done-when **verificados** para cerrar; 5B depende de un paso humano (T7) que puede quedar en espera días — no debería retener el cierre de la lógica ya probada.
2. Las preguntas abiertas que bloquean (plataforma, ajuste, tolerancia) solo afectan a 5B; 5A puede arrancar hoy.
3. Si la sample data multi-símbolo trae sorpresas (T4), el retrabajo queda contenido en 5B.

Contra-argumento (por si se prefiere una sola etapa): C3 (cadena de consolidators) podría revelar un defecto de diseño de `SymbolData` que obligue a reabrir 5A. Mitigación: T3 incluye un test que simula ambas rutas de alimentación (daily directo vs encadenado), bajando ese riesgo antes de cerrar 5A.

Si se aprueba el fraccionamiento, PLAN.md §7 se edita: Etapa 5A (T1–T3, Done-when 1–3) y Etapa 5B (T4–T7, Done-when 4–8), con 5B dependiente de 5A. **Edición a PLAN.md pendiente de aprobación del usuario** (regla de flujo del CLAUDE.md).
