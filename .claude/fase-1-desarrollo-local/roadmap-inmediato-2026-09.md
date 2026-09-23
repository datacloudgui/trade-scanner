# Roadmap inmediato — ciclo de septiembre 2026

**Fecha:** 2026-09-22 · **Estado:** PROPUESTA (requiere aprobación antes de tocar código)
**Rama actual:** `feature/etapa-6-features-rules` · **Último commit:** `f8ded63` (2026-09-13)
**Entrada:** auditoría del estado real del repo (PLAN.md + git + código) tras ~2 meses sin avance de etapas.

> Este documento NO reemplaza a [PLAN.md](../../PLAN.md) (fuente de verdad operativa). Es la
> propuesta de secuencia para el próximo ciclo; al aprobarse, sus unidades se convierten en
> entradas de PLAN.md §7 con su spec propio.

---

## 1. Estado real verificado (2026-09-22)

| Etapa | Estado real | Evidencia |
|---|---|---|
| 1–4, 5A | completada | PLAN.md + commits |
| **5B** | **en progreso** — F2/F3 abiertas (validación manual ≤0,25% + fixture autoritativo); `test_sma_regression.py` sigue marcado "INTERINO" | [PLAN.md:275](../../PLAN.md#L275) |
| 6 / 6B | implementadas y commiteadas (6B figura "en progreso" en PLAN pese a estar commiteada) | `03880f2`, `dd44dfb` |
| 7 / 8 | completadas — 225 passed, backtest dev EXIT=0 | `0e0b88d`, `0cd92e2` |
| **9A** (Alpaca REST, Opción C de ADR-002) | **T1–T6 cerradas**; **T7** (portabilidad local↔cloud, DoD nº5) y **T8** (matriz de proveedor) pendientes; **T9** (live paper, DoD nº4) diferida por QC pago | [etapa-09a-conexion-alpaca.md:3](etapa-09a-conexion-alpaca.md#L3) |
| **9B** (triaje Codex E1–E8) | **19 de 20** hallazgos VIGENTE corregidos | `b5294bb`, `9acf292`, `53be8bd` |
| **10** (toggle `enabled` + `filters` por `TF:periodo`) | implementada y commiteada | `8b0afc2` |
| **11** (fecha del backtest derivada del CSV) | **solo spec, sin implementar** (`grep parse_asof_date` = 0 hits) | [etapa-11-fecha-desde-universo.md](etapa-11-fecha-desde-universo.md) |
| 9 (validación integral Fase 1) | pendiente | [PLAN.md:361](../../PLAN.md#L361) |

### Revisión Codex: aplicada salvo #12

De 26 hallazgos consolidados (2 ya corregidos, 2 decisiones conscientes, 2 documentadas,
**20 VIGENTES**), el ciclo 9B corrigió **19**. Verificado por muestreo en código actual:
#7 ordenamiento por fecha en [seed_object_store.sh:62-69](../../scripts/seed_object_store.sh#L62-L69),
#21 `_emit_file` incondicional en [output.py:245](../../trade-scanner/core/output.py#L245),
#11 `_HARD_CAP = 200` en [universe.py:33](../../trade-scanner/core/universe.py#L33),
#18 guards en [rules.py:50](../../trade-scanner/core/rules.py#L50).

**Abierto: #12 (ALTO) — el scan cruza universos entre estrategias.** `initialize()` materializa la
unión global de tickers y `run_group_scan` pasa el mapa completo de `symbol_data` a cada pipeline.
Sigue vigente (`grep by_strategy|by_member` = 0 hits). Propuesta de diseño completa en
[propuesta-diseno-12.md](../../revisiones/20260619-205134/propuesta-diseno-12.md).

---

## 2. Hallazgo que reordena las prioridades

**El screener hoy no puede producir una watchlist correcta, y la causa no es la fecha hardcodeada
sino la cobertura de datos.** Medición del 2026-09-22 sobre `storage/universes/swing_advances.csv`
(*as of 09-13-2026*), aplicando el `universe_filter` real de `swing_eod`
(`avg_vol > 1e6 and price > 5`):

| Métrica | Valor |
|---|---|
| Tickers post-filtro (advances) | **65** |
| Sin zip en `data/equity/usa/daily/` | **26 (40 %)** — INTC, AMD, GME, SWKS, FSLY, ASO, ATEC… |
| Última barra de los que sí tienen datos | **2026-06-18 … 2026-07-10** (moda: 2026-07-02) |
| `end_date` que pide el algoritmo | **2026-09-01** ([main.py:40](../../trade-scanner/main.py#L40)) |

Los símbolos sin warmup se excluyen vía `is_ready()` y solo dejan un contador `ready: N/M` en el
log. **Consecuencia: la watchlist sale "limpia" aunque se haya calculado sobre poco más de la mitad
del universo, y ni el JSON ni el CSV de salida lo delatan.** Es un fallo silencioso y plausible —
la peor combinación cuando hay dinero detrás.

**Corolario sobre #12:** en `config/strategies.json` solo `swing_eod` está `enabled: true`
(las otras tres en `false` desde Etapa 10). Con un único pipeline, la unión global *es* su universo
→ **#12 está hoy inerte**. Se vuelve real el día que se habilite `swing_eod_short`.

---

## 3. Unidades de trabajo propuestas

### U1 — Cobertura de datos del ciclo semanal · P0 · ~4-6 h

**Qué:**
1. Preflight host-side en `scripts/` (patrón de `check_alpaca_credentials.py`: exit code usable como
   gate) que, dado el CSV del universo, aplique el mismo filtro y reporte tickers post-filtro,
   cuántos tienen zip, cuántos llegan hasta `asof`, y la lista de faltantes.
2. Encadenar el refresh al runbook: `scripts/alpaca_to_lean.py --universe <csv> --end <asof>` ya es
   multi-símbolo con paginación y throttle y escribe a `data/equity/usa/daily`. **No hace falta
   downloader nuevo**, hace falta que el refresh sea un paso obligatorio del ciclo.
3. Exponer la cobertura en la salida, no solo en el log: `universe_size` / `ready` en el envelope de
   `ScanResult` ([core/output.py](../../trade-scanner/core/output.py)), para que la watchlist sea
   auto-descriptiva y auditable.
4. README: insertar refresh + preflight en "Operación semanal" ([README.md:124-142](../../README.md#L124-L142)).

**Por qué ahora:** es la diferencia entre "el screener funciona" y "el screener miente en silencio".
Ninguna unidad posterior tiene valor si la entrada está incompleta.
**Desbloquea:** corridas confiables (incluida U2) y la revisión manual de watchlists del Done-when de Etapa 9.
**Riesgo de no hacerlo:** operar sobre una watchlist calculada con el 40-58 % del universo y SMAs de
hace dos meses, sin señal de alarma.

> **Spike incrustado (~1 h del trader, no de código): cerrar 5B F2/F3.** Con los datos frescos,
> comparar SMA 8/20/200 en D/W/M de SPY/AAPL/IBM contra TradingView/IBKR, congelar los valores como
> fixture autoritativo y sustituir el test "INTERINO".
> **El cross-check de 9A T4 (Alpaca↔Stooq ≤0,2259 %) NO satisface el Done-when de 5B:** mide acuerdo
> *entre dos proveedores*, no acuerdo con la plataforma de referencia del trader, y sobre todo no
> valida la convención lunes→domingo de `Calendar.WEEKLY` contra el gráfico que se mira al operar —
> el riesgo nombrado en SPECS §11 y en el gotcha de [CLAUDE.md:73](../../CLAUDE.md#L73).

### U2 — Etapa 11: fecha derivada del universo + resultados por fecha · P0 · ~4-6 h

**Qué:** implementar [etapa-11-fecha-desde-universo.md](etapa-11-fecha-desde-universo.md) tal cual
(T1–T5): `parse_asof_date` / `read_asof_date` en `core/universe.py` (sin imports LEAN),
`backtest_start_buffer_days` en config, derivación del rango en `prod` dentro de `initialize()`, y
`results/{base}/{YYYYMMDD}/latest.json`.

**Por qué después de U1:** U2 elimina la edición manual de `main.py` cada semana
([README.md:133-137](../../README.md#L133-L137)), pero solo tiene sentido cuando los datos llegan
hasta `asof`; si no, derivar la fecha automáticamente solo hace que el reloj pida barras inexistentes.
**Desbloquea:** reproducir la watchlist de una fecha pasada sin pisar la actual, y elimina la clase de
error "corrí el CSV nuevo con el rango viejo" — que es exactamente el estado del repo hoy.
**Riesgo de no hacerlo:** fricción manual semanal en el paso más crítico del flujo (ya costó dos meses
de inactividad).

**Decisión a tomar explícitamente al implementar:** la carpeta por fecha rompe el contrato de puntero
fijo que consume `scripts/notify_email.py` ([README.md:153](../../README.md#L153)). O el script
resuelve la carpeta más reciente, o se mantiene además un `results/{base}/latest.json` apuntando a la
última corrida. No dejar que emerja.

### U3 — #12: partición del universo por estrategia + encender el lado corto · P1 · ~3-4 h

**Qué:** implementar [propuesta-diseno-12.md](../../revisiones/20260619-205134/propuesta-diseno-12.md)
(≈15 líneas en `main.py`, ≈5 en `core/pipeline.py`, 2 tests que cierran también #25) y **acto seguido**
poner `swing_eod_short` en `enabled: true`.

**Por qué en tercer lugar pese a ser el único ALTO abierto:** hoy es latente, no activo (§2). Su valor
no es cerrar un hallazgo, es **habilitar el lado corto sin envenenar los largos**: el universo
`swing_declines` ya está sembrado y sin usar.
**Riesgo de no hacerlo:** al encender el short, la watchlist de largos incluirá tickers del universo de
declines rankeados con reglas de largo, y el correo lo propagará.

### U4 — Cierre formal de Fase 1 · P2 · ~4-5 h

**Qué:** 9A T7 (portabilidad: zips Alpaca ↔ Stooq vía `DefaultDataProvider`, evidencia = `git diff` de
`.py` vacío), 9A T8 (matriz de proveedor), #23 (activar `qc_notify` en el entorno cloud), #5
(documentar el anchor SPY daily-only) y firma del checklist de los 6 DoD de SPECS §8, **con el nº4
(working bar en live) explícitamente diferido** y justificado por ADR-002.

**Por qué al final:** no cambia nada para el trader; es auditoría de algo que ya es cierto por
construcción.
**Riesgo de no hacerlo:** ninguno a corto plazo; a medio plazo, entrar a Fase 2 (VPS) sin haber
demostrado la portabilidad que la Fase 2 asume.

---

## 4. Posición sobre la tensión: usabilidad semanal antes que cierre formal

**Recomendación: U1/U2 antes que U4, con 5B F2/F3 como única excepción no negociable.**

Los 6 DoD de SPECS §8 no son un fin: son proxies de "el screener produce watchlists en las que se
puede confiar". Cinco están sustancialmente demostrados (9A T4/T5/T6 + Etapas 7/8); lo que resta de E9
es ceremonia de evidencia que no cambia el comportamiento del sistema. Mientras tanto hay un fallo
operativo real y silencioso (§2) que ningún DoD captura, porque el DoD se escribió asumiendo datos
frescos.

La excepción: **5B F2/F3 sí es riesgo de corrección, no papeleo.** Si la semana de `Calendar.WEEKLY`
no cuadra con el gráfico de referencia, `main_timeframe: "W"` y los filtros `W:8`/`W:20` de Etapa 10
están calibrados contra una realidad distinta de la que se mira al operar. Por eso va como spike de
una hora dentro de U1, no como etapa aparte.

---

## 5. Decisiones abiertas de #12 — recomendación

| Pregunta | Recomendación | Argumento |
|---|---|---|
| ¿ADR-006 nuevo o ampliar ADR-005? | **ADR-006 nuevo** | ADR-005 responde *qué se calcula* (snapshot único, reglas como filtros puros), ámbito L3/L4. #12 es un invariante de **L5/orquestación**: "cada pipeline escanea exactamente el mapa de su universo declarado; la unión global existe solo para suscripción y warmup". El triaje registra que ADR-005 "no sanciona el scan sobre la unión" → es un vacío de decisión, justo para lo que existe un ADR nuevo. Reabrir un ADR cerrado es peor señal en spec-driven que añadir uno. Referencia cruzada "Relacionado: ADR-005". |
| ¿Optimizar warmup por símbolo? | **No** | R4 (un solo plan) es lo que hace el arranque predecible y el log auditable. El ahorro es marginal: las cuatro estrategias declaran las mismas series D/W/M 8/20/200. |
| ¿Universo vacío post-filtro? | **Sección vacía sin error, pero con WARNING y registro en el envelope** | Hoy "universo vacío" y "0 candidatos legítimos" producen la misma salida siendo diagnósticos opuestos. Encaja con la cobertura de U1. |

---

## 6. POC Finnhub: diferir a post-V1, sin archivar

El POC (`scripts/poc/`) **no viola la regla dura** "el código solo habla con la API de `QCAlgorithm`":
es host-side, lado productor, análogo a `alpaca_to_lean.py`. El problema es de alcance y secuencia:

- **Earnings BMO/AMC** es un filtro de riesgo de evento, no una señal de entrada. Ninguna regla de V1
  lo consume y SPECS §6 no lo lista. Integrarlo ahora obliga a inventar semántica de producto
  (¿excluyo candidatos con earnings en 48 h?, ¿los marco?) mientras el screener escanea medio universo
  con datos de julio.
- **`10DayAverageTradingVolume`** sí tiene encaje limpio: sustituir el `avg_vol` del CSV de Barchart en
  `universe_filter` y mitigar el volumen IEX subestimado (SPECS §11). Pero eso cambia la fuente del
  contrato de entrada — toca `core/universe.py` y `UniverseSpec`, y merece su propia etapa con ADR.

**Acción:** dejarlo donde está (funcional, con tests offline), añadir una línea en `docs/ROADMAP.md`
bajo candidatos de Fase 2 con las dos vías de integración, y **cerrar por escrito la pregunta abierta
del commit `f8ded63`** para que deje de bloquear el avance.

---

## 7. Higiene documental

1. **Serio — `PLAN.md` no contiene las Etapas 9A, 9B, 10 ni 11** (`grep` = 0 hits). Como
   [CLAUDE.md:7](../../CLAUDE.md#L7) lo declara fuente de verdad operativa con precedencia máxima, el
   contrato con el agente lleva tres meses desincronizado del código y los specs viven sueltos en
   `.claude/fase-1-desarrollo-local/`. Explica parte del "trabajo exploratorio fuera del flujo de
   etapas" del último commit. **Resincronizar §7 con 9A/9B/10/11 (≈30 min) antes de tocar código.**
2. **`docs/ROADMAP.md` y `docs/DEVLOG.md` desfasados:** ROADMAP dice "última cerrada 5A, siguiente 5B";
   DEVLOG termina el 2026-06-13 en Etapa 6. Una pasada de 30-45 min **al terminar U2**, con una entrada
   comprimida por etapa (fecha + enlace al spec); no reconstruir el detalle histórico.
3. **Rama:** `feature/etapa-6-features-rules` acumula E6B, E7, E8, 9A, 9B, 10 y 11 — siete etapas y
   tres meses bajo el nombre de la primera. Mergear a `develop` **tal cual** (sin partirla
   retroactivamente) antes de U1, y abrir `feature/operacion-semanal` para U1+U2.

---

## 8. Archivos críticos para la implementación

| Archivo | Rol en este ciclo |
|---|---|
| [trade-scanner/main.py](../../trade-scanner/main.py) | rango/universo/warmup (L26-90), conteo `ready` (L270-275), `run_group_scan` (L400-409) |
| [trade-scanner/core/universe.py](../../trade-scanner/core/universe.py) | `parse_asof_date`/`read_asof_date` (U2), sin imports LEAN |
| [trade-scanner/core/output.py](../../trade-scanner/core/output.py) | carpeta por fecha (U2), cobertura en el envelope (U1) |
| [scripts/alpaca_to_lean.py](../../scripts/alpaca_to_lean.py) | refresh semanal `--universe/--end` (U1) |
| [config/strategies.json](../../config/strategies.json) | `backtest_start_buffer_days` (U2), `enabled` de `swing_eod_short` (U3) |
| [PLAN.md](../../PLAN.md) | resincronizar §7 antes de tocar código |
