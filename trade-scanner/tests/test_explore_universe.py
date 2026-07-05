"""#8/#9 (triaje E1–E8): explore_universe.py — footer por patrón Barchart + guard PERCENT.

#8: el footer se detecta por el patrón "Downloaded from Barchart..." y NO por forma del
símbolo; los tickers no estándar (BRK.B) deben quedar como filas de datos y reportarse
en la sección 4 (antes salían ocultos como "footer" y la sección quedaba siempre vacía).
#9: una columna porcentual vacía/sucia no debe abortar con `min([])`.

El script vive en scripts/ (montado como /Scripts, en PYTHONPATH dentro de run_tests.sh);
sin CLR.
"""
import pytest

explore_universe = pytest.importorskip(
    "explore_universe", reason="scripts/ no está en PYTHONPATH (correr vía run_tests.sh)"
)


def _row(symbol: str, pct: str = "+1.00%") -> dict:
    return {"Symbol": symbol, "Latest": "10.0", "%Change": pct, "5D Avg Vol": "2000000"}


# (#8) footer por patrón; BRK.B es DATO (no footer)
def test_classify_rows_footer_by_pattern_keeps_nonstandard_tickers():
    footer = {"Symbol": 'Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT',
              "Latest": "", "%Change": "", "5D Avg Vol": ""}
    data, footers = explore_universe.classify_rows([_row("AAPL"), _row("BRK.B"), footer])
    assert [r["Symbol"] for r in data] == ["AAPL", "BRK.B"]
    assert footers == [footer]


# (#8) sección 4: el no estándar se reporta (ya no se lo traga el footer)
def test_nonstandard_symbols_reported_in_output(tmp_path, capsys):
    csv_file = tmp_path / "u.csv"
    csv_file.write_text(
        "Symbol,Latest,%Change,5D Avg Vol\n"
        "AAPL,10.0,+1.00%,2000000\n"
        "BRK.B,300.0,+0.50%,3000000\n"
        '"Downloaded from Barchart.com as of 06-05-2026 08:51pm CDT",,,\n'
    )
    explore_universe.run(str(csv_file))
    out = capsys.readouterr().out
    assert "BRK.B" in out
    assert "Encontrados (1)" in out          # sección 4 no vacía
    assert "Filas de footer descartadas:       1" in out


# (#9) columna porcentual completamente vacía → no aborta con min([])
def test_empty_percent_column_does_not_crash(tmp_path, capsys):
    csv_file = tmp_path / "u.csv"
    csv_file.write_text(
        "Symbol,Latest,%Change,5D Avg Vol\n"
        "AAPL,10.0,,2000000\n"
        "MSFT,20.0,,3000000\n"
    )
    explore_universe.run(str(csv_file))   # no debe lanzar
    out = capsys.readouterr().out
    assert "sin valores válidos" in out
