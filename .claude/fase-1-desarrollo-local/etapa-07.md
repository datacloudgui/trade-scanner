# Etapa 7 — ScanPipeline + estrategias declarativas + schedule

**Estado:** en progreso
**Depende de:**
- **Etapa 6B** (cerrada): `build_position_snapshot`, `snapshot_evidence`, `mirror_buckets`/`_MIRROR`/`SIDE_BY_DIRECTION`, `SMAPositionRule.evaluate(snapshot)`, `NotExtended` (sin `max_pct`), `RuleResult`, `ScanResult` mínimo (`rules_passed_count` + `sma_evidence`), `format_filter_line`/`format_final_line` en `core/pipeline.py`.
- **Etapa 5B** (en progreso, F1/F2 cerradas): `main.py` con warmup integrado (`set_warm_up(depth, DAILY)` engine-managed), `SymbolData` caliente por símbolo con consolidator cableado a la suscripción, `plan_warmup` global.
**Autoridad de diseño:** [ADR-005](../decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md) (§9.1 dónde vive la composición, §9.2 inclusión de `near`, §9.4 snapshot per-estrategia) · [ADR-004](../decisions/ADR-004-cadencia-evaluacion-intradia.md) (cadencia; market_close V1 vs day-trading Fase 2). **Modelo de precio (A) y granularidad de exclusión (B) ratificados en conversación 2026-06-18** (§"Decisiones de diseño" D7.4/D7.7).
**Estimado:** 7–10 h (refactor de precio en E6 + L4 pipeline + composición declarativa + integración L5 + backtest de validación).

**Contexto.** Las Etapas 6/6B entregaron la capa de negocio puro aislada: el snapshot único de posición precio↔SMA y las rules como filtros sobre buckets ya asignados, simétricas long/short. Falta **ensamblar**: una estrategia = universo + rules + schedule, todas en un solo nodo, produciendo `ScanResult`s. Al diseñar ese ensamblaje afloraron dos decisiones de semántica que **se cierran aquí antes de tocar código** (no son detalles de implementación):

- **(A) Modelo de precio.** El snapshot debe comparar **un único precio "ahora"** contra la SMA de cada timeframe (lo que pide SPECS §6: "precio sobre SMA20 en D, W y M"), no el cierre por-timeframe que codificó E6. Y ese precio sale **siempre del working bar** (el día en curso para `market_close`, el día recién cerrado para `swing_eod`), porque con suscripción minute la barra diaria de hoy **no se consolida** a la hora del scan: "hoy" solo existe en el working bar; las SMAs quedan sobre periodos **cerrados**. `partial_bar` pasa a ser metadato (mercado abierto vs cerrado), no un cambio de fuente de precio.
- **(B) Exclusión por series referenciadas.** Un símbolo se excluye si una serie que **una rule referencia** está fría — no por `is_ready()` global, que sobre-excluiría acciones jóvenes con SMAs declaradas-pero-no-usadas (p. ej. `W:200` para un warmup futuro) frías.

La **salida a archivo/notificación queda para Etapa 8**: aquí el `ScanResult` vive en memoria + log.

---

## Decisiones de diseño

> Numeradas D7.x. Las que tocan semántica de precio/buckets/simetría o cruce de capas son las de mayor cuidado; config/log son mecánicas. D7.4 (precio) y D7.7 (exclusión) son las ratificadas el 2026-06-18.

### D7.1 — Todo se resuelve en `initialize()`; el scan es lectura pura

El `ScanPipeline` recibe **ya resuelto** en `initialize()` (una vez por sesión, no por scan): los `bucket_thresholds` (`resolve_bucket_thresholds`), la unión deduplicada de `series` `(tf, period)` que sus rules referencian (D6B.2 — `set`), la lista de rules **ya construidas** con su `side` espejado, el `top_n`, y el flag `partial_bar` de la estrategia. El callback del `ScheduledEvent` solo lee estado de `SymbolData` y arma el `ScanResult`: cero parsing de config, cero composición, cero resolución de `direction` en el hot path. Coherente con la regla de capas (L4 lee; no calcula).

### D7.2 — Composición declarativa en `strategies/`, no en `strategies.json` (ADR-005 §9.1)

Qué rules tiene cada estrategia (con qué `buckets_allowed` canónicos y `label`) vive en **módulos `StrategyConfig` en `strategies/`**, no en un bloque de `strategies.json`. Razón: la lista de rules es *código de composición* (referencia a clases/presets de `core/rules.py`), no datos de calibración; serializarla a JSON reintroduce un mini-DSL sin ganancia. De `strategies.json` se siguen leyendo los **datos**: `universe`, `direction`, `schedule`, `universe_filter`, `timeframes` (warmup), `bucket_thresholds`. `StrategyConfig` es puro: lleva `name`, el flag `partial_bar`, `build_rules(side)` y `series(side)`. La asociación nombre-de-config → `StrategyConfig` vive en un registro `STRATEGIES` (D7.9-C3); `universe`/`schedule`/`direction` los cruza `main.py`.

### D7.3 — `direction → side` en un solo punto (`SIDE_BY_DIRECTION`)

La traducción `long→"above"` / `short→"below"` se hace **una vez**, en `initialize()`, leyendo `cfg["direction"]` y aplicando `SIDE_BY_DIRECTION` (ya existe en `core/features.py`). El `side` se pasa a `build_rules(side)`; las rules se autoran en vocabulario canónico "above" y `mirror_buckets` (interno a `SMAPositionRule`) las proyecta. Ni las rules ni el pipeline vuelven a mirar `direction` (ADR-005 §9.1: resuelto en un solo punto, no esparcido).

### D7.4 — Modelo de precio: precio único = working bar (ambos scans), SMA sobre periodos cerrados *(A — ratificada 2026-06-18)*

Tres piezas que se cierran juntas porque son inseparables:

**(A.1) Precio único contra la SMA de cada tf — refactor de E6.**
La posición es `(precio − SMA(tf,period)) / SMA(tf,period)` con **un solo precio** comparado contra las tres SMAs, no `sd.close(tf)` por timeframe. E6 codificó el cierre por-tf ([features.py:109](../../trade-scanner/core/features.py#L109)): para W comparaba el cierre de *la última semana cerrada* y para M *el último mes cerrado* — tres precios distintos y, para W/M, rancios. SPECS §6 pide "precio sobre SMA20 en D, W y M": **un** precio actual contra las tres medias. Beneficio colateral: la evidencia queda internamente consistente (`SMA·(1+distance_pct)` da el mismo precio en los 3 tf). Implica cambiar la firma de `position_vs_sma` (recibe el precio; deja de leer `sd.close(tf)`) y migrar sus tests — es el único punto donde esta etapa **toca E6**.

**(A.2) El precio sale del working bar; "hoy" no entra en la SMA.**
Con suscripción minute, el consolidator diario es `timedelta(days=1)` con frontera a medianoche ([timeframes.py:11-16](../../trade-scanner/core/timeframes.py#L11-L16)): la barra diaria de hoy **no se emite** a las 15:30 ni a las 16:01 (la siguiente medianoche aún no llega); emite con la primera barra del día siguiente. Consecuencias a la hora del scan, **idénticas para ambas estrategias**:
- `sd.working_bar.close` = precio de hoy (parcial intradía para `market_close`; sesión completa, aún no emitida, para `swing_eod` tras el cierre).
- las SMAs solo se actualizan en `data_consolidated` (al emitir) ⇒ reflejan **hasta la última vela cerrada = ayer**; leer el working bar **no** las toca.

Por eso el precio de referencia es **siempre** el working bar, vía un helper único `reference_price(sd)` = `working_bar.close` o, si no hay working bar (día sin datos, premercado), el último cierre consolidado. La comparación queda, consistente intradía y al cierre: **precio de hoy (working bar) vs SMA sobre periodos cerrados**. `swing_eod` y `market_close` ya **no se diferencian por la fuente de precio** (ambos working bar) sino solo por `partial_bar` (metadato: `market_close`=True mercado abierto, `swing_eod`=False mercado cerrado — declarado por estrategia, determinista por su horario).

**(A.3) Robustez al timing de emisión + verificación en backtest.**
`reference_price` es robusto a *cómo* emita LEAN: si la diaria de hoy no se emitió, el precio sale del working bar; si se emitió, sale del cierre consolidado — en ambos casos es "hoy". Lo que **sí** depende del timing es: (i) `day_change_pct` (asume `sd.close("D")`=ayer, D7.6), y (ii) si la SMA de `swing_eod` incluye hoy. Comportamiento **esperado** (`timedelta(days=1)`): hoy no se emite hasta la sesión siguiente ⇒ la SMA de `swing_eod` excluye hoy (off-by-one frente a TradingView/IBKR, que sí incluyen la vela en curso; ~`(close[T]−close[T-20])/20`, aceptado — la validación histórica de 5B compara barras completadas y no se afecta). Si el backtest mostrara que LEAN emite al cierre de mercado, `swing_eod` incluiría hoy "gratis" (alineado al chart) y habría que activar la contingencia de `day_change_pct`. **T6 registra el comportamiento observado en la bitácora.**

**Reconciliación V1 vs Fase 2 (suscripción minute).** El working bar exige `Resolution.MINUTE` (hoy `main.py` suscribe `DAILY`, simplificación de 5B). Lo que entra en V1 y lo que queda para Fase 2:

| Pieza | Etapa 7 (V1) | Fase 2 |
|---|---|---|
| Suscripción `Resolution.MINUTE` (working bar del consolidator diario) | ✅ | — |
| Precio = working bar en scans programados (`reference_price`) | ✅ (ambas estrategias) | — |
| **Timeframes intradía** (SMAs de 1/5/15/2-min en `SymbolData`) | ❌ Fase 2 (el bloqueante real, L2) | ✅ |
| **Cadencia event-driven** por barra de 2-min (day trading) | ❌ Fase 2 (ADR-004) | ✅ |

### D7.5 — Snapshot per (símbolo, estrategia); no se comparte en V1 (ADR-005 §9.4)

Cada estrategia construye su snapshot por símbolo con **sus** `(thresholds, series)`. En V1 los universos long/short son disjuntos (`swing_advances` vs `swing_declines`); `swing_eod`/`market_close` comparten universo y rules pero difieren en `partial_bar`. No se comparte snapshot: compartir es optimización futura gateada en `(thresholds, series)` idénticos — fuera de alcance.

### D7.6 — Ranking por `day_change_pct` (feature L3 nueva); sin accesor nuevo en L2 *(simplificación de A.2)*

El `top_n` se toma por `day_change_pct` (gainers para long, decliners para short). `day_change_pct(sd) = (reference_price(sd) − sd.close("D")) / sd.close("D")`. **Clave (A.2):** como la barra de hoy no está consolidada al scan, `sd.close("D")` **ya es el cierre de ayer** — así que `day_change` compara hoy (working bar) vs ayer (cierre consolidado) **sin** necesitar el `RollingWindow`/`previous_close` que tenía el borrador. Esto **borra una adición a L2**: L2 queda intacto en esta etapa.
- **Dirección del ranking:** `desc` para long (mayores subidas), `asc` para short (mayores caídas; `*_declines` ya es el universo de caídas, se ordena por la caída de **hoy**). Tie-break por ticker alfabético ⇒ watchlists reproducibles (Done-when #1).
- **Contingencia (solo si T6 muestra emisión-al-cierre):** si `sd.close("D")` resultara ser *hoy* en `swing_eod`, `day_change` daría 0; ahí se añadiría un `previous_close()` (RollingWindow de 2) y se desambiguaría por presencia de working bar. No se implementa salvo que la verificación lo exija.

### D7.7 — Exclusión por series **referenciadas**, no `is_ready()` global *(B — ratificada 2026-06-18)*

El gate de exclusión es: **todas las `(tf,period)` que las rules de la estrategia referencian están listas** (`all(sd.is_ready(tf, period) for (tf,period) in series)`). **No** `is_ready()` global: este chequea **todas** las SMAs declaradas, incluidas `D:200`/`W:200` (declaradas para warmup/rules futuras pero que **ninguna rule de V1 usa**); una acción joven con esas frías quedaría excluida de más, violando D6B.2. El gate corre **antes del ranking** (así el `top_n` se llena con símbolos evaluables, sin que un símbolo frío-en-`W:20` con `day_change` alto robe un slot y luego caiga). Cada exclusión se loguea con causa precisa (`warmup incompleto: serie W:20 fría`). El `FeatureNotReady` del builder (D6B.3) queda como **backstop** defensivo (p. ej. `SMA==0` degenerada), no como gate primario. El embudo de filtrado se reporta con `format_filter_line`/`format_final_line` (6B/T6) — arranca en `top_n`, tras el gate y el ranking.

### D7.8 — `ScanResult` completo (extiende el contrato mínimo de 6B)

Se añaden al dataclass los campos de PLAN §5: `strategy`, `as_of`, `ticker`, `direction`, `partial_bar`, `price`, `time_frames_evaluated`, `passed_rules`. `price` = el `reference_price` único (no per-tf). `sma_evidence` = `snapshot_evidence` proyectado sobre la **unión de series** (no recompute, D6B.7). `rules_passed_count` = nº de rules `required` que pasaron. El pipeline lo llena; la serialización CSV/JSON es Etapa 8.

### D7.9 — Decisiones menores cerradas (C) *(resueltas para no bloquear el arranque)*

- **C1 — Dirección del ranking short:** `asc` por `day_change_pct` (mayores caídas). Cerrado en D7.6.
- **C2 — `working_bar` None al scan** (día sin datos / premercado / medio día sin trades): `reference_price` cae al último cierre consolidado y el símbolo **se sigue escaneando**; `partial_bar` conserva el valor de la estrategia (es metadato del horario, no de la disponibilidad de datos). Se loguea el fallback.
- **C3 — 4 estrategias / 2 módulos:** registro explícito en `strategies/__init__.py`: `STRATEGIES = {"swing_eod": swing_eod, "swing_eod_short": swing_eod, "market_close": market_close, "market_close_short": market_close}` (las variantes `*_short` apuntan a la **misma** `StrategyConfig`; el `side` se resuelve aparte vía `direction`). Sin stripping mágico de sufijos.
- **C4 — Datos/entorno del backtest (T6):** se valida en el **harness `dev`** (universo `sample_dev` = SPY/AAPL/IBM, ya con data sembrada de 5B), suficiente para demostrar mecánica, reproducibilidad, working bar y exclusión. El backtest a escala prod (≈74 tickers) es **Etapa 9** (requiere sembrar más data). Para ejercitar la exclusión se incluye/usa un símbolo de historia corta.
- **C5 — `as_of` en UTC:** `as_of = self.utc_time` (LEAN expone el reloj UTC), ISO-8601, conforme a §5. No usar `self.time` (TZ del activo) crudo.
- **C6 — `top_n`:** se mantiene a nivel `environment` (config actual: dev=2, prod=50); el pipeline lo recibe ya resuelto. Mover a bloque de estrategia es innecesario en V1.

---

## Tareas

> `(FABLE xhigh)` en subtareas con semántica de precio/buckets/simetría o cruce de capas. Resto `high`; config/log/commit `medium`. Cada tarea abre con **Por qué**.

### T1 — Precio único de referencia: refactor de `position_vs_sma` + `reference_price` (L3, `core/features.py`)

**Por qué.** Es el núcleo de la decisión A. Sin esto, el snapshot compara cierres por-timeframe (W/M rancios) y el working bar no tiene dónde entrar. Unificar el precio en `reference_price` hace que el snapshot, `day_change` y la evidencia hablen de un solo "precio ahora", y deja `position_vs_sma` puro respecto a la *fuente* del precio (la decide el builder, una vez). Es el único cambio a E6 de la etapa, por eso va primero y aislado.

- **T1.1 (FABLE xhigh)** — `reference_price(sd) -> float`: `float(sd.working_bar.close)` si hay working bar, si no `sd.close("D")` (C2). Helper único del "precio ahora" (A.2).
- **T1.2 (FABLE xhigh)** — Cambiar `position_vs_sma(sd, tf, period, thresholds, price)`: recibe el `price` y computa `distance_pct = (price − sma)/sma`; **deja de leer `sd.close(tf)`**. Conserva el contrato de fríos (`is_ready(tf,period)` y `sma==0` → `FeatureNotReady`) y `_bucketize`.
- **T1.3** — `build_position_snapshot(sd, series, thresholds)`: computa `price = reference_price(sd)` **una vez** y lo pasa a cada `position_vs_sma`. Firma externa intacta (sigue sin recibir precio); el precio único es interno. Mantiene D6B.1/D6B.2/D6B.3.
- **T1.4 — Migración de tests E6.** Reescribir los tests de `position_vs_sma`/`_bucketize`/snapshot para el nuevo contrato (precio inyectado / `reference_price`); cero tests muertos.

**Criterio de aceptación:**
- (a) `reference_price` devuelve `working_bar.close` cuando hay working bar y `close("D")` cuando no (ambos casos con stub sintético).
- (b) `position_vs_sma` ya **no** referencia `sd.close(tf)` (grep vacío dentro de la función); `distance_pct` usa el `price` inyectado; fríos y `sma==0` siguen levantando `FeatureNotReady`.
- (c) `build_position_snapshot` con un stub multi-`(tf,period)` y working bar fijo: los 3 tf usan **el mismo** precio; la evidencia es internamente consistente (`value·(1+distance_pct)` ≈ `price` en cada tf, tol. `1e-9`); `position_vs_sma` se invoca **una vez por serie**.
- (d) `core/features.py` sin imports de `AlgorithmImports` a nivel de módulo.
- `bash scripts/run_tests.sh` verde.

### T2 — `day_change_pct` (L3, `core/features.py`) para el ranking

**Por qué.** El `top_n` rankea por el movimiento de **hoy** (no por el `%Change` del CSV, que es del día de export y rompería reproducibilidad). A.2 lo hace barato: `sd.close("D")` ya es ayer, así que no hace falta tocar L2.

- **T2.1** — `day_change_pct(sd) -> float = (reference_price(sd) − sd.close("D")) / sd.close("D")`; si `sd.close("D")` no existe o es 0 → `FeatureNotReady`. Sin imports de `QCAlgorithm`. Documentar la dependencia de A.2 (`close("D")`=ayer al scan) y la contingencia D7.6.

**Criterio de aceptación:**
- (a) Para un stub con `close("D")=c0` y `working_bar.close=c1`, devuelve `(c1−c0)/c0`; sin working bar usa `close("D")` como precio (cambio 0 si no hay sesión nueva — caso degenerado documentado).
- (b) `FeatureNotReady` claro si falta el cierre consolidado o es 0.
- (c) `core/features.py` sin `AlgorithmImports`. `run_tests.sh` verde.

### T3 — Composición declarativa de estrategias (`strategies/`)

**Por qué.** Una estrategia V1 es composición, no lógica nueva (D7.2): declara *qué* rules canónicas usa y *si* su scan es intradía. Mantenerlo en `strategies/` (no en JSON) deja la simetría long/short resuelta por `side` en un solo punto (D7.3) y permite testear la composición sin engine.

- **T3.1 (FABLE xhigh)** — `strategies/base.py`: `StrategyConfig` (dataclass puro) con `name: str`, `partial_bar: bool`, `build_rules(side: str) -> list[SMAPositionRule]`, y `series(side) -> set[tuple[str,int]]` (unión deduplicada derivada de las rules). Las rules se autoran en vocabulario canónico "above"; `side` lo inyecta el pipeline.
- **T3.2 (FABLE xhigh)** — `strategies/swing_eod.py`: `StrategyConfig(name="swing_eod", partial_bar=False, rules=[SMAPositionRule(20,["W","M"],ABOVE,side,label="SMA"), SMAPositionRule(20,["D"],ABOVE,side,label="SMA"), NotExtended(8,"D",side)])`, con `ABOVE = {"above_mild","above_strong","extended_above"}` (`near` **excluido** — "above" estricto; inclusión de `near` es calibración E9, ADR-005 §9.2).
- **T3.3** — `strategies/market_close.py`: **mismas rules** que `swing_eod` (PLAN §6); única diferencia `partial_bar=True`. Sin lógica nueva.
- **T3.4** — `strategies/__init__.py`: registro `STRATEGIES` (C3) nombre-de-config → `StrategyConfig` (variantes `*_short` → misma instancia).

**Criterio de aceptación:**
- (a) `swing_eod.build_rules("above")` → 3 rules con `name` exactos `AboveSMA(20,W+M)`, `AboveSMA(20,D)`, `NotExtended(8,D)`; `build_rules("below")` → `BelowSMA(20,W+M)`, `BelowSMA(20,D)`, `NotExtended(8,D)` con `buckets_allowed` espejados (`below_*`; `extended_below` excluido en `NotExtended`).
- (b) `series(side)` de `swing_eod` = `{("D",8),("D",20),("W",20),("M",20)}` (independiente del side).
- (c) `swing_eod.partial_bar is False`; `market_close.partial_bar is True`; rules idénticas entre ambas.
- (d) `STRATEGIES` mapea las 4 claves de config a 2 instancias; `strategies/` sin imports de `AlgorithmImports`/`QCAlgorithm`. `run_tests.sh` verde.

### T4 — `ScanPipeline` + `ScanResult` completo (`core/pipeline.py`)

**Por qué.** Es el embudo end-to-end y el único lugar donde se materializa A (precio único) y B (exclusión por referenciadas). Mantenerlo puro (sin CLR) permite testear todo el flujo con `SymbolData` sintético.

- **T4.1 (FABLE xhigh)** — `ScanPipeline` construido con `(strategy_name, direction, side, rules, series, thresholds, top_n, partial_bar)`. `scan(symbol_data_map, as_of) -> list[ScanResult]`:
  1. **Gate (B):** conservar símbolos con `all(sd.is_ready(tf,period) for (tf,period) in series)`; excluir+loguear el resto con causa (serie referenciada fría). **No** `is_ready()` global.
  2. **Ranking:** ordenar los del gate por `day_change_pct(sd)` (`desc` long / `asc` short, tie-break ticker); tomar `top_n`.
  3. **Snapshot + cascada:** por símbolo del `top_n`, `build_position_snapshot(sd, series, thresholds)` (precio único interno); `try/except FeatureNotReady` como backstop (excluir+log); aplicar rules en orden, AND de las `required`, sin short-circuit; `format_filter_line` por rule.
  4. **`ScanResult`** por superviviente: `price=reference_price(sd)`, `partial_bar` (de la estrategia), `sma_evidence=snapshot_evidence(snapshot, series)`, `rules_passed_count`, `time_frames_evaluated`, `passed_rules`, `as_of`, `strategy`, `ticker`, `direction`. `format_final_line` al cerrar.
- **T4.2** — Extender el dataclass `ScanResult` (6B/T7) con los campos de §5 (D7.8), con defaults que no rompan los tests de contrato mínimo de 6B.

**Criterio de aceptación:**
- (a) Sobre un `symbol_data_map` sintético, `scan` produce `ScanResult`s solo para los que pasan **todas** las rules `required`; conteo y orden reproducibles (tie-break ticker).
- (b) **B:** un símbolo con una serie **referenciada** (`W:20`) fría se excluye y loguea; un símbolo con una serie **declarada-no-referenciada** (`W:200`) fría **no** se excluye. Verificado con stub.
- (c) Ranking: long `desc`, short `asc` por `day_change_pct`; el embudo logueado reproduce el formato 6B/T6 y arranca en `top_n`; `build_position_snapshot` se invoca **una vez por símbolo**.
- (d) `ScanResult` con `price` único, `partial_bar` de la estrategia, `sma_evidence` consistente (mismo precio en los 3 tf), `rules_passed_count` y campos de §5; tests mínimos de 6B/T7 siguen verdes.
- (e) `core/pipeline.py` sin imports de `AlgorithmImports`. `run_tests.sh` verde.

### T5 — Integración en `main.py` (L5): minute subscription + pipelines + schedule

**Por qué.** Cablear L5: el working bar exige minute (D7.4), un pipeline por estrategia (config=datos × `strategies/`=composición), y el callback real en vez del stub. El warmup de 5B no debe regresar.

- **T5.1 (FABLE xhigh)** — Suscripción `Resolution.MINUTE` (manteniendo `SPLIT_ADJUSTED` y `subscription_manager.add_consolidator(symbol, sd.daily_consolidator)`) para tener `working_bar` intradía. **Warmup intacto:** `set_warm_up(depth, Resolution.DAILY)` (resolución de warmup ⟂ resolución de suscripción; 5A T3.9 probó minute→daily == daily-directo). **Probe de emisión (A.3):** en el primer scan real, loguear `working_bar` y `sd.close("D")` de un símbolo para confirmar que hoy **no** está consolidado (valida A.2 antes de confiar en `day_change`).
- **T5.2** — En `initialize()`, por cada estrategia de config: `composition = STRATEGIES[name]`, `side = SIDE_BY_DIRECTION[cfg["direction"]]`, `thresholds = resolve_bucket_thresholds(full_config, name)`, `rules = composition.build_rules(side)`, `series = composition.series(side)`, `top_n = env_cfg["top_n"]`, `partial_bar = composition.partial_bar` → construir un `ScanPipeline`. Dict `name -> pipeline`.
- **T5.3** — Reemplazar `_scan_stub` por el callback real: bajo `is_warming_up`, `results = pipeline.scan(self.symbol_data, self.utc_time)`, loguear embudo + nº candidatos (escritura a archivo = Etapa 8; aquí memoria + log). `ScheduledEvent` por estrategia anclado a SPY (wiring ya existe).

**Criterio de aceptación (verificable en backtest, T6):**
- (a) `main.py` sin composición de rules ni umbrales hardcodeados; todo de config + `strategies/`.
- (b) Suscripción minute; el warmup completa igual que en 5B (mismas profundidades/ready); probe confirma `close("D")`=ayer al scan.
- (c) Un `ScheduledEvent` por estrategia dispara a su hora (timestamps) y ejecuta el pipeline real.

### T6 — Backtest de validación (≥3 meses), reproducibilidad y verificación de emisión

**Por qué.** El schedule, el working bar y el timing de emisión **no son unit-testeables sin engine**: se validan en backtest. Aquí se cierran los 3 Done-when del PLAN y se registra el comportamiento real de emisión (A.3).

- **T6.1** — `lean backtest "trade-scanner"` en harness `dev` ≥3 meses: ambas estrategias disparan, el embudo se loguea, se generan `ScanResult`s.
- **T6.2** — **Reproducibilidad:** dos corridas → misma watchlist (tickers, orden, evidencia) en ≥2 fechas conocidas; citar en el cierre.
- **T6.3** — **Verificación de emisión (A.3):** registrar en la bitácora si la diaria de hoy está emitida al scan (esperado: no) y, por tanto, si la SMA de `swing_eod` incluye o no hoy. Si se emite al cierre → activar contingencia `day_change` (D7.6).
- **T6.4** — **Barra parcial + exclusión:** `partial_bar=True` solo en `market_close`; `swing_eod` `False`; un símbolo de historia corta queda excluido y logueado por serie referenciada fría (B).

**Criterio de aceptación:**
- (a) Backtest ≥3 meses sin errores; evidencia (log) de los 3 Done-when del PLAN + el hallazgo de emisión citada en el cierre.
- (b) Watchlists reproducibles en fechas conocidas (mismo input → misma salida), con evidencia por candidato (`sma_evidence` + `passed_rules`).
- (c) `bash scripts/run_tests.sh` verde; commit `[Etapa 7] ...` + bitácora `etapa-07-decisiones-y-pendientes.md`.

---

## Consideraciones técnicas específicas al stack

1. **Pureza de capas (dura).** `core/pipeline.py`, `core/features.py`, `core/rules.py`, `strategies/` importables **sin CLR** (cero `AlgorithmImports` salvo `TYPE_CHECKING`). El pipeline **lee** estado de `SymbolData`; nunca pide datos ni calcula indicadores. Solo `main.py` usa `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify`, `self.utc_time`.
2. **Precio único (A.1).** `position_vs_sma` recibe el precio; `build_position_snapshot` lo computa con `reference_price` una vez por símbolo. Nunca un cierre por-tf en el numerador. La evidencia es consistente solo si el precio es único — es un invariante a testear (T1.c).
3. **"Hoy" vive en el working bar (A.2).** Las SMAs (D y, por la cadena, W/M) solo se actualizan en `data_consolidated` ([symbol_data.py:61-63](../../trade-scanner/core/symbol_data.py#L61-L63)); el working bar es lectura aparte y **no** las alimenta. La SMA queda sobre periodos cerrados (= ayer al scan), consistente intradía y al cierre. Quien "optimice" empujando el working bar a la SMA rompe la estabilidad y la validación de 5B.
4. **Timing de emisión (A.3).** `reference_price` es robusto a cómo emita LEAN; `day_change_pct` y "SMA de swing incluye hoy" **no** lo son → probe temprano en T5 + registro en T6. Esperado: `timedelta(days=1)` no emite hoy hasta la sesión siguiente.
5. **Exclusión por referenciadas (B).** El gate usa `is_ready(tf,period)` sobre la `series` de la estrategia, **antes** del ranking; nunca `is_ready()` global (sobre-excluye por SMAs declaradas-no-usadas frías). El `FeatureNotReady` del builder es backstop, no gate.
6. **Warmup ⟂ resolución de suscripción.** Minute es solo para el working bar; warmup sigue `set_warm_up(depth, DAILY)`. Verificar en backtest que los consolidators reciben las barras del warmup con la suscripción minute (riesgo de implementación, no de diseño).
7. **Memoria/CPU con 200 símbolos × minute** (riesgo SPECS §11): la suscripción minute multiplica el feed. Medir tiempo/memoria del backtest y documentar; si fuese inviable, restringir minute a la unión de universos que usan working bar (en V1, todo el universo).
8. **Reproducibilidad (Done-when #1).** Universo alfabético (`UniverseSpec` ya) + ranking con tie-break por ticker ⇒ misma watchlist en re-runs. Evitar dependencias del orden de iteración de dicts no ordenados.
9. **ScheduledEvents anclados a SPY** (`after_market_close(spy,1)`, `before_market_close(spy,30)`); guard `is_warming_up`. Ya cableado en 5B; T5 solo cambia el callback. `as_of = self.utc_time` (C5).
10. **IEX / 15-min delay (live, Fase 1).** En `lean live` paper el working bar de `market_close` refleja ~15:15 ET; documentado en `as_of`. En backtest es exacto. No es problema de arquitectura (ADR-004).
11. **`top_n`/`bucket_thresholds` desde config; cero hardcodeo.** `top_n` a nivel environment (C6); umbrales placeholder (calibración E9).
12. **Tests en Docker (`scripts/run_tests.sh`).** Pipeline/features/rules/strategies con stubs sintéticos (sin CLR). Schedule, working bar y emisión se validan en backtest (evidencia en el cierre, no test unitario).

---

## Qué NO hacer en esta etapa (fuera de scope)

- **`OutputSink` / serialización CSV-JSON / notificación por entorno** — **Etapa 8**. El `ScanResult` vive en memoria + log; no se escribe watchlist ni se dispara `NotificationManager`.
- **Timeframes intradía (1/5/15/2-min) en `SymbolData`** — **Fase 2** (ADR-004 / ADR-005 §8): el bloqueante real es L2. El working bar de V1 es el del consolidator **diario**, no marcos intradía. (El precio-vivo de V1 **sí** lo usan ambas estrategias; lo diferido es añadir *marcos* intradía, no la lectura del working bar.)
- **Cadencia event-driven por barra de 2-min / day trading** — **Fase 2** (ADR-004). En V1 cada estrategia corre 1×/día en su horario.
- **Contingencia `previous_close`/`RollingWindow`** — solo si T6 muestra emisión-al-cierre (D7.6). No implementar especulativamente.
- **Compartir snapshot entre estrategias** — optimización futura gateada en `(thresholds, series)` idénticos (ADR-005 §9.4).
- **Calibración de `bucket_thresholds`** ni **decidir si `near` cuenta como "above"** — **Etapa 9** (ADR-005 §9.2). Default: "above" estricto (`near` excluido).
- **Reglas nuevas** (pullback, top-losers específicas, fundamentales) — fuera de V1 (SPECS §11). `market_close` reusa las rules de `swing_eod`.
- **Forzar la emisión de la barra de hoy (A2)** para alinear la SMA de `swing_eod` al chart — no en esta etapa; se acepta el off-by-one (A.3) salvo que el hallazgo de T6 lo haga gratis.
- **Backtest a escala prod (≈74 tickers)** y **`lean live`/smoke-test Alpaca** — **Etapa 9**. **`refresh_universe` real** sigue no-op.
- **Tocar la fórmula de warmup, el registro de `TimeframeSpec`, `lean.json`** — estables desde 5A/5B.
- **Cualquier import de `QCAlgorithm`/`self.history`/datos** en L3/L4 (`features`, `rules`, `pipeline`, `strategies`).

---

## Done when (medible)

- [ ] **Precio único (A.1):** `position_vs_sma` recibe el precio y no lee `sd.close(tf)`; `reference_price` y `build_position_snapshot` aplican un solo precio a las 3 SMAs; evidencia consistente; tests E6 migrados. `run_tests.sh` verde.
- [ ] **Composición declarativa:** `swing_eod`/`market_close` componen sus rules canónicas; `build_rules("above"/"below")` dan `name`/`buckets_allowed` espejados correctos; `direction→side` en un solo punto; `partial_bar` por estrategia; registro `STRATEGIES` mapea las 4 claves. Test verde.
- [ ] **Pipeline end-to-end:** `ScanPipeline.scan` con gate por **series referenciadas** (B), ranking `top_n` (`desc` long/`asc` short), snapshot **1×/símbolo** con precio único, cascada de rules y embudo (formato 6B/T6); `ScanResult` con `price` único + `partial_bar` + `sma_evidence` + campos de §5. Test verde.
- [ ] **Backtest ≥3 meses (PLAN DW#1):** ambas estrategias disparan a su hora y generan watchlists **reproducibles** en ≥2 fechas conocidas, con evidencia por candidato. Evidencia (log) en el cierre.
- [ ] **Barra parcial (PLAN DW#2 / SPECS DW#4):** `market_close` reporta `price` del working bar con `partial_bar=True`; `swing_eod` `False`; SMAs sobre periodos cerrados en ambas. Comportamiento de emisión **registrado** en la bitácora (A.3). Verificado en backtest.
- [ ] **Exclusión por referenciadas (PLAN DW#3 / B):** símbolos con una serie **referenciada** fría excluidos y logueados; una SMA declarada-no-referenciada fría **no** excluye. Verificado en log.
- [ ] **Capas limpias + suite verde:** `core/*` y `strategies/` sin imports de `QCAlgorithm`/`self.history`; L2 intacto (sin accesor nuevo); `run_tests.sh` verde; backtest sin errores. Commit `[Etapa 7] ...` + bitácora `etapa-07-decisiones-y-pendientes.md`.

---

## Preguntas abiertas / decisiones diferidas

- [ ] **Inclusión de `near` en "above"** (ADR-005 §9.2): default de esta etapa = estricto (`near` excluido). Calibración/ratificación en **Etapa 9**; no condiciona el diseño (solo el set `buckets_allowed`).
- [ ] **Resultado de la verificación de emisión (A.3):** se **resuelve en T6** (no antes): si LEAN emite la diaria al cierre de mercado, `swing_eod` incluiría hoy en la SMA (alineado al chart) y se activa la contingencia `day_change` (D7.6). Se registra el hallazgo y, si aplica, se abre el ajuste menor.
- [ ] **Coste minute a escala** (200 símbolos): se mide en T6/Etapa 9; si resulta inviable en Fase 1, restringir la suscripción minute (consideración técnica #7). No bloquea el diseño.
