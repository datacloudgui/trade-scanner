"""Tests de core/rules.py (Etapa 6, T3).

L4 negocio puro. rules.py no importa AlgorithmImports; la suite corre dentro de
Docker (el import de `core` pasa por __init__, que sí toca CLR vía symbol_data).
T3: AboveSMA — AND sobre tfs, evidencia `{tf:{period:{value,distance_pct,bucket}}}`,
fail-fast de `buckets_allowed` en construcción, `name` = `AboveSMA(p,tf+tf)`.
"""
from types import SimpleNamespace

import pytest

from core.features import BUCKETS, FeatureNotReady
from core.rules import AboveSMA, RuleResult


THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}
# Buckets "por encima" típicos de AboveSMA (todos los above).
ABOVE = {"above_mild", "above_strong", "extended_above"}


class StubSymbolData:
    """Stub multi-tf: cada tf con su (sma, close) → distinto bucket por tf.

    Implementa solo la API que lee position_vs_sma: is_ready / sma / close.
    """

    def __init__(self, series: dict, ready: bool = True):
        # series: {tf: (sma_value, close_value)}
        self.symbol = "STUB"
        self._series = series
        self._ready = ready

    def is_ready(self, tf, period) -> bool:
        return self._ready

    def sma(self, tf, period):
        sma_value, _ = self._series[tf]
        return SimpleNamespace(current=SimpleNamespace(value=sma_value))

    def close(self, tf):
        return self._series[tf][1]


def _assert_evidence(evidence: dict, expected: dict) -> None:
    """Forma exacta `{tf:{period:{value,distance_pct,bucket}}}`: claves en cada
    nivel idénticas; value/bucket exactos; distance_pct con tolerancia 1e-9.

    expected: `{tf: {period: (value, distance_pct, bucket)}}`.
    """
    assert set(evidence) == set(expected)
    for tf, periods in expected.items():
        assert set(evidence[tf]) == set(periods)
        for period, (value, dist, bucket) in periods.items():
            entry = evidence[tf][period]
            assert set(entry) == {"value", "distance_pct", "bucket"}
            assert entry["value"] == value
            assert entry["distance_pct"] == pytest.approx(dist, abs=1e-9)
            assert entry["bucket"] == bucket


# (a) — todos los tf en buckets permitidos → passed=True; name y evidence completos
def test_and_passes_when_all_tfs_in_allowed_buckets():
    sd = StubSymbolData({"W": (100.0, 105.0), "M": (100.0, 102.0)})
    result = AboveSMA(20, ["W", "M"], buckets_allowed=ABOVE).evaluate(sd, THRESHOLDS)
    assert isinstance(result, RuleResult)
    assert result.passed is True
    assert result.name == "AboveSMA(20,W+M)"
    assert result.required is True
    _assert_evidence(
        result.evidence,
        {
            "W": {20: (100.0, 0.05, "above_strong")},
            "M": {20: (100.0, 0.02, "above_mild")},
        },
    )


# (b) — UN tf fuera de rango → passed=False (AND, no OR); evidencia con AMBOS tf
def test_and_fails_when_one_tf_out_of_range():
    # W above_strong (∈ ABOVE), M near (∉ ABOVE) → la rule no pasa
    sd = StubSymbolData({"W": (100.0, 105.0), "M": (100.0, 100.0)})
    result = AboveSMA(20, ["W", "M"], buckets_allowed=ABOVE).evaluate(sd, THRESHOLDS)
    assert result.passed is False
    _assert_evidence(
        result.evidence,
        {
            "W": {20: (100.0, 0.05, "above_strong")},
            "M": {20: (100.0, 0.0, "near")},
        },
    )


# (b2) — no hay short-circuit: aunque el PRIMER tf falle, se evalúan todos
def test_evidence_complete_even_when_first_tf_fails():
    sd = StubSymbolData({"D": (100.0, 100.0), "W": (100.0, 105.0)})  # D near (∉), W ∈
    result = AboveSMA(20, ["D", "W"], buckets_allowed=ABOVE).evaluate(sd, THRESHOLDS)
    assert result.passed is False
    assert set(result.evidence) == {"D", "W"}
    assert result.evidence["W"][20]["bucket"] == "above_strong"


# (d) — buckets_allowed con un bucket inexistente → revienta al CONSTRUIR
def test_invalid_buckets_allowed_raises_at_construction():
    with pytest.raises(ValueError, match="desconocidos"):
        AboveSMA(20, ["D"], buckets_allowed={"above_mild", "not_a_bucket"})


# Los 7 buckets exactos son un buckets_allowed válido (fija que BUCKETS es el set aceptado)
def test_all_seven_buckets_allowed_is_valid():
    rule = AboveSMA(20, ["D"], buckets_allowed=set(BUCKETS))
    assert rule.buckets_allowed == set(BUCKETS)


# name con un solo tf: AboveSMA(20,D)
def test_name_single_tf():
    assert AboveSMA(20, ["D"], buckets_allowed=ABOVE).name == "AboveSMA(20,D)"


# required se propaga a RuleResult
def test_required_flag_propagates_to_result():
    sd = StubSymbolData({"D": (100.0, 105.0)})
    result = AboveSMA(
        20, ["D"], buckets_allowed=ABOVE, required=False
    ).evaluate(sd, THRESHOLDS)
    assert result.required is False


# Fríos: la rule NO los maneja — deja propagar FeatureNotReady (exclusión = Etapa 7)
def test_cold_series_propagates_feature_not_ready():
    sd = StubSymbolData({"D": (100.0, 105.0)}, ready=False)
    with pytest.raises(FeatureNotReady):
        AboveSMA(20, ["D"], buckets_allowed=ABOVE).evaluate(sd, THRESHOLDS)
