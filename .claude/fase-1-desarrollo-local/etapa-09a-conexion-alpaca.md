# Etapa 9A — Datos reales D/W/M vía Alpaca REST (Opción C) + portabilidad local↔cloud

**Estado:** en progreso (T1–T6 ✅; T7 portabilidad y T8 matriz pendientes; T9 live diferida)
**Depende de:** Etapa 8 (cerrada). Desbloquea los DONE WHEN nº **1, 2 y 5** de [SPECS §8/§10](../../SPECS.md) dentro de [Etapa 9](etapa-09.md). El nº4 (working bar intradía en *live*) queda **diferido** a la rebanada live (T9, opcional) porque exige feed en tiempo real.
**Autoridad de diseño:** [ADR-002](../decisions/ADR-002-qc-module-auth-constraint.md) (ampliado 2026-06-20 — **Opción C adoptada** para datos; B/A reservadas para live), [SPECS §5 dec. 6–7](../../SPECS.md) (fuente de datos = configuración; portabilidad local↔cloud), [PLAN §1 reglas 1–2](../../PLAN.md), [CLAUDE.md](../../CLAUDE.md) (reglas duras). Deferral [D9-1](etapa-09.md) (batching de historia, ahora resuelto en la capa de descarga, no en `main.py`).

---

## Objetivo

Conectar el screener a **datos reales de Alpaca** para todos sus marcos (diario, semanal, mensual) **sin escribir una sola línea de código que mencione Alpaca y sin pagar QC**. La vía es la **Opción C de ADR-002**: un script host-side que descarga barras **diarias** desde la API REST de Alpaca y las escribe como zips en formato LEAN, reusando el converter ya construido en Etapa 5B. El algoritmo sigue hablando solo con la API de `QCAlgorithm` y lee el feed que `lean.json` apunte; **de dónde salió el zip es invisible para `main.py`**.

El entregable transversal es doble:
1. **Datos D/W/M reales** que habilitan el warmup preciso (DoD nº1) y el backtest multi-mes reproducible con evidencia (DoD nº2).
2. **Portabilidad demostrada** (DoD nº5): el mismo algoritmo corre con dos fuentes distintas cambiando solo configuración — zips locales (Alpaca/Stooq) ↔ data provider de QC cloud (free tier, $0).

La **conexión a brokerage live** (módulo Alpaca, `working_bar` intradía) se separa explícitamente y se difiere a una rebanada opcional (T9): es lo único que requiere un feed en tiempo real y no es necesario para validar la lógica D/W/M.

---

## Contexto y tensión de diseño

El proyecto ya corre end-to-end en `lean backtest` con data local (Etapas 1–8, 225 tests verdes). Lo que falta para "datos reales" es **el límite L6/L1**: de dónde salen las barras. La restricción dura ([ADR-002](../decisions/ADR-002-qc-module-auth-constraint.md)) es que el **provider de datos de Alpaca en `lean.json`** y `lean data download` disparan el sistema de módulos NuGet del CLI (`installs: true`, `minimum-seat: Researcher`) → auth QC server-side + costo, chocando con el objetivo "$0/mes".

**Hallazgo que resuelve la tensión (ADR-002, ampliación):** las SMAs W/M se construyen con consolidators de calendario de LEAN a partir de barras **diarias** (verificado en 5A T3.9). Por tanto, **toda la lógica D/W/M —incluido el backtest largo— solo necesita historia diaria**, que la API REST de Alpaca entrega con la sola API key (sin QC, sin módulo NuGet). La Opción C convierte el problema de "provider en runtime" en un problema de "data-prep host-side", exactamente como el converter Stooq de 5B y `seed_sample_data.sh`.

**El principio que no se rompe (D9-1):** el algoritmo es agnóstico a la fuente. `main.py` llama `self.history(symbols, depth, resolution)` y se suscribe con `add_equity`; lee zips LEAN vía el `DefaultDataProvider` configurado en `lean.json`. El **cómo** se obtuvieron esos zips (multi-símbolo, paginación, throttle a rate-limit de Alpaca) vive en el script de descarga, **nunca** en el algoritmo.

---

## Decisiones de diseño (D9A.x)

### D9A.1 — La descarga es data-prep host-side, no un provider en runtime (regla rectora)
El downloader Alpaca es un script de `scripts/` (lado PRODUCTOR), análogo a [stooq_to_lean.py](../../scripts/stooq_to_lean.py) y `seed_sample_data.sh`. Escribe `data/equity/usa/daily/<sym>.zip` y termina. En runtime, `main.py` solo conoce el feed de `lean.json` (`DefaultDataProvider`). **Prohibido** importar SDK de Alpaca o `urllib`/REST desde `main.py`/`core/*`; **prohibido** cualquier `if provider == "alpaca"` en código del algoritmo. La agnosticidad se verifica por `grep` limpio (`grep -ri alpaca trade-scanner/**/*.py` vacío).

### D9A.2 — Separar "datos D/W/M" (en scope, Opción C) de "feed live intradía" (diferido, B/A)
Dos problemas distintos que no se mezclan:
- **Datos históricos diarios** → Opción C, $0, esta etapa (T3–T8).
- **Feed live en tiempo real** (minute → `working_bar` → `partial_bar=True`) → Opción B (compilar módulo, $0 frágil) o A (QC Researcher, pago). **Diferido** a T9 (opcional); fuera del objetivo $0 de Fase 1.

### D9A.3 — Reusar el emisor LEAN de 5B; ajuste split para casar con la referencia
El downloader **no reimplementa** el formato LEAN: refactoriza `to_lean_rows` y `write_lean_zip` de [stooq_to_lean.py](../../scripts/stooq_to_lean.py) a un módulo compartido (`scripts/lean_daily.py`) y los importa. Solo cambia la **fuente de filas** (REST Alpaca en vez de CSV Stooq). Alpaca se pide con `adjustment=split` (split-only adjusted) para casar con los precios split-adjusted de Stooq usados en 5B y con la referencia del trader. Precios en deci-centavos (×10000), volumen entero crudo — idéntico a 5B.

### D9A.4 — Credenciales: `.env` + lectura host-side, nunca en el repo
El downloader lee `ALPACA_KEY_ID`/`ALPACA_SECRET_KEY` del entorno o del `.env` gitignoreado, con el mismo loader que [check_alpaca_credentials.py](../../scripts/check_alpaca_credentials.py). Nunca se hardcodean ni se imprimen. El `lean.json` versionado no contiene secretos (el `DefaultDataProvider` no los necesita).

### D9A.5 — Portabilidad = zips locales ↔ QC cloud free tier
La demostración del DoD nº5 ("fuente = solo `lean.json`") se hace corriendo el **mismo** `main.py`/`core/*` bajo dos fuentes: (a) zips LEAN locales (Alpaca o Stooq) vía `DefaultDataProvider`; (b) data provider de QC cloud (free tier, $0 — backtest cloud ilimitado con datos incluidos). Sin tocar código entre ambas.

### D9A.6 — Cero órdenes, también cuando llegue el live
La regla dura V1 se mantiene en toda la etapa, incluida la rebanada live opcional: el brokerage paper (si se hace T9) es solo conexión/contexto. `grep` de `market_order`/`set_holdings`/`set_quantity` debe seguir vacío.

---

## Tareas (con criterio de aceptación por tarea)

### T1 — Registrar la decisión: Opción C adoptada *(bloqueante, ya hecho en ADR)*
[ADR-002](../decisions/ADR-002-qc-module-auth-constraint.md) ya documenta la elección de C para datos + el diferimiento de B/A para live (ampliación 2026-06-20).
- **CA:** ADR-002 con la Opción C marcada como adoptada para datos, su costo ($0), comandos que habilita (`lean backtest` con zips locales; `lean cloud backtest` free) y los que NO (`lean live` Alpaca → requiere B/A). ✅ cumplido al abrir esta etapa.

### T2 — Smoke test de credenciales **y** market data
Extender [check_alpaca_credentials.py](../../scripts/check_alpaca_credentials.py) para tocar también el endpoint de **datos** (`GET /v2/stocks/bars` o `/v2/stocks/{symbol}/bars`, `timeframe=1Day`), que es el que usará el downloader.
- **CA:** `python scripts/check_alpaca_credentials.py` valida la cuenta paper **y** devuelve ≥1 barra diaria de ≥1 símbolo desde el endpoint de market data; exit code 0/≠0 usable como gate; solo stdlib del `.venv` (sin `alpaca-py`).

### T3 — Downloader Alpaca REST → zips LEAN diarios *(núcleo de la etapa)*
Nuevo `scripts/alpaca_to_lean.py` (host-side): lee el CSV de universo, pide barras **diarias** a Alpaca (`adjustment=split`), y reusa el emisor LEAN de 5B (D9A.3) para escribir `data/equity/usa/daily/<sym>.zip`. Resuelve en la capa de descarga (no en `main.py`, D9-1): endpoint **multi-símbolo** (≤200 símbolos por request), **paginación** (`next_page_token`), y **throttle** al rate-limit de Alpaca free (~200 req/min).
- **CA:** `python scripts/alpaca_to_lean.py --universe config/universes/<u>.csv` produce zips válidos para todos los tickers del universo; el log reporta por símbolo nº de barras + rango de fechas; es **idempotente** (re-correr sobre el mismo rango no corrompe) e **incremental** si se pasa un rango; `grep -ri alpaca trade-scanner/**/*.py` vacío (el script vive en `scripts/`, no en el algoritmo); reusa `to_lean_rows`/`write_lean_zip` (sin reimplementar el formato).

### T4 — Cross-check de fidelidad + SMAs coherentes
Análogo al cross-check de 5B (F3): verificar que los zips de Alpaca cargan en `SymbolData` y producen SMAs D/W/M coherentes con la referencia del trader.
- **CA:** para ≥3 símbolos, las SMAs D/W/M computadas vía `SymbolData` desde los zips Alpaca cuadran con la referencia (TradingView/Stooq) dentro de la tolerancia de 5B (≤0,25%); discrepancias por IEX (volumen) documentadas, no "corregidas" en código; test de regresión con fixture autoritativo (extiende el de 5B F3 T6.4).

### T5 — Warmup real del universo contra zips Alpaca + budget coherente con historia disponible
Correr el warmup real del universo completo leyendo los zips Alpaca, con la profundidad derivada por `plan_warmup` (sin hardcodeo).
- **CA:** los `SymbolData` del universo completan warmup contra los zips Alpaca con la profundidad derivada (no hardcodeada); log con filas + duración + nº de símbolos ready/no-ready; confirmado que el `warmup_budget` de prod es coherente con la **historia disponible en Alpaca (~desde 2016)** → **M:200 no viable** (ya excluida por budget con warning desde 5B); símbolos con historia insuficiente excluidos y logueados (`is_ready()`), nunca evaluados en frío.

### T6 — Backtest D/W/M multi-mes con datos Alpaca reales *(rebanada de datos del "backtest 6–12 meses")*
Correr `lean backtest "trade-scanner"` sobre un rango de varios meses con los zips Alpaca, disparando ambos horarios programados.
- **CA:** el backtest corre sin errores sobre datos Alpaca reales multi-mes; genera `ScanResult`/watchlists con evidencia por candidato; **reproducibilidad** verificada (watchlist byte-idéntica entre dos corridas, como en Etapa 7); evidencia citada (rutas de `storage/results/<base>/` + nº de scans disparados). *(La revisión manual de watchlists de fechas conocidas es la otra rebanada de [Etapa 9](etapa-09.md), no aquí.)*

### T7 — Portabilidad local↔cloud *(DoD nº5, eje de modularidad)*
Correr el **mismo** `main.py`/`core/*` bajo dos fuentes cambiando solo configuración (D9A.5): (a) zips locales; (b) data provider de QC cloud (free tier, `lean cloud backtest` o el IDE web de QC, $0).
- **CA:** el mismo algoritmo corre bajo las dos fuentes; `git diff` de `.py` vacío entre corridas; evidencia citada (dos logs / dos comandos con su salida). Si el `lean cloud backtest` por CLI exige tier de org pagado, se documenta y se usa el **IDE web free de QC** como leg cloud (garantizado $0); como fallback de agnosticidad de directorio, se demuestra además zips-Alpaca ↔ zips-Stooq vía `DefaultDataProvider`. Esto cierra el DONE WHEN nº5 del SPECS.

### T8 — Matriz de proveedor (referencia para Fase 2)
Tabla: por fuente (Alpaca-zip local / Stooq-zip local / QC cloud free / [futuro: Alpaca live B/A]), qué se toca para cambiar, qué credenciales, costo, y limitaciones operativas.
- **CA:** sección de referencia escrita con la matriz; cada limitación de Alpaca free citada con su impacto: **IEX** (~2,5% del volumen → usar **volumen relativo**, nunca absoluto), **historia desde ~2016** (→ M:200 fuera de budget prod), **rate-limit ~200 req/min** (afecta descarga, no el scan), **15 min de delay** (solo relevante en live, T9).

### T9 — *(DIFERIDA / opcional)* Live paper con working bar intradía vía Opción B o A
Fuera del objetivo $0 de Fase 1. Solo si se decide habilitar `lean live` paper: resolver el módulo Alpaca por **B** (compilar `Lean.Brokerages.Alpaca` y montar el .dll con `--volume` en Docker, $0 pero frágil) o **A** (QC Researcher, pago). Suscripción `Resolution.MINUTE` → `working_bar` → `market_close` con `partial_bar=True` y precio = working bar real; delay IEX reflejado en `as_of` (no compensado en código). Cero órdenes.
- **CA (si se ejecuta):** una sesión `lean live` paper arranca y conecta sin error de módulo; `market_close` reporta `partial_bar=True` con working bar real; `OutputSink` genera la salida del entorno; delay documentado en `as_of`; `grep` de órdenes vacío. **Mientras no se ejecute, el DoD nº4 del SPECS queda explícitamente diferido** con esta justificación.

---

## Consideraciones técnicas específicas al stack

- **El downloader es host-side y reusa 5B.** No reimplementa el formato LEAN (D9A.3): refactor de `to_lean_rows`/`write_lean_zip` a `scripts/lean_daily.py`, importado por `stooq_to_lean.py` y `alpaca_to_lean.py`. El round-trip de 5B (±1 unidad ×10000) debe seguir verde tras el refactor.
- **`adjustment=split` en Alpaca** para casar con el split-only adjusted de Stooq (5B) y la referencia. `raw`/`all`/`dividend` cambian los precios y romperían el cross-check (T4).
- **Multi-símbolo + paginación + throttle van en el script, no en `main.py`** (D9-1). El endpoint v2 acepta ≤200 símbolos por request; `next_page_token` para historia larga; sleep para respetar ~200 req/min de free. `main.py` jamás ve red.
- **Alpaca free = IEX:** volumen subestimado (usar **volumen relativo** en filtros, nunca absoluto) + historia desde ~2016 (→ M:200 fuera de budget prod, ya con warning desde 5B) + rate-limit ~200 req/min (afecta solo la descarga) + 15 min delay (solo relevante en live, T9).
- **`${VAR}` no se expande en `lean.json`** (gotcha Etapa 1): con Opción C ya no hay credenciales en `lean.json` (el `DefaultDataProvider` lee zips locales). Las claves Alpaca viven solo en `.env`, usadas por el downloader host-side.
- **El reloj del backtest necesita datos en el rango** (gotcha Etapa 2): el rango de fechas del backtest (`config.json` de LEAN) debe caer dentro del rango descargado; si no, el engine no avanza. SPY como ancla de calendario sigue aplicando.
- **El switch de salida ya está aislado** en `core/output.py` (Etapa 8) y se elige por `config/notifications.json`. No re-tocar esa capa aquí.
- **Tests:** la lógica testeable (parseo de respuesta Alpaca → tuplas, emisor LEAN compartido, cross-check de SMAs) corre en Docker vía `scripts/run_tests.sh` con respuestas Alpaca **sintéticas** (sin red en el test). Lo demás (descarga real, backtest multi-mes) se verifica por logs/archivos de la corrida real (definición de "verificado" de CLAUDE.md). El downloader se mockea como `notify_email.py`: la función de fetch HTTP aislada y mockeada.

---

## Qué NO hacer en esta etapa (fuera de scope)

- **NO escribir lógica de Alpaca en el algoritmo.** Nada de SDK ni `urllib` en `main.py`/`core/*`; nada de `if provider ==`. La red vive solo en `scripts/alpaca_to_lean.py` (host-side). `grep -ri alpaca trade-scanner/**/*.py` vacío.
- **NO colocar órdenes** de ningún tipo, ni en la rebanada live opcional (T9). Regla dura V1.
- **NO contratar QC (Opción A) para datos.** El objetivo es $0; A solo se considera si se decide el live (T9) y el presupuesto lo permite.
- **NO configurar el data/history provider Alpaca en `lean.json`** (dispara el módulo NuGet, ADR-002). La fuente en runtime es `DefaultDataProvider` sobre zips locales.
- **NO la revisión manual de watchlists de fechas conocidas** — esa es la otra rebanada de [Etapa 9](etapa-09.md) (validación funcional).
- **NO calibrar `bucket_thresholds`** ni tocar reglas/features/pipeline (congelados desde 6B).
- **NO refactorizar `core/output.py`** ni el sistema de notificación (cerrado en Etapa 8).
- **NO hardcodear profundidad de warmup** para acomodar la historia de Alpaca: se respeta `plan_warmup`/`warmup_budget`.

---

## Done when (medible)

- [x] **T1:** ADR-002 actualizado con la Opción C adoptada para datos + costo ($0) + comandos que habilita/no habilita.
- [x] **T2:** `scripts/check_alpaca_credentials.py` valida cuenta paper **y** market data (≥1 barra diaria), exit code usable como gate. *(2026-06-20: cuenta `PA3OLUYQ2GEU` ACTIVE + 5 barras 1Day IEX de AAPL, EXIT=0; volumen IEX subestimado confirmado en la barra.)*
- [x] **T3:** `scripts/alpaca_to_lean.py` produce zips LEAN diarios válidos para el universo (multi-símbolo + paginación + throttle en el script), idempotente, reusando el emisor de 5B; `grep -ri alpaca trade-scanner/**/*.py` vacío. *(2026-06-20: 234 passed en Docker; emisor extraído a `lean_daily.py` con round-trip 5B verde; descarga real sample_dev 4/4 EXIT=0 a `data/alpaca_lean/daily`; idempotencia por hash; algoritmo alpaca-free. Decisiones/hallazgos —incl. ticker FB reasignado— en [etapa-09a-decisiones-y-pendientes.md](etapa-09a-decisiones-y-pendientes.md).)*
- [x] **T4:** cross-check de fidelidad ≤0,25% para ≥3 símbolos + SMAs D/W/M coherentes vía `SymbolData`; test de regresión con fixture autoritativo verde. *(2026-06-20: 238 passed; Alpaca↔Stooq SPY/AAPL/IBM máx 0,2259% —AAPL M:20— mediana <0,02%; fixture SPY-Alpaca congelado. Detalle en [etapa-09a-decisiones-y-pendientes.md](etapa-09a-decisiones-y-pendientes.md).)*
- [x] **T5:** warmup del universo completo contra zips Alpaca con profundidad derivada (no hardcodeada); baseline (filas + duración + nº símbolos ready) logueado; budget prod coherente con historia Alpaca. *(2026-06-21: env=prod, 141 símbolos, `set_warm_up(1010, DAILY)` =W:200 driver bajo budget 1100; 122.669 barras/8.69s; ready 112/141; W:200 fría por símbolo en listados recientes. **Matiz:** en prod no hay exclusión de M:200 porque las estrategias no la declaran —el guardrail M:200+warning es del superset dev/5B—. Requirió fechas+resolución env-condicional en `main.py`. Detalle en [etapa-09a-decisiones-y-pendientes.md](etapa-09a-decisiones-y-pendientes.md) y [etapa-09a-test-run.md](etapa-09a-test-run.md).)*
- [x] **T6:** backtest D/W/M multi-mes sobre datos Alpaca reales, watchlists reproducibles con evidencia (byte-idéntica entre 2 corridas); evidencia citada. *(2026-06-21: rango 2026-01-02..06-19, 462 scans, 4 estrategias; watchlist materializada en `storage/results/<base>/`; **reproducibilidad**: 482 archivos byte-idénticos entre 2 corridas. Suite 239 passed tras actualizar tests a la regla `D+W+M`.)*
- [ ] **T7:** el mismo algoritmo corre bajo dos fuentes (zips locales ↔ QC cloud free) cambiando **solo** configuración; `git diff` de `.py` vacío (cierra DONE WHEN nº5 del SPECS).
- [ ] **T8:** matriz de proveedor documentada con las limitaciones de Alpaca free y su impacto en el screener.
- [~] **T9 (diferida/opcional):** live paper con working bar vía B/A — fuera del objetivo $0; DoD nº4 del SPECS diferido con justificación hasta que se ejecute.
- [ ] Commit `[Etapa 9A] ...`; secretos fuera del repo verificado (`.env` gitignoreado, `lean.json` sin valores reales).

---

## Mapa de DONE WHEN del SPECS cubiertos por esta etapa

| DoD SPECS (§8) | Cobertura en 9A |
|---|---|
| 1. Warmup preciso, SMAs cuadran | ✅ T4 + T5 (datos Alpaca reales) |
| 2. Watchlists reproducibles con evidencia | ✅ T6 |
| 3. Schedules disparan por calendario | ✅ ya en Etapa 7; confirmado en T6 |
| 4. Working bar intradía (`partial_bar=True`) en live | ⏸️ **diferido** a T9 (requiere feed live, B/A) |
| 5. Cambio de fuente = solo config | ✅ T7 |
| 6. Salida/notificación por entorno aislada | ✅ ya en Etapa 8 |
