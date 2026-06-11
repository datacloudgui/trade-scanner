# Etapa 5A — Decisiones y pendientes (cierre 2026-06-11)

Rescate del checkpoint de la etapa (4 sesiones, todas el 2026-06-11). Evidencia final:
`bash scripts/run_tests.sh` → **31 passed** (T3.1–T3.11 + 6 tests previos del repo).
Commits: `[Etapa 5A] docs` · `T1` (d42c4d3) · `T2` (f6d22a9) · `T3.1–T3.8` (b49632f) · `T3.9` (1417da7) · `T3.10–T3.11 y cierre`.

## Decisiones de diseño tomadas durante la etapa

- **`consolidator_factory` como campo opcional al final de `TimeframeSpec`**: mantiene la construcción posicional `TimeframeSpec("30T", "minute", 30, 60)` (T3.2) y el import perezoso del CLR en funciones privadas del módulo, no en if/elif por código.
- **`plan_warmup(..., registry=...)` opcional** (default `TIMEFRAMES`): los tests inyectan registros sintéticos sin mutar el global; la firma del spec queda intacta para los llamadores.
- **CLR lazy dentro de `SymbolData.__init__`** (no a nivel de módulo): `import core` funciona en el host sin Docker y el export eager en `core/__init__.py` no rompe "`import core.timeframes` sin CLR" (formalizado como test vía subprocess).
- **SMA se actualiza con `bar.end_time`, nunca `time`**: con `time` la SMA queda desplazada un periodo.
- **W/M solo consumen la barra diaria consolidada** (cadena D4): una sola ruta de verdad; equivalencia warmup/runtime garantizada (verificada exacta en T3.9).
- **El consolidator diario raíz existe siempre**, declare D periodos o no: es la entrada única de la cadena y la fuente de `working_bar`.
- **`SymbolData.scan(time)` añadido a la interfaz** (no estaba en el spec original): flush del diario primero y luego de los encadenados; `scan` solo emite si el periodo venció (seguro a mitad de semana/mes). Motivado por el hallazgo nº 1.
- **Timeframes con `source_resolution != "daily"` → ValueError explícito** en `SymbolData`: la cadena intradía real es de etapa futura; fallar claro antes que construir mal.
- **Lambdas con default-arg** (`lambda _s, bar, _sma=sma: ...`) al cablear SMAs en loop (bug clásico de closure compartido).
- **Introspección pública** `sd.timeframes` y `sd.declared` para tests (T3.8) y logs de 5B.
- **Done-when "con warning" de PLAN.md §5A**: marcado con alcance ajustado — la exclusión por presupuesto y el reporte de profundidad están testeados (T3.3); el warning lo emite el llamador (`main.py`, 5B) según D2 del spec.

## Hallazgos verificados en Docker

1. **La emisión del consolidator es perezosa SIEMPRE** — incluso una barra diaria que llena exactamente el periodo queda en `working_data` hasta una barra posterior o `scan(time)`; el lag se encadena a W/M (la barra W de la semana 1 exige que una barra diaria de la semana 2 sea *emitida*, no solo pusheada). La consideración técnica 3 del spec original era falsa y fue corregida.
2. **`scan()` también emite en consolidators de calendario** (`Calendar.WEEKLY`/`MONTHLY`), verificado en T3.4 — habilita refrescar SMAs W/M el mismo día del cierre de periodo en runtime.
3. **Equivalencia EXACTA de rutas** (T3.9): el consolidator diario redondea `time` a 00:00, por lo que la barra diaria construida desde minutos es bit-idéntica a la diaria directa, y la cadena W hereda la identidad (barras y SMAs iguales con `==` estricto). No hay asimetría en LEAN que corregir en 5B.
4. **Gotchas de tests dentro de la imagen LEAN**: `Symbol.create(..., EQUITY, ...)` lanza NullReference fuera del engine (exige map file provider) → usar `Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")`. Para scripts directos (no `python -m pytest`), añadir `/Lean/Launcher/bin/Debug` al `PYTHONPATH`.

## Pendientes que hereda 5B

- **El warmup debe cerrar con `SymbolData.scan(end_time de la última barra)`** — sin esto las SMAs quedan un periodo frías (hallazgo nº 1). `buffer_bars` absorbe el +1 en producción.
- **Considerar un `scan(now)` programado en runtime** antes del scan de reglas: con el hallazgo nº 2, las SMAs W/M se refrescan el mismo día del cierre de periodo en vez de ~1 día tarde.
- **Cablear el presupuesto de warmup** desde `environments` de `strategies.json` y loguear warning por cada serie excluida (cierra el Done-when "con warning" en su sentido completo).
- `strategies.json` prod → `D:[8,20,200]`, `W:[8,20,200]` (decisión ya tomada, efecto observable en 5B).
- Preguntas abiertas que siguen en el spec: convención de códigos intradía (`"5T"`/`"15T"`/`"30T"`, ratificar al implementarlos) y `plan_warmup` global vs por símbolo (decidir en 5B).

## Pendientes fuera de la etapa (decisión del usuario)

- `config/strategies.json` modificado sin commitear desde antes de la sesión 1 (dev: top_n 5→2, max_universe 10→2) — confirmar si es intencional.
- `.DS_Store` modificado (ruido de macOS) — candidato a `.gitignore`.
- El archivo de la Etapa 4 perdió su extensión: `etapa-04-decisiones-y-pendientes-md` → renombrar a `.md` (el enlace en PLAN.md ya apunta al nombre sin extensión).
