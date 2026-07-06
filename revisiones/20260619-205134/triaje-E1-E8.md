# Triaje de la revisión Codex — Etapas E1–E8

**Fecha:** 2026-06-20 · **Rama:** `feature/etapa-6-features-rules`
**Entrada:** `revisiones/20260619-205134/etapa-0{1..8}-informe.md` (los 8 informes existen; `*-log.md` ignorados).
**Método:** consolidación + dedupe de los 8 informes; cada hallazgo verificado contra el **código actual** y contra PLAN.md > SPECS.md > CLAUDE.md > ADR-* > etapa-*-decisiones.
**Solo triaje:** no se modificó código ni se escribió ningún spec.

**38 hallazgos crudos → 26 consolidados.** Duplicados fusionados: README (E1/E2/E3/E4/E5/E8 → 1), `COLUMN_ALIASES` (E3/E4 → 1), universo-por-estrategia (E4/E5/E7/E8 → 1), cierre de 5B (E5/E6 → 1), y los "sin test" de E3 plegados a su hallazgo de código.

> **Cobertura ampliada:** esta versión incorpora E6 (features/rules), E7 (pipeline/strategies) y E8 (output). El hallazgo más recurrente — mezcla de universos (#12) — aparece ya en **4 informes** (E4, E5, E7, E8), lo que eleva su confianza.

---

## 1. Tabla de triaje

| # | etapa(s) informe | archivo:línea | sev. | capa | clasificación | evidencia | nota |
|---|---|---|---|---|---|---|---|
| 1 | E1-1 | `backtests/2026-06-11_00-47-42/code/main.py:20` (`set_holdings`) | CRÍTICO | L5 | **YA CORREGIDO** | `main.py` actual sin órdenes (grep `set_holdings/market_order/liquidate` = 0); `backtests/` no trackeado y gitignoreado | Codex revisó un **artefacto** del smoke E1, no el fuente. Invariante "cero órdenes" se cumple HOY. |
| 2 | E1-2, E2-2, E3-5, E4-6, E5-5, E8-6 | `README.md:49,58,72,103,111,124,135` | ALTO | docs/L1 | **VIGENTE** | README sigue: `lean init`/`lean login`, "claves Alpaca en `lean.json`", proyecto `Screener`, estrategias y notificación en `config.json`, CSV viejo sin `direction`/envelope | El tramo de credenciales es de seguridad (dirige secretos a archivo commiteado). Contradice ADR-002, PLAN §4/§5, E2/E3/E8. |
| 3 | E1-3 | `backtests/2026-06-11_00-47-42/log.txt:58` | MEDIO | L6 | **YA CORREGIDO** (moot) | E7 (`PLAN.md:331`) y E8 (`PLAN.md:345`) reportan backtest dev `EXIT=0` | "Sequence contains no elements" era falta de sample data en E1; resuelto por `seed_sample_data.sh`. |
| 4 | E1-4 | `etapa-01.md:30` / `.gitignore:160` | BAJO | L1 | **DECISIÓN CONSCIENTE** | Etapa 2 movió el store a `storage/` (regenerable desde `config/`+`universes/`) | Dir vacío no se preserva en git, pero el store local es regenerable por diseño. |
| 5 | E2-1 | `main.py:123` (anchor SPY fallback `Resolution.DAILY`) | MEDIO | L5 | **DECISIÓN CONSCIENTE → documentar** | `main.py:86` suscribe TODO el universo a `Resolution.MINUTE`; el reloj avanza por esas barras | El anchor solo aporta market-hours (independiente de resolución). Seguro HOY, sin documentar. *Verificar vs LEAN un env con universo daily-only.* |
| 6 | E2-3 | `main.py:431` (`_time_rule_for`) | BAJO | tests | **VIGENTE** | sin test unitario del mapeo schedule→time-rule | E8 añadió invariantes de grupo D8.7, pero solo se ejercitan en backtest. Ver #24. |
| 7 | E3-1, E3-6 | `scripts/seed_object_store.sh:57` | ALTO | L1 | **VIGENTE** | `find ... \| sort \| tail -1` sobre `…-{MM-DD-YYYY}.csv` (PLAN §5) | `12-31-2025` ordena > `01-02-2026` → siembra el universo MÁS VIEJO al cruzar mes/año. Sin test (E3-6). |
| 8 | E3-2 | `scripts/explore_universe.py:57,138` | MEDIO | L1 | **VIGENTE** | `non_standard` (l.138) se calcula sobre `data_rows`, que ya excluyó lo que no matchea `SYMBOL_RE` → **siempre vacío** | Tickers reales no estándar (`BRK.B`) se ocultan como "footer". Script de dev. |
| 9 | E3-3, E3-7 | `scripts/explore_universe.py:93` | BAJO | L1 | **VIGENTE** | columnas `PERCENT` sin el guard `if valid` de las numéricas (l.100) → `min([])` lanza | Aborta en CSV sucio en vez de diagnosticar. Sin test (E3-7). Script de dev. |
| 10 | E3-4, E4-3 | `core/universe.py:10` (`COLUMN_ALIASES`) | MEDIO | L3 | **DECISIÓN CONSCIENTE → documentar** | `etapa-04.md:77,93` acota el alias map a las 5 columnas usadas; "columnas extra se ignoran" | Tensión con PLAN §5 (11 cols, "definitivo"). Sin impacto HOY. Reconciliar doc si E9 añade filtros. |
| 11 | E4-1 | `core/universe.py:76` (`max_tickers`) | MEDIO | L3 | **VIGENTE** | trunca a `max_tickers` (= `env_cfg.max_universe`) pero no fuerza el tope **absoluto** 200 | `max_universe>200` viola la regla dura "≤200 post-filtro" (CLAUDE.md/PLAN §5). Depende de config correcta. |
| 12 | E4-2, E5-4, **E7-1, E8-1** | `main.py:47-56,379`; `core/pipeline.py:100` | ALTO | L5 | **VIGENTE** | `tickers` = unión global; `_scan_group` pasa `self.symbol_data` (mapa completo) a CADA pipeline | Long evalúa también `swing_declines` y viceversa. Rompe entidad `UniverseSpec` (SPECS) y D7.5. E8 lo propaga a archivos/correo. Enmascarado en dev. **Requiere decisión de diseño / posible ADR.** |
| 13 | E4-4 | `core/universe.py:20,52` (`_REQUIRED_COLUMNS`) | BAJO | L3 | **VIGENTE** | columnas requeridas hardcodeadas a `avg_vol_5d/price`, no derivadas de `filter_expr`; errores de `df.query` sin envolver | Latente: filtro sobre alias no mapeado falla tarde. Sin impacto en V1. |
| 14 | E4-5 | `tests/test_universe.py:52` | BAJO | tests | **VIGENTE** | sin test de tope absoluto 200 ni de alias completo | Blinda #11/#10. |
| 15 | E5-1, **E6-1** | `etapa-05b.md:159`; `PLAN.md:276,289`; `test_sma_regression.py:1` | ALTO | tests | **VIGENTE** (abierto por diseño) | PLAN marca 5B "en progreso"; F2/F3 (validación ≤0,25% + fixture autoritativo) sin `[x]`; test "INTERINO" | No es regresión: etapa deliberadamente abierta. E6 hereda la falta de base SMA real validada. T7.2/T7.3 pendientes. |
| 16 | E5-2 | `test_sma_regression.py:70`; `test_t5_stooq_crosscheck.py:81,85,86` | ALTO | tests | **VIGENTE** | `skipif(not …exists())` sobre rutas bajo `data/` (gitignoreado) | En checkout limpio la suite queda verde sin ejercer el criterio central de E5. |
| 17 | E5-3 | `scripts/seed_sample_data.sh:54,66-72` | MEDIO | L1 | **VIGENTE** | baja `daily/{aapl,ibm}.zip` del repo **LEAN** (l.54) pero escribe factor files **neutros** comentados como origen **Stooq** (l.66-72) | Incoherencia fuente↔factor: puede no reproducir T6.1. Ligado a 5B abierto (#15). |
| 18 | E6-2 | `core/rules.py:54,69-83` (`SMAPositionRule`) | MEDIO | L4 | **VIGENTE** | el constructor no valida `tfs` no vacío; `evaluate([])` no itera → `passed=True`, evidencia `{}` | Una rule mal compuesta pasa TODO en silencio. Baja alcanzabilidad: `tfs` viene de código (`strategies/`), no de config. Guard defensivo barato. |
| 19 | E6-3 | `core/features.py:258-265` (`resolve_bucket_thresholds`) | MEDIO | L3 | **VIGENTE** | no valida que `bucket_thresholds` sea mapping ni que los valores sean numéricos; `"near":"0.005"` o lista truthy → `TypeError`/`AttributeError` | Config malformada (ObjectStore, editable) cae en error opaco, no en `ValueError` claro. `[] or {}` ya cubre lista vacía; falta el resto. |
| 20 | E7-2 | `main.py:65,72,136`; `core/pipeline.py:106`; `symbol_data.py:128-140` | MEDIO | L5/L4 | **VIGENTE** | las series de las rules (`composition.series`) no se validan contra `plan.included`; si el presupuesto excluye una serie referenciada, `sd.is_ready(tf,p)` → `sma()` lanza `KeyError` (no exclusión controlada) | El gate no captura `KeyError` → crashea el scan. Latente: hoy el budget incluye todas las series. Apunta a validar en `initialize()` antes de registrar schedules. |
| 21 | E8-2 | `core/output.py:214-221,248-264` (`emit`/`_emit_file`) | MEDIO | L4 | **VIGENTE** | `emit` solo corre `_emit_file` si `channels` contiene `"file"`; un `channels:[]`/`["qc_notify"]`/`["host_email"]` deja sin JSON/CSV/latest | Contradice D8.3 ("SIEMPRE archivo"), que el código solo garantiza vía el default cuando el env falta. Enmascarado: config actual siempre trae `"file"`. Apunta a persistir archivo incondicionalmente. |
| 22 | E8-3 | `core/output.py:261-263,284` | BAJO | L4 | **VIGENTE** | `object_store.save(...)` y `notify.email(...)` retornan `bool` pero el código ignora el resultado y loguea éxito siempre | Un fallo de escritura/notificación queda invisible. *Verificar vs LEAN la semántica del retorno (¿`False`=fallo?).* |
| 23 | E8-4 | `config/notifications.json:7-8` | BAJO | L1 | **VIGENTE** | solo `dev=["file"]` y `prod=["file","host_email"]`; ningún entorno con `qc_notify` | El handler existe y está testeado, pero cloud `env=prod` no dispara `NotificationManager` (SPECS #6). Diferible a E9 (config/doc). |
| 24 | E8-5 | `main.py:164,358`; `tests/test_output.py:260` | BAJO | tests | **VIGENTE** | sin test del wiring L5 `notification_groups` → 1 schedule/base → `_scan_group` → 1 solo `emit` | La evidencia es backtest/log, no un test de regresión. Cubre también #6 (invariantes schedule/partial_bar). |
| 25 | E7-3 | `tests/test_pipeline.py:160`; `tests/test_strategies.py:160` | BAJO | tests | **VIGENTE** | tests cubren `ScanPipeline` con mapas ya filtrados, no el wiring `UniverseSpec→main.py→pipeline.scan` | Por eso la suite no detecta #12. Apunta a test L5 con universos long/short disjuntos. |
| 26 | E7-4 | `etapa-07-t6-decisiones-y-pendientes.md:20,52`; `PLAN.md:331` | BAJO | L6 | **DECISIÓN CONSCIENTE** | backtest ≥3 meses + candidato con working_bar intradía vivo **diferidos a E9** (decisión usuario; falta data minute multi-símbolo) | No es bug. Trazabilidad de SPECS DW#4 queda parcial en E7 (IBM ejercita fallback `close("D")`); obligatorio cuando E9 tenga data minute. |

---

## 2. Detalle por hallazgo VIGENTE / "documentar decisión"

**#2 — README desactualizado (ALTO, docs/L1).** Guía a `lean init`/`lean login` y a poner claves de Alpaca en `lean.json` (commiteado), describe estrategias/notificación en `config.json` y un CSV viejo sin `direction`/envelope. El tramo de credenciales es una ruta directa a fuga de secretos (contradice ADR-002 y el flujo `.env`). Apunta a reescribir Setup/Config/Universo/Salida al contrato real de E2–E8 (`config/strategies.json`, `config/notifications.json`, `storage/results/<base>/latest.json`).

**#5 — Anchor SPY en `Resolution.DAILY` (MEDIO, L5 · documentar decisión).** En prod SPY cae al anchor daily, pero no rompe: el reloj avanza por la suscripción MINUTE de todo el universo y `before_market_close(spy,…)` usa las market-hours de SPY, independientes de la resolución del feed. Falta dejar escrita esa garantía. *Verificar vs LEAN el caso límite de un env con universo daily-only.*

**#6 — Sin test del mapeo schedule (BAJO, tests).** `_time_rule_for` traduce strings de schedule a time-rules sin regresión pytest; un cambio de string rompería el schedule en silencio. Se solapa con #24 (wiring de grupo).

**#7 — Selección de CSV "más reciente" rota (ALTO, L1).** `sort | tail -1` sobre nombres `MM-DD-YYYY` ordena lexicográficamente: al cruzar mes/año siembra el universo más antiguo. Corrompe silenciosamente el universo efectivo. Apunta a parsear la fecha y ordenar por `YYYYMMDD`, con test (`12-31-2025` vs `01-02-2026`).

**#8 — `explore_universe.py` oculta tickers no estándar (MEDIO, L1).** `non_standard` se calcula sobre `data_rows`, ya filtrado por `^[A-Z]{1,5}$`, así que siempre sale vacío y `BRK.B` aparece como "footer". Debilita el reporte exploratorio de E3. Apunta a detectar el footer por patrón Barchart y reportar el resto como no estándar.

**#9 — `explore_universe.py` aborta con porcentajes vacíos (BAJO, L1).** Las columnas `PERCENT` no replican el guard `if valid:` de las numéricas → `min([])` lanza ante una columna porcentual vacía/sucia. Apunta a aplicar el mismo guard `n/a`.

**#11 — Tope duro 200 no garantizado en código (MEDIO, L3).** `UniverseSpec` trunca a `max_tickers` (de `env_cfg["max_universe"]`); nada impide `>200`. "≤200 post-filtro" es regla dura de producto y hoy depende de que la config no se equivoque. Apunta a un guardrail `min(max_tickers, 200)` o validación en `__init__`.

**#12 — Scan cruza universos entre estrategias (ALTO, L5).** El universo se materializa como unión global y cada `pipeline.scan` recibe el mapa completo, así que una estrategia long rankea/evalúa también símbolos de `swing_declines` (y viceversa); E8 lo propaga a archivos/correo. Viola la entidad `UniverseSpec` y D7.5 (universos disjuntos). Las rules (precio vs SMA) + dirección del ranking lo mitigan en la práctica pero no lo garantizan; en dev queda enmascarado (`sample_dev` único). ADR-005 menciona universos disjuntos solo para no compartir snapshots — **no** sanciona el scan sobre la unión. Apunta a conservar `symbols_by_strategy` y pasar a cada pipeline su mapa filtrado (+ test, ver #25). **Requiere decisión de diseño / posible ADR nuevo.** (Corroborado por E4/E5/E7/E8.)

**#13 — Columnas requeridas hardcodeadas (BAJO, L3).** `_REQUIRED_COLUMNS={avg_vol_5d,price}` no deriva de `filter_expr` y los errores de `df.query` no se envuelven con contexto. Latente; sin impacto en V1.

**#14 — Falta cobertura de invariantes de E4 (BAJO, tests).** Sin test del tope absoluto 200 ni del alias map completo. Blinda #11 y #10.

**#15 — Etapa 5B abierta vs su Done-when (ALTO, tests · abierto por diseño).** F2/F3 (validación manual ≤0,25% + fixture autoritativo) sin cerrar; test vigente "INTERINO". E6 hereda la falta de base SMA real validada. No es regresión sino etapa "en progreso" en PLAN. Apunta a congelar valores SPY/AAPL/IBM D/W/M y un test no-interino.

**#16 — Tests críticos de E5 se saltan sin datos (ALTO, tests).** `skipif(not …exists())` sobre rutas bajo `data/` (gitignoreado) deja un checkout limpio "verde" sin ejercer la matemática SMA/Stooq. Apunta a fixtures mínimos versionados o un preflight que falle si faltan los datos.

**#17 — `seed_sample_data.sh` mezcla zips LEAN con factores neutros Stooq (MEDIO, L1).** Baja `daily/{aapl,ibm}.zip` del repo LEAN pero sobrescribe sus factor files como neutros, comentados como Stooq split-only. Puede no reproducir T6.1 (incoherencia fuente/factor). Ligado a 5B abierto (#15).

**#18 — `SMAPositionRule(tfs=[])` pasa todo (MEDIO, L4).** El constructor no exige `tfs` no vacío; `evaluate` con `tfs=[]` no itera y devuelve `passed=True` con evidencia vacía. Una rule mal compuesta deja pasar todos los símbolos. Alcanzabilidad baja (las rules se construyen en código `strategies/`, no en config) pero el guard es trivial. Apunta a `if not tfs: raise ValueError` + test de construcción.

**#19 — `resolve_bucket_thresholds` frágil ante config malformada (MEDIO, L3).** Valida el orden `0<near<mild<extended` pero asume mapping con valores numéricos; `"near":"0.005"` (string) o un `bucket_thresholds` truthy no-dict caen en `TypeError`/`AttributeError`, no en un `ValueError` de config claro. La config vive en ObjectStore (editable). Apunta a validar mapping, castear a `float` y rechazar bool/NaN/inf, con tests.

**#20 — Series de rules no validadas contra el plan de warmup (MEDIO, L5/L4).** `composition.series(side)` se construye independiente de `plan_warmup`. Si el presupuesto excluye por error una serie que una rule referencia, `SymbolData` no crea esa SMA y el gate (`sd.is_ready(tf,p)` → `sma()`) lanza `KeyError` no capturado → crashea el scan, en vez de fallar en `initialize()` con un `ValueError` claro o excluir de forma controlada. Latente (hoy el budget incluye todo). Apunta a validar en `initialize()` que las series referenciadas ⊆ `plan.included` antes de registrar schedules.

**#21 — `OutputSink` no garantiza el archivo (MEDIO, L4).** `emit` ejecuta `_emit_file` solo si `channels` contiene `"file"`; el "SIEMPRE archivo" de D8.3 solo se cumple por el default cuando el env está ausente, no ante un `channels` explícito sin `"file"` (`[]`, `["qc_notify"]`, `["host_email"]`) → se pierde JSON/CSV/latest y `host_email` puede loguear "listo" sin `latest.json`. Enmascarado por la config actual (siempre trae `"file"`). Apunta a persistir el archivo incondicionalmente (fuera de la lista de canales) o fail-fast si falta.

**#22 — Retornos de `save`/`email` ignorados (BAJO, L4).** `object_store.save` y `notify.email` retornan `bool` pero el código loguea éxito siempre; un fallo de escritura/envío queda invisible. *Verificar vs LEAN que `False` signifique fallo.* Apunta a comprobar los tres `save` y el `email`.

**#23 — Sin entorno `qc_notify` en config (BAJO, L1).** `notifications.json` solo define `dev`/`prod` con `file`/`host_email`; el handler `qc_notify` existe y está testeado pero ningún entorno lo activa, así que cloud `env=prod` no dispararía `NotificationManager` (SPECS #6). Diferible a E9: añadir un env `cloud` con `["file","qc_notify"]` o documentar el cambio previo al live.

**#24 — Sin test del wiring de notificación L5 (BAJO, tests).** No hay test que proteja `notification_groups` → un schedule por base → `_scan_group` → exactamente un `emit` por base (incluye invariantes schedule/partial_bar de D8.7 y secciones vacías). La evidencia es backtest/log. Apunta a inyectar/mockear el agrupador.

**#25 — Sin test del wiring de universo L5 (BAJO, tests).** Los tests ejercitan `ScanPipeline` con mapas ya filtrados, nunca el camino `UniverseSpec→main.py→pipeline.scan`; por eso la suite no detecta #12. Apunta a un test L5 con ObjectStore mock y universos long/short disjuntos verificando que cada pipeline reciba solo su mapa.

**#5 / #10 — documentar decisión:** #5 (anchor daily seguro pero sin justificar por escrito) y #10 (alias map acotado a 5 columnas en `etapa-04.md:77` vs §5 de PLAN con 11). Ambas son razonables pero la discrepancia con la fuente de máxima precedencia merece una nota de reconciliación.

---

## 3. Resumen de conteos

**Por clasificación (26 consolidados):**

| Clasificación | N | # |
|---|---|---|
| YA CORREGIDO | 2 | #1, #3 |
| DECISIÓN CONSCIENTE (no tocar) | 2 | #4, #26 |
| documentar decisión | 2 | #5, #10 |
| FALSO POSITIVO | 0 | — |
| **VIGENTE** | **20** | #2, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25 |

**Por severidad (solo VIGENTE = 20):**

| Severidad | N | # |
|---|---|---|
| CRÍTICO | 0 | — |
| ALTO | 5 | #2, #7, #12, #15, #16 |
| MEDIO | 5 | #8, #11, #17, #20, #21 |
| BAJO | 10 | #6, #9, #13, #14, #18, #19, #22, #23, #24, #25 |

**Reglas duras (prioridad máxima del proyecto):**
- **Cero órdenes: OK** — el único hallazgo (#1) era un artefacto gitignoreado; el fuente actual no coloca órdenes (verificado en E1/E2/E3/E4/E5/E6/E7/E8: ningún informe halló órdenes activas).
- **Portabilidad local↔cloud:** sin violación. El switch de canal vive en `output.py` (D8.4, grep sin `if env ==` fuera). #5 (anchor) y #21 (file siempre) tocan robustez, no portabilidad.
- **Capas L1–L6:** sin violación de import/dependencia (L3/L4 puras, sin `AlgorithmImports`). #12 es un fallo de **alcance de datos** en L5 (no de capa) que contradice la entidad `UniverseSpec` de SPECS → prioridad alta y vía decisión de diseño.

**Prioridad sugerida de atención (VIGENTE):**
1. **#12** (cruce de universos) y **#7** (siembra de universo viejo) — corrompen el universo efectivo del scan; #12 ya impacta archivos/correo (E8).
2. **#21** (archivo no garantizado) y **#20** (KeyError por serie excluida) — robustez de la persistencia y del scan.
3. **#16/#15** (integridad de la validación E5), **#2** (seguridad doc).
4. **#11** (tope 200), **#18/#19** (guards de config), y el resto.

> Cluster de **test gaps** (#14, #24, #25 + #6): varios hallazgos VIGENTE son la ausencia del test que habría atrapado un hallazgo de código (#25↔#12, #24↔#6/D8.7, #14↔#11). Cerrarlos en bloque protege contra regresión de los arreglos.

---

## 4. Pendiente

**Triaje completo de E1–E8.** Ya no quedan informes Codex por mergear: los 8 existen y están consolidados aquí (E6 incorporada pese a que su `-informe.md` llegó después del primer triaje). Próximo paso fuera de este triaje: escribir el spec de Etapa 9B a partir de los VIGENTE priorizados (no incluido aquí por instrucción).
