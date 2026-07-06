"""lean_daily.py — Emisor compartido: filas OHLCV → zip diario en formato LEAN.

POR QUÉ (D9A.3 de Etapa 9A): tanto el converter Stooq (5B) como el downloader Alpaca (9A)
deben escribir EXACTAMENTE el mismo formato LEAN daily. Para no duplicar (ni divergir) el
emisor, vive aquí y lo importan ambos productores. La fuente de las filas cambia (CSV Stooq
vs REST Alpaca); el formato de salida es uno solo.

FORMATO LEAN daily: `<sym>.csv` dentro de `<sym>.zip`, una fila por día:
  `YYYYMMDD 00:00,O*10000,H*10000,L*10000,C*10000,Volume`
Precios en deci-centavos enteros (×10000); volumen entero crudo.

Sin dependencias externas: stdlib pura (zipfile).
"""
from __future__ import annotations

import zipfile
from pathlib import Path

# Tupla canónica de una barra diaria: (date 'YYYY-MM-DD', open, high, low, close, volume).
DailyBar = tuple[str, float, float, float, float, int]

_PRICE_SCALE = 10000  # LEAN: precios en deci-centavos enteros.


def to_lean_rows(rows: list[DailyBar]) -> list[str]:
    """Barras (date 'YYYY-MM-DD', o, h, l, c, v) → líneas en formato LEAN daily."""
    out: list[str] = []
    for date, o, h, low, c, v in rows:
        stamp = date.replace("-", "")  # YYYY-MM-DD → YYYYMMDD
        out.append(
            f"{stamp} 00:00,"
            f"{round(o * _PRICE_SCALE)},"
            f"{round(h * _PRICE_SCALE)},"
            f"{round(low * _PRICE_SCALE)},"
            f"{round(c * _PRICE_SCALE)},"
            f"{v}"
        )
    return out


def write_lean_zip(symbol: str, lean_rows: list[str], out_dir: Path) -> Path:
    """Escribe `<sym>.csv` dentro de `<sym>.zip` en out_dir (nombres en minúsculas).

    Modo "w": re-escribir el mismo símbolo/rango regenera el zip limpio (idempotente).
    """
    sym = symbol.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{sym}.zip"
    body = "\n".join(lean_rows) + "\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{sym}.csv", body)
    return zip_path
