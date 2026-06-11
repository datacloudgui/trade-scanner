"""Tests unitarios de UniverseSpec.

No usan AlgorithmImports — corren dentro de Docker pero sin el CLR path.
Fixture base: MockObjectStore retorna CSV sintético construido en el test.
"""
import pytest

from core.universe import UniverseSpec

_HEADER = 'Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low","5D Avg Vol",Time'


def _row(symbol: str, price: float, vol: float, pct5d: str = "+5.00%", pct1d: str = "+1.00%") -> str:
    return f"{symbol},Test Corp,{pct5d},{price},0.5,{pct1d},0.5,{price},{price},{vol:.0f},2026-06-05"


def _csv(*rows: str) -> str:
    return "\n".join([_HEADER] + list(rows))


class MockObjectStore:
    def __init__(self, csv_content: str):
        self._content = csv_content

    def read(self, key: str) -> str:
        return self._content


class RaisingObjectStore:
    def read(self, key: str) -> str:
        raise KeyError(f"Object with path '{key}' was not found in the Object Store")


FILTER = "avg_vol_5d > 1e6 and price > 5"


# T3.1 — El filtro funciona con alias normalizados
def test_filter_returns_matching_tickers():
    csv = _csv(
        _row("AAA", price=10.0, vol=2_000_000),   # pasa: vol > 1e6 AND price > 5
        _row("BBB", price=10.0, vol=500_000),       # falla: vol ≤ 1e6
        _row("CCC", price=3.0,  vol=2_000_000),     # falla: price ≤ 5
        _row("DDD", price=15.0, vol=3_000_000),     # pasa
        _row("EEE", price=20.0, vol=4_000_000),     # pasa
    )
    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    assert sorted(result) == ["AAA", "DDD", "EEE"]
    assert len(result) == 3


# T3.2 — Tope duro trunca correctamente
def test_hard_cap_truncates_to_max_tickers():
    rows = [_row(sym, price=10.0, vol=2_000_000)
            for sym in ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ"]]
    csv = _csv(*rows)
    result = UniverseSpec("k", FILTER, max_tickers=5).load(MockObjectStore(csv))
    assert len(result) == 5
    # Orden alfabético garantiza los primeros 5 después del sort
    assert result == ["AAA", "BBB", "CCC", "DDD", "EEE"]


# T3.3 — Footer strip elimina filas inválidas
def test_footer_strip_excludes_non_ticker_rows():
    csv = _csv(
        _row("AAA", price=10.0, vol=2_000_000),
        _row("BBB", price=10.0, vol=2_000_000),
        _row("CCC", price=10.0, vol=2_000_000),
        '"Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT"',
    )
    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    assert len(result) == 3
    assert "Downloaded" not in " ".join(result)


# T3.4 — Columna requerida faltante lanza error con mensaje claro
def test_missing_required_column_raises_key_error():
    # CSV sin la columna "5D Avg Vol" → avg_vol_5d no aparece tras el rename
    header_no_vol = 'Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Chg","5D High","5D Low",Time'
    row = "AAA,Test Corp,+5.00%,10.0,0.5,+1.00%,0.5,10.0,10.0,2026-06-05"
    csv = header_no_vol + "\n" + row
    with pytest.raises(KeyError, match="avg_vol_5d"):
        UniverseSpec("k", FILTER).load(MockObjectStore(csv))


# T3.5 — KeyError de ObjectStore se propaga sin transformar
def test_object_store_key_not_found_propagates():
    with pytest.raises(KeyError):
        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())
