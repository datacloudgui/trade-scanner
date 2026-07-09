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
import itertools
from types import SimpleNamespace

import pytest

from core.features import (
    BUCKETS,
    DEFAULT_BUCKET_THRESHOLDS,
    SIDE_BY_DIRECTION,
    FeatureNotReady,
    PositionResult,
    _bucketize,
    _MIRROR,
    build_position_snapshot,
    day_change_pct,
    mirror_buckets,
    position_vs_sma,
    reference_price,
    resolve_bucket_thresholds,
    resolve_filters,
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


# ---------------------------------------------------------------------------
# T1.1 (Etapa 7) — reference_price: precio único "ahora" = working bar, o cierre
# diario consolidado (= ayer) como fallback sin working bar (premercado, C2).
# ---------------------------------------------------------------------------

class ReferencePriceStub:
    """Stub mínimo del criterio: `.working_bar` (con `.close`) y `.close("D")`.

    `working_close=None` modela "sin working bar" (premercado / día sin trades).
    Registra las llamadas a `close` para verificar que el cierre diario solo se
    consulta en el fallback (no cuando hay working bar).
    """

    def __init__(self, working_close, daily_close):
        self.symbol = "STUB"
        self.working_bar = (
            None if working_close is None else SimpleNamespace(close=working_close)
        )
        self._daily_close = daily_close
        self.calls: list[str] = []

    def close(self, tf: str):
        self.calls.append(tf)
        return self._daily_close


# (a) hay working bar → usa working_bar.close y NO consulta el cierre diario
def test_reference_price_uses_working_bar_when_present():
    sd = ReferencePriceStub(working_close=104.5, daily_close=100.0)
    price = reference_price(sd)
    assert price == 104.5
    assert isinstance(price, float)
    assert sd.calls == []  # con working bar no toca el cierre consolidado


# (a) sin working bar (None) → fallback al cierre diario consolidado (= ayer, C2)
def test_reference_price_falls_back_to_daily_close_without_working_bar():
    sd = ReferencePriceStub(working_close=None, daily_close=100.0)
    price = reference_price(sd)
    assert price == 100.0
    assert sd.calls == ["D"]  # leyó el cierre del timeframe diario


# float() normaliza el decimal de C# del working bar (int → float prueba el cast)
def test_reference_price_casts_working_bar_close_to_float():
    sd = ReferencePriceStub(working_close=99, daily_close=100.0)
    price = reference_price(sd)
    assert price == 99.0
    assert isinstance(price, float)


# ---------------------------------------------------------------------------
# T2.1 (Etapa 7) — day_change_pct: (reference_price − close("D")) / close("D"),
# score del ranking top_n. close("D")=ayer al scan (A.2); FeatureNotReady si el
# cierre consolidado no está (AttributeError) o es 0.
# ---------------------------------------------------------------------------

class DayChangeStub:
    """Stub para day_change_pct: `.close("D")` (cierre de ayer) y `.working_bar` (hoy).

    `working_close=None` modela "sin working bar" (reference_price cae a close("D")).
    `daily_raises=True` simula el cierre consolidado no disponible: barra consolidada
    None → AttributeError al leer `.close`, como la API real de SymbolData.
    """

    def __init__(self, daily_close, working_close, daily_raises: bool = False):
        self.symbol = "STUB"
        self._daily_close = daily_close
        self._daily_raises = daily_raises
        self.working_bar = (
            None if working_close is None else SimpleNamespace(close=working_close)
        )

    def close(self, tf: str) -> float:
        assert tf == "D"  # day_change solo mira el cierre diario consolidado
        if self._daily_raises:
            raise AttributeError("'NoneType' object has no attribute 'close'")
        return self._daily_close


# (a) con working bar: (c1 − c0) / c0
@pytest.mark.parametrize(
    "c0, c1, expected",
    [(100.0, 105.0, 0.05), (100.0, 95.0, -0.05), (100.0, 100.0, 0.0), (50.0, 60.0, 0.2)],
)
def test_day_change_with_working_bar(c0, c1, expected):
    sd = DayChangeStub(daily_close=c0, working_close=c1)
    assert day_change_pct(sd) == pytest.approx(expected, abs=1e-9)


# (a) sin working bar → reference_price = close("D") ⇒ cambio 0 (degenerado documentado)
def test_day_change_without_working_bar_is_zero():
    sd = DayChangeStub(daily_close=100.0, working_close=None)
    assert day_change_pct(sd) == 0.0


# (b) cierre consolidado no disponible (AttributeError) → FeatureNotReady, antes de reference_price
def test_day_change_missing_daily_close_raises():
    sd = DayChangeStub(daily_close=None, working_close=105.0, daily_raises=True)
    with pytest.raises(FeatureNotReady, match="no disponible"):
        day_change_pct(sd)


# (b) cierre consolidado == 0 → FeatureNotReady (sin base para el cambio; evita /0)
def test_day_change_zero_daily_close_raises():
    sd = DayChangeStub(daily_close=0.0, working_close=105.0)
    with pytest.raises(FeatureNotReady, match="== 0"):
        day_change_pct(sd)


# --- T1.2 — position_vs_sma ---

THRESHOLDS = {"near": 0.005, "mild": 0.03, "extended": 0.10}


class StubSymbolData:
    """Stub mínimo del nuevo contrato (T1.2): .sma().current.value / .is_ready().

    El precio se INYECTA (A.1): `position_vs_sma` ya NO lee el cierre, así que `close()`
    levanta AssertionError para blindar en runtime que la feature no lo toca. Registra
    las llamadas para verificar que lee solo la serie pedida (regla L3: solo lectura).
    """

    def __init__(self, sma_value: float, ready: bool = True):
        self.symbol = "STUB"
        self._sma_value = sma_value
        self._ready = ready
        self.calls: list[tuple] = []

    def is_ready(self, tf: str, period: int) -> bool:
        self.calls.append(("is_ready", tf, period))
        return self._ready

    def sma(self, tf: str, period: int):
        self.calls.append(("sma", tf, period))
        return SimpleNamespace(current=SimpleNamespace(value=self._sma_value))

    def close(self, tf: str) -> float:
        raise AssertionError(
            "position_vs_sma no debe leer close() tras T1.2 (precio inyectado)"
        )


def _stub_bucketize(monkeypatch, returns: str = "bucket_stub") -> list[tuple]:
    """Sustituye _bucketize (T1.3 pendiente) y devuelve el registro de llamadas."""
    calls: list[tuple] = []

    def fake(distance_pct, thresholds):
        calls.append((distance_pct, thresholds))
        return returns

    monkeypatch.setattr("core.features._bucketize", fake)
    return calls


# T1.2 — contrato de fríos: serie no ready → FeatureNotReady (corta antes de leer SMA)
def test_cold_series_raises_feature_not_ready():
    sd = StubSymbolData(sma_value=100.0, ready=False)
    with pytest.raises(FeatureNotReady, match="W:20"):
        position_vs_sma(sd, "W", 20, THRESHOLDS, price=105.0)
    assert sd.calls == [("is_ready", "W", 20)]  # corta tras is_ready, sin leer la SMA


# T1.2 — contrato de fríos: SMA == 0 (distancia indefinida) → FeatureNotReady
def test_zero_sma_raises_feature_not_ready():
    sd = StubSymbolData(sma_value=0.0)
    with pytest.raises(FeatureNotReady, match="D:8"):
        position_vs_sma(sd, "D", 8, THRESHOLDS, price=105.0)


# T1.2 (b) — la feature NO lee el cierre: el precio se inyecta (A.1). El stub levanta
# si se llamara close(); además se verifica vía el registro de llamadas.
def test_position_vs_sma_does_not_read_close(monkeypatch):
    _stub_bucketize(monkeypatch)
    sd = StubSymbolData(sma_value=100.0)
    position_vs_sma(sd, "D", 20, THRESHOLDS, price=110.0)  # no levanta (no toca close)
    assert all(call[0] != "close" for call in sd.calls)


# T1.2 — distance_pct = (price - sma) / sma con tolerancia 1e-9; value = SMA usada
@pytest.mark.parametrize(
    "price, expected_distance",
    [(105.0, 0.05), (95.0, -0.05), (100.0, 0.0)],
)
def test_distance_pct_formula(monkeypatch, price, expected_distance):
    _stub_bucketize(monkeypatch)
    sd = StubSymbolData(sma_value=100.0)
    result = position_vs_sma(sd, "D", 20, THRESHOLDS, price=price)
    assert result.distance_pct == pytest.approx(expected_distance, abs=1e-9)
    assert result.value == 100.0  # la SMA usada, no el precio


# T1.2 — el bucket viene de _bucketize (con la distancia y los thresholds recibidos),
# y la feature lee exactamente la serie (tf, period) pedida (ya sin leer close)
def test_delegates_bucket_and_reads_declared_series(monkeypatch):
    bucketize_calls = _stub_bucketize(monkeypatch, returns="above_mild")
    sd = StubSymbolData(sma_value=200.0)
    result = position_vs_sma(sd, "W", 20, THRESHOLDS, price=204.0)
    assert result == PositionResult(value=200.0, distance_pct=0.02, bucket="above_mild")
    assert bucketize_calls == [(pytest.approx(0.02, abs=1e-9), THRESHOLDS)]
    assert sd.calls == [("is_ready", "W", 20), ("sma", "W", 20)]  # ya NO ("close", "W")


# --- T1.3 — _bucketize: tabla de 7 buckets, fronteras exactas y no-hardcodeo ---

NEAR, MILD, EXT = THRESHOLDS["near"], THRESHOLDS["mild"], THRESHOLDS["extended"]
EPS = 1e-12  # un ulp grande: inalcanzable vía división real, perfecto para frontera


# T1.3 — los 7 buckets (interiores) y los 6 cortes exactos, vía position_vs_sma
# con SMA=100 (precios elegidos para que (price-100)/100 caiga exacto en el corte)
@pytest.mark.parametrize(
    "price, expected_distance, expected_bucket",
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
def test_seven_buckets_and_six_exact_cuts(price, expected_distance, expected_bucket):
    result = position_vs_sma(StubSymbolData(100.0), "D", 20, THRESHOLDS, price=price)
    assert result.bucket == expected_bucket
    assert result.distance_pct == pytest.approx(expected_distance, abs=1e-9)


# T1.3 — no-hardcodeo: un segundo set de thresholds mueve los cortes
CUSTOM_THRESHOLDS = {"near": 0.01, "mild": 0.05, "extended": 0.08}


@pytest.mark.parametrize(
    "price, default_bucket, custom_bucket",
    [
        (109.0, "above_strong", "extended_above"),  # +9%: bajo 0.10, sobre 0.08
        (108.0, "above_strong", "extended_above"),  # corte exacto +extended custom
        (104.0, "above_strong", "above_mild"),      # +4%: mild sube 0.03 → 0.05
        (100.7, "above_mild", "near"),              # +0.7%: near sube 0.005 → 0.01
        (99.3, "below_mild", "near"),               # espejo de +0.7%
        (92.0, "below_strong", "extended_below"),   # corte exacto −extended custom
    ],
)
def test_second_threshold_set_moves_the_cuts(price, default_bucket, custom_bucket):
    sd = StubSymbolData(100.0)
    assert position_vs_sma(sd, "D", 20, THRESHOLDS, price=price).bucket == default_bucket
    assert position_vs_sma(sd, "D", 20, CUSTOM_THRESHOLDS, price=price).bucket == custom_bucket


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


# ---------------------------------------------------------------------------
# #19 (triaje E1–E8) — config malformada (ObjectStore editable) debe caer en ValueError
# claro: mapping validado, valores casteados a float, bool/NaN/inf rechazados.
# ---------------------------------------------------------------------------

# strings numéricos de un JSON editado a mano se toleran casteando a float
def test_resolve_casts_numeric_strings_to_float():
    config = {"bucket_thresholds": {"near": "0.005", "mild": "0.03", "extended": "0.10"}}
    resolved = resolve_bucket_thresholds(config, "swing_eod")
    assert resolved == {"near": 0.005, "mild": 0.03, "extended": 0.10}
    assert all(isinstance(v, float) for v in resolved.values())


@pytest.mark.parametrize(
    "bad_value",
    [True, False, "abc", None, [0.005], {"x": 1}, float("nan"), float("inf"), "-inf"],
)
def test_resolve_rejects_non_numeric_bool_nan_inf(bad_value):
    config = {"bucket_thresholds": {"near": bad_value, "mild": 0.03, "extended": 0.10}}
    with pytest.raises(ValueError, match="near"):
        resolve_bucket_thresholds(config, "swing_eod")


# bucket_thresholds truthy pero no-dict (global o de estrategia) → ValueError, no AttributeError
@pytest.mark.parametrize("bad_block", [[0.005, 0.03], "0.005", 42])
def test_resolve_rejects_non_mapping_thresholds_block(bad_block):
    with pytest.raises(ValueError, match="bucket_thresholds"):
        resolve_bucket_thresholds({"bucket_thresholds": bad_block}, "swing_eod")
    with pytest.raises(ValueError, match="bucket_thresholds"):
        resolve_bucket_thresholds(
            {"strategies": {"swing_eod": {"bucket_thresholds": bad_block}}}, "swing_eod"
        )


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
# R2 (Etapa 10) — resolve_filters: buckets_allowed por (tf, period) desde config `filters`.
# ---------------------------------------------------------------------------

# ausente/None → {} (retrocompatible: cada rule usa su default del código)
def test_resolve_filters_absent_returns_empty_dict():
    assert resolve_filters({}, "swing_eod") == {}
    assert resolve_filters({"strategies": {"swing_eod": {}}}, "swing_eod") == {}
    assert (
        resolve_filters({"strategies": {"swing_eod": {"filters": None}}}, "swing_eod") == {}
    )


# parsea "TF:period" → (tf, period) y castea la lista de buckets a frozenset
def test_resolve_filters_parses_keys_and_casts_to_frozenset():
    config = {
        "strategies": {
            "swing_eod": {
                "filters": {
                    "W:8": ["near"],
                    "W:20": ["near", "above_mild"],
                    "D:20": ["above_mild", "above_strong", "extended_above"],
                }
            }
        }
    }
    resolved = resolve_filters(config, "swing_eod")
    assert resolved == {
        ("W", 8): frozenset({"near"}),
        ("W", 20): frozenset({"near", "above_mild"}),
        ("D", 20): frozenset({"above_mild", "above_strong", "extended_above"}),
    }
    assert isinstance(resolved[("W", 8)], frozenset)


# una estrategia sin bloque filters (o distinta de la pedida) no contamina el resultado
def test_resolve_filters_scoped_to_strategy_name():
    config = {
        "strategies": {
            "swing_eod": {"filters": {"D:20": ["near"]}},
            "market_close": {},
        }
    }
    assert resolve_filters(config, "market_close") == {}
    assert resolve_filters(config, "nonexistent") == {}


# buckets desconocidos (fuera de BUCKETS) → ValueError claro, no KeyError silencioso aguas abajo
def test_resolve_filters_rejects_unknown_bucket():
    config = {"strategies": {"swing_eod": {"filters": {"D:20": ["not_a_bucket"]}}}}
    with pytest.raises(ValueError, match="not_a_bucket"):
        resolve_filters(config, "swing_eod")


# clave mal formada ("sin ':'", tf vacío, period no numérico) → ValueError claro
@pytest.mark.parametrize("bad_key", ["D20", ":20", "D:", "D:veinte", "D:20:30"])
def test_resolve_filters_rejects_malformed_key(bad_key):
    config = {"strategies": {"swing_eod": {"filters": {bad_key: ["near"]}}}}
    with pytest.raises(ValueError, match="clave inválida"):
        resolve_filters(config, "swing_eod")


# filters truthy pero no-dict (p. ej. una lista) → ValueError, no AttributeError
@pytest.mark.parametrize("bad_block", [["D:20"], "D:20", 42])
def test_resolve_filters_rejects_non_mapping_block(bad_block):
    config = {"strategies": {"swing_eod": {"filters": bad_block}}}
    with pytest.raises(ValueError, match="filters"):
        resolve_filters(config, "swing_eod")


# el valor de una clave debe ser una lista (no un string suelto ni un set)
def test_resolve_filters_rejects_non_list_value():
    config = {"strategies": {"swing_eod": {"filters": {"D:20": "near"}}}}
    with pytest.raises(ValueError, match="lista de"):
        resolve_filters(config, "swing_eod")


# ---------------------------------------------------------------------------
# T1.1 (Etapa 6B) — build_position_snapshot: snapshot único {tf:{period:PositionResult}}
# computado una vez por serie, propaga frío y solo cubre las series referenciadas.
# ---------------------------------------------------------------------------

class MultiSeriesStub:
    """SymbolData sintético multi-(tf,period) para el builder del snapshot.

    `working_bar.close` es el precio único "ahora" que el builder inyecta a las 3 SMAs
    (A.1/A.2: `reference_price` lo lee una vez); `sma`/`is_ready` son per-(tf,period).
    `close()` levanta: con working bar presente el fallback de reference_price no se usa.
    Registra cada lectura para verificar que el builder computa una serie a lo sumo una
    vez y que NO toca series fuera de las pedidas.
    """

    def __init__(self, price: float, smas: dict, cold=frozenset()):
        self.symbol = "STUB"
        self.working_bar = SimpleNamespace(close=price)  # precio único "ahora"
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
        raise AssertionError(
            "build_position_snapshot no debe leer close() con working bar presente"
        )


# (a) forma exacta {tf:{period:PositionResult}} con value/distance_pct/bucket esperados,
# con UN solo precio (working bar) comparado contra las 3 SMAs (A.1)
def test_snapshot_shape_and_values():
    sd = MultiSeriesStub(
        price=105.0,
        smas={("W", 20): 100.0, ("M", 20): 105.0, ("D", 8): 120.0},
    )
    snapshot = build_position_snapshot(sd, [("W", 20), ("M", 20), ("D", 8)], THRESHOLDS)

    assert set(snapshot) == {"W", "M", "D"}
    assert set(snapshot["W"]) == {20} and set(snapshot["M"]) == {20} and set(snapshot["D"]) == {8}
    expected = {
        ("W", 20): (100.0, 0.05, "above_strong"),    # 105 vs 100
        ("M", 20): (105.0, 0.0, "near"),             # 105 vs 105
        ("D", 8): (120.0, -0.125, "extended_below"),  # 105 vs 120
    }
    for (tf, period), (value, dist, bucket) in expected.items():
        pos = snapshot[tf][period]
        assert isinstance(pos, PositionResult)
        assert pos.value == value
        assert pos.distance_pct == pytest.approx(dist, abs=1e-9)
        assert pos.bucket == bucket


# (c) precio único: las 3 SMAs se comparan contra el MISMO precio (working bar) y la
# evidencia es internamente consistente — value·(1+distance_pct) reconstruye el precio.
def test_snapshot_uses_single_price_consistently():
    price = 105.0
    sd = MultiSeriesStub(
        price=price,
        smas={("W", 20): 100.0, ("M", 20): 105.0, ("D", 8): 120.0},
    )
    snapshot = build_position_snapshot(sd, [("W", 20), ("M", 20), ("D", 8)], THRESHOLDS)
    for periods in snapshot.values():
        for pos in periods.values():
            assert pos.value * (1 + pos.distance_pct) == pytest.approx(price, abs=1e-9)


# (a)+(c) position_vs_sma se invoca UNA vez por serie, con el MISMO precio inyectado, y
# reference_price se computa UNA sola vez por símbolo (precio único, A.2)
def test_each_series_computed_once_with_single_price(monkeypatch):
    calls: list[tuple] = []
    ref_calls: list = []

    def spy(sd, tf, period, thresholds, price):
        calls.append((sd, tf, period, thresholds, price))
        return f"pos:{tf}:{period}"  # sentinela: prueba el agrupamiento sin recomputar

    def ref_spy(sd):
        ref_calls.append(sd)
        return 42.0  # precio único

    monkeypatch.setattr("core.features.position_vs_sma", spy)
    monkeypatch.setattr("core.features.reference_price", ref_spy)
    sd = object()
    series = [("W", 20), ("M", 20), ("D", 8)]
    snapshot = build_position_snapshot(sd, series, THRESHOLDS)

    assert snapshot == {"W": {20: "pos:W:20"}, "M": {20: "pos:M:20"}, "D": {8: "pos:D:8"}}
    assert ref_calls == [sd]  # reference_price 1× por símbolo
    assert calls == [
        (sd, "W", 20, THRESHOLDS, 42.0),
        (sd, "M", 20, THRESHOLDS, 42.0),
        (sd, "D", 8, THRESHOLDS, 42.0),
    ]


# (a) dos periods sobre el MISMO tf anidan bajo la misma clave tf (dict anidado plano)
def test_multiple_periods_same_tf_nest_under_one_tf_key():
    sd = MultiSeriesStub(
        price=101.0,
        smas={("D", 8): 100.0, ("D", 20): 100.0},
    )
    snapshot = build_position_snapshot(sd, [("D", 8), ("D", 20)], THRESHOLDS)
    assert set(snapshot) == {"D"}
    assert set(snapshot["D"]) == {8, 20}


# (b) serie fría en `series` → FeatureNotReady que DETIENE la construcción (símbolo+serie)
def test_cold_series_halts_and_propagates():
    sd = MultiSeriesStub(
        price=105.0,
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
        price=105.0,
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


# (d) proyección de un snapshot REAL (vía builder): forma que consume SMAPositionRule.evaluate
# como evidencia (la construcción inline de la vieja AboveSMA se reemplazó por snapshot_evidence)
def test_snapshot_evidence_reproduces_builder_snapshot_schema():
    sd = MultiSeriesStub(
        price=105.0,  # precio único contra ambas SMAs (A.1)
        smas={("W", 20): 100.0, ("M", 20): 105.0},
    )
    snap = build_position_snapshot(sd, [("W", 20), ("M", 20)], THRESHOLDS)
    evidence = snapshot_evidence(snap, [("W", 20), ("M", 20)])
    _assert_evidence(
        evidence,
        {
            "W": {20: (100.0, 0.05, "above_strong")},  # 105 vs 100
            "M": {20: (105.0, 0.0, "near")},           # 105 vs 105
        },
    )


# ---------------------------------------------------------------------------
# T2.1 (Etapa 6B) — mirror_buckets + _MIRROR + SIDE_BY_DIRECTION: biyección above↔below
# involutiva y total sobre los 7 buckets, `near` autoespejo; identidad en "above".
# ---------------------------------------------------------------------------

def _powerset(items):
    """Los 2^n subconjuntos (como frozensets) — incluye el vacío y el total."""
    return [
        frozenset(combo)
        for r in range(len(items) + 1)
        for combo in itertools.combinations(items, r)
    ]


# _MIRROR es una biyección total e involutiva sobre los 7 buckets, con `near` autoespejo:
# blinda el caso de frontera contra un refactor que "optimice" a un if y olvide `near`.
def test_mirror_table_is_total_involutive_bijection():
    assert set(_MIRROR) == set(BUCKETS)               # 7 claves = los 7 buckets
    assert set(_MIRROR.values()) == set(BUCKETS)      # imagen = los 7 buckets (sobre + iny)
    assert all(_MIRROR[_MIRROR[b]] == b for b in BUCKETS)  # involutiva
    assert _MIRROR["near"] == "near"                  # near autoespejo


# (a)+(c)+(e) exhaustivo sobre los 128 subconjuntos: identidad (above), involución
# (below∘below = id) y cierre (resultado ⊆ BUCKETS) en ambos lados.
def test_mirror_exhaustive_identity_involution_and_closure():
    all_buckets = frozenset(BUCKETS)
    for subset in _powerset(BUCKETS):
        assert mirror_buckets(subset, "above") == frozenset(subset)   # (a) identidad
        below = mirror_buckets(subset, "below")
        assert mirror_buckets(below, "below") == frozenset(subset)    # (c) involución
        assert mirror_buckets(subset, "above") <= all_buckets         # (e) cierre above
        assert below <= all_buckets                                   # (e) cierre below


# (b) near autoespejo en el API público
def test_mirror_near_is_self_symmetric():
    assert mirror_buckets({"near"}, "below") == frozenset({"near"})


# (d) above→below explícito: los 3 buckets canónicos "above" → sus 3 espejos "below"
def test_mirror_above_set_to_below_set():
    result = mirror_buckets({"above_mild", "above_strong", "extended_above"}, "below")
    assert result == frozenset({"below_mild", "below_strong", "extended_below"})


# mirror_buckets devuelve frozenset (inmutable: seguro como atributo de la rule)
def test_mirror_returns_frozenset():
    assert isinstance(mirror_buckets({"above_mild"}, "above"), frozenset)
    assert isinstance(mirror_buckets({"above_mild"}, "below"), frozenset)


# vacío → frozenset vacío en ambos lados (degenerado pero total)
def test_mirror_empty_set():
    assert mirror_buckets(set(), "above") == frozenset()
    assert mirror_buckets(set(), "below") == frozenset()


# (e) side inválido → ValueError fail-fast (no "above"/"below" exacto)
@pytest.mark.parametrize("bad_side", ["long", "short", "ABOVE", "Below", "", "up", None])
def test_mirror_invalid_side_raises(bad_side):
    with pytest.raises(ValueError, match="side inválido"):
        mirror_buckets({"near"}, bad_side)


# SIDE_BY_DIRECTION: única fuente de la traducción direction→side (D6B.4)
def test_side_by_direction_mapping():
    assert SIDE_BY_DIRECTION == {"long": "above", "short": "below"}
    # coherente con los `side` que acepta mirror_buckets
    assert set(SIDE_BY_DIRECTION.values()) == {"above", "below"}
