"""Tests de core/pipeline.py — ScanResult (T7) + formateadores del log de filtrado (T6), Etapa 6B.

L4 negocio puro: pipeline.py no importa AlgorithmImports. T6: los formateadores solo dan formato a
contadores (NO ejecutan filtrado — eso es Etapa 7); el test reproduce LITERALMENTE las 4 líneas del
ejemplo de la spec, incluidos la flecha U+2192 y el signo menos U+2212 (no el guion ASCII). T7:
contrato mínimo de ScanResult — construible sin args, campos nuevos con sus defaults, sin lógica de
llenado (eso es Etapa 7).
"""
from types import SimpleNamespace

import pytest

from core.pipeline import (
    ScanPipeline,
    ScanResult,
    format_filter_line,
    format_final_line,
    validate_series_against_plan,
)
from core.rules import RuleResult
from strategies.swing_eod import swing_eod


# (criterio T6) las 4 líneas del ejemplo, reproducidas literalmente desde contadores
def test_filter_log_reproduces_example_lines_literally():
    lines = [
        format_filter_line("swing_eod", "AboveSMA(20,W+M)", 50, 38, "required"),
        format_filter_line("swing_eod", "AboveSMA(20,D)", 38, 29, "required"),
        format_filter_line("swing_eod", "NotExtended(8,D)", 29, 22, "required"),
        format_final_line("swing_eod", 22),
    ]
    assert lines == [
        "[swing_eod] AboveSMA(20,W+M): 50 → 38 (−12 required)",
        "[swing_eod] AboveSMA(20,D): 38 → 29 (−9 required)",
        "[swing_eod] NotExtended(8,D): 29 → 22 (−7 required)",
        "[swing_eod] final: 22 candidatos",
    ]


# dropped = n_in - n_out (incluso 0); kind="optional" se renderiza tal cual
def test_filter_line_computes_dropped_and_renders_optional():
    assert (
        format_filter_line("market_close", "NotExtended(8,D)", 29, 29, "optional")
        == "[market_close] NotExtended(8,D): 29 → 29 (−0 optional)"
    )


# símbolos exactos: flecha U+2192 y signo menos U+2212 (no '->' ni guion ASCII '-')
def test_filter_line_uses_exact_unicode_symbols():
    line = format_filter_line("s", "R", 10, 3, "required")  # dropped = 7
    assert "→" in line                 # → flecha
    assert "(−7 required)" in line     # − signo menos
    assert "->" not in line                 # no la flecha ASCII
    assert "-7" not in line                 # no el guion ASCII en el dropped


# ---------------------------------------------------------------------------
# T7 (Etapa 6B) — ScanResult: contrato mínimo (sin lógica de llenado, eso es Etapa 7).
# Campos nuevos del rediseño del snapshot: rules_passed_count + sma_evidence (proyección).
# ---------------------------------------------------------------------------

# (T7) contrato mínimo: construible sin args; los campos nuevos traen sus defaults
def test_scanresult_minimal_contract_defaults():
    result = ScanResult()
    assert result.rules_passed_count == 0
    assert result.sma_evidence == {}


# (T7) sma_evidence admite la proyección del snapshot {tf:{period:{value,distance_pct,bucket}}}
def test_scanresult_accepts_snapshot_projection_shape():
    evidence = {"D": {20: {"value": 150.20, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    result = ScanResult(rules_passed_count=2, sma_evidence=evidence)
    assert result.rules_passed_count == 2
    assert result.sma_evidence == evidence


# (T7) default_factory: cada instancia tiene su PROPIO dict (no el clásico bug de default mutable)
def test_scanresult_evidence_default_is_per_instance():
    a = ScanResult()
    a.sma_evidence["D"] = {20: {}}
    assert ScanResult().sma_evidence == {}  # una instancia nueva no ve la mutación de `a`


# (T4.2) ScanResult extendido con los campos de §5, todos con default → contrato mínimo intacto
def test_scanresult_section5_fields_have_defaults():
    r = ScanResult()
    assert r.strategy == "" and r.ticker == "" and r.direction == ""
    assert r.as_of is None and r.partial_bar is False and r.price == 0.0
    assert r.time_frames_evaluated == [] and r.passed_rules == []


# ---------------------------------------------------------------------------
# T4.1 — ScanPipeline: gate (B) → ranking top_n → snapshot+cascada → ScanResult.
# Stubs sintéticos (sin CLR). Las rules reales (swing_eod) ejercitan la cascada de
# verdad; StubRule controla la orquestación cuando no importa la lógica de buckets.
# ---------------------------------------------------------------------------

THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}
SWING_SERIES = {("D", 8), ("D", 20), ("W", 20), ("M", 20)}


class FakeSymbolData:
    """SymbolData sintético para el pipeline: `.symbol.value` (ticker), `.working_bar` (precio
    "ahora"), `.close("D")` (cierre de ayer), `.is_ready`/`.sma` por serie. `price=None` → sin
    working bar; `cold` marca series no-ready."""

    def __init__(self, ticker, price, daily_close, smas, cold=frozenset()):
        self.symbol = SimpleNamespace(value=ticker)
        self.working_bar = None if price is None else SimpleNamespace(close=price)
        self._daily_close = daily_close
        self._smas = dict(smas)
        self._cold = set(cold)

    def is_ready(self, tf, period):
        return (tf, period) not in self._cold

    def sma(self, tf, period):
        return SimpleNamespace(current=SimpleNamespace(value=self._smas[(tf, period)]))

    def close(self, tf):
        return self._daily_close


class StubRule:
    """Rule de orquestación: `name`/`required` del contrato de SMAPositionRule; `evaluate`
    devuelve un veredicto fijo e ignora el snapshot (la lógica de buckets se prueba en
    test_rules). Para tests donde solo importa el flujo del pipeline, no el filtrado real."""

    def __init__(self, name, passed=True, required=True):
        self.name = name
        self._passed = passed
        self.required = required

    def evaluate(self, snapshot):
        return RuleResult(passed=self._passed, evidence={}, name=self.name, required=self.required)


def _pipeline(rules, *, direction="long", side="above", series=SWING_SERIES, top_n=50,
              partial_bar=False):
    return ScanPipeline(
        strategy_name="swing_eod", direction=direction, side=side, rules=rules,
        series=series, thresholds=THRESHOLDS, top_n=top_n, partial_bar=partial_bar,
    )


def _as_map(symbols):
    return {sd.symbol.value: sd for sd in symbols}


# price=102 vs SMA=100 en las 4 series → above_mild en todas → pasa las rules "above".
def _passing(ticker, daily_close):
    return FakeSymbolData(
        ticker, price=102.0, daily_close=daily_close,
        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0},
    )


# price=98 vs SMA=100 → below_mild → pasa las rules "below" (decliners).
def _below_passing(ticker, daily_close):
    return FakeSymbolData(
        ticker, price=98.0, daily_close=daily_close,
        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0},
    )


# (b) gate: serie REFERENCIADA fría excluye; serie declarada-NO-referenciada fría NO excluye
def test_gate_excludes_referenced_cold_keeps_unreferenced_cold():
    log = []
    series = {("D", 20), ("W", 20)}
    a = FakeSymbolData("AAA", 102.0, 100.0, {("D", 20): 100.0, ("W", 20): 100.0},
                       cold={("W", 20)})                       # W:20 referenciada y fría
    b = FakeSymbolData("BBB", 102.0, 100.0,
                       {("D", 20): 100.0, ("W", 20): 100.0, ("W", 200): 0.0},
                       cold={("W", 200)})                      # W:200 fría pero NO referenciada
    results = _pipeline([StubRule("R1")], series=series).scan(
        _as_map([a, b]), as_of="t0", log=log.append
    )
    assert [r.ticker for r in results] == ["BBB"]
    assert any("AAA" in line and "W:20 fría" in line for line in log)


# (c) ranking long: desc por day_change_pct, tie-break ticker, corta en top_n
def test_ranking_long_desc_and_top_n():
    syms = [_passing("AAA", 100.0), _passing("BBB", 98.0),
            _passing("CCC", 101.0), _passing("DDD", 100.0)]
    # day_change: BBB≈0.0408, AAA=0.02, DDD=0.02, CCC≈0.0099 → top2 desc = BBB, AAA (tie→ticker)
    results = _pipeline([StubRule("R1")], direction="long", top_n=2).scan(_as_map(syms), "t0")
    assert [r.ticker for r in results] == ["BBB", "AAA"]


# (c) ranking short: asc por day_change_pct (mayores caídas primero), con rules "below" reales
def test_ranking_short_asc_and_top_n():
    syms = [_below_passing("AAA", 100.0), _below_passing("BBB", 102.0),
            _below_passing("CCC", 99.0)]
    # day_change: BBB≈-0.0392, AAA=-0.02, CCC≈-0.0101 → top2 asc = BBB, AAA
    results = _pipeline(swing_eod.build_rules("below"), direction="short", side="below",
                        top_n=2).scan(_as_map(syms), "t0")
    assert [r.ticker for r in results] == ["BBB", "AAA"]


# (a) solo los que pasan TODAS las required quedan; rules reales (cascada de verdad)
def _ok():
    return _passing("AAA", 100.0)                                  # above_mild en todo → pasa


def _fails_above_d():
    return FakeSymbolData("BBB", 102.0, 100.0,
        {("D", 8): 100.0, ("D", 20): 130.0, ("W", 20): 100.0, ("M", 20): 100.0})  # D:20 below


def _fails_not_extended():
    return FakeSymbolData("CCC", 102.0, 100.0,
        {("D", 8): 90.0, ("D", 20): 100.0, ("W", 20): 100.0, ("M", 20): 100.0})   # D:8 extended


def test_only_symbols_passing_all_required_become_results():
    results = _pipeline(swing_eod.build_rules("above")).scan(
        _as_map([_ok(), _fails_above_d(), _fails_not_extended()]), "t0"
    )
    assert [r.ticker for r in results] == ["AAA"]
    # count = solo rules REQUIRED que pasaron (AboveSMA(8,D) es required=False → no cuenta);
    # passed_rules lista TODAS las que pasaron, incluida la opcional. R2: SMA20 dividida
    # por-tf (D/W/M) en vez de una rule multi-tf D+W+M → sube de 2 a 4 required.
    assert results[0].rules_passed_count == 4
    assert results[0].passed_rules == [
        "AboveSMA(20,D)", "AboveSMA(20,W)", "AboveSMA(20,M)", "AboveSMA(8,D)", "NotExtended(8,D)"
    ]


# (c) embudo: format_filter_line por rule (cascada) + format_final_line; arranca tras gate+ranking
def test_funnel_cascade_lines():
    log = []
    _pipeline(swing_eod.build_rules("above")).scan(
        _as_map([_ok(), _fails_above_d(), _fails_not_extended()]), "t0", log=log.append
    )
    # R2: SMA20 dividida por-tf → BBB (D:20 extended_below) ya cae en el primer paso (D), W y M
    # de BBB no llegan a evaluarse (ya está fuera del funnel); CCC (D:8 extended_above) sobrevive
    # hasta NotExtended, que es donde queda excluido.
    assert log == [
        "[swing_eod] AboveSMA(20,D): 3 → 2 (−1 required)",
        "[swing_eod] AboveSMA(20,W): 2 → 2 (−0 required)",
        "[swing_eod] AboveSMA(20,M): 2 → 2 (−0 required)",
        "[swing_eod] AboveSMA(8,D): 2 → 2 (−0 optional)",   # optional: informa sin descartar
        "[swing_eod] NotExtended(8,D): 2 → 1 (−1 required)",
        "[swing_eod] final: 1 candidatos",
    ]


# (d) ScanResult: campos de §5, price único, partial_bar, evidencia consistente (mismo precio 3 tf)
def test_scanresult_fields_and_single_price_evidence():
    sd = FakeSymbolData("AAA", price=105.0, daily_close=100.0,
        smas={("D", 8): 100.0, ("D", 20): 100.0, ("W", 20): 102.0, ("M", 20): 103.0})
    [res] = _pipeline(swing_eod.build_rules("above"), partial_bar=False).scan(
        _as_map([sd]), as_of="2026-06-19T21:00:00Z"
    )
    assert res.strategy == "swing_eod"
    assert res.ticker == "AAA"
    assert res.direction == "long"
    assert res.partial_bar is False
    assert res.price == 105.0
    assert res.as_of == "2026-06-19T21:00:00Z"
    assert res.time_frames_evaluated == ["D", "W", "M"]   # orden canónico, no alfabético
    # R2: 4 required (AboveSMA(20,D)+(20,W)+(20,M)+NotExtended; AboveSMA(8,D) es optional → no cuenta)
    assert res.rules_passed_count == 4
    # evidencia internamente consistente: value·(1+distance_pct) == el precio único (105) en cada serie
    for periods in res.sma_evidence.values():
        for entry in periods.values():
            assert entry["value"] * (1 + entry["distance_pct"]) == pytest.approx(105.0, abs=1e-9)


# (c) build_position_snapshot se invoca UNA vez por símbolo
def test_build_snapshot_called_once_per_symbol(monkeypatch):
    import core.pipeline as pipeline_mod

    calls = []
    real = pipeline_mod.build_position_snapshot

    def spy(sd, series, thresholds):
        calls.append(sd.symbol.value)
        return real(sd, series, thresholds)

    monkeypatch.setattr(pipeline_mod, "build_position_snapshot", spy)
    _pipeline([StubRule("R1")]).scan(_as_map([_passing("AAA", 100.0), _passing("BBB", 100.0)]), "t0")
    assert sorted(calls) == ["AAA", "BBB"]
    assert len(calls) == len(set(calls))  # exactamente una vez por símbolo


# (backstop) pasa el gate (series ready) pero una SMA es degenerada (==0) → build_position_snapshot
# levanta FeatureNotReady; el pipeline lo excluye+loguea sin crashear (no es el gate primario).
def test_snapshot_backstop_excludes_degenerate_sma():
    log = []
    sd = FakeSymbolData("AAA", 102.0, 100.0,
        {("D", 8): 100.0, ("D", 20): 0.0, ("W", 20): 100.0, ("M", 20): 100.0})  # D:20 SMA==0
    results = _pipeline([StubRule("R1")]).scan(_as_map([sd]), "t0", log=log.append)
    assert results == []
    assert any("AAA" in line for line in log)  # excluido y logueado


# (d) partial_bar de la estrategia se propaga al ScanResult (market_close=True vs swing_eod=False)
def test_partial_bar_propagates_to_scanresult():
    [res] = _pipeline(swing_eod.build_rules("above"), partial_bar=True).scan(
        _as_map([_passing("AAA", 100.0)]), "t0"
    )
    assert res.partial_bar is True


# ---------------------------------------------------------------------------
# #20 (triaje E1–E8) — validate_series_against_plan: series de rules ⊆ plan de warmup,
# validado en initialize() (fail-fast) en vez de KeyError en pleno scan.
# ---------------------------------------------------------------------------

def test_validate_series_missing_from_plan_raises_valueerror():
    with pytest.raises(ValueError, match=r"swing_eod.*M:200"):
        validate_series_against_plan(
            "swing_eod",
            series={("D", 20), ("M", 200)},
            available={("D", 20), ("W", 20)},
        )


def test_validate_series_subset_of_plan_passes():
    validate_series_against_plan(
        "swing_eod", series={("D", 20)}, available={("D", 20), ("W", 20)}
    )  # no lanza


# (a) watchlist reproducible: mismo input → misma salida (tickers + orden)
def test_results_reproducible_across_runs():
    def run():
        syms = [_passing("CCC", 98.0), _passing("AAA", 100.0), _passing("BBB", 100.0)]
        results = _pipeline([StubRule("R1")], top_n=3).scan(_as_map(syms), "t0")
        return [r.ticker for r in results]

    # CCC (change≈0.0408) primero; AAA y BBB empatan en 0.02 → tie-break ticker asc
    assert run() == ["CCC", "AAA", "BBB"]
    assert run() == run()


# ---------------------------------------------------------------------------
# #25 (triaje E1–E8, parcial) — contrato de universos disjuntos a nivel pipeline: cada
# pipeline escanea SOLO el mapa que recibe; con mapas long/short disjuntos ningún ticker
# cruza de lado. El test del wiring L5 completo (UniverseSpec→main.py→pipeline.scan con
# mapa filtrado POR estrategia) llega con el fix de #12 (separado a decisión de diseño).
# ---------------------------------------------------------------------------

def test_disjoint_long_short_maps_produce_disjoint_results():
    long_map = _as_map([_passing("AAA", 100.0), _passing("BBB", 100.0)])
    short_map = _as_map([_below_passing("XXX", 102.0), _below_passing("YYY", 102.0)])

    long_results = _pipeline(
        swing_eod.build_rules("above"), direction="long"
    ).scan(long_map, "t0")
    short_results = _pipeline(
        swing_eod.build_rules("below"), direction="short", side="below"
    ).scan(short_map, "t0")

    long_tickers = {r.ticker for r in long_results}
    short_tickers = {r.ticker for r in short_results}
    assert long_tickers == {"AAA", "BBB"}
    assert short_tickers == {"XXX", "YYY"}
    assert long_tickers.isdisjoint(short_tickers)
    assert all(r.direction == "long" for r in long_results)
    assert all(r.direction == "short" for r in short_results)
