# T3 (Etapa 7) — Composición declarativa: `StrategyConfig` + `swing_eod`/`market_close` + `STRATEGIES` (2026-06-18)

L4, `strategies/`. Composición sin lógica nueva (D7.2): una estrategia declara *qué* rules canónicas usa
y *si* su scan es intradía. Código **100% aditivo** (archivos nuevos) — no toca `core/rules.py` ni los
tests previos. **T3 cerrada completa** (T3.1–T3.4):

- **T3.1** — `strategies/base.py`: `StrategyConfig` (la decisión de diseño: rules como factories).
- **T3.2** — `strategies/swing_eod.py`: la primera config concreta.
- **T3.3** — `strategies/market_close.py`: misma composición, solo difiere `partial_bar=True`.
- **T3.4** — `strategies/__init__.py`: registro `STRATEGIES` (4 claves → 2 instancias).

## Resultado contra el criterio de aceptación (T3 completo)

| Criterio T3 | Estado | Evidencia |
|---|---|---|
| (a) `swing_eod.build_rules("above")` → `AboveSMA(20,W+M)`, `AboveSMA(20,D)`, `NotExtended(8,D)` | ✅ | `test_swing_eod_above_rule_names` |
| (a) `build_rules("below")` → `Below*` + buckets espejados (`extended_below` excluido en NotExtended) | ✅ | `test_swing_eod_below_rule_names_and_mirror` |
| (a) "above" estricto: `near` excluido de las AboveSMA | ✅ | `test_swing_eod_above_excludes_near` (buckets exactos, no el constante) |
| (b) `series(side)` de swing_eod = `{(D,8),(D,20),(W,20),(M,20)}`, independiente del side | ✅ | `test_swing_eod_series` |
| (c) `swing_eod.partial_bar is False`; `market_close.partial_bar is True`; rules idénticas entre ambas | ✅ | `test_swing_eod_partial_bar_and_name`, `test_market_close_partial_bar_and_name`, `test_market_close_rules_identical_to_swing_eod` |
| (d) `STRATEGIES` mapea las 4 claves a 2 instancias (`*_short` → misma instancia) | ✅ | `test_strategies_registry_maps_four_keys_to_two_instances` |
| Mecanismo `StrategyConfig` (build_rules/series/fresh/fail-fast) — T3.1 | ✅ | 6 tests con `_sample_config()` sintético |
| (d) `strategies/` sin `AlgorithmImports`/`QCAlgorithm`/`self.history` | ✅ | `grep` → solo docstrings |
| `run_tests.sh` verde | ✅ | **167 passed, 13 warnings in 6.20s** (Docker) — 153 (pre-T3) + 6 (T3.1) + 5 (T3.2) + 3 (T3.3/T3.4) |

**Veredicto: ✅ T3 cerrada (T3.1–T3.4).** Done-when #2 de la etapa marcado `[~]` **parcial**: la composición
+ registro están completos y verdes; falta solo el **wiring** `direction→side` de **T5** (`main.py` lee
`cfg["direction"]`, aplica `SIDE_BY_DIRECTION` y pasa el `side` a `build_rules`). El mecanismo ya existe
(SIDE_BY_DIRECTION desde 6B + `build_rules(side)`); nada lo invoca en el flujo todavía.

## Cambios

**`strategies/base.py` (T3.1, nuevo):** `StrategyConfig` (`@dataclass(frozen=True)`, `name`/`partial_bar`/
`rules: list[Callable[[str], SMAPositionRule]]`) con `build_rules(side)` (instancias frescas) y
`series(side)` (unión deduplicada de `(tf, period)` derivada de las rules). `SMAPositionRule` solo bajo
`TYPE_CHECKING`. Cero CLR.

**`strategies/swing_eod.py` (T3.2, nuevo):** instancia módulo-level `swing_eod = StrategyConfig(...)` con
3 factories — `SMAPositionRule(20,["W","M"],ABOVE,side)`, `SMAPositionRule(20,["D"],ABOVE,side)`,
`NotExtended(8,"D",side)` — y `ABOVE = frozenset({"above_mild","above_strong","extended_above"})` local.
`partial_bar=False`.

**`strategies/market_close.py` (T3.3, nuevo):** instancia `market_close = StrategyConfig(name="market_close",
partial_bar=True, rules=swing_eod.rules)` — reusa el **mismo list** de factories de swing_eod.

**`strategies/__init__.py` (T3.4):** añade `STRATEGIES = {"swing_eod": swing_eod, "swing_eod_short": swing_eod,
"market_close": market_close, "market_close_short": market_close}` + `__all__`. Antes era solo docstring.

**`tests/test_strategies.py`:** +6 tests T3.1 (mecanismo, `_sample_config` sintético), +5 tests T3.2
(config real `swing_eod`), +3 tests T3.3/T3.4 (market_close partial_bar + rules idénticas + registro).
`153 → 167`.

## Decisiones tomadas

### D-T3.1.a — `rules` son **factories `side -> rule`**, no instancias *(la decisión central de T3)*
La spec escribe `rules=[SMAPositionRule(...,side,...), ...]` con `side` como variable libre: solo funciona
si cada entrada es una factory. Una instancia fija su `side`/espejo en construcción ⇒ no se proyecta a
long+short desde una sola config. Guardar factories deja `direction→side` en un solo punto (D7.3) y la
simetría sin re-declarar reglas. `build_rules(side)` las materializa; `series(side)` las introspecta.

### D-T3.1.b — `series` se **deriva** de las rules (no se almacena), vía `build_rules`
"Unión deduplicada derivada de las rules" ⇒ no un campo aparte que se desincronice. Para leer
`.tfs`/`.period` hay que construir las rules; side-independiente, pero la firma lleva `side` porque
construir exige uno. El pipeline lo llama 1× en initialize() (D7.1), sin coste en el hot path.

### D-T3.1.c — `frozen=True` pese al campo `list`
Comunica inmutabilidad (config = value object). El `list` lo hace no-hasheable (auto-`__hash__`), pero
las configs son **valores** de `STRATEGIES` (T3.4), nunca claves → no se hashean. Sin footgun real.

### D-T3.1.d — No revalido `side` en `StrategyConfig`
`build_rules` → factory → `SMAPositionRule.__init__` → `mirror_buckets` (ya valida `side`, ValueError
fail-fast). Revalidar duplicaría sin ganancia. `test_build_rules_invalid_side_raises` lo confirma.

### D-T3.2.a — `ABOVE` vive **local a `swing_eod.py`** *(resuelve la decisión menor abierta en T3.1)*
No se comparte. En V1 solo existen swing_eod/market_close, y market_close (T3.3) reusará `swing_eod.rules`
(con `ABOVE` ya horneado en las factories) ⇒ no necesita `ABOVE` por separado (YAGNI). Además ADR-005 §9.2
marca la inclusión de `near` como calibración E9: tener `ABOVE` por módulo de estrategia es el seam correcto
si E9 calibra por estrategia. Extraer a un preset compartido luego es trivial.

### D-T3.2.b — Los tests asertan **buckets concretos**, no el constante `ABOVE`
`test_swing_eod_above_excludes_near` compara contra `frozenset({"above_mild","above_strong","extended_above"})`
literal, no contra `ABOVE` importado: así un `ABOVE` mal definido (p. ej. con `near`) **falla** el test en
vez de pasar por usar el mismo símbolo. Pin real del "above estricto".

### D-T3.2.c — `ABOVE` como `frozenset` módulo-level
Inmutable y compartido por las 3 factories sin riesgo de mutación. `SMAPositionRule`/`mirror_buckets`
aceptan cualquier iterable, así que `frozenset` encaja sin fricción.

### D-T3.3.a — `market_close.rules = swing_eod.rules` (mismo list object), no un `_RULES` compartido
"Mismas reglas que swing_eod" (PLAN §6) se vuelve **literal**: las dos configs comparten el mismísimo list
de factories, así que es imposible que diverjan en un refactor (no hay dos definiciones que mantener
sincronizadas). Un `_RULES` intermedio en un tercer módulo no añade nada en V1 (solo estas dos estrategias
comparten composición) y diluiría dónde "viven" las reglas. `test_market_close_rules_identical_to_swing_eod`
lo pin­cha con `market_close.rules is swing_eod.rules`. La única diferencia entre configs es `partial_bar`.

### D-T3.4.a — `*_short` → MISMA instancia que su long; sin stripping de sufijo (C3)
`STRATEGIES` mapea 4 claves a 2 instancias: `swing_eod_short` → la instancia `swing_eod`, etc. El `side`
NO se deriva del sufijo `_short` (frágil, mágico) sino aparte, de `cfg["direction"]` vía `SIDE_BY_DIRECTION`
en main.py (T5). El registro es explícito (4 entradas literales), sin lógica de parsing de nombres.
`test_strategies_registry_maps_four_keys_to_two_instances` verifica `is` + que hay exactamente 2 instancias.

## Pendiente

- **Wiring `direction→side` (T5):** lo único que falta para cerrar el Done-when #2 (marcado `[~]`). `main.py`,
  por estrategia: `side = SIDE_BY_DIRECTION[cfg["direction"]]` → `composition.build_rules(side)` /
  `composition.series(side)`. El mecanismo ya existe; es el call site.
- **Resto de Etapa 7:** T4 (`ScanPipeline` + `ScanResult` completo — primer uso real de `build_position_snapshot`,
  `day_change_pct`, gate B), T5 (integración `main.py` + minute subscription), T6 (backtest ≥3 meses).
- **Docs alineadas (2026-06-18):** `etapa-07.md` Done-when #2 → `[~]`; `PLAN.md` Etapa 7 → "en progreso";
  `SPECS.md` línea de Estado → "7 en progreso (L3 precio + composición L4)".
- **Commit:** gated por el usuario. Acumulado sin commitear (T1+T2+T3 completo): `core/features.py`,
  `tests/test_features.py`, `strategies/base.py`, `strategies/swing_eod.py`, `strategies/market_close.py`,
  `strategies/__init__.py`, `tests/test_strategies.py`, `etapa-07.md`, `PLAN.md`, `SPECS.md`, bitácoras
  `etapa-07-t1/t2/t3-…`.
