# ADR-004 — Cadencia de evaluación para reglas intradía (day trading)

**Estado:** propuesto (para Fase 2+; V1 es solo swing/EOD)
**Fecha:** 2026-06-13
**Supersede a:** —
**Supersedido por:** —

---

## Contexto

V1 del screener evalúa en horarios programados (`after_close`, `before_close_30m`) — una vez al día por estrategia (ver `main.py`, `ScheduledEvents` anclados a SPY). Las features (`position_vs_sma`) y rules (`AboveSMA`/`NotExtended`) leen estado ya calculado por `SymbolData`: `sma(tf, period).current.value` y `close(tf)`, costo **O(1) por serie**. Las SMAs W/M son estables intradía y la barra parcial del día se **excluye** a propósito (decisión de 5A: SMAs estables, deseado para swing).

Se planteó cómo cambia este panorama si en el futuro se agregan reglas de **day trading** (decisiones intradía sobre marcos de 1/5/15-min), y cuál es la cadencia óptima de evaluación: ¿cada minuto, cada N minutos, o en cada instante/tick?

Este ADR fija el criterio **antes** de implementarlo, para que la decisión no se tome ad-hoc cuando llegue Fase 2.

---

## Qué cambia con reglas intradía

1. **Timeframes intradía** — se añaden consolidators de 1/5/15-min. Implica suscripción `Resolution.MINUTE` y warmup más profundo (más barras). La profundidad de warmup ya se **deriva de config** (PLAN.md §4), así que escala sin hardcodeo.
2. **La barra parcial pasa a importar.** V1 excluye la barra en curso (SMAs estables intradía). Day trading necesita el precio *ahora* → leer `working_bar`/precio vivo, no solo la barra cerrada. Cambio semántico: una feature nueva (p. ej. `position_vs_sma_live`) o un parámetro que decida barra-cerrada vs barra-en-curso. **No** se modifica `position_vs_sma` actual (su contrato "SMA estable, barra cerrada" sigue siendo correcto para swing).
3. **Frecuencia de evaluación** — ya no 1×/día; hay que correr intradía.
4. **Datos** — Alpaca free = IEX + 15 min de delay → no apto para decisiones intradía reales. Es un límite de *datos*, no de arquitectura (ver [ADR-003](ADR-003-stooq-como-fuente-de-datos.md)).

Lo que **no** cambia: `position_vs_sma`/`AboveSMA`/`NotExtended` siguen siendo lecturas O(1) sobre `SymbolData`. Solo cambia el *trigger* de evaluación y, si la regla mira "precio ahora", la fuente del precio (barra parcial).

---

## Decisión

**Evaluar event-driven, en el cierre de barra del marco de decisión más pequeño que use la estrategia. Ni por tick/instante, ni por reloj arbitrario.**

Regla operativa: **una evaluación por barra de la señal.** Si la estrategia decide sobre barras de 5-min, se evalúa cuando consolida la barra de 5-min (handler del consolidator), no cada minuto ni cada tick.

### Por qué

| Cadencia | Veredicto | Motivo |
|---|---|---|
| **Cada instante / tick** | ❌ | No hay SMA nueva entre barras → trabajo tirado; el dato free es delayed/sampled igual; el costo escala con universo × frecuencia sin ganancia de señal |
| **Cada minuto fijo** | ⚠️ Solo si el marco de decisión es 1-min | Si se decide en 5-min, evaluar cada minuto repite 4 evaluaciones sin información nueva |
| **Event-driven en cierre de barra** | ✅ | Una evaluación por barra, alineada al dato; O(1) por serie como hoy; sin polling |

Fundamento: la **SMA no cambia entre barras**; lo único que se mueve dentro de la barra en curso es el precio de la barra parcial, que se captura al cierre de esa barra. Evaluar más fino que la barra de señal no aporta información.

---

## Encaje con lo implementado

- **Trigger:** hoy el scan se dispara con `ScheduledEvents` (time-based, 1×/día). Para intradía se cambia el *trigger* a un handler del consolidator del marco de N-min (evento en el cierre de barra), o a un `ScheduledEvent` cada N min **alineado** a la barra. La capa de orquestación (L5, `main.py`) es la única que cambia.
- **Features/rules:** sin cambios — siguen siendo lecturas O(1). Lo único nuevo sería una variante de feature que lea la barra parcial si la regla mira "precio ahora".
- **Config:** el marco de decisión y su periodo siguen declarándose en `config/strategies.json` (regla dura: nada de timeframes/cadencias hardcodeadas).

## Costo estimado (orden de magnitud)

Por evaluación: símbolos × tf × periodos lecturas+divisiones, todas O(1). Aun con 200 símbolos evaluados en cada cierre de barra de 5-min (~78 barras/día), el cuello de botella **no** es cómputo — es la **resolución/latencia del dato** y la semántica de la barra parcial.

---

## Consecuencias

- V1 (swing/EOD) **no se toca**: este ADR es para Fase 2+.
- Cuando se implemente day trading: cambiar solo el trigger en L5 + (si aplica) feature que lea barra parcial; reusar `position_vs_sma`/rules tal cual.
- Resolver antes la fuente de datos intradía (Alpaca free no sirve para decisiones reales por el delay de 15 min — ver ADR-003).

## Revisión futura

Revisar cuando: (a) se priorice una estrategia intradía en el roadmap, o (b) se consiga una fuente de datos intradía sin delay. En ese momento, confirmar el marco de decisión por estrategia y elegir trigger (consolidator handler vs scheduled alineado).
