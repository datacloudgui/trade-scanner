# Checkpoint Etapa 5A — progreso por sesión

> Archivo temporal de progreso. Si la sesión se interrumpe, retomar desde el último checkpoint marcado.
> Borrar al cerrar la Etapa 5A.

---

## Sesión 4 (2026-06-11) — T3.9: equivalencia de rutas daily vs minute

### Alcance
Solo **T3.9** (pedido del usuario). Test en `tests/test_symbol_data.py`: dos `SymbolData` idénticos, ruta (a) barras diarias directas vs ruta (b) 3 minutos/día (open/mid/close) que agregan al mismo OHLCV. Identidad EXACTA exigida: 11 barras diarias emitidas, 2 barras W (OHLCV+time/end_time) y SMAs finales D:3 y W:2. Flush con el mismo `scan(time)` en ambas rutas.

### Checkpoints sesión 4

- [x] CP1 — Test T3.9 escrito (datos variados por día: O=100+i, H=105+i, L=97+i, C=102+i, V=100+10i; minutos 9:31/12:00/15:59 con volúmenes 30/40/V-70; identidad exacta en 11 barras D + 2 barras W + SMAs D:3 y W:2)
- [x] CP2 — `bash scripts/run_tests.sh` verde a la primera: **29 passed** (28 previos + T3.9). La equivalencia se cumple con identidad exacta — el consolidator diario normaliza `time`/`end_time` (redondeo a 00:00), así que la barra construida de minutos es bit-idéntica a la diaria directa, y la cadena W hereda la identidad.
- [x] CP3 — Done-when de equivalencia marcados (etapa-05a.md + PLAN.md §5A); estado → T3.1–3.9 ✅, faltan T3.10–T3.11
- [x] CP4 — Commit `[Etapa 5A] T3.9` (este commit)

---

## Sesión 3 (2026-06-11) — T3 parcial: tests T3.1–T3.8

### Alcance
Solo **T3.1–T3.8** (pedido del usuario): `tests/test_timeframes.py` (T3.1–T3.3, sin CLR) y `tests/test_symbol_data.py` (T3.4–T3.8, Docker). **T3.9–T3.11 quedan para la sesión siguiente.** Flushes con ambos mecanismos (trailing bar y `scan`); T3.4 prueba además `scan()` sobre consolidator de calendario (no cubierto por el ad-hoc de T2 — condiciona frescura W/M en 5B).

### Checkpoints sesión 3

- [x] CP1 — `tests/test_timeframes.py` escrito (T3.1 fórmula parametrizada ×9, T3.2 extensibilidad 30T con registry inyectado, T3.3 presupuesto, + import sin CLR vía subprocess, + KeyError tf desconocido)
- [x] CP2 — `tests/test_symbol_data.py` escrito (T3.4 semana viernes + scan calendario, T3.5 mes calendario + trailing bar, T3.6 SMA W(3)=20.0 a mano vía cadena, T3.7 buffer expulsa semana parcial close-100, T3.8 unión exacta ×3 tests)
- [x] CP3 — `bash scripts/run_tests.sh` verde a la primera: **28 passed** (6 previos + 22 nuevos)
- [x] CP4 — Done-when marcados (verificados por ejecución): etapa-05a.md → T3.8, T3.1–T3.2, T3.3 y grep/import-sin-CLR; PLAN.md §5A → unión exacta, fórmula generalizada y no-QCAlgorithm. El de `plan_warmup` en PLAN.md queda sin marcar: su redacción exige "con warning" y el warning lo emite el llamador en 5B (mismatch de redacción a resolver al cierre).
- [x] CP5 — Pendientes actualizados + commit `[Etapa 5A] T3.1–T3.8` (este commit)

### ✅ Hallazgo positivo sesión 3
**`scan()` funciona también en consolidators de calendario** (verificado en T3.4: emitió la barra W2 un lunes 00:00 vía `cons.scan(...)`, sin trailing bar). Implicación para 5B: en runtime se puede programar un `SymbolData.scan(now)` (p. ej. antes del scan de reglas) para que las SMAs W/M se refresquen el mismo día del cierre de periodo, sin esperar a que la primera barra diaria de la semana/mes siguiente sea emitida (que llegaría ~1 día tarde).

---

## Sesión 2 (2026-06-11) — T2: `core/symbol_data.py`

### Alcance
Solo **T2** según D3/D4 del spec: `SymbolData` con cadena minute→daily→W/M, `working_bar`, `is_ready`, sin instancia de QCAlgorithm. Validación de criterios T2 por ejecución ad-hoc en Docker (los tests pytest formales son T3, sesión siguiente). Una sesión anterior de hoy se interrumpió tras la fase de lectura: nada de T2 había llegado a disco.

### Checkpoints sesión 2

- [x] CP0 — Contexto releído (etapa-05a.md, checkpoint, timeframes.py, universe.py, PLAN.md §5A); verificado en disco que T2 no existía
- [x] CP1 — Estados/spec actualizados (etapa-05a.md → T2 en curso)
- [x] CP2 — `core/symbol_data.py` escrito (D3+D4: cadena daily→W/M, working_bar, is_ready, sma(), declared/timeframes para introspección)
- [x] CP3 — Export en `core/__init__.py` + verificado: `import core` y `import core.symbol_data` en host sin `clr`/`AlgorithmImports` en sys.modules
- [x] CP4 — Validación ad-hoc en Docker de criterios T2: **24/24 PASS** (script temporal `_adhoc_t2_validation.py`, borrado tras ejecutar; T3 formaliza):
  - [x] unión exacta: `{"D":{8,20},"W":{20}}` → sin consolidator M, sin SMA W:8; set vacío no construye
  - [x] `is_ready()` False sin excepciones con barras insuficientes; True con suficientes **tras `scan()`** (ver hallazgo)
  - [x] `working_bar` OHLC parcial correcto a mitad de día (open 1ª/high máx/low mín/close última) y None antes de la primera barra
  - [x] cadena D→W: barra semanal cierra viernes (close 14), SMA W con `end_time` lunes 00:00 sem. siguiente
  - [x] `sma()` KeyError nombra serie y declaradas; timeframe desconocido → KeyError que lo nombra
  - [x] sanity equivalencia: día construido de minutos → SMA D idéntica a close diario (T3.9 formaliza)
- [x] CP5 — `bash scripts/run_tests.sh` verde (6 passed; sin tests nuevos aún — son T3)
- [x] CP6 — Greps Done-when: `grep QCAlgorithm core/symbol_data.py` sin resultados; `import core` host sin CLR
- [x] CP7 — Docs actualizados (etapa-05a.md: consideración 3 corregida con el hallazgo, `scan()` en la interfaz, estado T2 ✅) + commit `[Etapa 5A] T2` (este commit)

### Decisiones de diseño sesión 2 (precisión de datos)
- **SMA se actualiza con `bar.end_time`, nunca `time`** (nota técnica 4 del spec): con `time` la SMA queda desplazada un periodo.
- **W/M solo consumen la barra diaria consolidada** (D4): una sola ruta de verdad; warmup (daily) y runtime (minute) producen exactamente las mismas barras W/M.
- **Consolidator diario raíz existe siempre** (aunque D no declare periodos): es la entrada única de la cadena y la fuente de `working_bar`.
- **CLR lazy dentro de `SymbolData.__init__`** (no a nivel de módulo): el spec permite import de tipos a nivel de módulo, pero el lazy mantiene `import core` funcional en el host sin Docker (mismo patrón que universe/timeframes) y permite export eager en `core/__init__.py` sin romper el Done-when "`import core.timeframes` sin CLR".
- **Lambdas con default-arg** (`lambda _s, bar, _sma=sma: ...`) al cablear SMAs en loop (nota 5: bug clásico de closure).
- **Timeframes con `source_resolution != "daily"` → ValueError explícito**: la cadena intradía real es de etapa futura; fallar claro antes que construir mal.

### 🔴 HALLAZGO sesión 2 (afecta T3.9 y warmup de 5B)
**La emisión del consolidator es perezosa INCLUSO con barras diarias que llenan exactamente el periodo.** La nota técnica 3 del spec ("una barra diaria completa exactamente el periodo" → emite) es empíricamente falsa: verificado en Docker, tras 3 barras diarias la SMA(3) tiene solo 2 muestras — la última barra queda en `working_data` hasta la barra siguiente o `scan(time)`. El lag se encadena: la barra W de la semana 1 requiere que una barra diaria de la semana 2 sea *emitida* (no solo pusheada).
**Decisión:** se añade `SymbolData.scan(time)` (flush: daily primero, luego encadenados — `scan` solo emite si el periodo venció, es seguro a mitad de semana/mes). Sin esto el warmup de 5B dejaría las SMAs un periodo frías. El spec ya anticipaba `scan(time)` en el gotcha transversal de T3; `buffer_bars` absorbe el +1 en producción. Consecuencias: (1) T3.9/T3.x deben usar trailing bar o `scan()`; (2) el warmup de 5B debe terminar con `scan(última end_time)`; (3) corregida la consideración técnica 3 de etapa-05a.md.
**Gotcha extra para T3:** `Symbol.create(..., EQUITY, ...)` exige map file provider (solo existe dentro del engine) → en tests usar `Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")`. Y para scripts directos (no `python -m pytest`): añadir `/Lean/Launcher/bin/Debug` al `PYTHONPATH`.

---

## Sesión 1 (2026-06-11) — T1: `core/timeframes.py` ✅ completada

### Checkpoints sesión 1

- [x] CP0 — Contexto leído (CLAUDE.md, etapa-05a.md, PLAN.md §5A, core/universe.py como patrón)
- [x] CP1 — Estados a `en progreso` (PLAN.md + etapa-05a.md)
- [x] CP2 — `core/timeframes.py` escrito (TimeframeSpec, TIMEFRAMES, warmup_bars, plan_warmup, WarmupPlan, PlannedSeries)
- [x] CP3 — Export en `core/__init__.py`
- [x] CP4 — Criterios T1 verificados por ejecución (venv host, sin CLR):
  - [x] tabla D1 exacta (D/W/M × 8/20/200)
  - [x] plan con budget {"daily": 1200} → depth {"daily": 1010}, M:200 excluida, 8 incluidas
  - [x] plan sin budget → depth {"daily": 4221}, nada excluido
  - [x] `import core.timeframes` sin AlgorithmImports ni clr en sys.modules
  - [x] (extra) KeyError nombra el código desconocido; spec sintético 30T → 6060 sin tocar fórmula
- [x] CP5 — `bash scripts/run_tests.sh` verde (6 passed) + smoke test de `make_consolidator()` D/W/M dentro de la imagen LEAN (lazy import del CLR funciona)
- [x] CP6 — Commits: `[Etapa 5A] docs: fraccionar Etapa 5...` (PLAN.md + specs) y `[Etapa 5A] T1: ...` (código)

## Pendientes de la Etapa 5A (estado al cierre de la sesión 3)

- ~~T2~~ ✅ (sesión 2) · ~~T3.1–T3.8~~ ✅ (sesión 3, 28 passed) · ~~T3.9~~ ✅ (sesión 4, 29 passed — equivalencia con identidad exacta).
- **T3.10–T3.11** — lo único que falta de la etapa (en `tests/test_symbol_data.py`):
  - **T3.10 working bar** (ya cubierto ad-hoc en sesión 2: open 1ª/high máx/low mín/close última + None inicial — formalizar como pytest).
  - **T3.11 readiness**: `is_ready("W", 20)` falso con 19 barras W / verdadero con 20; `is_ready()` agregado refleja la serie más lenta. Ojo: generar 20 semanas (~101 barras diarias) — usar helper con `timedelta`.
  - Helpers ya disponibles en el archivo: `daily_bar`, `flat_day`, `collect`, `push_week`, `assert_bars_identical`, SPY vía `generate_equity(..., False)`.
- **Al cerrar la etapa** (tras T3.9–11): marcar Done-when restantes, PLAN.md §5A Estado → `completada`, borrar este checkpoint. **Resolver mismatch de redacción**: el Done-when de PLAN.md "`plan_warmup()` excluye series sobre presupuesto **con warning**" — la exclusión está testeada (T3.3) pero el warning lo emite el llamador (main.py, 5B por D2); proponer al usuario marcarlo como está o ajustar la redacción.
- **Fuera de la etapa (sigue pendiente de decisión del usuario):** `config/strategies.json` modificado sin commitear (dev: top_n 5→2, max_universe 10→2) — confirmar si es intencional; `.DS_Store` (ruido macOS, considerar gitignore).

### Decisiones sesión 1
- **Factories de consolidator como campo opcional** (`consolidator_factory: Callable | None`, último campo de la dataclass): mantiene `TimeframeSpec("30T", "minute", 30, 60)` construible posicionalmente (T3.2) y el import perezoso del CLR queda en funciones privadas del módulo (`_daily_consolidator`, etc.), no en if/elif por código.
- **`plan_warmup` acepta `registry` opcional** (default `TIMEFRAMES`): firma del spec intacta para los llamadores, pero T3.2 podrá inyectar el registro sintético sin mutar el dict global.

### Notas sesión 1
- Patrón a seguir: `core/universe.py` (sin AlgorithmImports a nivel módulo).
- T3.2 exige `TimeframeSpec("30T", "minute", 30, 60)` construible posicionalmente → campos extra de la dataclass deben ser opcionales al final.
- Verificación de hoy ≠ tests formales: `tests/test_timeframes.py` se crea en T3.
