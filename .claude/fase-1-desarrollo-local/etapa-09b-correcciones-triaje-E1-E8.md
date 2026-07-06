# Etapa 9B — Reporte de correcciones del triaje Codex E1–E8

**Fecha:** 2026-07-05 · **Rama:** `feature/etapa-6-features-rules`
**Entrada:** `revisiones/20260619-205134/triaje-E1-E8.md` (26 hallazgos, 20 VIGENTE)
**Prompt ejecutado:** `revisiones/20260619-205134/prompt-fable-correcciones.md`

**Evidencia global:** suite completa verde en Docker tras cada grupo (A: 253 → B: 270 → C: 284 passed) + smoke backtest dev (`2026-07-05_14-09-56`) sin errores: schedules registrados por base, un `emit` por scan, archivos escritos en `storage/results/<base>/`.

| Commit | Grupo | Hallazgos |
|---|---|---|
| `b5294bb` | A — ALTO | #7, #21, #20, #2 |
| `9acf292` | B — MEDIO | #11, #18, #19, #17, #8, #9 |
| `53be8bd` | C — BAJO | #6, #24, #22, #23, #13, #14, #25 (parcial), #15/#16, notas #5/#10 |

> **Nota de higiene de commits:** el working tree traía trabajo de la **Etapa 9A sin commitear** (main.py fechas por entorno, universe.py aliases por periodo, converters, lean.json). En los archivos compartidos se stagearon SOLO los hunks 9B (`git apply --cached` con patch construido sobre HEAD); los cambios 9A siguen intactos como modificaciones sin stagear para su propio commit `[Etapa 9A]`.

---

## Grupo A — ALTO (corrompían el universo o la persistencia)

### #7 — `scripts/seed_object_store.sh`: selección del CSV "más reciente" rota

- **Qué corregía mal:** `find | sort | tail -1` ordenaba los nombres `*-{MM-DD-YYYY}.csv` **lexicográficamente**: `sp500-advances-12-31-2025.csv` > `sp500-advances-01-02-2026.csv`, así que al cruzar mes/año se sembraba el universo **más viejo** en `storage/universes/` — corrupción silenciosa del universo efectivo de TODOS los scans siguientes.
- **Corrección:** se parsea la fecha del nombre con regex bash y se antepone la clave `YYYYMMDD` antes del `sort` (`12-31-2025` → `20251231`); nombres sin fecha parseable reciben clave `00000000` (pierden contra cualquier fecha real).
- **Afecta:** solo la selección del archivo fuente; el flujo (cp → `storage/universes/<key>.csv` → mv a `processed/`) no cambia. Se añadieron overrides por env var (`TRADE_SCANNER_CONFIG_SRC`, `TRADE_SCANNER_UNIVERSES_SRC`, `TRADE_SCANNER_OBJECT_STORE_SRC`, `TRADE_SCANNER_STORAGE`) SOLO para poder testear el script con dirs temporales — sin variables seteadas el comportamiento es idéntico. `run_tests.sh` ahora exporta `TRADE_SCANNER_SCRIPTS=/Scripts`.
- **Verificación:** `tests/test_seed_object_store.py` ejecuta el script real vía subprocess: caso cruce de año (`12-31-2025` vs `01-02-2026` → gana 2026) y caso mismo mes.

### #21 — `core/output.py`: el archivo no estaba garantizado

- **Qué corregía mal:** `emit` solo ejecutaba `_emit_file` si `"file"` estaba en la lista de canales del entorno. Un `channels: []`, `["qc_notify"]` o `["host_email"]` explícito perdía JSON/CSV/`latest.json` — y `host_email` podía loguear "listo para script host" sin que existiera el `latest.json` que ese script consume. Contradecía D8.3 ("SIEMPRE archivo"). Enmascarado porque la config actual siempre trae `"file"`.
- **Corrección:** `_emit_file` se ejecuta **incondicionalmente** al inicio de `emit`, fuera de la tabla de canales; `"file"` en `channels` ahora es redundante y se ignora (no duplica escritura).
- **Afecta:** con la config actual, cero cambio observable (mismos 3 archivos por scan). Cambia el comportamiento ante config incompleta/errónea: la auditoría ya no depende de la config.
- **Verificación:** tests `test_emit_persists_file_even_without_file_channel` y `test_emit_persists_file_with_empty_channels`.

### #20 — series de rules no validadas contra el plan de warmup

- **Qué corregía mal:** `composition.series(side)` se construía independiente de `plan_warmup`. Si el `warmup_budget` excluía una serie que una rule referencia, `SymbolData` no creaba esa SMA y el gate del pipeline (`sd.is_ready(tf,p)` → `sma()`) lanzaba `KeyError` **no capturado** en pleno `ScheduledEvent` → crash del scan en runtime, sin pista de config. Latente: hoy el budget incluye todas las series referenciadas.
- **Corrección:** nueva función pura `validate_series_against_plan(strategy, series, available)` en `core/pipeline.py`; `main.initialize()` la llama por estrategia con `available = plan.included` antes de construir cada `ScanPipeline`. Config inconsistente → `ValueError` con la lista de series faltantes y la sugerencia ("sube warmup_budget o quita esas series").
- **Afecta:** el fallo se mueve de runtime (crash opaco) a `initialize()` (error explícito). Con la config actual no dispara (verificado: dev y prod cubren todas las series referenciadas).
- **Verificación:** tests en `test_pipeline.py` (falta `M:200` → ValueError con nombre de estrategia; subconjunto válido → pasa).

### #2 — README desactualizado (incluía riesgo de seguridad)

- **Qué corregía mal:** el README guiaba a `lean init`/`lean login` (requieren QC pago — contradice ADR-002 y el gotcha de Etapa 1), a **poner claves de Alpaca en `lean.json`** (archivo commiteado → ruta directa a fuga de secretos), describía el proyecto como `Screener`, la config de estrategias/notificación en `config.json` y un CSV de universo con esquema viejo (`ticker,price,avg_dollar_volume`, sin `direction`).
- **Corrección:** reescritura completa de Setup / Configuración / Universo / Salida / Estructura al contrato real E2–E8: workspace clonado con `lean.json` versionado y org-id placeholder; credenciales SOLO en `.env`; `config/strategies.json` + `config/notifications.json` vía ObjectStore; universos Barchart `*-advances/declines-MM-DD-YYYY.csv` con auto-detección de vista 1D/5D/1M/3M; salida `storage/results/<base>/{ts}.json|csv + latest.json` con secciones long/short; estrategias V1 con sus variantes short.
- **Afecta:** solo documentación; ningún cambio de código. Elimina el vector de fuga de credenciales por seguir instrucciones.

---

## Grupo B — MEDIO (robustez y guards)

### #11 — `core/universe.py`: tope duro 200 no garantizado

- **Qué corregía mal:** `UniverseSpec` truncaba a `max_tickers` (= `env_cfg["max_universe"]`) sin tope absoluto: un `max_universe: 500` en config violaba la regla dura "≤200 post-filtro" (CLAUDE.md/PLAN §5). La regla de producto dependía de que la config no se equivocara.
- **Corrección:** constante `_HARD_CAP = 200` y clamp en `__init__`: `self.max_tickers = min(max_tickers, 200)` con WARNING si la config pedía más.
- **Afecta:** config con `max_universe ≤ 200` (la actual): sin cambio. Config errónea: se degrada a 200 con aviso en vez de violar la regla.
- **Verificación:** `test_absolute_cap_200_overrides_config` (250 filas, `max_tickers=500` → salen 200).

### #18 — `core/rules.py`: `SMAPositionRule(tfs=[])` pasaba todo

- **Qué corregía mal:** el constructor no exigía `tfs` no vacío; `evaluate([])` no iteraba → `passed=True` con evidencia `{}`. Una rule mal compuesta dejaba pasar TODOS los símbolos en silencio. Alcanzabilidad baja (las rules se componen en `strategies/`, no en config), pero el guard es trivial.
- **Corrección:** `if not tfs: raise ValueError` en construcción (fail-fast, mismo patrón que la validación de `buckets_allowed` y `side`).
- **Afecta:** ninguna rule existente (todas declaran tfs); solo errores de composición futuros.
- **Verificación:** `test_empty_tfs_raises_at_construction`.

### #19 — `core/features.py`: `resolve_bucket_thresholds` frágil ante config malformada

- **Qué corregía mal:** asumía mapping con valores numéricos. `"near": "0.005"` (string) rompía la comparación con `TypeError`; un `bucket_thresholds` truthy no-dict (lista, string) caía en `AttributeError`. La config vive en ObjectStore y se edita a mano: el error debía ser de config, no de tipo.
- **Corrección:** `_validated_mapping` (no-dict → ValueError con scope global/estrategia) y `_threshold_as_float` (castea a `float`; rechaza `bool` explícito — en Python `True` colaría como `1.0` —, NaN e inf; no-numérico → ValueError con la clave y el valor).
- **Afecta:** config bien formada: idéntico (mismo merge override > global > defaults, misma validación de orden `0<near<mild<extended`). Strings numéricos ahora se **toleran** casteando (antes rompían). Config rota: `ValueError` claro en `initialize()`.
- **Verificación:** 3 tests nuevos parametrizados en `test_features.py` (cast de strings; bool/NaN/inf/no-numérico; bloque no-mapping global y de estrategia).

### #17 — `scripts/seed_sample_data.sh`: incoherencia fuente↔factor AAPL/IBM

- **Qué corregía mal:** el script bajaba `daily/{aapl,ibm}.zip` del **repo LEAN** (precios raw) y luego escribía factor files **neutros** comentados como origen Stooq. En un checkout limpio la combinación quedaba incoherente: precios raw + factor=1 = splits sin ajustar → SMAs mal → no reproduce T6.1. (Con los zips ya generados por el converter, el `fetch` idempotente los saltaba y quedaba bien "de casualidad".)
- **Corrección:** AAPL/IBM ya **no se bajan** del repo LEAN. Si `daily/<sym>.zip` no existe, el script avisa que debe generarse con el converter Stooq (`scripts/stooq_to_lean.py`) y NO escribe el factor neutro; si existe (Stooq), escribe el factor neutro como antes. FB queda como par coherente LEAN (zip + factores reales LEAN).
- **Afecta:** un checkout limpio ya no produce datos silenciosamente incoherentes para AAPL/IBM: el backtest dev correrá sin esos símbolos (con aviso) hasta correr el converter. Es un trade-off deliberado: datos ausentes con aviso > datos incorrectos sin aviso.
- **Verificación:** script de shell sin test automatizado (no corre en la imagen); verificado por inspección y porque los datos locales ya existen (el preflight de #15/#16 cubre la presencia).

### #8 / #9 — `scripts/explore_universe.py`: footer y porcentajes

- **Qué corregía mal (#8):** el "footer" se definía como "toda fila cuyo Symbol no matchee `^[A-Z]{1,5}$`". Consecuencia doble: los tickers reales no estándar (`BRK.B`) se ocultaban como footer, y `non_standard` (sección 4) se calculaba sobre `data_rows` ya filtrado → **siempre vacío**. El reporte exploratorio de E3 mentía por diseño.
- **Corrección (#8):** el footer se detecta por el patrón real de Barchart (`Downloaded from Barchart…`, función `classify_rows` extraída y testeable); todo lo demás es dato, y la sección 4 reporta los que no matchean el regex.
- **Qué corregía mal (#9):** las columnas `PERCENT` no tenían el guard `if valid:` de las numéricas → una columna porcentual vacía/sucia abortaba el script con `min([])` en vez de diagnosticar.
- **Corrección (#9):** mismo patrón `if valid: … else: "sin valores válidos"`.
- **Afecta:** solo el script de perfilado (dev, host); el parser de producción (`core/universe.py`) no cambia aquí.
- **Verificación:** `tests/test_explore_universe.py` (BRK.B reportado como no estándar y no como footer; CSV con `%Change` vacío no crashea).

---

## Grupo C — BAJO (tests, doc, config)

### #6 — mapeo schedule→time-rule sin test

- **Qué afecta:** `_time_rule_for` traducía los strings de config a time-rules sin regresión: un typo en `"after_close"` o un cambio del `+1 min` (D5) rompía el schedule **en silencio** (grupo omitido con log).
- **Cambio:** el mapeo se extrajo a `core/scheduling.py::time_rule_for(schedule, time_rules, anchor)` (puro, duck-typed, cero AlgorithmImports); `main._time_rule_for` es ahora un delegado de una línea. Comportamiento idéntico.
- **Verificación:** `tests/test_scheduling.py` con recorder: `after_close → after_market_close(SPY, 1)`, `before_close_30m → before_market_close(SPY, 30)`, desconocido → `None` sin llamadas.

### #24 — wiring de notificación L5 sin test

- **Qué afecta:** el invariante central de Etapa 8 (`notification_groups` → un schedule por base → `_scan_group` → **exactamente un** `emit` con secciones por dirección) solo tenía evidencia de backtest/log, no test de regresión.
- **Cambio:** el cuerpo de `_scan_group` se extrajo a `core/pipeline.py::run_group_scan(...)` (recibe pipelines, mapa, `emit` y `log` inyectados); en `main._scan_group` quedan SOLO los guards que necesitan el algoritmo (warmup y probe A.3). Comportamiento idéntico (verificado además con el smoke backtest: mismas líneas de log `scan @`/`emit @`).
- **Verificación:** 3 tests en `test_output.py`: un solo emit con ambas secciones (lado activo sin candidatos = sección vacía, D8.6), `partial_bar` propagado, miembro inactivo omitido sin sembrar sección.

### #22 — retornos de `save`/`email` ignorados

- **Qué corregía mal:** `object_store.save` y `notify.email` retornan `bool` (semántica LEAN: `False` = escritura/encolado fallido) pero el código logueaba éxito siempre — un fallo de persistencia o de correo quedaba invisible.
- **Corrección:** helper `OutputSink._save` (los 3 archivos) y chequeo en `_emit_qc_notify`: `is False` → línea `ERROR` en el log (y en el caso del correo, no se loguea el "enviado"). El chequeo es `is False` **estricto**: mocks/stores duck-typed que retornan `None` no cuentan como fallo.
- **Afecta:** camino feliz idéntico; camino de fallo ahora deja traza.
- **Verificación:** tests con store/notify que retornan `False` (3 ERROR por emit de archivos; ERROR "no encolado" sin línea de éxito) y con `None` (sin ERROR).

### #23 — sin entorno con `qc_notify`

- **Qué afectaba:** el handler `qc_notify` existía y estaba testeado, pero ningún entorno lo activaba → en QC cloud con `env=prod` jamás dispararía `NotificationManager` (criterio nº6 de SPECS).
- **Cambio:** `config/notifications.json` añade `"cloud": { "channels": ["file", "qc_notify"], "notify_empty": false }`. `dev`/`prod` intactos. Para usarlo en cloud habrá que setear `"env": "cloud"` en los parámetros del proyecto (decisión de deploy de E9).

### #13 — columnas requeridas hardcodeadas / errores de `df.query` sin contexto

- **Qué afectaba:** `_REQUIRED_COLUMNS` no se deriva de `filter_expr`; un filtro sobre una columna sin alias mapeado pasaba las verificaciones y recién reventaba en `df.query` con el error crudo de pandas (sin decir qué universo ni qué filtro).
- **Cambio:** `df.query` se envuelve: cualquier excepción → `ValueError` con la key del universo, el `filter_expr` y las columnas disponibles; nota en el código explicando la limitación (derivar columnas del filtro queda como mejora futura si E9 añade filtros).
- **Verificación:** `test_filter_on_unknown_column_raises_valueerror_with_context`.

### #14 — cobertura de invariantes de E4

- **Cambio (solo tests):** `test_universe.py` gana un bloque autocontenido: tope ABSOLUTO 200 sobre config excesiva (blinda #11) y alias map completo usado por un filtro que combina volumen + `price` + `pct_chg_1d` (blinda #10). El bloque deriva el alias de volumen de `_REQUIRED_COLUMNS` para no acoplarse al rename de 9A (`avg_vol_5d` → `avg_vol`).

### #25 — test de universos disjuntos (**parcial**)

- **Cambio (solo tests):** `test_disjoint_long_short_maps_produce_disjoint_results` fija el contrato a nivel pipeline: cada `ScanPipeline` produce resultados SOLO del mapa que recibe. Es el guard de regresión que protegerá el fix de #12.
- **Por qué parcial:** el test L5 completo (`UniverseSpec → main.py → pipeline.scan` con mapa filtrado POR estrategia) **fallaría hoy** — precisamente porque #12 sigue vigente. Llega junto con la implementación aprobada de #12.

### #15 / #16 — la suite quedaba verde sin los datos de E5

- **Qué afectaba:** `test_sma_regression.py` y `test_t5_stooq_crosscheck.py` usan `skipif` sobre rutas bajo `data/` (gitignoreado): en un checkout limpio la suite pasaba **sin ejercer** la matemática SMA/fidelidad Stooq (el criterio central de E5).
- **Cambio:** `tests/test_e5_data_preflight.py` **falla** (no salta) si falta alguno de los 3 artefactos (`equity/usa/daily/spy.zip`, `stooq_lean/daily/spy.zip`, `stooq/spy_us_d.csv`), con la instrucción de regeneración de cada uno. Se eligió preflight sobre fixtures versionados (la alternativa del prompt) porque el fixture útil requiere ~4221 barras (M:200) y el autoritativo es justamente el F3 pendiente de 5B.
- **Ojo:** esto NO cierra 5B — F2/F3 (validación manual ≤0,25% + fixture autoritativo TradingView/IBKR) siguen abiertas en PLAN. El preflight solo elimina el verde falso.

### #5 / #10 — decisiones documentadas (sin cambio de comportamiento)

- **#5 (main.py):** nota junto al ancla SPY: el fallback `Resolution.DAILY` es seguro porque el reloj avanza por las suscripciones del universo y `before/after_market_close` usa las market-hours de SPY (independientes de la resolución del feed). Queda anotado el caso límite pendiente de verificar (entorno con universo 100 % daily).
- **#10 (universe.py):** nota sobre `COLUMN_ALIASES`: el alias map se acota a propósito a las columnas usadas (etapa-04) frente a las 11 columnas de PLAN §5; si E9+ filtra por columnas nuevas, ampliar map y `_REQUIRED_COLUMNS` a la vez.

### No tocados (por instrucción del prompt)

- **#1, #3:** ya corregidos en el código actual (artefactos de E1).
- **#4, #26:** decisiones conscientes (store regenerable; backtest ≥3 meses diferido a E9).

---

## #12 — Cruce de universos: comportamiento actual vs. propuesta

**Estado:** NO implementado en este ciclo (por instrucción). Propuesta completa en
`revisiones/20260619-205134/propuesta-diseno-12.md`. Aquí, el desglose con ejemplos.

### Comportamiento actual (el bug)

En `initialize()` el universo se materializa como **unión global**:

```python
tickers: set[str] = set()
for name, cfg in strategies_config.items():
    spec = UniverseSpec(...)          # universo DE ESA estrategia
    tickers.update(spec.load(...))    # ... pero se funde todo en un solo set
```

y en el scan, `run_group_scan` pasa `self.symbol_data` (el mapa **completo**) a cada pipeline.
La pertenencia ticker→estrategia se pierde en cuanto termina el loop de carga.

**Ejemplo con datos concretos (prod).** Supongamos los CSVs del día:

- `swing_advances.csv` (gainers, para las long): `NVDA` (+4.2 %), `AAPL` (+2.1 %)
- `swing_declines.csv` (decliners, para las short): `XYZ` (−3.0 %), `QQQW` (−5.5 %)

Unión global = `{NVDA, AAPL, XYZ, QQQW}` — los 4 reciben `SymbolData` y warmup (esto es correcto
y se conserva). Pero al disparar el grupo `swing_eod`:

1. **`swing_eod` (long) escanea también XYZ y QQQW.** Ranking `day_change_pct desc` sobre los
   4; con `top_n=50` todos entran al embudo de rules.
2. **Un decliner puede salir en la watchlist LONG.** `XYZ` cayó −3 % hoy (por eso está en el
   CSV de declines), pero viene de un uptrend fuerte: su precio sigue **por encima** de
   SMA20 D/W/M y no está extendido vs SMA8. Pasa `AboveSMA(20,D+W+M)` y `NotExtended(8,D)` →
   aparece como candidato `long` de `swing_eod`... siendo un símbolo que el trader exportó
   como *decliner*. Simétricamente, un gainer en downtrend puede colarse en la watchlist SHORT.
3. **El `top_n` se comparte entre universos.** Con `top_n` chico (dev: 2), un símbolo del
   universo ajeno puede **desplazar** del ranking a uno del universo propio (p. ej. un decliner
   con rebote intradía de +3 % le quita el slot a AAPL +2.1 % en el ranking long).
4. **E8 lo propaga.** El envelope/CSV/correo de la base `swing_eod` lista a `XYZ` en la sección
   LONG: `storage/results/swing_eod/latest.json` y el correo a suscriptores mienten sobre el
   origen del candidato.
5. **Ruido de gate:** si `QQQW` tiene series frías, el log de `swing_eod` (long) reporta
   "excluido QQQW: warmup incompleto" aunque QQQW jamás debió estar en ese scan.

**Por qué no se ve en dev:** el override `environments.dev.universe = "sample_dev"` fuerza el
MISMO universo para todas las estrategias → la unión coincide con cada universo individual y el
bug es invisible en todos los backtests dev. Por eso 4 informes de Codex (E4/E5/E7/E8) lo
detectaron leyendo código y ningún backtest lo mostró.

**Qué lo mitiga hoy (pero no lo garantiza):** las rules direccionales (un decliner suele estar
bajo sus SMAs → no pasa las rules "above") y la dirección del ranking. El ejemplo del punto 2
muestra que la mitigación es estadística, no estructural.

### Comportamiento con la propuesta

**Invariante nuevo (candidato a ADR-006):** *cada pipeline escanea exactamente el mapa
`{Symbol: SymbolData}` de SU universo declarado; la unión global existe solo para
suscripción/warmup.*

Cambios (≈20 líneas + tests):

1. `initialize()` conserva la pertenencia al cargar cada universo y materializa **una vez**
   (los universos son estáticos en V1; `refresh_universe` es no-op):

   ```python
   self.symbol_data_by_strategy = {
       name: {s: sd for s, sd in self.symbol_data.items() if s.value in tickers}
       for name, tickers in tickers_by_strategy.items()
   }
   ```

2. `run_group_scan` cambia `symbol_data_map: dict` → `symbol_data_by_member: dict[str, dict]`
   y adentro hace `pipeline.scan(symbol_data_by_member.get(name, {}), ...)`. El emit único por
   base no se toca.

**El mismo ejemplo, con la propuesta:**

| | Hoy | Con propuesta |
|---|---|---|
| `swing_eod` (long) escanea | `{NVDA, AAPL, XYZ, QQQW}` | `{NVDA, AAPL}` |
| `swing_eod_short` escanea | `{NVDA, AAPL, XYZ, QQQW}` | `{XYZ, QQQW}` |
| ¿XYZ (decliner en uptrend) puede salir LONG? | **Sí** (pasa las rules above) | **No** (no está en su mapa) |
| ¿Un decliner con rebote consume slot del `top_n` long? | Sí | No |
| Warmup/SymbolData de los 4 símbolos | unión global | unión global (sin cambio, invariante L2 intacto) |
| Log de exclusión por frío | símbolos ajenos aparecen | solo símbolos del universo propio |
| dev (override `sample_dev`) | todos escanean sample_dev | idéntico (mapas iguales entre sí) |

**Casos borde previstos:**
- *Ticker en ambos universos* (posible si un símbolo aparece en advances Y declines): comparte
  `SymbolData` (un solo warmup) y ambas estrategias lo evalúan, cada una por estar en SU mapa.
  Correcto y sin conflicto con ADR-005 (que solo prohíbe compartir snapshots).
- *Universo vacío post-filtro:* la estrategia escanea `{}` → 0 candidatos → sección vacía en el
  envelope (comportamiento ya existente para "sin candidatos").

**Qué NO cambia:** suscripciones (`add_equity`), plan de warmup global (R4: un solo plan — se
propone NO optimizar requirements por símbolo en este ciclo), `OutputSink`, el contrato del
envelope, las rules.

**Tests que cerrarían #25 completo junto con el fix:** `run_group_scan` con mapas por miembro
disjuntos + `FakePipeline` que registra `scanned_with` (cada pipeline recibe SU mapa); test
L5-style `UniverseSpec` + `MockObjectStore` con CSVs advances/declines disjuntos verificando la
partición de los mapas.

**Decisiones abiertas antes de implementar (para Guillermo):**
1. ¿ADR-006 nuevo o ampliación de ADR-005?
2. ¿Optimizar warmup por símbolo (series = unión solo de las estrategias que lo contienen)?
   Propuesta: no en este ciclo (rompe R4 por ahorro marginal).
3. ¿Miembro con universo vacío = sección vacía sin error? Propuesta: sí.

---

## Pendientes que deja este ciclo

1. **#12:** aprobar/ajustar la propuesta y decidir ADR → implementar + completar #25.
2. **5B (F2/F3):** validación manual ≤0,25 % y fixture autoritativo — el preflight de #15/#16
   solo evita el verde falso, no cierra la etapa.
3. **#5:** verificar vs LEAN el caso límite de un entorno con universo 100 % daily.
4. **Etapa 9A:** el trabajo del working tree sigue sin commitear (intacto tras este ciclo);
   commitearlo con su propio `[Etapa 9A]` cuando se cierre esa etapa.
5. **`env=cloud` (#23):** activar `"env": "cloud"` en los parámetros del proyecto al hacer el
   deploy cloud de E9.
