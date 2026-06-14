"""Tests de core/features.py (Etapa 6).

No usan AlgorithmImports — L3 es negocio puro; corren dentro de Docker sin CLR.
T1.1: contrato del dataclass PositionResult (campos, side derivado, igualdad, frozen).
T1.2: position_vs_sma — contrato de fríos (FeatureNotReady), distance_pct y delegación
en _bucketize (stubeada con monkeypatch); SymbolData stub del criterio.
T1.3: _bucketize — 7 buckets + 6 cortes exactos vía position_vs_sma, no-hardcodeo con
segundo set de thresholds, y ownership de frontera con epsilon + espejo (directo).
T2.2: resolve_bucket_thresholds — 3 rutas de merge (global / override / defaults),
always-3-keys y validación de orden 0 < near < mild < extended.
"""
import dataclasses
from types import SimpleNamespace

import pytest

from core.features import (
    BUCKETS,
    DEFAULT_BUCKET_THRESHOLDS,
    FeatureNotReady,
    PositionResult,
    _bucketize,
    build_position_snapshot,
    position_vs_sma,
    resolve_bucket_thresholds,
    snapshot_evidence,
)


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


# --- T1.3 — _bucketize: tabla de 7 buckets, fronteras exactas y no-hardcodeo ---

NEAR, MILD, EXT = THRESHOLDS["near"], THRESHOLDS["mild"], THRESHOLDS["extended"]
EPS = 1e-12  # un ulp grande: inalcanzable vía división real, perfecto para frontera


# T1.3 — los 7 buckets (interiores) y los 6 cortes exactos, vía position_vs_sma
# con SMA=100 (cierres elegidos para que (close-100)/100 caiga exacto en el corte)
@pytest.mark.parametrize(
    "close, expected_distance, expected_bucket",
    [
        # interiores de los 7 buckets
        (112.0, 0.12, "extended_above"),
        (105.0, 0.05, "above_strong"),
        (101.0, 0.01, "above_mild"),
        (100.0, 0.0, "near"),
        (99.0, -0.01, "below_mild"),
        (95.0, -0.05, "below_strong"),
        (88.0, -0.12, "extended_below"),
        # 6 cortes exactos: la frontera pertenece al bucket más alejado de la SMA
        (110.0, 0.10, "extended_above"),   # +extended: >= inclusivo
        (103.0, 0.03, "above_strong"),     # +mild
        (100.5, 0.005, "above_mild"),      # +near
        (99.5, -0.005, "below_mild"),      # −near: <= inclusivo (espejo)
        (97.0, -0.03, "below_strong"),     # −mild
        (90.0, -0.10, "extended_below"),   # −extended
    ],
)
def test_seven_buckets_and_six_exact_cuts(close, expected_distance, expected_bucket):
    result = position_vs_sma(StubSymbolData(100.0, close), "D", 20, THRESHOLDS)
    assert result.bucket == expected_bucket
    assert result.distance_pct == pytest.approx(expected_distance, abs=1e-9)


# T1.3 — no-hardcodeo: un segundo set de thresholds mueve los cortes
CUSTOM_THRESHOLDS = {"near": 0.01, "mild": 0.05, "extended": 0.08}


@pytest.mark.parametrize(
    "close, default_bucket, custom_bucket",
    [
        (109.0, "above_strong", "extended_above"),  # +9%: bajo 0.10, sobre 0.08
        (108.0, "above_strong", "extended_above"),  # corte exacto +extended custom
        (104.0, "above_strong", "above_mild"),      # +4%: mild sube 0.03 → 0.05
        (100.7, "above_mild", "near"),              # +0.7%: near sube 0.005 → 0.01
        (99.3, "below_mild", "near"),               # espejo de +0.7%
        (92.0, "below_strong", "extended_below"),   # corte exacto −extended custom
    ],
)
def test_second_threshold_set_moves_the_cuts(close, default_bucket, custom_bucket):
    sd = StubSymbolData(100.0, close)
    assert position_vs_sma(sd, "D", 20, THRESHOLDS).bucket == default_bucket
    assert position_vs_sma(sd, "D", 20, CUSTOM_THRESHOLDS).bucket == custom_bucket


# T1.3 — ownership de cada frontera, directo sobre _bucketize: el valor exacto cae
# en el bucket más alejado de la SMA; un epsilon hacia el centro lo devuelve al
# bucket interior. Seguro contra off-by-epsilon (< vs <=) en refactors futuros.
@pytest.mark.parametrize(
    "distance, expected_bucket",
    [
        (NEAR - EPS, "near"),           (NEAR, "above_mild"),
        (MILD - EPS, "above_mild"),     (MILD, "above_strong"),
        (EXT - EPS, "above_strong"),    (EXT, "extended_above"),
        (-NEAR + EPS, "near"),          (-NEAR, "below_mild"),
        (-MILD + EPS, "below_mild"),    (-MILD, "below_strong"),
        (-EXT + EPS, "below_strong"),   (-EXT, "extended_below"),
    ],
)
def test_bucketize_boundary_ownership_with_epsilon(distance, expected_bucket):
    assert _bucketize(distance, THRESHOLDS) == expected_bucket


# T1.3 — propiedad espejo: bucketize(-d) es el reflejo de bucketize(d) para todo d
# (vale también en los cortes porque "frontera → bucket más alejado" es simétrico)
def test_bucketize_mirror_symmetry():
    mirror = {
        "extended_above": "extended_below",
        "above_strong": "below_strong",
        "above_mild": "below_mild",
        "near": "near",
    }
    for d in (0.0, 0.002, NEAR, 0.01, MILD, 0.05, EXT, 0.12):
        above = _bucketize(d, THRESHOLDS)
        assert above in BUCKETS
        assert _bucketize(-d, THRESHOLDS) == mirror[above], f"espejo roto en d={d}"


# ---------------------------------------------------------------------------
# T2.2 — resolve_bucket_thresholds: 3 rutas de merge + always-3-keys + validación
# ---------------------------------------------------------------------------

# Ruta (a): solo global presente (sin override de estrategia) → usa el global tal cual.
def test_resolve_uses_global_when_no_strategy_override():
    config = {
        "bucket_thresholds": {"near": 0.01, "mild": 0.04, "extended": 0.09},
        "strategies": {"swing_eod": {"universe": "x"}},  # sin bucket_thresholds
    }
    assert resolve_bucket_thresholds(config, "swing_eod") == {
        "near": 0.01, "mild": 0.04, "extended": 0.09,
    }


# Ruta (b): override de estrategia gana CLAVE-A-CLAVE; las ausentes caen al global.
def test_resolve_strategy_override_wins_key_by_key():
    config = {
        "bucket_thresholds": {"near": 0.005, "mild": 0.03, "extended": 0.10},
        "strategies": {"swing_eod": {"bucket_thresholds": {"extended": 0.08}}},
    }
    # solo 'extended' viene del override; near/mild del global (merge poco profundo)
    assert resolve_bucket_thresholds(config, "swing_eod") == {
        "near": 0.005, "mild": 0.03, "extended": 0.08,
    }


# Ruta (c): ausencia total de bucket_thresholds → defaults del código.
def test_resolve_falls_back_to_code_defaults():
    config = {"strategies": {"swing_eod": {"universe": "x"}}}
    resolved = resolve_bucket_thresholds(config, "swing_eod")
    assert resolved == {"near": 0.005, "mild": 0.03, "extended": 0.10}
    assert resolved == DEFAULT_BUCKET_THRESHOLDS
    assert resolved is not DEFAULT_BUCKET_THRESHOLDS  # copia, no alias mutable


# Estrategia inexistente → sin override → cae al global.
def test_resolve_unknown_strategy_uses_global():
    config = {
        "bucket_thresholds": {"near": 0.01, "mild": 0.04, "extended": 0.09},
        "strategies": {},
    }
    assert resolve_bucket_thresholds(config, "nonexistent") == {
        "near": 0.01, "mild": 0.04, "extended": 0.09,
    }


# Merge parcial en CUALQUIER ruta → el dict resuelto SIEMPRE trae exactamente las 3 claves.
@pytest.mark.parametrize(
    "config",
    [
        {},                                                          # nada → defaults
        {"bucket_thresholds": {"near": 0.001}},                      # global parcial
        {"strategies": {"s": {"bucket_thresholds": {"mild": 0.04}}}},  # override parcial
    ],
)
def test_resolve_always_returns_three_keys(config):
    resolved = resolve_bucket_thresholds(config, "s")
    assert set(resolved) == {"near", "mild", "extended"}


# Validación: el dict RESUELTO debe cumplir 0 < near < mild < extended (entrada de config).
@pytest.mark.parametrize(
    "bad",
    [
        {"near": 0.05, "mild": 0.03, "extended": 0.10},   # near > mild
        {"near": 0.005, "mild": 0.10, "extended": 0.03},  # mild > extended
        {"near": 0.0, "mild": 0.03, "extended": 0.10},    # near no es > 0
        {"near": -0.01, "mild": 0.03, "extended": 0.10},  # near negativo
        {"near": 0.03, "mild": 0.03, "extended": 0.10},   # near == mild (no es estricto)
    ],
)
def test_resolve_rejects_disordered_thresholds(bad):
    with pytest.raises(ValueError):
        resolve_bucket_thresholds({"bucket_thresholds": bad}, "swing_eod")


# La validación corre sobre el resultado del MERGE: un override válido-en-aislamiento
# que rompe el orden contra el global resto se rechaza igual.
def test_resolve_override_can_trigger_validation():
    config = {
        "bucket_thresholds": {"near": 0.005, "mild": 0.03, "extended": 0.10},
        "strategies": {"swing_eod": {"bucket_thresholds": {"near": 0.05}}},  # near > mild tras merge
    }
    with pytest.raises(ValueError):
        resolve_bucket_thresholds(config, "swing_eod")


# ---------------------------------------------------------------------------
# T1.1 (Etapa 6B) — build_position_snapshot: snapshot único {tf:{period:PositionResult}}
# computado una vez por serie, propaga frío y solo cubre las series referenciadas.
# ---------------------------------------------------------------------------

class MultiSeriesStub:
    """SymbolData sintético multi-(tf,period) para el builder del snapshot.

    `close(tf)` depende solo del tf (como la API real); `sma`/`is_ready` son
    per-(tf,period). Registra cada lectura para verificar que el builder computa
    una serie a lo sumo una vez y que NO toca series fuera de las pedidas.
    """

    def __init__(self, closes: dict, smas: dict, cold=frozenset()):
        self.symbol = "STUB"
        self._closes = closes          # {tf: close_value}
        self._smas = smas              # {(tf, period): sma_value}
        self._cold = set(cold)         # {(tf, period)} not ready
        self.calls: list[tuple] = []

    def is_ready(self, tf, period) -> bool:
        self.calls.append(("is_ready", tf, period))
        return (tf, period) not in self._cold

    def sma(self, tf, period):
        self.calls.append(("sma", tf, period))
        return SimpleNamespace(current=SimpleNamespace(value=self._smas[(tf, period)]))

    def close(self, tf):
        self.calls.append(("close", tf))
        return self._closes[tf]


# (a) forma exacta {tf:{period:PositionResult}} con value/distance_pct/bucket esperados
def test_snapshot_shape_and_values():
    sd = MultiSeriesStub(
        closes={"W": 105.0, "M": 102.0, "D": 101.0},
        smas={("W", 20): 100.0, ("M", 20): 100.0, ("D", 8): 100.0},
    )
    snapshot = build_position_snapshot(sd, [("W", 20), ("M", 20), ("D", 8)], THRESHOLDS)

    assert set(snapshot) == {"W", "M", "D"}
    assert set(snapshot["W"]) == {20} and set(snapshot["M"]) == {20} and set(snapshot["D"]) == {8}
    expected = {
        ("W", 20): (100.0, 0.05, "above_strong"),
        ("M", 20): (100.0, 0.02, "above_mild"),
        ("D", 8): (100.0, 0.01, "above_mild"),
    }
    for (tf, period), (value, dist, bucket) in expected.items():
        pos = snapshot[tf][period]
        assert isinstance(pos, PositionResult)
        assert pos.value == value
        assert pos.distance_pct == pytest.approx(dist, abs=1e-9)
        assert pos.bucket == bucket


# (a) position_vs_sma se invoca UNA vez por serie, con args correctos y en orden
def test_each_series_computed_exactly_once(monkeypatch):
    calls: list[tuple] = []

    def spy(sd, tf, period, thresholds):
        calls.append((sd, tf, period, thresholds))
        return f"pos:{tf}:{period}"  # sentinela: prueba el agrupamiento sin recomputar

    monkeypatch.setattr("core.features.position_vs_sma", spy)
    sd = object()
    series = [("W", 20), ("M", 20), ("D", 8)]
    snapshot = build_position_snapshot(sd, series, THRESHOLDS)

    assert snapshot == {"W": {20: "pos:W:20"}, "M": {20: "pos:M:20"}, "D": {8: "pos:D:8"}}
    assert calls == [(sd, "W", 20, THRESHOLDS), (sd, "M", 20, THRESHOLDS), (sd, "D", 8, THRESHOLDS)]


# (a) dos periods sobre el MISMO tf anidan bajo la misma clave tf (dict anidado plano)
def test_multiple_periods_same_tf_nest_under_one_tf_key():
    sd = MultiSeriesStub(
        closes={"D": 101.0},
        smas={("D", 8): 100.0, ("D", 20): 100.0},
    )
    snapshot = build_position_snapshot(sd, [("D", 8), ("D", 20)], THRESHOLDS)
    assert set(snapshot) == {"D"}
    assert set(snapshot["D"]) == {8, 20}


# (b) serie fría en `series` → FeatureNotReady que DETIENE la construcción (símbolo+serie)
def test_cold_series_halts_and_propagates():
    sd = MultiSeriesStub(
        closes={"W": 105.0, "M": 102.0},
        smas={("W", 20): 100.0, ("M", 20): 100.0},
        cold={("W", 20)},
    )
    with pytest.raises(FeatureNotReady, match=r"STUB.*W:20"):
        build_position_snapshot(sd, [("W", 20), ("M", 20)], THRESHOLDS)
    # detiene: la serie posterior M:20 nunca se consultó (no se silencia ni continúa)
    assert ("is_ready", "M", 20) not in sd.calls


# (c) serie declarada-pero-no-referenciada (⊄ series): ni se computa ni excluye el símbolo
def test_unreferenced_declared_series_not_computed_nor_excluding():
    # ("M",200) existe en el stub (declarada) y está FRÍA: si el builder la computara,
    # levantaría FeatureNotReady. Como NO está en `series`, ni se mira ni rompe el snapshot.
    sd = MultiSeriesStub(
        closes={"W": 105.0, "M": 102.0},
        smas={("W", 20): 100.0, ("M", 20): 100.0, ("M", 200): 0.0},
        cold={("M", 200)},
    )
    snapshot = build_position_snapshot(sd, [("W", 20), ("M", 20)], THRESHOLDS)  # no levanta

    assert set(snapshot["M"]) == {20}                 # M:200 no aparece en el snapshot
    assert ("is_ready", "M", 200) not in sd.calls     # ni siquiera se consultó su frialdad


# ---------------------------------------------------------------------------
# T1.2 (Etapa 6B) — snapshot_evidence: proyección pura {tf:{period:{value,distance_pct,bucket}}}
# sobre un subconjunto de series, sin `side` y sin recompute.
# ---------------------------------------------------------------------------

def _assert_evidence(evidence: dict, expected: dict) -> None:
    """Forma exacta `{tf:{period:{value,distance_pct,bucket}}}` (sin `side`); claves de
    cada nivel idénticas; value/bucket exactos; distance_pct con tolerancia 1e-9.

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


def _sample_snapshot() -> dict:
    """Snapshot armado a mano (sin stub ni builder): aísla la proyección pura."""
    return {
        "W": {20: PositionResult(value=100.0, distance_pct=0.05, bucket="above_strong")},
        "M": {20: PositionResult(value=200.0, distance_pct=-0.02, bucket="below_mild")},
        "D": {
            8: PositionResult(value=50.0, distance_pct=0.01, bucket="above_mild"),
            20: PositionResult(value=48.0, distance_pct=0.04, bucket="above_strong"),
        },
    }


# (d) esquema exacto para un SUBCONJUNTO: M (no pedida) y D:20 (no pedida) quedan fuera
def test_snapshot_evidence_projects_exact_schema_for_subset():
    evidence = snapshot_evidence(_sample_snapshot(), [("W", 20), ("D", 8)])
    _assert_evidence(
        evidence,
        {
            "W": {20: (100.0, 0.05, "above_strong")},
            "D": {8: (50.0, 0.01, "above_mild")},
        },
    )


# (d) descarta `side` aunque el PositionResult de origen lo tenga (below → side="below")
def test_snapshot_evidence_drops_side():
    snap = {"M": {20: PositionResult(value=200.0, distance_pct=-0.02, bucket="below_mild")}}
    assert snap["M"][20].side == "below"  # el origen sí trae side...
    entry = snapshot_evidence(snap, [("M", 20)])["M"][20]
    assert "side" not in entry            # ...pero la evidencia no
    assert entry == {"value": 200.0, "distance_pct": -0.02, "bucket": "below_mild"}


# (d) dos `period` del mismo `tf` anidan bajo una sola clave `tf`
def test_snapshot_evidence_multiple_periods_same_tf():
    evidence = snapshot_evidence(_sample_snapshot(), [("D", 8), ("D", 20)])
    _assert_evidence(
        evidence,
        {"D": {8: (50.0, 0.01, "above_mild"), 20: (48.0, 0.04, "above_strong")}},
    )


# (d) proyección de un snapshot REAL (vía builder): forma idéntica al dict inline que hoy
# arma AboveSMA.evaluate (rules.py:69-75) y que T3 reemplaza por esta función
def test_snapshot_evidence_reproduces_builder_snapshot_schema():
    sd = MultiSeriesStub(
        closes={"W": 105.0, "M": 102.0},
        smas={("W", 20): 100.0, ("M", 20): 100.0},
    )
    snap = build_position_snapshot(sd, [("W", 20), ("M", 20)], THRESHOLDS)
    evidence = snapshot_evidence(snap, [("W", 20), ("M", 20)])
    _assert_evidence(
        evidence,
        {
            "W": {20: (100.0, 0.05, "above_strong")},
            "M": {20: (100.0, 0.02, "above_mild")},
        },
    )
