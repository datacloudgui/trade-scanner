"""T4 (Etapa 9A): cross-check Alpaca↔Stooq de SMAs D/W/M + fixture de regresión congelado.

Stooq es la REFERENCIA (validada vs TradingView en 5B T6.3). Ambas fuentes son split-only
adjusted (Alpaca `adjustment=split`; Stooq skip-dividends/skip-others). Por tanto las SMAs
computadas por `SymbolData` desde los zips Alpaca deben cuadrar con las de Stooq dentro de la
tolerancia ≤0,25% — el margen absorbe el ruido IEX (close IEX vs consolidado) en líquidos.

Cobertura: los zips Alpaca del demo cubren 2024-01-02.. → solo las SMAs cuyo período cabe en
ese rango están ready (D:8/20/200, W:8/20, M:8/20). W:200/M:200 se omiten del cross-check
(historia Alpaca insuficiente; cubierto por Stooq/5B). El cross-check compara solo (tf,período)
ready en AMBAS fuentes.

Datos requeridos (montados en /Data por run_tests.sh):
  - data/alpaca_lean/daily/{spy,aapl,ibm}.zip   (downloader Alpaca, T3)
  - data/stooq_lean/daily/{spy,aapl,ibm}.zip    (converter Stooq, 5B)
En su ausencia el test se salta (skipif), como los cross-checks de 5B.
"""
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar

from core.symbol_data import SymbolData

SYMBOLS = ["SPY", "AAPL", "IBM"]
REQS = {"D": {8, 20, 200}, "W": {8, 20, 200}, "M": {8, 20, 200}}
COMPARE_AT = datetime(2026, 6, 1)  # dentro del overlap Alpaca(2024-)↔Stooq(..2026-06-11)
TOL = 0.0025                       # 0,25% relativo (tolerancia de 5B)

_DATA_DIR = Path(os.environ.get("TRADE_SCANNER_DATA")
                 or Path(__file__).resolve().parents[2] / "data")
ALPACA_DIR = _DATA_DIR / "alpaca_lean/daily"
STOOQ_DIR = _DATA_DIR / "stooq_lean/daily"


def _symbol(ticker: str) -> Symbol:
    return Symbol(SecurityIdentifier.generate_equity(ticker, Market.USA, False), ticker)


def _load_bars(zip_path: Path, sym: Symbol, before: datetime) -> list:
    """Filas LEAN del zip → TradeBars diarios anteriores a `before` (orden ascendente)."""
    with zipfile.ZipFile(zip_path) as zf:
        lines = zf.read(zf.namelist()[0]).decode().splitlines()
    bars = []
    for ln in lines:
        stamp, o, h, lo, c, v = ln.split(",")
        t = datetime.strptime(stamp.split(" ")[0], "%Y%m%d")
        if t >= before:
            break
        bars.append(TradeBar(t, sym, int(o) / 10000, int(h) / 10000,
                             int(lo) / 10000, int(c) / 10000, int(v), timedelta(days=1)))
    return bars


def _build(zip_path: Path, ticker: str, before: datetime) -> SymbolData:
    sym = _symbol(ticker)
    sd = SymbolData(sym, REQS)
    for bar in _load_bars(zip_path, sym, before):
        sd.update(bar)
    sd.scan(before)  # cierra el warmup (hallazgo #1 de 5A)
    return sd


def _ready_smas(sd: SymbolData) -> dict[tuple[str, int], float]:
    out = {}
    for tf, periods in REQS.items():
        for p in periods:
            sma = sd.sma(tf, p)
            if sma.is_ready:
                out[(tf, p)] = float(sma.current.value)
    return out


_PRESENT = ALPACA_DIR.exists() and STOOQ_DIR.exists() and all(
    (ALPACA_DIR / f"{s.lower()}.zip").exists() and (STOOQ_DIR / f"{s.lower()}.zip").exists()
    for s in SYMBOLS
)
skip_if_absent = pytest.mark.skipif(
    not _PRESENT,
    reason="faltan zips alpaca_lean/stooq_lean: corre scripts/alpaca_to_lean.py + converter 5B",
)


@skip_if_absent
@pytest.mark.parametrize("ticker", SYMBOLS)
def test_t4_alpaca_matches_stooq_smas(ticker: str):
    """Las SMAs D/W/M de Alpaca cuadran con Stooq (≤0,25%) en las series ready de ambas."""
    alpaca = _ready_smas(_build(ALPACA_DIR / f"{ticker.lower()}.zip", ticker, COMPARE_AT))
    stooq = _ready_smas(_build(STOOQ_DIR / f"{ticker.lower()}.zip", ticker, COMPARE_AT))

    common = sorted(set(alpaca) & set(stooq))
    # Garantiza que comparamos series significativas (no un set vacío por bug de carga).
    assert {("D", 8), ("D", 20), ("D", 200), ("W", 8), ("W", 20)} <= set(common), (
        f"{ticker}: faltan series esperadas en el cross-check; common={common}"
    )

    errors = []
    for key in common:
        a, s = alpaca[key], stooq[key]
        rel = abs(a - s) / s if s else 0.0
        if rel > TOL:
            errors.append(f"{ticker} {key[0]}:{key[1]} alpaca={a:.4f} stooq={s:.4f} rel={rel*100:.3f}%")
    assert not errors, "Discrepancias > 0,25%:\n" + "\n".join(f"  {e}" for e in errors)


# Fixture autoritativo (extiende el de 5B F3 T6.4): SMAs de SPY desde el zip Alpaca del demo
# (2024-01-02..2026-06-18), congeladas en COMPARE_AT=2026-06-01. Rol: que refactors del downloader
# o del emisor compartido no rompan la matemática en silencio. (tf,p) -> (valor, samples, end_time).
FROZEN_SPY_ALPACA = {
    ("D", 8): (746.945, 604, datetime(2026, 5, 30)),
    ("D", 20): (739.299, 604, datetime(2026, 5, 30)),
    ("D", 200): (681.15075, 604, datetime(2026, 5, 30)),
    ("W", 8): (725.315, 126, datetime(2026, 6, 1)),
    ("W", 20): (694.8025, 126, datetime(2026, 6, 1)),
    ("M", 8): (693.755, 29, datetime(2026, 6, 1)),
    ("M", 20): (638.307, 29, datetime(2026, 6, 1)),
}


@skip_if_absent
def test_t4_spy_alpaca_sma_regression_frozen():
    """SMAs de SPY-Alpaca reproducen el fixture congelado (valor exacto + samples + end_time)."""
    sd = _build(ALPACA_DIR / "spy.zip", "SPY", COMPARE_AT)
    for (tf, period), (value, samples, end_time) in sorted(FROZEN_SPY_ALPACA.items()):
        sma = sd.sma(tf, period)
        assert sma.is_ready, f"{tf}:{period} no ready"
        assert float(sma.current.value) == pytest.approx(value, rel=1e-12), f"{tf}:{period} valor"
        assert int(sma.samples) == samples, f"{tf}:{period} samples"
        assert sma.current.end_time == end_time, f"{tf}:{period} end_time (off-by-one)"
