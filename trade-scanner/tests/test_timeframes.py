"""T3.1–T3.3 (Etapa 5A): fórmula de warmup, extensibilidad del registro y plan con presupuesto.

Estos tests NO importan AlgorithmImports: la fórmula y el plan son funciones puras
(D1/D2 del spec). El no-uso del CLR se verifica explícitamente vía subprocess.
"""
import os
import subprocess
import sys

import pytest

from core.timeframes import TIMEFRAMES, TimeframeSpec, plan_warmup

# Tabla D1 del spec: warmup = period × bars_per_period + buffer
# D: n+5 · W: n×5+10 · M: n×21+21
EXPECTED_DEPTHS = {
    ("D", 8): 13, ("D", 20): 25, ("D", 200): 205,
    ("W", 8): 50, ("W", 20): 110, ("W", 200): 1010,
    ("M", 8): 189, ("M", 20): 441, ("M", 200): 4221,
}


# --- T3.1 — fórmula: tabla D1 completa ---

@pytest.mark.parametrize("tf,period", sorted(EXPECTED_DEPTHS))
def test_t3_1_warmup_bars_reproduces_d1_table(tf, period):
    assert TIMEFRAMES[tf].warmup_bars(period) == EXPECTED_DEPTHS[(tf, period)]


# --- T3.2 — extensibilidad: timeframe nuevo sin tocar la fórmula ---

def test_t3_2_synthetic_intraday_timeframe_without_touching_formula():
    # 30 minutos: 30 barras minute por periodo, buffer 60 → 200×30+60 = 6060
    spec_30t = TimeframeSpec("30T", "minute", 30, 60)
    assert spec_30t.warmup_bars(200) == 6060


def test_t3_2_plan_groups_minute_apart_from_daily():
    registry = {"D": TIMEFRAMES["D"], "30T": TimeframeSpec("30T", "minute", 30, 60)}
    plan = plan_warmup({"D": {20}, "30T": {200}}, registry=registry)
    # cada resolución fuente reporta su propia profundidad: D:20 → 25, 30T:200 → 6060
    assert plan.depth_by_resolution == {"daily": 25, "minute": 6060}
    assert not plan.excluded


# --- T3.3 — plan con presupuesto: M:200 excluida con budget 1200; sin budget nada se excluye ---

ALL_REQUIREMENTS = {"D": {8, 20, 200}, "W": {8, 20, 200}, "M": {8, 20, 200}}


def test_t3_3_budget_excludes_m200_and_caps_depth():
    plan = plan_warmup(ALL_REQUIREMENTS, budget={"daily": 1200})
    # profundidad = max de las incluidas: W:200 → 1010 (M:200 = 4221 queda fuera)
    assert plan.depth_by_resolution == {"daily": 1010}
    assert [(s.tf, s.period, s.warmup_bars) for s in plan.excluded] == [("M", 200, 4221)]
    assert len(plan.included) == 8
    assert ("M", 200) not in {(s.tf, s.period) for s in plan.included}


def test_t3_3_no_budget_includes_everything():
    plan = plan_warmup(ALL_REQUIREMENTS, budget=None)
    assert plan.depth_by_resolution == {"daily": 4221}
    assert not plan.excluded
    assert len(plan.included) == 9


def test_unknown_timeframe_raises_keyerror_naming_it():
    with pytest.raises(KeyError, match="X"):
        plan_warmup({"X": {8}})


# --- Done-when: `import core.timeframes` funciona sin CLR ---

def test_import_core_timeframes_without_clr():
    """En este proceso pytest el CLR ya está cargado por otros tests; se verifica
    en un intérprete limpio que importar el módulo no arrastra clr/AlgorithmImports."""
    code = (
        "import sys; import core.timeframes; "
        "assert 'clr' not in sys.modules and 'AlgorithmImports' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ.copy())
