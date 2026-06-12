#!/usr/bin/env python3
"""stooq_to_lean.py — Converter host-side: CSV en formato Stooq → zip diario LEAN.

POR QUÉ (D3 de Etapa 5B): el boundary de agnosticidad de fuente exige que todo lo que
produce datos escriba archivos en formato LEAN dentro de `data/equity/usa/daily/`; `main.py`
solo lee vía `self.history`/feed y nunca sabe de dónde vino el zip. Este script es el lado
PRODUCTOR (data-prep fuera del algoritmo, análogo a seed_sample_data.sh). Sin SDK de datos:
stdlib pura (csv + zipfile).

ENTRADA (formato Stooq daily): header `Date,Open,High,Low,Close,Volume` (Stooq incluye a
veces `Adj Close`/`OpenInt`, que se ignoran), fechas `YYYY-MM-DD`, precios decimales
split-adjusted. El orden de filas de Stooq no se asume: SIEMPRE se reordena ascendente.

SALIDA (formato LEAN daily): `<sym>.csv` dentro de `<sym>.zip`, una fila por día:
  `YYYYMMDD 00:00,O*10000,H*10000,L*10000,C*10000,Volume`
Los precios van en deci-centavos enteros (×10000); el volumen entero crudo.

FETCH (T5.4): la descarga automática desde Stooq está bloqueada por anti-bot (proof-of-work
JS) + cuota diaria de descargas CSV ('Access denied'). Por eso el CSV de entrada se baja
manualmente del navegador (Stooq lo permite) y se pasa por --input. El fetch automatizado
se difiere a Etapa 9 (ver ADR-003). El converter es agnóstico a CÓMO llegó el CSV.

USO:
  python scripts/stooq_to_lean.py --input spy_us_d.csv --symbol SPY \
      --out data/equity/usa/daily
"""
from __future__ import annotations

import argparse
import csv
import io
import zipfile
from pathlib import Path

# Header canónico de Stooq daily; comparamos en minúsculas para tolerar variaciones.
_STOOQ_COLS = {"date", "open", "high", "low", "close", "volume"}
_PRICE_SCALE = 10000  # LEAN: precios en deci-centavos enteros.


class ConvertError(ValueError):
    """Entrada Stooq malformada o sin filas válidas."""


def parse_stooq_csv(text: str) -> list[tuple[str, float, float, float, float, int]]:
    """Parsea CSV Stooq → filas (date 'YYYY-MM-DD', o, h, l, c, vol) ordenadas ascendente.

    Filas con valores no numéricos (ej. 'N/D' de Stooq en días sin dato) se descartan.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ConvertError("CSV vacío o sin header")
    cols = {c.strip().lower(): c for c in reader.fieldnames}
    missing = _STOOQ_COLS - cols.keys()
    if missing:
        raise ConvertError(
            f"Columnas Stooq faltantes: {sorted(missing)} (header={reader.fieldnames})"
        )

    rows: list[tuple[str, float, float, float, float, int]] = []
    skipped = 0
    for rec in reader:
        try:
            date = rec[cols["date"]].strip()
            o = float(rec[cols["open"]])
            h = float(rec[cols["high"]])
            low = float(rec[cols["low"]])
            c = float(rec[cols["close"]])
            v = int(round(float(rec[cols["volume"]])))
        except (ValueError, KeyError, AttributeError):
            skipped += 1
            continue
        rows.append((date, o, h, low, c, v))

    if not rows:
        raise ConvertError("Sin filas numéricas válidas tras el parseo")
    if skipped:
        print(f"  [stooq] {skipped} filas descartadas (valores no numéricos)")

    rows.sort(key=lambda r: r[0])  # ascendente por fecha, sin asumir orden de origen
    return rows


def to_lean_rows(rows: list[tuple[str, float, float, float, float, int]]) -> list[str]:
    """Filas Stooq parseadas → líneas en formato LEAN daily (deci-centavos enteros)."""
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
    """Escribe `<sym>.csv` dentro de `<sym>.zip` en out_dir (nombres en minúsculas)."""
    sym = symbol.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{sym}.zip"
    body = "\n".join(lean_rows) + "\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{sym}.csv", body)
    return zip_path


def convert(input_csv: Path, symbol: str, out_dir: Path) -> Path:
    """Pipeline completo: lee CSV Stooq → LEAN rows → escribe zip. Devuelve la ruta del zip."""
    text = input_csv.read_text()
    rows = parse_stooq_csv(text)
    lean_rows = to_lean_rows(rows)
    zip_path = write_lean_zip(symbol, lean_rows, out_dir)
    print(
        f"  [stooq→lean] {symbol}: {len(lean_rows)} barras "
        f"({rows[0][0]}..{rows[-1][0]}) → {zip_path}"
    )
    return zip_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Convierte CSV Stooq daily a zip LEAN.")
    ap.add_argument("--input", required=True, type=Path, help="CSV Stooq de entrada")
    ap.add_argument("--symbol", required=True, help="Ticker (ej. SPY)")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("data/equity/usa/daily"),
        help="Directorio destino (default: data/equity/usa/daily)",
    )
    args = ap.parse_args()
    convert(args.input, args.symbol, args.out)


if __name__ == "__main__":
    main()
