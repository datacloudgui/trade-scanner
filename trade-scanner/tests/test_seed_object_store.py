"""#7 (triaje E1–E8): seed_object_store.sh debe sembrar el CSV MÁS RECIENTE por la fecha
del nombre (MM-DD-YYYY, PLAN §5), no por orden lexicográfico del nombre.

Caso que rompía: 12-31-2025 vs 01-02-2026 — lexicográficamente "12-31-2025" > "01-02-2026",
así que `sort | tail -1` sembraba el universo MÁS VIEJO al cruzar mes/año.

Sin CLR: ejecuta el script real vía subprocess con dirs temporales (overrides por env var).
El script se resuelve por TRADE_SCANNER_SCRIPTS (montado en /Scripts por run_tests.sh) con
fallback a <workspace>/scripts para corridas en el host.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(
    os.environ.get("TRADE_SCANNER_SCRIPTS")
    or Path(__file__).resolve().parents[2] / "scripts"
)
SCRIPT = SCRIPTS_DIR / "seed_object_store.sh"


def _run_seed(tmp_path: Path, csv_files: dict[str, str]) -> tuple[Path, Path]:
    """Arma un workspace temporal (config/ + object-store con `csv_files`) y corre el script."""
    data_dir = tmp_path / "object-store"
    data_dir.mkdir()
    for filename, content in csv_files.items():
        (data_dir / filename).write_text(content)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "strategies.json").write_text("{}")
    dest = tmp_path / "storage"

    env = dict(
        os.environ,
        TRADE_SCANNER_CONFIG_SRC=str(config_dir),
        TRADE_SCANNER_UNIVERSES_SRC=str(tmp_path / "universes"),  # no existe → sección 4 se salta
        TRADE_SCANNER_OBJECT_STORE_SRC=str(data_dir),
        TRADE_SCANNER_STORAGE=str(dest),
    )
    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, f"script falló:\n{result.stdout}\n{result.stderr}"
    return data_dir, dest


@pytest.mark.skipif(not SCRIPT.exists(), reason="seed_object_store.sh no montado")
def test_seed_selects_most_recent_by_date_across_year_boundary(tmp_path):
    """12-31-2025 vs 01-02-2026: debe ganar 01-02-2026 (fecha real, no lexicográfica)."""
    data_dir, dest = _run_seed(
        tmp_path,
        {
            "sp500-advances-12-31-2025.csv": "Symbol\nOLD\n",
            "sp500-advances-01-02-2026.csv": "Symbol\nNEW\n",
        },
    )
    assert (dest / "universes/swing_advances.csv").read_text() == "Symbol\nNEW\n"
    # El sembrado se archiva en processed/; el viejo queda sin procesar para trazabilidad.
    assert (data_dir / "processed/sp500-advances-01-02-2026.csv").exists()
    assert (data_dir / "sp500-advances-12-31-2025.csv").exists()


@pytest.mark.skipif(not SCRIPT.exists(), reason="seed_object_store.sh no montado")
def test_seed_selects_most_recent_within_same_month(tmp_path):
    """Mismo mes: 06-18-2026 > 06-05-2026 (el orden por fecha también cubre el caso simple)."""
    _, dest = _run_seed(
        tmp_path,
        {
            "sp500-declines-06-05-2026.csv": "Symbol\nOLD\n",
            "sp500-declines-06-18-2026.csv": "Symbol\nNEW\n",
        },
    )
    assert (dest / "universes/swing_declines.csv").read_text() == "Symbol\nNEW\n"
