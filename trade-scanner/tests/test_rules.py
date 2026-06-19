"""Tests de core/rules.py — SMAPositionRule (Etapa 6B, T3).

L4 negocio puro. rules.py no importa AlgorithmImports; la suite corre dentro de
Docker (el import de `core` pasa por __init__, que sí toca CLR vía symbol_data).
SMAPositionRule filtra sobre el snapshot precalculado (`evaluate(snapshot)`): AND
sobre tfs sin short-circuit, mirror en construcción para short, `name` por side+label,
evidencia `{tf:{period:{value,distance_pct,bucket}}}` vía snapshot_evidence.

El contrato de fríos del builder se prueba en test_features.py (no en las rules, que
asumen snapshot caliente). AboveSMA fue eliminado en T3.2 (un solo símbolo de clase).
"""
import pytest

from core.features import BUCKETS, PositionResult, _bucketize
from core.rules import NotExtended, RuleResult, SMAPositionRule


# Buckets "por encima" canónicos (vocabulario above); el mirror los lleva a short.
ABOVE = {"above_mild", "above_strong", "extended_above"}


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


# ---------------------------------------------------------------------------
# T3 (Etapa 6B) — SMAPositionRule: filtro puro sobre el snapshot (evaluate(snapshot)),
# mirror en construcción para short, name por side+label, AND sin short-circuit.
# ---------------------------------------------------------------------------

def _snapshot(spec: dict) -> dict:
    """Snapshot `{tf:{period:PositionResult}}` desde `{(tf,period):(value,distance_pct,bucket)}`.

    Construye PositionResult directo (sin stub ni builder): aísla el filtro de la medición —
    evaluate solo lee `.bucket`; la evidencia proyecta value/distance_pct/bucket.
    """
    snap: dict = {}
    for (tf, period), (value, dist, bucket) in spec.items():
        snap.setdefault(tf, {})[period] = PositionResult(
            value=value, distance_pct=dist, bucket=bucket
        )
    return snap


# (a) Largo: todos los tf en buckets permitidos → passed=True; evidencia y name completos
def test_long_passes_when_all_tfs_in_allowed_buckets():
    snap = _snapshot({
        ("W", 20): (100.0, 0.05, "above_strong"),
        ("M", 20): (100.0, 0.02, "above_mild"),
    })
    rule = SMAPositionRule(20, ["W", "M"], buckets_allowed=ABOVE, side="above")
    result = rule.evaluate(snap)
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


# (a) Largo: UN tf fuera → passed=False (AND, no OR)
def test_long_fails_when_one_tf_out_of_range():
    snap = _snapshot({
        ("W", 20): (100.0, 0.05, "above_strong"),  # ∈ ABOVE
        ("M", 20): (100.0, 0.0, "near"),           # ∉ ABOVE
    })
    result = SMAPositionRule(20, ["W", "M"], buckets_allowed=ABOVE, side="above").evaluate(snap)
    assert result.passed is False


# (b) Corto: mismos buckets canónicos, mirror a below_*. extended_below pasa; above_* no.
def test_short_mirror_filters_below_buckets():
    rule = SMAPositionRule(20, ["D"], buckets_allowed=ABOVE, side="below")
    # el set permitido quedó espejado a los below_*
    assert rule.buckets_allowed == frozenset({"below_mild", "below_strong", "extended_below"})
    passes = rule.evaluate(_snapshot({("D", 20): (100.0, -0.12, "extended_below")}))
    fails = rule.evaluate(_snapshot({("D", 20): (100.0, 0.05, "above_strong")}))
    assert passes.passed is True
    assert fails.passed is False


# (b) name corto: BelowSMA(...)
def test_short_name_renders_below():
    assert SMAPositionRule(20, ["W", "M"], ABOVE, side="below").name == "BelowSMA(20,W+M)"
    assert SMAPositionRule(20, ["D"], ABOVE, side="below").name == "BelowSMA(20,D)"


# (c) Evidencia con AMBOS tf aun cuando el PRIMERO falla (sin short-circuit)
def test_smarule_evidence_complete_even_when_first_tf_fails():
    snap = _snapshot({
        ("D", 20): (100.0, 0.0, "near"),           # ∉ ABOVE → falla
        ("W", 20): (100.0, 0.05, "above_strong"),  # ∈ ABOVE
    })
    result = SMAPositionRule(20, ["D", "W"], buckets_allowed=ABOVE, side="above").evaluate(snap)
    assert result.passed is False
    _assert_evidence(
        result.evidence,
        {
            "D": {20: (100.0, 0.0, "near")},
            "W": {20: (100.0, 0.05, "above_strong")},
        },
    )


# (d) buckets_allowed inválido → ValueError EN CONSTRUCCIÓN (sobre los buckets canónicos)
def test_smarule_invalid_buckets_allowed_raises_at_construction():
    with pytest.raises(ValueError, match="desconocidos"):
        SMAPositionRule(20, ["D"], buckets_allowed={"above_mild", "not_a_bucket"}, side="above")


# (d) side inválido → ValueError en construcción (vía mirror_buckets)
def test_invalid_side_raises_at_construction():
    with pytest.raises(ValueError, match="side inválido"):
        SMAPositionRule(20, ["D"], buckets_allowed=ABOVE, side="sideways")


# (e) Los 7 buckets son un buckets_allowed válido; el mirror a short sigue ⊆ BUCKETS
def test_all_seven_buckets_allowed_is_valid_both_sides():
    assert SMAPositionRule(20, ["D"], set(BUCKETS), side="above").buckets_allowed == frozenset(BUCKETS)
    assert SMAPositionRule(20, ["D"], set(BUCKETS), side="below").buckets_allowed == frozenset(BUCKETS)


# (e) name para 1 y N tf en lado largo + label custom (NotExtended-style)
def test_name_variants():
    assert SMAPositionRule(20, ["D"], ABOVE, side="above").name == "AboveSMA(20,D)"
    assert SMAPositionRule(20, ["W", "M"], ABOVE, side="above").name == "AboveSMA(20,W+M)"
    assert SMAPositionRule(
        8, ["D"], set(BUCKETS) - {"extended_above"}, side="above", label="NotExtended"
    ).name == "NotExtended(8,D)"


# (e) evaluate NO maneja fríos: sobre snapshot construido nunca toca FeatureNotReady; una
# serie ausente es KeyError (error de programación), no se silencia ni se trata como frío.
def test_evaluate_does_not_handle_cold_missing_series_is_keyerror():
    rule = SMAPositionRule(20, ["D", "W"], buckets_allowed=ABOVE, side="above")
    snap = _snapshot({("D", 20): (100.0, 0.05, "above_strong")})  # falta W:20
    with pytest.raises(KeyError):
        rule.evaluate(snap)


# required se propaga a RuleResult
def test_required_flag_propagates():
    snap = _snapshot({("D", 20): (100.0, 0.05, "above_strong")})
    result = SMAPositionRule(20, ["D"], ABOVE, side="above", required=False).evaluate(snap)
    assert result.required is False


# ---------------------------------------------------------------------------
# T4 (Etapa 6B) — NotExtended: preset (constructor con nombre) de SMAPositionRule que
# excluye el bucket favorable-extremo. Sin max_pct: el corte lo fija el bucket_thresholds.
# extended ÚNICO de la estrategia, ya aplicado al bucketizar el snapshot (supersede D4).
# ---------------------------------------------------------------------------

# (a) Largo: falla en extended_above; pasa en above_strong (justo por debajo del corte extended)
def test_notextended_long_fails_extended_passes_strong():
    rule = NotExtended(8, "D", side="above")
    assert rule.name == "NotExtended(8,D)"
    assert rule.required is True
    fails = rule.evaluate(_snapshot({("D", 8): (100.0, 0.12, "extended_above")}))
    passes = rule.evaluate(_snapshot({("D", 8): (100.0, 0.05, "above_strong")}))
    assert fails.passed is False
    assert passes.passed is True


# (a) el set permitido excluye SOLO el bucket favorable-extremo (los otros 6 pasan)
def test_notextended_long_allows_all_but_extended_above():
    rule = NotExtended(8, "D", side="above")
    assert rule.buckets_allowed == frozenset(set(BUCKETS) - {"extended_above"})


# (b) Corto: el mirror excluye extended_below; falla en extended_below, pasa en below_strong
def test_notextended_short_mirrors_to_exclude_extended_below():
    rule = NotExtended(8, "D", side="below")
    assert rule.name == "NotExtended(8,D)"  # name independiente del side (label custom)
    assert rule.buckets_allowed == frozenset(set(BUCKETS) - {"extended_below"})
    fails = rule.evaluate(_snapshot({("D", 8): (100.0, -0.12, "extended_below")}))
    passes = rule.evaluate(_snapshot({("D", 8): (100.0, -0.05, "below_strong")}))
    assert fails.passed is False
    assert passes.passed is True


# (c) el ÚNICO bucket_thresholds.extended de la estrategia mueve el corte de NotExtended
# (reemplaza al viejo test de max_pct per-regla, que ya no existe). El snapshot se construye
# con el MISMO _bucketize de producción a dos `extended`; MISMA rule, MISMA distancia (+9%):
# con extended=0.10 → above_strong (pasa); con extended=0.08 → extended_above (falla).
THRESHOLDS_LOOSE = {"near": 0.005, "mild": 0.03, "extended": 0.10}
THRESHOLDS_TIGHT = {"near": 0.01, "mild": 0.05, "extended": 0.08}


def _snapshot_at(tf, period, value, distance_pct, thresholds) -> dict:
    """Snapshot de 1 serie bucketizado por el _bucketize REAL al `thresholds` dado:
    aísla que el corte de NotExtended lo fija el `extended` del snapshot, no la rule."""
    return {tf: {period: PositionResult(value, distance_pct, _bucketize(distance_pct, thresholds))}}


def test_notextended_cut_driven_by_strategy_extended_threshold():
    rule = NotExtended(8, "D", side="above")
    snap_loose = _snapshot_at("D", 8, 100.0, 0.09, THRESHOLDS_LOOSE)  # extended=0.10
    snap_tight = _snapshot_at("D", 8, 100.0, 0.09, THRESHOLDS_TIGHT)  # extended=0.08
    assert snap_loose["D"][8].bucket == "above_strong"
    assert snap_tight["D"][8].bucket == "extended_above"
    assert rule.evaluate(snap_loose).passed is True
    assert rule.evaluate(snap_tight).passed is False


# (d) evidencia con la misma forma {tf:{period:{value,distance_pct,bucket}}} que SMAPositionRule
def test_notextended_evidence_shape():
    rule = NotExtended(8, "D", side="above")
    result = rule.evaluate(_snapshot({("D", 8): (100.0, 0.05, "above_strong")}))
    _assert_evidence(result.evidence, {"D": {8: (100.0, 0.05, "above_strong")}})


# required se propaga a través del preset (no se fuerza a True)
def test_notextended_required_flag_propagates():
    rule = NotExtended(8, "D", side="above", required=False)
    assert rule.required is False
