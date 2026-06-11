# Checkpoint Etapa 5A — progreso por sesión

> Archivo temporal de progreso. Si la sesión se interrumpe, retomar desde el último checkpoint marcado.
> Borrar al cerrar la Etapa 5A.

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

## Pendientes de la Etapa 5A (estado al cierre de la sesión 2)

- ~~T2~~ ✅ completada (sesión 2): `core/symbol_data.py` + `scan(time)` (añadido por el hallazgo de emisión perezosa).
- **T3** — `tests/test_timeframes.py` + `tests/test_symbol_data.py` (T3.1–T3.11 en Docker). Única tarea restante de la etapa. Las verificaciones ad-hoc de T1 (sesión 1) y T2 (sesión 2, 24 checks) NO sustituyen los pytest formales. Notas imprescindibles para T3:
  - Emisión perezosa: empujar trailing bar o usar `SymbolData.scan(time)` / `consolidator.scan(time)` para flushear (hallazgo sesión 2; el lag se encadena a W/M).
  - `Symbol.create(..., EQUITY, ...)` revienta sin map file provider → usar `Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")`.
  - T3.2 inyecta registro sintético vía `plan_warmup(..., registry=...)`; `TimeframeSpec("30T", "minute", 30, 60)` posicional.
  - En `SymbolData`, introspección pública para T3.8: `sd.timeframes` (consolidators) y `sd.declared` (series).
- Checkboxes "Done when" de PLAN.md §5A y de etapa-05a.md: sin marcar (correcto — todos dependen de T3, salvo el grep de QCAlgorithm ya verificado pero que se re-verifica al cierre).
- Al cerrar la etapa: PLAN.md §5A Estado → `completada` + borrar este archivo de checkpoint.
- **Fuera de la etapa (sigue pendiente de decisión del usuario):** `config/strategies.json` modificado sin commitear (dev: top_n 5→2, max_universe 10→2) — confirmar si es intencional; `.DS_Store` (ruido macOS, considerar gitignore).

### Decisiones sesión 1
- **Factories de consolidator como campo opcional** (`consolidator_factory: Callable | None`, último campo de la dataclass): mantiene `TimeframeSpec("30T", "minute", 30, 60)` construible posicionalmente (T3.2) y el import perezoso del CLR queda en funciones privadas del módulo (`_daily_consolidator`, etc.), no en if/elif por código.
- **`plan_warmup` acepta `registry` opcional** (default `TIMEFRAMES`): firma del spec intacta para los llamadores, pero T3.2 podrá inyectar el registro sintético sin mutar el dict global.

### Notas sesión 1
- Patrón a seguir: `core/universe.py` (sin AlgorithmImports a nivel módulo).
- T3.2 exige `TimeframeSpec("30T", "minute", 30, 60)` construible posicionalmente → campos extra de la dataclass deben ser opcionales al final.
- Verificación de hoy ≠ tests formales: `tests/test_timeframes.py` se crea en T3.
