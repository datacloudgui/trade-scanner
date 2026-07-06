"""Tests unitarios de UniverseSpec.

No usan AlgorithmImports — corren dentro de Docker pero sin el CLR path.
Fixture base: MockObjectStore retorna CSV sintético construido en el test.
"""
import pytest

from core.universe import UniverseSpec, _PERIOD_VOL_COLS

# ── Helpers ──────────────────────────────────────────────────────────────────

def _header(vol_col: str = "5D Avg Vol", pct_col: str = "5D %Chg") -> str:
    return f'Symbol,Name,"{pct_col}",Latest,Change,%Change,"{vol_col}",Time'


def _row(
    symbol: str,
    price: float,
    vol: float,
    pct_period: str = "+5.00%",
    pct1d: str = "+1.00%",
) -> str:
    return f"{symbol},Test Corp,{pct_period},{price},0.5,{pct1d},{vol:.0f},2026-06-05"


def _csv(*rows: str, vol_col: str = "5D Avg Vol", pct_col: str = "5D %Chg") -> str:
    return "\n".join([_header(vol_col, pct_col)] + list(rows))


class MockObjectStore:
    def __init__(self, csv_content: str):
        self._content = csv_content

    def read(self, key: str) -> str:
        return self._content


class RaisingObjectStore:
    def read(self, key: str) -> str:
        raise KeyError(f"Object with path '{key}' was not found in the Object Store")


FILTER = "avg_vol > 1e6 and price > 5"

# ── Tests base ────────────────────────────────────────────────────────────────

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


# T3.4 — CSV sin ninguna columna de volumen conocida → error descriptivo
def test_missing_vol_column_raises_with_descriptive_message():
    # CSV con columna de volumen desconocida ("YTD Avg Vol" no está en _PERIOD_VOL_COLS)
    header_unknown_vol = 'Symbol,Name,"YTD %Chg",Latest,Change,%Change,"YTD Avg Vol",Time'
    row = "AAA,Test Corp,+5.00%,10.0,0.5,+1.00%,2000000,2026-06-05"
    csv = header_unknown_vol + "\n" + row
    with pytest.raises(KeyError, match="columna de volumen"):
        UniverseSpec("k", FILTER).load(MockObjectStore(csv))


# T3.5 — KeyError de ObjectStore se propaga sin transformar
def test_object_store_key_not_found_propagates():
    with pytest.raises(KeyError):
        UniverseSpec("universes/missing.csv", FILTER).load(RaisingObjectStore())


# ── Auto-detect de periodo (1D / 5D / 1M / 3M) ───────────────────────────────

_PERIOD_PARAMS = [
    ("1D Avg Vol", "1D %Chg"),
    ("5D Avg Vol", "5D %Chg"),
    ("1M Avg Vol", "1M %Chg"),
    ("3M Avg Vol", "3M %Chg"),
]


@pytest.mark.parametrize("vol_col,pct_col", _PERIOD_PARAMS)
def test_autodetect_period_schema(vol_col: str, pct_col: str):
    """Todas las vistas de Barchart (1D/5D/1M/3M) deben cargar sin error."""
    csv = _csv(
        _row("AAA", price=10.0, vol=2_000_000),
        _row("BBB", price=3.0,  vol=2_000_000),   # falla price
        _row("CCC", price=10.0, vol=500_000),       # falla vol
        vol_col=vol_col,
        pct_col=pct_col,
    )
    result = UniverseSpec("k", FILTER).load(MockObjectStore(csv))
    assert result == ["AAA"]


@pytest.mark.parametrize("vol_col,pct_col", _PERIOD_PARAMS)
def test_autodetect_maps_to_canonical_avg_vol(vol_col: str, pct_col: str):
    """El filtro usa 'avg_vol' (canónico); debe funcionar igual en todos los periodos."""
    csv = _csv(
        _row("ZZZ", price=20.0, vol=5_000_000),
        vol_col=vol_col,
        pct_col=pct_col,
    )
    result = UniverseSpec("k", "avg_vol > 1e6 and price > 5").load(MockObjectStore(csv))
    assert result == ["ZZZ"]


# ── Separadores de miles de Barchart ─────────────────────────────────────────

# 9A/T5 — Barchart formatea %Chg grandes y volúmenes con separador de miles (quoted).
def test_thousands_separator_in_pct_and_volume_parses():
    row = 'CAST,"Freecast Inc","+1,153.11%",8.07,2.92,+56.70%,"101,584,617",2026-06-18'
    result = UniverseSpec("k", FILTER).load(MockObjectStore(_csv(row)))
    assert result == ["CAST"]  # vol 101.5M > 1e6 y price 8.07 > 5 → pasa sin error de float


# ─────────────────────────────────────────────────────────────────────────────
# #14 / #13 (triaje E1–E8) — tope absoluto 200, alias map completo, errores de filtro
# con contexto. Bloque autocontenido: construye su propio CSV vista 5D y deriva el alias
# canónico de volumen de _REQUIRED_COLUMNS (no se acopla al nombre exacto del alias).
# ─────────────────────────────────────────────────────────────────────────────

import itertools
import string

from core.universe import _REQUIRED_COLUMNS as _REQUIRED

_VOL_ALIAS = next(iter(_REQUIRED - {"price"}))
_HEADER_5D = 'Symbol,Name,"5D %Chg",Latest,Change,%Change,"5D Avg Vol",Time'


def _row_5d(symbol: str, price: float = 10.0, vol: int = 2_000_000,
            pct1d: str = "+1.00%") -> str:
    return f"{symbol},Test Corp,+5.00%,{price},0.5,{pct1d},{vol},2026-06-05"


# (#14, blinda #11) tope ABSOLUTO de producto: aunque config pida max_tickers > 200, salen ≤200
def test_absolute_cap_200_overrides_config():
    symbols = ["".join(c) for c in itertools.product(string.ascii_uppercase, repeat=2)]
    rows = [_row_5d(sym) for sym in symbols[:250]]
    csv = "\n".join([_HEADER_5D] + rows)
    result = UniverseSpec("k", "price > 5", max_tickers=500).load(MockObjectStore(csv))
    assert len(result) == 200


# (#14, blinda #10) alias map completo: Symbol→ticker, Latest→price, %Change→pct_chg_1d y
# la columna de volumen del periodo → alias canónico; el filtro puede usarlos todos a la vez
def test_full_alias_map_supports_filter_on_all_aliases():
    csv = "\n".join([
        _HEADER_5D,
        _row_5d("AAA", price=10.0, vol=2_000_000, pct1d="+2.00%"),   # pasa todo
        _row_5d("BBB", price=10.0, vol=2_000_000, pct1d="-1.00%"),   # falla pct_chg_1d
        _row_5d("CCC", price=3.0, vol=2_000_000, pct1d="+2.00%"),    # falla price
        _row_5d("DDD", price=10.0, vol=500_000, pct1d="+2.00%"),     # falla vol
    ])
    filt = f"{_VOL_ALIAS} > 1e6 and price > 5 and pct_chg_1d > 0"
    assert UniverseSpec("k", filt).load(MockObjectStore(csv)) == ["AAA"]


# (#13) filtro sobre columna sin alias → ValueError con universo, filtro y columnas disponibles
def test_filter_on_unknown_column_raises_valueerror_with_context():
    csv = "\n".join([_HEADER_5D, _row_5d("AAA")])
    with pytest.raises(ValueError, match=r"universes/x\.csv.*columna_fantasma"):
        UniverseSpec("universes/x.csv", "columna_fantasma > 1").load(MockObjectStore(csv))
