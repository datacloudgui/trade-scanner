"""Test offline del POC earnings_volume (T2 CA): stub de Finnhub, sin red.

Corre con el Python del host (.venv): `python scripts/poc/test_earnings_volume.py`.
No usa pytest ni la imagen LEAN — es un script host-side puro stdlib (D-POC.6).
"""
import argparse
from datetime import date

import earnings_volume as ev


class StubClient:
    """Cliente falso: devuelve un calendar fijo y métricas por símbolo. Sin red."""

    def __init__(self, calendar):
        self._calendar = calendar
        self.metric_calls = []

    def earnings_calendar(self, start, end):
        # Devuelve solo las filas dentro de [start, end] (como haría Finnhub).
        return [r for r in self._calendar
                if start.isoformat() <= r["date"] <= end.isoformat()]

    def stock_metric(self, symbol):
        self.metric_calls.append(symbol)
        table = {
            "AAPL": {"10DayAverageTradingVolume": 64.76, "3MonthAverageTradingVolume": 70.1},
            "MSFT": {"10DayAverageTradingVolume": 22.0, "3MonthAverageTradingVolume": 25.0},
            "XYZ": {},  # sin métrica → None
        }
        return table.get(symbol, {})


def _ns(**kw):
    base = dict(next_week=False, next_day=False, range=None, date=None)
    base.update(kw)
    return argparse.Namespace(**base)


def _syms(rows):
    return sorted((r.get("symbol") or r.get("ticker")) for r in rows)


CAL = [
    {"date": "2026-07-13", "symbol": "AAPL", "hour": "amc"},
    {"date": "2026-07-13", "symbol": "ZZZ", "hour": "bmo"},   # start: BMO → descartado
    {"date": "2026-07-14", "symbol": "MSFT", "hour": "bmo"},  # interior: se conserva
    {"date": "2026-07-14", "symbol": "NVDA", "hour": "amc"},  # interior: se conserva
    {"date": "2026-07-15", "symbol": "XYZ", "hour": "bmo"},   # end: BMO → conservado
    {"date": "2026-07-15", "symbol": "WWW", "hour": "amc"},   # end: AMC → descartado
]


def test_resolve_windows():
    today = date(2026, 7, 9)  # jueves
    # --date D  →  start=D-1, end=D, filtro
    s, e, f, label = ev.resolve_window(_ns(date="2026-07-14"), today)
    assert (s, e, f, label) == (date(2026, 7, 13), date(2026, 7, 14), True, "date")
    # --next-day → today, today+1, filtro
    s, e, f, label = ev.resolve_window(_ns(next_day=True), today)
    assert (s, e, f, label) == (date(2026, 7, 9), date(2026, 7, 10), True, "next-day")
    # --range → S, E, filtro
    s, e, f, label = ev.resolve_window(_ns(range=["2026-07-13", "2026-07-15"]), today)
    assert (s, e, f, label) == (date(2026, 7, 13), date(2026, 7, 15), True, "range")
    # --range S==E → se trata como --date S
    s, e, f, _ = ev.resolve_window(_ns(range=["2026-07-14", "2026-07-14"]), today)
    assert (s, e, f) == (date(2026, 7, 13), date(2026, 7, 14), True)
    # --next-week → lunes(2026-07-13) a viernes(2026-07-17), sin filtro
    s, e, f, label = ev.resolve_window(_ns(next_week=True), today)
    assert (s, e, f, label) == (date(2026, 7, 13), date(2026, 7, 17), False, "next-week")
    print("✓ test_resolve_windows")


def test_boundary_filter_range():
    """--range S E (≥3 días): AMC(start) + interior completo + BMO(end)."""
    client = StubClient(CAL)
    rows = ev.collect(client, date(2026, 7, 13), date(2026, 7, 15), boundary_filter=True)
    assert _syms(rows) == ["AAPL", "MSFT", "NVDA", "XYZ"], _syms(rows)
    print("✓ test_boundary_filter_range")


def test_date_two_day_amc_bmo():
    """--date equivalente: rango de 2 días contiguos → AMC(start) + BMO(end), sin interior."""
    cal = [
        {"date": "2026-07-13", "symbol": "AAPL", "hour": "amc"},  # start AMC → sí
        {"date": "2026-07-13", "symbol": "ZZZ", "hour": "bmo"},   # start BMO → no
        {"date": "2026-07-14", "symbol": "MSFT", "hour": "bmo"},  # end BMO → sí
        {"date": "2026-07-14", "symbol": "WWW", "hour": "amc"},   # end AMC → no
    ]
    client = StubClient(cal)
    rows = ev.collect(client, date(2026, 7, 13), date(2026, 7, 14), boundary_filter=True)
    assert _syms(rows) == ["AAPL", "MSFT"], _syms(rows)
    print("✓ test_date_two_day_amc_bmo")


def test_next_week_no_filter():
    """--next-week: sin filtro de bordes → todas las filas del rango."""
    client = StubClient(CAL)
    rows = ev.collect(client, date(2026, 7, 13), date(2026, 7, 15), boundary_filter=False)
    assert len(rows) == 6, len(rows)
    print("✓ test_next_week_no_filter")


def test_universe_filter():
    client = StubClient(CAL)
    rows = ev.collect(client, date(2026, 7, 13), date(2026, 7, 15),
                      boundary_filter=True, universe={"AAPL", "MSFT"})
    assert _syms(rows) == ["AAPL", "MSFT"], _syms(rows)
    print("✓ test_universe_filter")


def test_attach_volume_and_none():
    client = StubClient(CAL)
    rows = [{"symbol": "AAPL", "hour": "amc", "date": "2026-07-13"},
            {"symbol": "XYZ", "hour": "bmo", "date": "2026-07-15"}]
    enriched = ev.attach_volume(client, rows)
    assert enriched[0]["avg_volume"] == 64.76
    assert enriched[1]["avg_volume"] is None  # XYZ sin métrica → None
    print("✓ test_attach_volume_and_none")


def test_min_avg_vol_filter():
    rows = [{"ticker": "AAPL", "hour": "amc", "avg_volume": 64.76, "avg_volume_3m": 70.1},
            {"ticker": "MSFT", "hour": "bmo", "avg_volume": 22.0, "avg_volume_3m": 25.0},
            {"ticker": "XYZ", "hour": "bmo", "avg_volume": None, "avg_volume_3m": None}]
    filtered = [r for r in rows if r["avg_volume"] is not None and r["avg_volume"] >= 30.0]
    assert _syms(filtered) == ["AAPL"], _syms(filtered)
    print("✓ test_min_avg_vol_filter")


if __name__ == "__main__":
    test_resolve_windows()
    test_boundary_filter_range()
    test_date_two_day_amc_bmo()
    test_next_week_no_filter()
    test_universe_filter()
    test_attach_volume_and_none()
    test_min_avg_vol_filter()
    print("\n✅ Todos los tests offline pasaron.")
