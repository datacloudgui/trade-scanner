"""
Perfilado de un CSV de universo exportado de Barchart.
Uso: python scripts/explore_universe.py <ruta_csv>
"""
import sys
import csv
import re
from pathlib import Path

EXPECTED_COLUMNS = [
    "Symbol", "Name", "5D %Chg", "Latest", "Change",
    "%Change", "5D Chg", "5D High", "5D Low", "5D Avg Vol", "Time",
]
SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")
PERCENT_COLUMNS = ["5D %Chg", "%Change"]
NUMERIC_COLUMNS = ["Latest", "Change", "5D Chg", "5D High", "5D Low", "5D Avg Vol"]
VOL_THRESHOLDS = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]


def parse_percent(value: str) -> float | None:
    try:
        return float(value.strip().lstrip("+").rstrip("%")) / 100
    except (ValueError, AttributeError):
        return None


def parse_numeric(value: str) -> float | None:
    try:
        return float(value.strip().replace(",", ""))
    except (ValueError, AttributeError):
        return None


def run(csv_path: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        print(f"ERROR: archivo no encontrado: {csv_path}")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"PERFILADO: {path.name}")
    print(f"{'='*70}")

    # --- Lectura bruta ---
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns_present = reader.fieldnames or []
        raw_rows = list(reader)

    total_raw = len(raw_rows)

    # --- Detección de footer (símbolo inválido) ---
    data_rows = []
    footer_rows = []
    for row in raw_rows:
        sym = row.get("Symbol", "").strip()
        if SYMBOL_RE.match(sym):
            data_rows.append(row)
        else:
            footer_rows.append(row)

    # --- Sección 1: estructura general ---
    print(f"\n--- Estructura general ---")
    print(f"  Filas totales (incluyendo footer): {total_raw}")
    print(f"  Filas de datos:                    {len(data_rows)}")
    print(f"  Filas de footer descartadas:       {len(footer_rows)}")
    if footer_rows:
        for fr in footer_rows:
            print(f"  Footer detectado: {dict(fr)}")

    print(f"\n  Columnas esperadas ({len(EXPECTED_COLUMNS)}): {EXPECTED_COLUMNS}")
    print(f"  Columnas presentes ({len(columns_present)}): {list(columns_present)}")
    missing = [c for c in EXPECTED_COLUMNS if c not in columns_present]
    extra = [c for c in columns_present if c not in EXPECTED_COLUMNS]
    if missing:
        print(f"  FALTANTES: {missing}")
    if extra:
        print(f"  EXTRA (se ignorarán): {extra}")
    if not missing and not extra:
        print("  Columnas: coinciden exactamente con las esperadas.")

    # --- Sección 2: análisis por columna ---
    print(f"\n--- Análisis por columna ---")

    for col in columns_present:
        values_raw = [r.get(col, "").strip() for r in data_rows]
        nulls = sum(1 for v in values_raw if v == "")

        if col in PERCENT_COLUMNS:
            parsed = [parse_percent(v) for v in values_raw if v != ""]
            valid = [v for v in parsed if v is not None]
            samples = [v for v in values_raw if v != ""][:3]
            print(f"  {col:15s} | tipo: percent% → float | nulos: {nulls} | "
                  f"rango: [{min(valid)*100:.2f}%, {max(valid)*100:.2f}%] | "
                  f"muestras crudas: {samples}")

        elif col in NUMERIC_COLUMNS:
            parsed = [parse_numeric(v) for v in values_raw if v != ""]
            valid = [v for v in parsed if v is not None]
            if valid:
                print(f"  {col:15s} | tipo: float | nulos: {nulls} | "
                      f"rango: [{min(valid):.2f}, {max(valid):.2f}]")
            else:
                print(f"  {col:15s} | tipo: float | nulos: {nulls} | sin valores válidos")

        else:
            samples = [v for v in values_raw if v != ""][:3]
            print(f"  {col:15s} | tipo: string | nulos: {nulls} | muestras: {samples}")

    # --- Sección 3: simulación de filtros ---
    print(f"\n--- Simulación de filtros de volumen (5D Avg Vol) ---")
    vols = [parse_numeric(r.get("5D Avg Vol", "")) for r in data_rows]
    prices = [parse_numeric(r.get("Latest", "")) for r in data_rows]

    print(f"  {'Umbral':>12s} | {'Tickers que pasan':>18s}")
    print(f"  {'-'*12}-+-{'-'*18}")
    for threshold in VOL_THRESHOLDS:
        passing = sum(1 for v in vols if v is not None and v > threshold)
        label = f"> {threshold/1e6:.1f}M" if threshold >= 1_000_000 else f"> {threshold/1e3:.0f}K"
        print(f"  {label:>12s} | {passing:>18d}")

    # Filtro combinado
    combined = sum(
        1 for v, p in zip(vols, prices)
        if v is not None and p is not None and v > 1_000_000 and p > 5
    )
    print(f"\n  Filtro combinado (avg_vol_5d > 1M AND price > 5): {combined} tickers pasan")

    # Volumen: estadísticas adicionales
    vols_valid = [v for v in vols if v is not None]
    if vols_valid:
        sorted_vols = sorted(vols_valid)
        n = len(sorted_vols)
        median_vol = sorted_vols[n // 2]
        print(f"  Mediana vol: {median_vol:,.0f} | Máximo: {max(vols_valid):,.0f}")

    # --- Sección 4: símbolos no estándar ---
    non_standard = [r.get("Symbol", "").strip() for r in data_rows
                    if not SYMBOL_RE.match(r.get("Symbol", "").strip())]
    print(f"\n--- Símbolos no estándar (no ^[A-Z]{{1,5}}$) en filas de datos ---")
    if non_standard:
        print(f"  Encontrados ({len(non_standard)}): {non_standard}")
    else:
        print("  Ninguno — todos los símbolos son estándar.")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/explore_universe.py <ruta_csv>")
        sys.exit(1)
    run(sys.argv[1])
