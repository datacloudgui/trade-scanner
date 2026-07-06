# Etapa 9B — Correcciones de la auditoría de código E1–E8

**Estado:** pendiente
**Depende de:** Etapa 8 (cerrada). Se intercala **antes** de la Etapa 9 (Validación integral Fase 1): cierra la deuda real de la auditoría Codex que, de no resolverse, invalidaría o dejaría sin verificar criterios DONE WHEN de E9.
**Autoridad de diseño:** PLAN.md > SPECS.md > CLAUDE.md; ADRs en `.claude/decisions/`. Triaje de origen: [revisiones/20260619-205134/triaje-E1-E8.md](../../revisiones/20260619-205134/triaje-E1-E8.md).
**Objetivo:** cerrar la deuda real de la auditoría E1–E8 **sin reabrir alcance ya ratificado por ADR** ni adelantar actividades de E9 (backtest a escala, `lean live`, `lean data download`). Solo se actúan los hallazgos **VIGENTE** y los **"documentar decisión"** del triaje; los YA CORREGIDO / DECISIÓN CONSCIENTE / FALSO POSITIVO no generan tareas.

**Contexto.** El triaje consolidó 38 hallazgos crudos de los 8 informes Codex en 26, de los cuales **20 VIGENTE** + **2 "documentar decisión"**. El hallazgo central — la mezcla de universos entre estrategias (#12) — aparece en 4 informes (E4, E5, E7, E8) y es el único que **bloquea duro** la validación de E9 al producir watchlists con tickers del universo equivocado a escala prod. El resto se reparte entre fixes recomendados ahora (tooling/robustez que E9 ejercita) y limpieza defensiva posponible pero barata.

> **Referencia de criterios DONE WHEN de Fase 1** (SPECS §10 / PLAN §8):
> 1. Carga y warmup precisos (SMA D/W/M cuadran vs referencia, **test de validación**).
> 2. Filtrado correcto (watchlist reproducible sobre fechas conocidas, evidencia por candidato).
> 3. Schedule operativo (`swing_eod`/`market_close` a sus horas; backtest + `lean live`).
> 4. Barra parcial funcional (`market_close`, working bar, `partial_bar=True`).
> 5. Fuente intercambiable (Alpaca↔QC = solo `lean.json`).
> 6. Salida por entorno (local CSV/JSON; cloud `NotificationManager`; sin ramas de negocio por entorno).

---

## Tabla resumen

| # | hallazgo | sev. | capa | archivo:línea | ¿bloquea E9? | recomendación |
|---|---|---|---|---|---|---|
| #12 | Cada pipeline escanea la **unión** de universos, no el suyo | ALTO | L5 | `main.py:47-56,379`; `pipeline.py:100` | **SÍ** — DONE WHEN #2 + "backtest 6–12m / revisar watchlists" | **T1** — filtrar `symbol_data_map` por estrategia |
| #15 | Validación SMA ≤0,25% + fixture autoritativo (5B) sin cerrar | ALTO | tests | `etapa-05b.md:159`; `PLAN.md:289`; `test_sma_regression.py:1` | **SÍ** — DONE WHEN #1 no se puede firmar | **T2** — cerrar T7.2/T7.3 de 5B |
| #16 | Tests críticos de validación se saltan si falta `data/` | ALTO | tests | `test_sma_regression.py:70`; `test_t5_stooq_crosscheck.py:81,85,86` | **SÍ** — DONE WHEN #1 (evidencia hueca) | **T3** — fixture versionado / preflight |
| #7 | `seed_object_store.sh` elige CSV "más reciente" por orden lexicográfico | ALTO | L1 | `seed_object_store.sh:57` | No (workflow 1-CSV, observable) | **T4** — fix recomendado ahora (siembra el universo de E9) |
| #2 | README guía a poner claves Alpaca en `lean.json` + flujo obsoleto | ALTO | docs/L1 | `README.md:49,58,72,103,111,124,135` | No (ningún DONE WHEN) | **T5** — fix recomendado ahora (seguridad; E9 monta creds Alpaca) |
| #5 | Anchor SPY cae a `Resolution.DAILY` en prod | MEDIO | L5 | `main.py:123` | No | **T6** — documentar decisión + verificar en E9 live (DONE WHEN #3) |
| #10 | `COLUMN_ALIASES` mapea 5 cols vs 11 de PLAN §5 | MEDIO | L3 | `core/universe.py:10` | No | **T7** — documentar decisión (reconciliar con §5) |
| #11 | `max_tickers` no fuerza el tope **absoluto** ≤200 | MEDIO | L3 | `core/universe.py:76` | No (config prod = 200) | **T8** — fix recomendado ahora (guardrail regla dura) |
| #20 | Series de rules no validadas vs `plan_warmup` → `KeyError` en scan | MEDIO | L5/L4 | `main.py:65,72,136`; `pipeline.py:106` | No (prod: serie máx M:20=441 ≤ budget 1100) | **T9** — fix recomendado ahora (E9 ajusta budget prod) |
| #21 | `emit()` no escribe archivo si `channels` excluye `"file"` | MEDIO | L4 | `output.py:248-264` | No (config actual trae `"file"`) | **T10** — fix recomendado ahora (honra D8.3; acopla #23) |
| #17 | `seed_sample_data.sh` mezcla zips LEAN con factores neutros "Stooq" | MEDIO | L1 | `seed_sample_data.sh:54,66-72` | No (E9 usa descarga fresca) | **T11** — fix recomendado ahora (alimenta #15/DONE WHEN #1) |
| #8 | `explore_universe.py` oculta tickers no estándar como footer | MEDIO | L1 | `explore_universe.py:57,138` | No | **T12** — fix recomendado ahora (vetting del universo prod de E9) |
| #18 | `SMAPositionRule(tfs=[])` pasa todo en silencio | BAJO | L4 | `core/rules.py:54,69-83` | No | **TC1** (batch) |
| #19 | `resolve_bucket_thresholds` frágil ante config no-numérica | BAJO | L3 | `core/features.py:258-265` | No | **TC1** (batch) |
| #13 | Columnas requeridas hardcodeadas; errores `df.query` sin contexto | BAJO | L3 | `core/universe.py:20,52` | No | **TC1** (batch) |
| #22 | Retornos `bool` de `save`/`email` ignorados | BAJO | L4 | `output.py:261-263,284` | No | **TC1** (batch) |
| #14 | Sin test de tope 200 ni de alias completo | BAJO | tests | `test_universe.py:52` | No | **TC2** (batch) |
| #6 | Sin test del mapeo schedule→time-rule | BAJO | tests | `main.py:431` | No | **TC2** (batch) |
| #24 | Sin test del wiring `notification_groups`→1 `emit`/base | BAJO | tests | `main.py:164,358` | No | **TC2** (batch) |
| #9 | `explore_universe.py` aborta con columna % vacía | BAJO | L1 | `explore_universe.py:93` | No | se hace dentro de **T12** (mismo archivo) |
| #25 | Sin test del wiring `UniverseSpec→main→scan` | BAJO | tests | `test_pipeline.py:160` | No | criterio de aceptación de **T1** |
| #23 | Sin entorno con canal `qc_notify` | BAJO | L1 | `config/notifications.json:7-8` | No | **Diferidos → E9** (setup cloud propio de E9) |

---

## Bloque A — ALTO (máxima severidad presente; no hay hallazgos CRÍTICO)

> Cero hallazgos CRÍTICO en el triaje. Este bloque agrupa los **ALTO**. Ninguno viola reglas duras de órdenes/portabilidad/capas (#12 es un fallo de *alcance de datos* en L5, no un cruce de import), así que ninguno hereda "prioridad máxima por regla dura"; el orden interno es por impacto sobre E9.

### T1 — Cada pipeline escanea solo el universo de su estrategia

1. **Origen:** triaje #12 (informes E4-2, E5-4, E7-1, E8-1) — `main.py:47-56` (unión global `tickers`), `main.py:379` (`pipeline.scan(self.symbol_data, …)`), `pipeline.py:100`.
2. **Severidad:** ALTO · **Capa:** L5 (orquestación; el pipeline L4 ya recibe su mapa como parámetro, no hay que tocarlo).
3. **Por qué es necesario — BLOQUEA E9.** Rompe el criterio **DONE WHEN #2** y la actividad de E9 "backtest 6–12 meses; revisar watchlists de fechas conocidas manualmente". A escala prod los universos `swing_advances` (long) y `swing_declines` (short) son **disjuntos** y ambos quedan suscritos; con el mapa completo, `swing_eod` (long) rankea y evalúa también símbolos de `swing_declines` (y viceversa), así que su watchlist puede contener tickers que **no pertenecen a su universo**. La revisión manual de E9 validaría watchlists contaminadas → resultado inválido. E8 además lo propaga a los archivos y al correo (DONE WHEN #6). En dev quedó enmascarado porque `sample_dev` es un único universo. **No choca con ADR-005**: ese ADR asume universos disjuntos para *no compartir snapshot*; este fix **alinea** la implementación con esa suposición, no la contradice.
4. **Criterio de aceptación medible:**
   - `main.py` conserva `symbols_by_strategy[name] = set(loaded)` en `initialize()` y `_scan_group` pasa a cada `pipeline.scan()` un `symbol_data_map` **filtrado** a los símbolos de esa estrategia (las variantes que comparten universo —`swing_eod`/`market_close` sobre `swing_advances`— comparten el mismo submapa).
   - **Nuevo test L5 de integración (cierra #25)** en `tests/`, ejecutable vía `scripts/run_tests.sh`, con `MockObjectStore`: `swing_eod` carga `{AAA}`, `swing_eod_short` carga `{BBB}` (universos disjuntos); tras el wiring, el `symbol_data_map` que recibe el pipeline long contiene **solo** `AAA` y el short **solo** `BBB`. Símbolos construidos con `Symbol(SecurityIdentifier.generate_equity("AAA", Market.USA, False), "AAA")` (no `Symbol.create(...EQUITY...)`).
   - Backtest dev sigue `EXIT=0` y la watchlist reproducible de dev (IBM short byte-idéntica entre 2 corridas) no regresiona.

### T2 — Cerrar la validación de precisión SMA de 5B (T7.2 manual + T7.3 fixture autoritativo)

1. **Origen:** triaje #15 (informes E5-1, E6-1) — `etapa-05b.md:159`, `PLAN.md:289`, `test_sma_regression.py:1` (test autodeclarado "INTERINO").
2. **Severidad:** ALTO · **Capa:** tests (sobre L2 `SymbolData`/`timeframes`).
3. **Por qué es necesario — BLOQUEA E9.** Es literalmente el **DONE WHEN #1**: "las SMA20 D/W/M de una muestra de símbolos cuadran contra valores de referencia (test de validación contra la plataforma de charting acordada)". Hoy 5B está "en progreso" (`PLAN.md:276`): F2/F3 sin `[x]` y el único test es interino. Sin cerrar esto, E9 **no puede firmar** DONE WHEN #1. La convención de semana de `Calendar.WEEKLY` (lunes→domingo, cierre viernes) es exactamente lo que la validación manual debe confirmar (SPECS §11).
4. **Criterio de aceptación medible:**
   - Validación manual ≤0,25% de SMA20 D/W/M de SPY/AAPL/IBM contra la plataforma de referencia (TradingView/IBKR), **registrada** en `etapa-05b-decisiones-y-pendientes.md` con valores y fecha.
   - Fixture autoritativo **versionado** (no bajo `data/` gitignoreado) con los valores congelados, y un test **no interino** en `tests/` que falle si la SMA del `SymbolData` diverge >0,25% del fixture. Corre dentro de la imagen LEAN vía `scripts/run_tests.sh`.
   - PLAN.md 5B: F2/F3 marcadas `[x]` y Estado → `completada`.

### T3 — Los tests de validación crítica no deben saltarse en checkout limpio

1. **Origen:** triaje #16 (informe E5-2) — `test_sma_regression.py:70`, `test_t5_stooq_crosscheck.py:81,85,86` (`skipif(not …exists())` sobre rutas bajo `data/`, gitignoreado).
2. **Severidad:** ALTO · **Capa:** tests.
3. **Por qué es necesario — BLOQUEA E9.** Sostiene la evidencia de **DONE WHEN #1**: si la validación SMA se salta silenciosamente en un clon limpio, el "test de validación" existe pero no se ejerce → la firma de DONE WHEN #1 sería hueca. Acoplado con T2: el fixture autoritativo de T2, al vivir versionado en `tests/fixtures/`, resuelve la causa raíz para ese test.
4. **Criterio de aceptación medible:**
   - El test autoritativo de T2 corre **siempre** (fixture versionado), sin `skipif` por datos ausentes.
   - Para los cross-checks que sí dependen de datos grandes no versionables (Stooq), o bien se reduce un fixture mínimo a `tests/fixtures/`, o bien `scripts/run_tests.sh` los convierte en **fallo de preflight** (no skip silencioso) cuando faltan, con instrucción de seed. Evidencia: `run_tests.sh` en imagen LEAN reporta `0 skipped` para los tests que respaldan DONE WHEN #1, o un fallo explícito si falta el dato.

### T4 — `seed_object_store.sh` debe elegir el CSV por fecha real, no por orden lexicográfico

1. **Origen:** triaje #7 (informes E3-1, E3-6) — `seed_object_store.sh:57` (`find … | sort | tail -1`).
2. **Severidad:** ALTO · **Capa:** L1 (tooling de host sobre ObjectStore).
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** El workflow normal (un CSV por tipo, archivado a `processed/`) evita el bug, y un universo mal sembrado es observable (conteo de líneas en el log). Pero los nombres `…-{MM-DD-YYYY}.csv` (PLAN §5) ordenan lexicográficamente mal al cruzar mes/año (`12-31-2025` > `01-02-2026` → siembra el **más viejo**). E9 vuelve a sembrar el universo prod para el backtest 6–12 meses; si se acumulan dos exports, la selección silenciosa del viejo corrompería el input de DONE WHEN #1/#2. Fix barato y determinista.
4. **Criterio de aceptación medible:**
   - El script extrae `YYYYMMDD` del nombre y selecciona el máximo por esa clave (no por `sort` de string).
   - Test shell/python en `tests/` (o en `scripts/` con runner) con un directorio temporal que contiene `…-advances-12-31-2025.csv` y `…-advances-01-02-2026.csv` y verifica que se siembra **2026**. Verificable en CI/host (no requiere LEAN).

### T5 — Reescribir README al flujo real (sin secretos en `lean.json`)

1. **Origen:** triaje #2 (informes E1-2, E2-2, E3-5, E4-6, E5-5, E8-6) — `README.md:49,58,72,103,111,124,135`.
2. **Severidad:** ALTO · **Capa:** docs/L1.
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora (seguridad).** Ningún DONE WHEN depende del README, pero el tramo de credenciales instruye "editar `lean.json` y agregar las claves de Alpaca" — y `lean.json` está **commiteado**. El prerrequisito bloqueante de E9 es montar credenciales Alpaca para `lean live`; seguir el README en ese momento es una ruta directa a fuga de secretos (contradice ADR-002 y el flujo `.env`). El resto del README (proyecto `Screener`, estrategias/notificación en `config.json`, CSV `ticker,price,avg_dollar_volume`) desorienta sobre el contrato real de E2–E8.
4. **Criterio de aceptación medible:**
   - README describe: workspace = raíz del repo, `lean.json` con campos de credenciales **vacíos** (valores reales solo en `.env` gitignoreado), sin `lean login` en Fase 1, proyecto `trade-scanner`, config de negocio en `config/strategies.json` + `config/notifications.json` (ObjectStore), universos CSV Barchart, salida en `storage/results/<base>/latest.json`.
   - `grep -nE "lean login|claves de Alpaca|Screener/config\.json|ticker,price,avg_dollar_volume" README.md` → **0 hits**.

---

## Bloque B — MEDIO

### T6 — Documentar por qué el anchor SPY en `Resolution.DAILY` es seguro (+ verificación en E9)

1. **Origen:** triaje #5 (informe E2-1) — `main.py:123`. Clasificación: **documentar decisión**.
2. **Severidad:** MEDIO · **Capa:** L5.
3. **Por qué es necesario — NO BLOQUEA.** En prod SPY no está en `swing_advances/declines` → cae al anchor daily. No rompe DONE WHEN #3 porque el reloj avanza por la suscripción `Resolution.MINUTE` de **todo** el universo (`main.py:86`) y `before_market_close(spy,…)`/`after_market_close` usan las *market hours* de SPY, independientes de la resolución del feed. Falta dejar esa garantía por escrito; y la confirmación empírica corresponde a E9 (`lean live` paper + timestamps).
4. **Criterio de aceptación medible:**
   - Comentario en `main.py:123` y entrada en `etapa-09b`/decisiones explicando: clock ← universo minute; anchor solo aporta market-hours. **Sin cambio de lógica.**
   - Checkbox añadido a E9 (DONE WHEN #3): verificar en `lean live` paper que ambos schedules disparan a su hora con SPY fuera del universo. *Si la verificación empírica de E9 mostrara misfire → reabrir como tarea de código (verificar con el usuario).*

### T7 — Reconciliar `COLUMN_ALIASES` con el contrato §5 de PLAN

1. **Origen:** triaje #10 (informes E3-4, E4-3) — `core/universe.py:10`. Clasificación: **documentar decisión**.
2. **Severidad:** MEDIO · **Capa:** L3.
3. **Por qué es necesario — NO BLOQUEA.** `etapa-04.md:77,93` acotó deliberadamente el alias map a las 5 columnas usadas ("columnas extra se ignoran"); funcionalmente correcto hoy (ningún `universe_filter` referencia `high_5d/chg_5d/…`). Pero PLAN §5 (máxima precedencia) lista 11 columnas como contrato "definitivo" → discrepancia que conviene zanjar por escrito, no en silencio.
4. **Criterio de aceptación medible:**
   - Documentar la decisión (mantener 5 alias por YAGNI; el resto se añade cuando un filtro los use) en `etapa-04-decisiones-y-pendientes.md` **o** reconciliar PLAN §5 anotando que el alias map activo es un subconjunto. Sin cambio de código obligatorio.
   - Si se opta por completar el mapa: añadir los 6 alias restantes + su parseo, cubierto por el test de alias de TC2.

### T8 — Tope duro absoluto ≤200 independiente de la config

1. **Origen:** triaje #11 (informe E4-1) — `core/universe.py:76`.
2. **Severidad:** MEDIO · **Capa:** L3.
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** `UniverseSpec` trunca a `max_tickers` (= `env_cfg["max_universe"]`, hoy 200 en prod) pero no impide `>200`. "≤200 post-filtro" es **regla dura** de producto (CLAUDE.md, PLAN §5, DONE WHEN #1 "≤200 símbolos"). E9 ejercita la carga de universo a escala; un guardrail barato evita que un futuro `max_universe` mal puesto viole la regla dura.
4. **Criterio de aceptación medible:**
   - `UniverseSpec` aplica `min(max_tickers, 200)` o valida en `__init__` (`1 <= max_tickers <= 200`), con log/raise explícito al recortar.
   - Test (TC2) con `max_tickers=201`/CSV>200 que verifica salida ≤200.

### T9 — Validar en `initialize()` que las series de las rules estén en el plan de warmup

1. **Origen:** triaje #20 (informe E7-2) — `main.py:65,72,136`; `pipeline.py:106` (`sd.is_ready(tf,p)` → `sma()` lanza `KeyError`).
2. **Severidad:** MEDIO · **Capa:** L5 (validación) / L4 (consumidor).
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** Con la config prod actual no se dispara: las series referenciadas por rules son D:8→13, D:20→25, W:20→110, **M:20→441** barras (fórmula PLAN §4: `D:n→n+5`, `W:n→n*5+10`, `M:n→n*21+21`), y el `warmup_budget` prod es `daily: 1100` ≥ 441. Pero E9 es exactamente cuando se ajusta el budget prod (Alpaca solo sirve ~10 años → M:200 ya excluido); si un ajuste excluyera por error una serie que una rule usa, el gate del scan lanzaría `KeyError` **no capturado** a mitad del backtest/live, en vez de un error claro de config en `initialize()`. Convierte un crash opaco (que rompería DONE WHEN #2/#3) en fail-fast.
4. **Criterio de aceptación medible:**
   - `initialize()` valida que, para cada pipeline, `composition.series(side) ⊆ plan.included`; si falta una serie referenciada, `raise ValueError` claro (estrategia + serie) **antes** de registrar schedules.
   - Test (en `tests/`, vía `run_tests.sh`): un plan que excluye una serie referenciada por una rule produce `ValueError` en construcción; el caso prod real (todas incluidas) no lanza.

### T10 — `OutputSink` persiste el archivo SIEMPRE, fuera de la lista de canales

1. **Origen:** triaje #21 (informe E8-2) — `output.py:248-264` (`_emit_file` solo corre si `channels` contiene `"file"`).
2. **Severidad:** MEDIO · **Capa:** L4.
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** La config actual siempre trae `"file"`, así que DONE WHEN #6 (local genera CSV/JSON) se verifica hoy. Pero D8.3 dice "SIEMPRE archivo (auditoría)" y el código solo lo garantiza por el *default* cuando el env falta, no ante un `channels` explícito sin `"file"`. E9 añade el entorno `qc_notify` (ver Diferidos #23); si ese env quedara como `["qc_notify"]` sin `"file"`, se perdería la auditoría durable en silencio. Acoplar el fix con la entrada de config de #23.
4. **Criterio de aceptación medible:**
   - `emit()` ejecuta la persistencia de archivo **incondicionalmente** (fuera del bucle de canales opcionales), o falla rápido si `"file"` no está presente.
   - Tests (en `tests/`): `channels=[]`, `["qc_notify"]`, `["host_email"]` → JSON/CSV/`latest.json` igualmente escritos (verificado sobre `MockObjectStore`).

### T11 — Separar el seed de sample LEAN del data de validación Stooq

1. **Origen:** triaje #17 (informe E5-3) — `seed_sample_data.sh:54,66-72` (baja `daily/{aapl,ibm}.zip` del repo LEAN pero escribe factor files **neutros** comentados como origen Stooq).
2. **Severidad:** MEDIO · **Capa:** L1.
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** E9 a escala prod usa descarga fresca (QC/Stooq), no este script de sample dev. Pero el data que produce alimenta la **validación de #15** (T2): factores neutros sobre zips LEAN (ya ajustados) puede dar SMAs de referencia incoherentes → contamina DONE WHEN #1. Hay que cerrar esta incoherencia antes de congelar el fixture autoritativo de T2.
4. **Criterio de aceptación medible:**
   - El script separa "seed LEAN sample" de "preparar data Stooq split-only", o ejecuta `stooq_to_lean.py` con CSVs explícitos y **falla** si no están (sin sobrescribir factores con origen inconsistente).
   - Comentarios del script coherentes con la fuente real de cada zip. Evidencia: el fixture de T2 se congela sobre data de origen único y documentado.

### T12 — Endurecer `explore_universe.py` (footer real + columnas % vacías)

1. **Origen:** triaje #8 (informe E3-2) — `explore_universe.py:57,138`; incluye #9 (informe E3-3/E3-7) — `explore_universe.py:93` (mismo archivo).
2. **Severidad:** MEDIO (#8) + BAJO (#9) · **Capa:** L1 (tooling de perfilado).
3. **Por qué es necesario — NO BLOQUEA, fix recomendado ahora.** No está en el runtime ni en ningún DONE WHEN, pero es la herramienta con la que se **vetea el CSV de universo prod antes de sembrarlo para E9**. Hoy `non_standard` se calcula sobre `data_rows` (ya filtrado por `^[A-Z]{1,5}$`) → siempre vacío, y un `BRK.B` se oculta como "footer"; además una columna porcentual íntegramente vacía aborta el script (`min([])`).
4. **Criterio de aceptación medible:**
   - El footer se detecta por patrón Barchart (p. ej. `Downloaded from Barchart.com`) y los símbolos inválidos restantes se reportan como **no estándar** (no como footer).
   - Las columnas `PERCENT` aplican el mismo guard `if valid` que las numéricas (`n/a` en vez de excepción).
   - Test (TC2) sobre fixtures pequeños: footer Barchart + un `BRK.B` reportado como no estándar + columna % vacía sin abortar.

---

## Bloque C — BAJO (limpieza agrupada)

### TC1 — Guards defensivos de config y composición (L3/L4)

1. **Origen:** triaje #18, #19, #13, #22.
2. **Severidad:** BAJO · **Capa:** L3/L4.
3. **Por qué — NO BLOQUEA.** Ninguno se dispara con la config/composición actual; son endurecimientos baratos que convierten fallos opacos en errores claros. Se hacen en bloque.
4. **Checklist + criterio de aceptación medible** (todos con test en `tests/`, vía `run_tests.sh`):
   - [ ] **#18** `core/rules.py`: `SMAPositionRule.__init__` rechaza `tfs` vacío con `ValueError`. Test de construcción que espera `ValueError` para `tfs=[]`. *(Alcanzabilidad baja: `tfs` viene de código en `strategies/`, no de config — pero un `evaluate` que pasa todo en silencio es un modo de fallo caro.)*
   - [ ] **#19** `core/features.py`: `resolve_bucket_thresholds` valida mapping, castea a `float`, rechaza bool/NaN/inf y emite `ValueError` de config claro (no `TypeError`/`AttributeError`). Tests para `"near":"0.005"`, valor no-numérico y `bucket_thresholds` no-dict.
   - [ ] **#13** `core/universe.py`: validar las columnas requeridas contra los aliases efectivamente usados por `filter_expr` (allowlist) y envolver errores de `df.query` con `universe_key`+`filter_expr`. Test con filtro sobre alias no mapeado → error con contexto.
   - [ ] **#22** `core/output.py`: comprobar los retornos `bool` de los tres `object_store.save(...)` y del `notify.email(...)`; si `False`, log de fallo explícito / raise, nunca "listo". Test con mock que devuelve `False`. *(Verificar contra la API de LEAN que `False` significa fallo de escritura/envío.)*

### TC2 — Cobertura de regresión de contratos y wiring (tests)

1. **Origen:** triaje #14, #6, #24 (#25 ya cubierto por T1).
2. **Severidad:** BAJO · **Capa:** tests.
3. **Por qué — NO BLOQUEA.** Blindan los fixes de A/B contra regresión. Se agrupan.
4. **Checklist + criterio de aceptación medible** (todos vía `run_tests.sh`):
   - [ ] **#14** Test del tope absoluto 200 (pareja de T8) y del alias map (estado tras T7): `max_tickers=201`/CSV>200 → ≤200; alias documentados presentes/ausentes según la decisión de T7.
   - [ ] **#6** Test del mapeo `_time_rule_for`: `"after_close"`/`"before_close_30m"` → la time-rule esperada; string desconocido → `None` (omitido). Si requiere extraer la función pura del mapeo para testearla sin `QCAlgorithm`, hacerlo sin tocar la lógica.
   - [ ] **#24** Test del wiring de notificación (extraer/inyectar el agrupador o mockear): `notification_groups` → un schedule por base, invariantes schedule/`partial_bar` de D8.7 (config inconsistente → `ValueError`), secciones vacías presentes, **exactamente un** `emit` por base. *Si el wiring resulta inseparable de `QCAlgorithm` sin refactor mayor, reducir el alcance al invariante D8.7 y dejar el "1 emit/base" como evidencia de backtest (verificar con el usuario).*

---

## Consideraciones técnicas específicas al stack

- **Pureza L3/L4:** `core/features.py`, `core/rules.py`, `core/pipeline.py`, `core/universe.py`, `core/output.py`, `core/email_render.py` **no** importan `AlgorithmImports`. Las correcciones (T1 filtra el mapa en L5, no en el pipeline; TC1 en features/rules/universe/output) deben preservarlo → testeables con mocks sin CLR.
- **Switch local/cloud solo en `output.py`:** T10 corrige *dónde/siempre* se persiste, **no** introduce ramas `if env == …` fuera del dispatch por canal (D8.4 / criterio nº6 SPECS).
- **Warmup derivado, nunca hardcodeado:** T9 valida contra el `plan_warmup` derivado de la fórmula §4 (`D:n→n+5`, `W:n→n*5+10`, `M:n→n*21+21`); no se introduce ningún número de barras fijo. El budget prod (`daily: 1100`) y la serie máxima referenciada (M:20→441) son datos de verificación, no constantes a hornear.
- **Consolidators perezosos:** cualquier test nuevo de SMA (T2/T3) debe cerrar con `SymbolData.scan(end_time)` o barra trailing para forzar la emisión perezosa (hallazgo D-E5A); sin el flush la última barra queda en `working_data` y la SMA sale un periodo fría.
- **ObjectStore, no `open()`:** el código de runtime lee/escribe vía `self.object_store`; los tests usan `MockObjectStore` con `.read(key)->str` / `.save(key,str)->bool`. T10/TC1#22 mockean los retornos.
- **`Symbol` en tests:** construir con `Symbol(SecurityIdentifier.generate_equity("AAA", Market.USA, False), "AAA")`; **nunca** `Symbol.create(..., EQUITY, ...)` (lanza NullReference fuera del engine). Para scripts directos en la imagen, `PYTHONPATH` con `/Lean/Launcher/bin/Debug`.
- **Cero órdenes:** ninguna tarea introduce `market_order`/`set_holdings`/`liquidate`/`buy`/`sell`. Grep limpio sigue siendo invariante.
- **Tests dentro de la imagen LEAN:** todo criterio "test" corre vía `scripts/run_tests.sh` (pythonnet/coreclr); pytest del host no tiene `AlgorithmImports`. Las pruebas de scripts L1 puros (T4 selección de CSV) sí pueden correr en host.

---

## Qué NO hacer en esta etapa (fuera de scope)

- **Nada de las actividades de E9:** sin backtest a escala (6–12 meses), sin `lean live`, sin `lean data download`, sin montar credenciales QC/Alpaca. La verificación empírica del anchor (T6) y del cloud `qc_notify` (#23) ocurre **en E9**, no aquí.
- **Sin calibración de `bucket_thresholds`** (`near/mild/extended`) ni de la inclusión de `near` en "above": es Etapa 9 / SPECS §11, ratificado en ADR-005 §9.2. TC1#19 endurece la *validación de tipos*, no cambia valores.
- **Ningún rediseño ya ratificado por ADR.** En particular el cableado manual de SMAs por `data_consolidated` (PLAN §4 / decisión congelada, no `register_indicator`) y el snapshot único / rules como filtros (ADR-005) no se tocan.
- **Hallazgos YA CORREGIDO / DECISIÓN CONSCIENTE / FALSO POSITIVO no generan tareas.** En concreto: `set_holdings` del artefacto E1 (gitignoreado), `data/object-store/` vacío (store regenerable en `storage/`), y el diferimiento de backtest ≥3 meses / candidato working-bar vivo a E9.
- **Los POSPONIBLES se listan en Diferidos pero NO se ejecutan aquí.**

---

## Diferidos

| # | hallazgo | destino | por qué es seguro diferir |
|---|---|---|---|
| #23 | Sin entorno con canal `qc_notify` en `notifications.json` | **Etapa 9** | Verificar DONE WHEN #6 lado cloud (`NotificationManager`) es actividad propia de E9 (`lean live`/cloud); añadir el env `cloud=["file","qc_notify"]` es parte de su setup. El handler ya existe y está testeado. Acoplar con T10 (file siempre) para no perder auditoría. |
| #26 | Backtest ≥3 meses + candidato con working bar intradía vivo | **Etapa 9** | Diferido por decisión usuario (falta data minute multi-símbolo; requiere `lean data download` QC-pago, ADR-002). DONE WHEN #4 se cierra con data real en E9. **DECISIÓN CONSCIENTE**, no deuda de código. |

> Ningún hallazgo vigente **choca** con un ADR (ADR-005 no sanciona el scan sobre la unión; #12 es un fix alineado con su supuesto de universos disjuntos), así que no hay entrada "requiere nuevo ADR". Si la verificación empírica de E9 contradijera el supuesto de T6 (anchor) o de T9 (budget prod), reabrir como tarea de código — marcado "verificar con el usuario" en su recomendación.

---

## Done when (medible)

- [ ] **Todos los hallazgos que BLOQUEAN E9 resueltos y verificados:** T1 (#12, DONE WHEN #2), T2 (#15, DONE WHEN #1), T3 (#16, DONE WHEN #1) — cada uno con su test/evidencia citada.
- [ ] `bash scripts/run_tests.sh` **verde dentro de la imagen LEAN**, incluyendo los tests nuevos de cada tarea de A y B (integración de universos disjuntos T1, fixture autoritativo no-interino T2/T3, validación de series vs plan T9, archivo-siempre T10, selección de CSV por fecha T4).
- [ ] **Bloque C cerrado:** checklist de TC1/TC2 completo; `grep` de regla dura limpio (`market_order|set_holdings|liquidate` = 0) y `grep` del README (T5) sin hits de flujo obsoleto/secretos.
- [ ] **Decisiones conscientes documentadas:** T6 (anchor daily seguro) y T7 (alias map subconjunto de §5) registradas en el doc correspondiente; PLAN.md 5B → `completada` tras T2.
- [ ] **Sin regresión de E1–E8:** backtest dev `EXIT=0`, watchlist reproducible byte-idéntica entre 2 corridas, cero `AlgorithmImports` en L3/L4.
- [ ] Diferidos (#23, #26) anotados en E9 para que no se pierdan.
