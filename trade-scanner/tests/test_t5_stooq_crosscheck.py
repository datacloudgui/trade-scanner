"""T5.3 (Etapa 5B): cross-check del converter Stooq — fidelidad de precios + SMAs vía SymbolData.

HALLAZGO (2026-06-11): Stooq provee precios **total-return adjusted** (split + dividendos
acumulados hacia atrás), NO split-only como el spy.zip de LEAN. Comparar Stooq vs LEAN-zip
en valores absolutos no es válido (diferencia ~7-23% según el horizonte de dividendos).
Ver etapa-05b-t5-3-decisiones-y-pendientes.md.

OBJETIVO del test: verificar que el converter preserva los precios del CSV Stooq exactamente
(dentro de la resolución ×10000) y que SymbolData computa SMAs coherentes. La validación
contra TradingView (T6.3) debe usar la vista "Adjusted" de TradingView para alinear con
los precios total-return de Stooq.

Datos requeridos:
  - data/stooq_lean/daily/spy.zip   (converter Stooq)
  - data/stooq/spy_us_d.csv         (CSV Stooq original, fuente de verdad para el test)
"""
import csv
import io
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar

from core.symbol_data import SymbolData

SPY = Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")
REQS = {"D": {8, 20, 200}, "W": {8, 20, 200}, "M": {8, 20, 200}}

# Punto de comparación dentro de la cobertura Stooq SPY (2005-02-25..hoy).
# Suficientes barras para D:200 (~2005+200d≈2005-10), W:200 (~2005+1400d≈2010), M:200 (~2022).
COMPARE_AT = datetime(2020, 6, 1)

_DATA_DIR = Path(os.environ.get("TRADE_SCANNER_DATA")
                 or Path(__file__).resolve().parents[2] / "data")
STOOQ_SPY_ZIP = _DATA_DIR / "stooq_lean/daily/spy.zip"
STOOQ_SPY_CSV = _DATA_DIR / "stooq/spy_us_d.csv"  # CSV original (montado desde data/)


def _expected_from_csv(csv_path: Path, before: datetime) -> dict[str, float]:
    """Lee el CSV Stooq y devuelve {YYYYMMDD: close} para fechas < before."""
    prices = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = row["Date"].replace("-", "")
            t = datetime.strptime(d, "%Y%m%d")
            if t >= before:
                continue
            prices[d] = float(row["Close"])
    return prices


def _zip_prices(zip_path: Path) -> dict[str, int]:
    """Lee el zip LEAN y devuelve {YYYYMMDD: close_raw (×10000)}."""
    prices = {}
    with zipfile.ZipFile(zip_path) as zf:
        lines = zf.read(zf.namelist()[0]).decode().splitlines()
    for ln in lines:
        stamp, _, _, _, c, _ = ln.split(",")
        d = stamp.split(" ")[0]
        prices[d] = int(c)
    return prices


def _load_bars(zip_path: Path, before: datetime) -> list:
    with zipfile.ZipFile(zip_path) as zf:
        lines = zf.read(zf.namelist()[0]).decode().splitlines()
    bars = []
    for ln in lines:
        stamp, o, h, lo, c, v = ln.split(",")
        t = datetime.strptime(stamp.split(" ")[0], "%Y%m%d")
        if t >= before:
            break
        bars.append(TradeBar(t, SPY, int(o)/10000, int(h)/10000,
                             int(lo)/10000, int(c)/10000, int(v), timedelta(days=1)))
    return bars


_STOOQ_ZIP_PRESENT = STOOQ_SPY_ZIP.exists()
_CSV_PRESENT = STOOQ_SPY_CSV.exists()


@pytest.mark.skipif(not _STOOQ_ZIP_PRESENT, reason="falta stooq_lean/daily/spy.zip")
@pytest.mark.skipif(not _CSV_PRESENT, reason="falta data/stooq/spy_us_d.csv")
def test_t5_spy_converter_price_fidelity():
    """El zip producido por el converter preserva los precios del CSV Stooq (rounding ×10000)."""
    csv_prices  = _expected_from_csv(STOOQ_SPY_CSV, COMPARE_AT)
    zip_prices  = _zip_prices(STOOQ_SPY_ZIP)

    # Verificar una muestra representativa de fechas dentro del overlap
    sample_dates = sorted(csv_prices.keys())[-20:]  # últimas 20 barras antes de COMPARE_AT
    errors = []
    for d in sample_dates:
        if d not in zip_prices:
            errors.append(f"{d}: falta en zip")
            continue
        expected_raw = round(csv_prices[d] * 10000)
        actual_raw   = zip_prices[d]
        # Tolerancia: ±1 unidad por redondeo de round()
        if abs(actual_raw - expected_raw) > 1:
            errors.append(
                f"{d}: csv={csv_prices[d]:.4f} (×10000={expected_raw}) zip={actual_raw} "
                f"diff={actual_raw-expected_raw}"
            )

    assert not errors, f"Discrepancias de precios CSV→zip:\n" + "\n".join(f"  {e}" for e in errors)


@pytest.mark.skipif(not _STOOQ_ZIP_PRESENT, reason="falta stooq_lean/daily/spy.zip")
def test_t5_spy_stooq_smas_ready_and_reasonable():
    """SymbolData carga el zip Stooq SPY y produce SMAs coherentes en COMPARE_AT.

    Cross-check: las SMAs D/W se computan; M:200 no-ready (esperado: Stooq SPY
    empieza 2005 y M:200 requiere 4221 barras → ready ~dic 2021).
    Rango plausible: precios Stooq son total-return adjusted → valores menores que raw.
    """
    bars = _load_bars(STOOQ_SPY_ZIP, COMPARE_AT)
    sd = SymbolData(SPY, REQS)
    for bar in bars:
        sd.update(bar)
    sd.scan(COMPARE_AT)

    # D y W hasta :200 deben estar ready con ~3868 barras desde 2005
    for tf in ("D", "W"):
        for p in (8, 20, 200):
            sma = sd.sma(tf, p)
            assert sma.is_ready, f"{tf}:{p} debería estar ready con {len(bars)} barras"
            v = float(sma.current.value)
            # Stooq total-return adjusted: SPY ~$277 en 2020-06 (vs raw ~$300)
            assert 200 < v < 400, f"{tf}:{p} valor fuera de rango plausible: {v:.2f}"

    # M:8 y M:20 deben estar ready; M:200 no (cobertura insuficiente desde 2005)
    for p in (8, 20):
        assert sd.sma("M", p).is_ready, f"M:{p} debería estar ready"
    assert not sd.sma("M", 200).is_ready, (
        "M:200 debería ser NOT READY para Stooq SPY (datos desde 2005, 4221 barras → ~dic 2021)"
    )
