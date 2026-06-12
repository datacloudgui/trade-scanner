"""T4 (Etapa 5B): fixture de regresión INTERINO — SMAs de SPY congeladas sobre SPY-zip.

Tercera ruta independiente (zip → TradeBars → SymbolData, sin engine ni self.history)
que debe reproducir los valores del backtest dev del 2026-06-11:

    ruta engine (set_warm_up) == ruta manual (gate T2.2) == este test

Rol: que los refactors de F2–F3 no rompan la matemática en silencio, y cross-check
permanente del gate de T2.2. NO es la validación manual de precisión (T7.2); el
fixture autoritativo de T7.3 (TradingView/IBKR) lo extiende/reemplaza.

Datos: data/equity/usa/daily/spy.zip (1998–2021), montado en /Data por run_tests.sh
(TRADE_SCANNER_DATA); en su ausencia el test se salta con instrucción de seed.
"""
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar

from core.symbol_data import SymbolData
from core.timeframes import plan_warmup

SPY = Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")

# Superset dev (override de environments.dev en strategies.json): incluye M:200.
REQUIREMENTS = {"D": {8, 20, 200}, "W": {8, 20, 200}, "M": {8, 20, 200}}

START = datetime(2016, 1, 4)  # start_date del backtest 5B; scan de cierre al mismo instante

_DATA_DIR = Path(os.environ.get("TRADE_SCANNER_DATA")
                 or Path(__file__).resolve().parents[2] / "data")
SPY_ZIP = _DATA_DIR / "equity/usa/daily/spy.zip"

# Congelado del backtest dev 2026-06-11 (storage/validation/sma_validation_20160104.csv,
# data RAW del zip — SPY no tiene splits → SPLIT_ADJUSTED == RAW):
# (tf, period) -> (sma_value, samples, end_time del último punto)
FROZEN = {
    ("D", 8): (204.925, 4221, datetime(2016, 1, 1)),
    ("D", 20): (205.1965, 4221, datetime(2016, 1, 1)),
    ("D", 200): (206.2078, 4221, datetime(2016, 1, 1)),
    ("W", 8): (205.3175, 876, datetime(2016, 1, 4)),
    ("W", 20): (202.118, 876, datetime(2016, 1, 4)),
    ("W", 200): (177.5696, 876, datetime(2016, 1, 4)),
    ("M", 8): (204.66125, 202, datetime(2016, 1, 1)),
    ("M", 20): (202.795, 202, datetime(2016, 1, 1)),
    ("M", 200): (133.415, 202, datetime(2016, 1, 1)),
}


def _spy_daily_bars_before_start() -> list:
    """Filas LEAN (fecha, OHLC×10000, V) → TradeBars diarios anteriores al start."""
    with zipfile.ZipFile(SPY_ZIP) as zf:
        lines = zf.read(zf.namelist()[0]).decode().splitlines()
    bars = []
    for line in lines:
        date_field, o, h, lo, c, v = line.split(",")
        time = datetime.strptime(date_field.split(" ")[0], "%Y%m%d")
        if time >= START:
            break  # el zip viene ordenado ascendente
        bars.append(
            TradeBar(time, SPY, int(o) / 10000, int(h) / 10000, int(lo) / 10000,
                     int(c) / 10000, int(v), timedelta(days=1))
        )
    return bars


@pytest.mark.skipif(
    not SPY_ZIP.exists(),
    reason="falta spy.zip: bash scripts/seed_sample_data.sh (y mount /Data en run_tests.sh)",
)
def test_5b_t4_spy_sma_regression_frozen():
    depth = plan_warmup(REQUIREMENTS).depth_by_resolution["daily"]
    assert depth == 4221  # fórmula M:200 = 200×21+21 — si cambia, recongelar a propósito

    bars = _spy_daily_bars_before_start()[-depth:]
    assert len(bars) == depth
    assert bars[-1].time == datetime(2015, 12, 31)  # última sesión antes del start

    sd = SymbolData(SPY, REQUIREMENTS)
    for bar in bars:
        sd.update(bar)
    sd.scan(START)  # cierre del warmup manual (hallazgo #1 de 5A)

    for (tf, period), (value, samples, end_time) in sorted(FROZEN.items()):
        sma = sd.sma(tf, period)
        assert sma.is_ready, f"{tf}:{period} no ready"
        assert float(sma.current.value) == pytest.approx(value, rel=1e-12), \
            f"{tf}:{period} valor"
        assert int(sma.samples) == samples, f"{tf}:{period} samples"
        assert sma.current.end_time == end_time, f"{tf}:{period} end_time (off-by-one)"
