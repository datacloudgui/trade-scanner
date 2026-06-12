"""Tests de core/features.py (Etapa 6).

No usan AlgorithmImports — L3 es negocio puro; corren dentro de Docker sin CLR.
T1.1: contrato del dataclass PositionResult (campos, side derivado, igualdad, frozen).
T1.2: position_vs_sma — contrato de fríos (FeatureNotReady), distance_pct y delegación
en _bucketize (stubeada con monkeypatch hasta T1.3); SymbolData stub del criterio.
"""
import dataclasses
from types import SimpleNamespace

import pytest

from core.features import FeatureNotReady, PositionResult, position_vs_sma


# T1.1 — side derivado del signo de distance_pct (>= 0 → "above")
@pytest.mark.parametrize(
    "distance_pct, expected_side",
    [
        (0.05, "above"),
        (0.0, "above"),    # frontera del contrato: el cero es "above"
        (-0.0, "above"),   # -0.0 >= 0 es True: mismo lado que 0.0
        (-0.05, "below"),
    ],
)
def test_side_derives_from_distance_sign(distance_pct, expected_side):
    result = PositionResult(value=100.0, distance_pct=distance_pct, bucket="near")
    assert result.side == expected_side


# T1.1 — side no es argumento del constructor: la derivación no se puede burlar
def test_side_is_not_an_init_argument():
    with pytest.raises(TypeError):
        PositionResult(value=100.0, distance_pct=-0.02, side="above", bucket="near")


# T1.1 — comparable por igualdad para asserts directos
def test_equality_by_value():
    a = PositionResult(value=100.0, distance_pct=0.02, bucket="above_mild")
    b = PositionResult(value=100.0, distance_pct=0.02, bucket="above_mild")
    assert a == b


def test_inequality_when_any_field_differs():
    base = PositionResult(value=100.0, distance_pct=0.02, bucket="above_mild")
    assert base != PositionResult(value=101.0, distance_pct=0.02, bucket="above_mild")
    assert base != PositionResult(value=100.0, distance_pct=0.03, bucket="above_mild")
    assert base != PositionResult(value=100.0, distance_pct=0.02, bucket="near")


# T1.1 — frozen=True: inmutable tras construcción
def test_frozen_rejects_mutation():
    result = PositionResult(value=100.0, distance_pct=0.02, bucket="above_mild")
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.bucket = "near"


# --- T1.2 — position_vs_sma ---

THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}


class StubSymbolData:
    """Stub mínimo del criterio: .sma().current.value / .close() / .is_ready().

    Registra las llamadas para verificar que la feature lee la serie pedida
    y nada más (regla L3: solo lectura vía la API de SymbolData).
    """

    def __init__(self, sma_value: float, close_value: float, ready: bool = True):
        self.symbol = "STUB"
        self._sma_value = sma_value
        self._close_value = close_value
        self._ready = ready
        self.calls: list[tuple] = []

    def is_ready(self, tf: str, period: int) -> bool:
        self.calls.append(("is_ready", tf, period))
        return self._ready

    def sma(self, tf: str, period: int):
        self.calls.append(("sma", tf, period))
        return SimpleNamespace(current=SimpleNamespace(value=self._sma_value))

    def close(self, tf: str) -> float:
        self.calls.append(("close", tf))
        return self._close_value


def _stub_bucketize(monkeypatch, returns: str = "bucket_stub") -> list[tuple]:
    """Sustituye _bucketize (T1.3 pendiente) y devuelve el registro de llamadas."""
    calls: list[tuple] = []

    def fake(distance_pct, thresholds):
        calls.append((distance_pct, thresholds))
        return returns

    monkeypatch.setattr("core.features._bucketize", fake)
    return calls


# T1.2 — contrato de fríos: serie no ready → FeatureNotReady (sin tocar SMA ni close)
def test_cold_series_raises_feature_not_ready():
    sd = StubSymbolData(sma_value=100.0, close_value=105.0, ready=False)
    with pytest.raises(FeatureNotReady, match="W:20"):
        position_vs_sma(sd, "W", 20, THRESHOLDS)
    assert ("close", "W") not in sd.calls  # corta antes de leer estado caliente


# T1.2 — contrato de fríos: SMA == 0 (distancia indefinida) → FeatureNotReady
def test_zero_sma_raises_feature_not_ready():
    sd = StubSymbolData(sma_value=0.0, close_value=105.0)
    with pytest.raises(FeatureNotReady, match="D:8"):
        position_vs_sma(sd, "D", 8, THRESHOLDS)


# T1.2 — distance_pct = (close - sma) / sma con tolerancia 1e-9; value = SMA usada
@pytest.mark.parametrize(
    "close, expected_distance",
    [(105.0, 0.05), (95.0, -0.05), (100.0, 0.0)],
)
def test_distance_pct_formula(monkeypatch, close, expected_distance):
    _stub_bucketize(monkeypatch)
    sd = StubSymbolData(sma_value=100.0, close_value=close)
    result = position_vs_sma(sd, "D", 20, THRESHOLDS)
    assert result.distance_pct == pytest.approx(expected_distance, abs=1e-9)
    assert result.value == 100.0  # la SMA usada, no el close


# T1.2 — el bucket viene de _bucketize (con la distancia y los thresholds recibidos),
# y la feature lee exactamente la serie (tf, period) pedida
def test_delegates_bucket_and_reads_declared_series(monkeypatch):
    bucketize_calls = _stub_bucketize(monkeypatch, returns="above_mild")
    sd = StubSymbolData(sma_value=200.0, close_value=204.0)
    result = position_vs_sma(sd, "W", 20, THRESHOLDS)
    assert result == PositionResult(value=200.0, distance_pct=0.02, bucket="above_mild")
    assert bucketize_calls == [(pytest.approx(0.02, abs=1e-9), THRESHOLDS)]
    assert sd.calls == [("is_ready", "W", 20), ("sma", "W", 20), ("close", "W")]
