"""Tests del downloader host-side `scripts/alpaca_to_lean.py` (Etapa 9A, T3).

El script corre en el `.venv` del host, pero se testea DENTRO de la imagen LEAN (run_tests.sh
monta `scripts/` en `/Scripts`). Se verifica SIN RED: el fetch HTTP (`_get`) se mockea. Cubre:
(a) lectura de universo con strip de footer, (b) parseo barra Alpaca → tupla LEAN y emisión de
la línea LEAN exacta vía el emisor compartido, (c) multi-símbolo + paginación en la capa de
descarga, (d) round-trip/idempotencia del zip.
"""
import zipfile
from pathlib import Path

import alpaca_to_lean as a2l
import lean_daily


def _noop_sleep(_seconds):  # throttle desactivado en tests
    return None


# ---------------------------------------------------------------------------
# (a) Lectura de universo: toma la columna Symbol, descarta el footer.
# ---------------------------------------------------------------------------

def test_read_universe_symbols_strips_footer(tmp_path: Path):
    csv = tmp_path / "u.csv"
    csv.write_text(
        'Symbol,Name,Latest\n'
        'SPY,"SPDR S&P 500",595.27\n'
        'AAPL,"Apple Inc",205.40\n'
        '"Downloaded from Barchart.com as of 06-05-2026"\n'
    )
    assert a2l.read_universe_symbols(csv) == ["AAPL", "SPY"]  # alfabético, sin footer


def test_read_universe_symbols_dedups(tmp_path: Path):
    csv = tmp_path / "u.csv"
    csv.write_text("Symbol\nIBM\nibm\nIBM\n")
    assert a2l.read_universe_symbols(csv) == ["IBM"]


# ---------------------------------------------------------------------------
# (b) Parseo Alpaca → tupla LEAN, y línea LEAN exacta (vía emisor compartido).
# ---------------------------------------------------------------------------

def test_alpaca_bars_to_rows_parses_and_sorts():
    bars = [
        {"t": "2026-06-15T04:00:00Z", "o": 293.99, "h": 297.78, "l": 291.75, "c": 296.53, "v": 1573337},
        {"t": "2026-06-12T04:00:00Z", "o": 290.0, "h": 295.0, "l": 289.5, "c": 294.0, "v": 1000000},
    ]
    rows = a2l.alpaca_bars_to_rows(bars)
    assert [r[0] for r in rows] == ["2026-06-12", "2026-06-15"]  # ordenado ascendente
    assert rows[1] == ("2026-06-15", 293.99, 297.78, 291.75, 296.53, 1573337)


def test_alpaca_bars_to_rows_skips_malformed():
    bars = [
        {"t": "2026-06-15T04:00:00Z", "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100},
        {"t": "2026-06-16T04:00:00Z", "o": None, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100},  # o inválido
        {"t": "2026-06-17T04:00:00Z", "h": 2.0, "l": 0.5, "c": 1.5, "v": 100},             # falta o
    ]
    rows = a2l.alpaca_bars_to_rows(bars)
    assert [r[0] for r in rows] == ["2026-06-15"]


def test_lean_line_matches_shared_emitter():
    rows = a2l.alpaca_bars_to_rows(
        [{"t": "2026-06-15T04:00:00Z", "o": 293.99, "h": 297.78, "l": 291.75, "c": 296.53, "v": 1573337}]
    )
    assert lean_daily.to_lean_rows(rows) == ["20260615 00:00,2939900,2977800,2917500,2965300,1573337"]


# ---------------------------------------------------------------------------
# (c) Multi-símbolo + paginación en la capa de descarga (red mockeada).
# ---------------------------------------------------------------------------

def test_fetch_paginates_and_merges(monkeypatch):
    # Dos páginas: la primera trae token; la segunda cierra. Dos símbolos en el chunk.
    pages = [
        {
            "bars": {
                "SPY": [{"t": "2026-06-12T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 10}],
                "AAPL": [{"t": "2026-06-12T04:00:00Z", "o": 2, "h": 2, "l": 2, "c": 2, "v": 20}],
            },
            "next_page_token": "TOK",
        },
        {
            "bars": {
                "SPY": [{"t": "2026-06-13T04:00:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 11}],
            },
            "next_page_token": None,
        },
    ]
    calls = {"n": 0, "tokens": []}

    def fake_get(url, headers):
        # Verifica que el page_token de la 2ª llamada viaja en la URL.
        calls["tokens"].append("page_token=TOK" in url)
        page = pages[calls["n"]]
        calls["n"] += 1
        return page

    monkeypatch.setattr(a2l, "_get", fake_get)
    result = a2l.fetch_daily_bars(
        ["SPY", "AAPL"], "2026-06-01", "2026-06-14", "k", "s", sleep=_noop_sleep
    )

    assert calls["n"] == 2                      # paginó: 2 requests
    assert calls["tokens"] == [False, True]     # 2ª request llevó el token
    assert [r[0] for r in result["SPY"]] == ["2026-06-12", "2026-06-13"]  # 2 páginas mergeadas
    assert [r[0] for r in result["AAPL"]] == ["2026-06-12"]


def test_fetch_chunks_large_universe(monkeypatch):
    # >100 símbolos ⇒ ≥2 requests (un chunk por cada ≤100).
    symbols = [f"S{i:03d}" for i in range(150)]
    seen_counts = []

    def fake_get(url, headers):
        # nº de símbolos pedidos en esta request (separados por coma, urlencoded como %2C).
        q = url.split("symbols=")[1].split("&")[0]
        seen_counts.append(len(q.split("%2C")))
        return {"bars": {}, "next_page_token": None}

    monkeypatch.setattr(a2l, "_get", fake_get)
    a2l.fetch_daily_bars(symbols, "2026-06-01", "2026-06-14", "k", "s", sleep=_noop_sleep)
    assert seen_counts == [100, 50]  # chunking ≤100


# ---------------------------------------------------------------------------
# (d) download(): escribe zip LEAN legible, omite símbolos sin datos, idempotente.
# ---------------------------------------------------------------------------

def test_download_writes_readable_zip_and_skips_empty(monkeypatch, tmp_path: Path):
    def fake_get(url, headers):
        return {
            "bars": {
                "SPY": [{"t": "2026-06-15T04:00:00Z", "o": 10, "h": 11, "l": 9, "c": 10.5, "v": 500}],
                # FB sin barras (delisted/sin IEX) → debe omitirse, sin zip.
            },
            "next_page_token": None,
        }

    monkeypatch.setattr(a2l, "_get", fake_get)
    written = a2l.download(["SPY", "FB"], tmp_path, "2026-06-01", "2026-06-16", "k", "s")

    assert written["FB"] is None
    spy_zip = written["SPY"]
    assert spy_zip == tmp_path / "spy.zip"
    with zipfile.ZipFile(spy_zip) as zf:
        body = zf.read("spy.csv").decode()
    assert body == "20260615 00:00,100000,110000,90000,105000,500\n"


def test_download_is_idempotent(monkeypatch, tmp_path: Path):
    def fake_get(url, headers):
        return {
            "bars": {"SPY": [{"t": "2026-06-15T04:00:00Z", "o": 10, "h": 11, "l": 9, "c": 10.5, "v": 500}]},
            "next_page_token": None,
        }

    expected = "20260615 00:00,100000,110000,90000,105000,500\n"
    monkeypatch.setattr(a2l, "_get", fake_get)

    a2l.download(["SPY"], tmp_path, "2026-06-01", "2026-06-16", "k", "s")
    with zipfile.ZipFile(tmp_path / "spy.zip") as zf:
        first = zf.read("spy.csv").decode()

    a2l.download(["SPY"], tmp_path, "2026-06-01", "2026-06-16", "k", "s")  # re-corre mismo rango
    with zipfile.ZipFile(tmp_path / "spy.zip") as zf:
        second = zf.read("spy.csv").decode()

    # Contenido idéntico tras re-correr (zip "w" regenera limpio, no acumula ni corrompe).
    assert first == second == expected
