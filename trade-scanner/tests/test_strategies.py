"""Tests de strategies/ (Etapa 7; R2 en Etapa 10).

T3.1: StrategyConfig — mecanismo de composición (build_rules above/below con names y espejo,
series dedup + side-independiente, partial_bar/name, instancias frescas, side inválido,
flattening de factories multi-rule, propagación de `filters`). Se prueba con un StrategyConfig
sintético (rules reales de core/rules.py, pero la estrategia concreta swing_eod/market_close es
T3.2/T3.3). Sin CLR: L4 es negocio puro.
"""
import pytest

from core.rules import NotExtended, SMAPositionRule
from strategies import STRATEGIES
from strategies.base import StrategyConfig
from strategies.market_close import market_close
from strategies.swing_eod import swing_eod

# Vocabulario canónico "above" estricto: `near` excluido (calibración de near = E9, ADR-005 §9.2).
ABOVE = {"above_mild", "above_strong", "extended_above"}


def _sample_config(partial_bar: bool = False) -> StrategyConfig:
    """Config sintética con la forma de swing_eod (T3.2) pero definida aquí: aísla el mecanismo
    de StrategyConfig de la estrategia concreta. Las `rules` son factories
    `(side, filters) -> [rule, ...]` (R2); estas ignoran `filters` (siempre defaults) porque el
    uso real de `filters` se prueba contra swing_eod más abajo."""
    return StrategyConfig(
        name="sample",
        partial_bar=partial_bar,
        rules=[
            lambda side, f: [SMAPositionRule(20, ["W", "M"], ABOVE, side, label="SMA")],
            lambda side, f: [SMAPositionRule(20, ["D"], ABOVE, side, label="SMA")],
            lambda side, f: [NotExtended(8, "D", side)],
        ],
    )


# (a) build_rules("above") → names canónicos AboveSMA + NotExtended, con el side propagado
def test_build_rules_above_names_and_side():
    rules = _sample_config().build_rules("above")
    assert [r.name for r in rules] == ["AboveSMA(20,W+M)", "AboveSMA(20,D)", "NotExtended(8,D)"]
    assert all(r.side == "above" for r in rules)


# (a) build_rules("below") → names espejados Below* y buckets espejados (NotExtended excluye
# extended_below en short; AboveSMA → BelowSMA con su set permitido reflejado)
def test_build_rules_below_names_and_mirror():
    rules = _sample_config().build_rules("below")
    assert [r.name for r in rules] == ["BelowSMA(20,W+M)", "BelowSMA(20,D)", "NotExtended(8,D)"]
    assert all(r.side == "below" for r in rules)
    assert rules[0].buckets_allowed == frozenset(
        {"below_mild", "below_strong", "extended_below"}
    )  # ABOVE espejado
    not_extended = rules[2].buckets_allowed
    assert "extended_below" not in not_extended  # el extremo favorable-short queda excluido
    assert "extended_above" in not_extended      # su espejo sí permitido


# (b) series(side) = unión deduplicada de (tf, period), independiente del side
def test_series_is_dedup_union_and_side_independent():
    cfg = _sample_config()
    expected = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
    assert cfg.series("above") == expected
    assert cfg.series("below") == expected  # mismo set: tf/period no cambian con el espejo


# build_rules devuelve instancias FRESCAS cada llamada (no comparte estado mutable entre scans)
def test_build_rules_returns_fresh_instances():
    cfg = _sample_config()
    first, second = cfg.build_rules("above"), cfg.build_rules("above")
    assert first is not second
    assert all(a is not b for a, b in zip(first, second))


# name y partial_bar se guardan tal cual (partial_bar = metadato del horario, D7.4)
def test_name_and_partial_bar_stored():
    assert _sample_config(partial_bar=True).partial_bar is True
    assert _sample_config().partial_bar is False
    assert _sample_config().name == "sample"


# side inválido (p. ej. 'long', que es una direction) → ValueError fail-fast desde build_rules
def test_build_rules_invalid_side_raises():
    with pytest.raises(ValueError, match="side inválido"):
        _sample_config().build_rules("long")


# R2: build_rules sin filters (None/ausente) es retrocompatible con el comportamiento pre-R2
def test_build_rules_without_filters_uses_defaults():
    cfg = _sample_config()
    assert [r.name for r in cfg.build_rules("above")] == [
        r.name for r in cfg.build_rules("above", None)
    ]
    assert [r.name for r in cfg.build_rules("above")] == [
        r.name for r in cfg.build_rules("above", {})
    ]


# R2: una factory que devuelve una LISTA de varias rules se aplana (no queda lista anidada)
def test_build_rules_flattens_multi_rule_factories():
    cfg = StrategyConfig(
        name="multi",
        partial_bar=False,
        rules=[
            lambda side, f: [
                SMAPositionRule(20, [tf], ABOVE, side, label="SMA") for tf in ("D", "W", "M")
            ],
        ],
    )
    rules = cfg.build_rules("above")
    assert [r.name for r in rules] == ["AboveSMA(20,D)", "AboveSMA(20,W)", "AboveSMA(20,M)"]


# R2: `filters` se propaga tal cual a cada factory — un override por (tf, period) cambia
# buckets_allowed de esa rule sin afectar a las demás
def test_build_rules_propagates_filters_per_series():
    cfg = StrategyConfig(
        name="multi",
        partial_bar=False,
        rules=[
            lambda side, f: [
                SMAPositionRule(20, [tf], f.get((tf, 20), ABOVE), side, label="SMA")
                for tf in ("D", "W", "M")
            ],
        ],
    )
    filters = {("W", 20): frozenset({"near"})}
    rules = cfg.build_rules("above", filters)
    by_tf = {r.name: r.buckets_allowed for r in rules}
    assert by_tf["AboveSMA(20,W)"] == frozenset({"near"})       # override aplicado
    assert by_tf["AboveSMA(20,D)"] == frozenset(ABOVE)          # sin override → default
    assert by_tf["AboveSMA(20,M)"] == frozenset(ABOVE)          # sin override → default


# R2: series(side, filters) también acepta filters (aunque el set de (tf,period) no cambia,
# solo los buckets_allowed) y sigue siendo side-independiente
def test_series_accepts_filters_without_changing_the_set():
    cfg = _sample_config()
    filters = {("W", 20): frozenset({"near"})}
    expected = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
    assert cfg.series("above", filters) == expected
    assert cfg.series("below", filters) == expected


# ---------------------------------------------------------------------------
# T3.2 — swing_eod: la StrategyConfig concreta (config real, no el stub sintético).
# Los asserts pinchan los buckets EXACTOS (no el constante ABOVE) para fijar de verdad
# el "above estricto" (near excluido) sin re-derivar del mismo símbolo.
# ---------------------------------------------------------------------------

# (a) build_rules("above"): 5 rules canónicas con names exactos, en orden (R2: SMA20 dividida
# por-tf en D/W/M en vez de una rule multi-tf D+W+M)
def test_swing_eod_above_rule_names():
    assert [r.name for r in swing_eod.build_rules("above")] == [
        "AboveSMA(20,D)",
        "AboveSMA(20,W)",
        "AboveSMA(20,M)",
        "AboveSMA(8,D)",
        "NotExtended(8,D)",
    ]


# (a) build_rules("below"): names espejados + buckets espejados (NotExtended excluye extended_below)
def test_swing_eod_below_rule_names_and_mirror():
    rules = swing_eod.build_rules("below")
    assert [r.name for r in rules] == [
        "BelowSMA(20,D)",
        "BelowSMA(20,W)",
        "BelowSMA(20,M)",
        "BelowSMA(8,D)",
        "NotExtended(8,D)",
    ]
    below = frozenset({"below_mild", "below_strong", "extended_below"})
    assert rules[0].buckets_allowed == below  # 20,D
    assert rules[1].buckets_allowed == below  # 20,W
    assert rules[2].buckets_allowed == below  # 20,M
    assert rules[3].buckets_allowed == below  # 8,D
    assert "extended_below" not in rules[4].buckets_allowed  # NotExtended short
    assert "extended_above" in rules[4].buckets_allowed      # su espejo sí permitido


# (a) "above" ESTRICTO: las AboveSMA excluyen `near` (decisión de etapa, ADR-005 §9.2). NotExtended
# NO es "above estricto" — permite near; solo excluye el extremo favorable.
def test_swing_eod_above_excludes_near():
    above = swing_eod.build_rules("above")
    strict = frozenset({"above_mild", "above_strong", "extended_above"})
    for rule in above[:4]:  # las 4 AboveSMA (20,D)/(20,W)/(20,M)/(8,D); NotExtended aparte
        assert rule.buckets_allowed == strict
        assert "near" not in rule.buckets_allowed


# R2: buckets_allowed viene de `filters` cuando la config trae una clave "tf:period" para esa
# rule; el resto sigue en el default ABOVE (sin override)
def test_swing_eod_above_honors_filters_override_per_series():
    filters = {("W", 20): frozenset({"near"})}
    rules = swing_eod.build_rules("above", filters)
    by_name = {r.name: r.buckets_allowed for r in rules}
    assert by_name["AboveSMA(20,W)"] == frozenset({"near"})
    assert by_name["AboveSMA(20,D)"] == frozenset({"above_mild", "above_strong", "extended_above"})
    assert by_name["AboveSMA(20,M)"] == frozenset({"above_mild", "above_strong", "extended_above"})
    assert by_name["AboveSMA(8,D)"] == frozenset({"above_mild", "above_strong", "extended_above"})


# R2: el mismo override se espeja al side "below", igual que el default (D6B.4)
def test_swing_eod_filters_override_mirrors_to_below():
    filters = {("W", 20): frozenset({"near"})}
    rules = swing_eod.build_rules("below", filters)
    by_name = {r.name: r.buckets_allowed for r in rules}
    assert by_name["BelowSMA(20,W)"] == frozenset({"near"})  # "near" es autoespejo


# R2: filters ausente (None) es retrocompatible — mismos names/buckets que sin el parámetro
def test_swing_eod_filters_none_is_backward_compatible():
    assert [r.buckets_allowed for r in swing_eod.build_rules("above")] == [
        r.buckets_allowed for r in swing_eod.build_rules("above", None)
    ]


# (b) series de swing_eod = unión deduplicada, independiente del side
def test_swing_eod_series():
    expected = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}
    assert swing_eod.series("above") == expected
    assert swing_eod.series("below") == expected


# (c) partial_bar False (swing corre con el mercado ya cerrado, D7.4); name correcto
def test_swing_eod_partial_bar_and_name():
    assert swing_eod.partial_bar is False
    assert swing_eod.name == "swing_eod"


# ---------------------------------------------------------------------------
# T3.3 — market_close: misma composición que swing_eod, solo difiere partial_bar.
# ---------------------------------------------------------------------------

# (c) market_close.partial_bar True (corre con el mercado abierto, D7.4); name correcto
def test_market_close_partial_bar_and_name():
    assert market_close.partial_bar is True
    assert market_close.name == "market_close"


# (c) rules IDÉNTICAS a swing_eod: mismo list de factories (literal) → mismos names/buckets
# en ambos sides; la única diferencia entre las dos configs es partial_bar.
def test_market_close_rules_identical_to_swing_eod():
    assert market_close.rules is swing_eod.rules  # mismas factories, no una copia
    for side in ("above", "below"):
        mc, se = market_close.build_rules(side), swing_eod.build_rules(side)
        assert [r.name for r in mc] == [r.name for r in se]
        assert [r.buckets_allowed for r in mc] == [r.buckets_allowed for r in se]
    assert market_close.series("above") == swing_eod.series("above")
    assert market_close.partial_bar != swing_eod.partial_bar  # único campo que difiere


# ---------------------------------------------------------------------------
# T3.4 — STRATEGIES: registro nombre-de-config → StrategyConfig (4 claves → 2 instancias).
# ---------------------------------------------------------------------------

# (d) las 4 claves de config mapean a 2 instancias; *_short apunta a la MISMA instancia que su long
def test_strategies_registry_maps_four_keys_to_two_instances():
    assert set(STRATEGIES) == {"swing_eod", "swing_eod_short", "market_close", "market_close_short"}
    assert STRATEGIES["swing_eod"] is swing_eod
    assert STRATEGIES["swing_eod_short"] is swing_eod          # misma instancia (side vía direction)
    assert STRATEGIES["market_close"] is market_close
    assert STRATEGIES["market_close_short"] is market_close    # misma instancia
    assert len({id(cfg) for cfg in STRATEGIES.values()}) == 2  # 4 claves, 2 instancias distintas
