"""#15/#16 (triaje E1–E8): preflight de los datos de validación de E5.

Los tests de regresión SMA (`test_sma_regression.py`, `test_t5_stooq_crosscheck.py`) usan
`skipif` sobre rutas bajo `data/` (gitignoreado): en un checkout limpio la suite quedaba
VERDE sin ejercer el criterio central de E5 (fidelidad de precios + matemática SMA).

Este preflight FALLA (no salta) si faltan los datos, con la instrucción de seed. Nota:
la Etapa 5B sigue "en progreso" en PLAN (F2/F3: validación manual ≤0,25% + fixture
autoritativo); este guard evita el verde falso mientras tanto, no cierra la etapa.
"""
import os
from pathlib import Path

_DATA_DIR = Path(
    os.environ.get("TRADE_SCANNER_DATA")
    or Path(__file__).resolve().parents[2] / "data"
)

# ruta relativa bajo data/ → cómo regenerarla
REQUIRED = {
    "equity/usa/daily/spy.zip": "bash scripts/seed_sample_data.sh",
    "stooq_lean/daily/spy.zip": "converter Stooq (scripts/stooq_to_lean.py)",
    "stooq/spy_us_d.csv": "descargar CSV Stooq SPY (ver etapa-05b-t5-3)",
}


def test_e5_validation_data_present():
    missing = [
        f"{rel}  (regenerar: {how})"
        for rel, how in REQUIRED.items()
        if not (_DATA_DIR / rel).exists()
    ]
    assert not missing, (
        "Datos de validación E5 ausentes — los tests de regresión SMA/Stooq se saltarían "
        "en silencio y la suite quedaría verde sin ejercerlos:\n  " + "\n  ".join(missing)
    )
