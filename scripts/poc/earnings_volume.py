"""earnings_volume.py — POC host-side: earnings BMO/AMC + volumen promedio 10d vía Finnhub.

POR QUÉ: reemplaza el flujo manual de Finviz (earnings + filtro de volumen + AMC/BMO +
próxima semana) por una llamada programática a Finnhub free tier. Es un POC EXPLORATORIO
del lado PRODUCTOR (como `alpaca_to_lean.py` / `check_alpaca_credentials.py`): vive fuera del
motor LEAN, NO toca `main.py`/`core/*` y solo emite datos (CSV + eco a stdout). Ningún import
de Finnhub entra al algoritmo. Ver `scripts/poc/SPEC-earnings-volume-finnhub.md`.

QUÉ HACE: dada una de cuatro selecciones de fecha, pide el earnings calendar US de Finnhub
(`/calendar/earnings`), aplica el filtro de bordes BMO/AMC (D-POC.2) y adjunta a cada símbolo
el volumen promedio diario a 10 días (`10DayAverageTradingVolume` de `/stock/metric`). Emite un
CSV con columnas `ticker, hour, avg_volume` (avg_volume en millones de acciones/día).

USO:
    python scripts/poc/earnings_volume.py (--next-week | --next-day | --range S E | --date D)
                                          [--universe config/universes/<u>.csv]
                                          [--min-avg-vol N]   # filtra avg_volume >= N (millones)
                                          [--csv out.csv]     # default: scripts/poc/out/...

CREDENCIALES (nunca en el repo): `FINNHUB_API_KEY` se lee del entorno o del `.env`
gitignoreado de la raíz. No se hardcodea ni se imprime. Solo stdlib (`urllib`): corre con el
Python del `.venv` sin instalar `finnhub-python` ni `requests` (D-POC.6).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _WORKSPACE / ".env"
_DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "out"

_BASE_URL = "https://finnhub.io/api/v1"
_METRIC_THROTTLE_S = 1.1  # ~60 req/min free tier (D-POC.5)


# --------------------------------------------------------------------------- #
# Credenciales                                                                 #
# --------------------------------------------------------------------------- #
def load_env_file(path: Path) -> dict[str, str]:
    """Parsea un .env simple (KEY=VALUE por línea) sin depender de python-dotenv."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str:
    """Devuelve FINNHUB_API_KEY, priorizando el entorno sobre el .env. Exit≠0 si falta."""
    file_env = load_env_file(_ENV_FILE)
    api_key = os.environ.get("FINNHUB_API_KEY") or file_env.get("FINNHUB_API_KEY")
    if not api_key:
        print("ERROR: falta FINNHUB_API_KEY (ni en el entorno ni en .env).", file=sys.stderr)
        sys.exit(2)
    return api_key


# --------------------------------------------------------------------------- #
# Cliente Finnhub (inyectable → tests con stub sin red)                        #
# --------------------------------------------------------------------------- #
class FinnhubClient:
    """Cliente REST mínimo sobre urllib. La API key va como query param `token` (nunca se imprime)."""

    def __init__(self, api_key: str, throttle_s: float = _METRIC_THROTTLE_S) -> None:
        self._api_key = api_key
        self._throttle_s = throttle_s
        self._metric_cache: dict[str, dict] = {}
        self._last_metric_call = 0.0

    def _get(self, endpoint: str, params: dict[str, str]) -> dict:
        query = urllib.parse.urlencode({**params, "token": self._api_key})
        request = urllib.request.Request(f"{_BASE_URL}{endpoint}?{query}")
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    def earnings_calendar(self, start: date, end: date) -> list[dict]:
        """GET /calendar/earnings en [start, end]. Una sola llamada para todo el rango."""
        payload = self._get(
            "/calendar/earnings",
            {"from": start.isoformat(), "to": end.isoformat()},
        )
        return payload.get("earningsCalendar") or []

    def stock_metric(self, symbol: str) -> dict:
        """GET /stock/metric?metric=all para un símbolo, con caché + throttle (~60 req/min)."""
        if symbol in self._metric_cache:
            return self._metric_cache[symbol]
        elapsed = time.monotonic() - self._last_metric_call
        if elapsed < self._throttle_s:
            time.sleep(self._throttle_s - elapsed)
        payload = self._get("/stock/metric", {"symbol": symbol, "metric": "all"})
        self._last_metric_call = time.monotonic()
        metric = payload.get("metric") or {}
        self._metric_cache[symbol] = metric
        return metric


# --------------------------------------------------------------------------- #
# Resolución de las 4 opciones → (start, end, boundary_filter)  (D-POC.1/.4)   #
# --------------------------------------------------------------------------- #
def _next_monday(today: date) -> date:
    """Lunes de la próxima semana (estrictamente futuro; si hoy es lunes, salta al siguiente)."""
    days_ahead = (0 - today.weekday() + 7) % 7 or 7
    return today + timedelta(days=days_ahead)


def resolve_window(args: argparse.Namespace, today: date) -> tuple[date, date, bool, str]:
    """Traduce la opción de CLI a (start, end, boundary_filter, label). Días naturales (D-POC.4)."""
    if args.date is not None:
        d = _parse_date(args.date)
        return d - timedelta(days=1), d, True, "date"
    if args.next_day:
        return today, today + timedelta(days=1), True, "next-day"
    if args.range is not None:
        s, e = _parse_date(args.range[0]), _parse_date(args.range[1])
        if e < s:
            print("ERROR: en --range S E se requiere S <= E.", file=sys.stderr)
            sys.exit(2)
        if s == e:  # D-POC.2: --range con S==E se trata como --date S
            return s - timedelta(days=1), s, True, "range"
        return s, e, True, "range"
    # --next-week: lunes→viernes próximos, sin filtro de bordes
    monday = _next_monday(today)
    return monday, monday + timedelta(days=4), False, "next-week"


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        print(f"ERROR: fecha inválida '{value}' (formato esperado YYYY-MM-DD).", file=sys.stderr)
        sys.exit(2)


# --------------------------------------------------------------------------- #
# Núcleo: collect + filtro de bordes (D-POC.1 / D-POC.2)                       #
# --------------------------------------------------------------------------- #
def _apply_boundary_filter(rows: list[dict], start: date, end: date) -> list[dict]:
    """Filtro de bordes (D-POC.2): start→solo AMC, end→solo BMO, interior→todo."""
    kept: list[dict] = []
    for row in rows:
        row_date = row.get("date")
        hour = (row.get("hour") or "").lower()
        if row_date == start.isoformat():
            if hour == "amc":
                kept.append(row)
            else:
                print(f"  [borde start] descartado {row.get('symbol')} hour='{hour or '∅'}' "
                      f"(solo se conserva AMC)", file=sys.stderr)
        elif row_date == end.isoformat():
            if hour == "bmo":
                kept.append(row)
            else:
                print(f"  [borde end] descartado {row.get('symbol')} hour='{hour or '∅'}' "
                      f"(solo se conserva BMO)", file=sys.stderr)
        else:  # día interior: se conserva todo (ventana de tenencia continua)
            kept.append(row)
    return kept


def collect(
    client: FinnhubClient,
    start: date,
    end: date,
    boundary_filter: bool,
    universe: set[str] | None = None,
) -> list[dict]:
    """Núcleo D-POC.1: pide el calendar del rango, aplica filtro de bordes y de universo.

    Devuelve filas crudas de Finnhub (dict con al menos `symbol`, `hour`, `date`).
    """
    rows = client.earnings_calendar(start, end)
    if boundary_filter:
        rows = _apply_boundary_filter(rows, start, end)
    if universe is not None:
        rows = [r for r in rows if (r.get("symbol") or "").upper() in universe]
    return rows


# --------------------------------------------------------------------------- #
# Join de volumen (D-POC.3)                                                    #
# --------------------------------------------------------------------------- #
def attach_volume(client: FinnhubClient, rows: list[dict]) -> list[dict]:
    """Adjunta 10Day/3Month AverageTradingVolume a cada fila. None + warning si falta."""
    enriched: list[dict] = []
    for row in rows:
        symbol = (row.get("symbol") or "").upper()
        metric = client.stock_metric(symbol) if symbol else {}
        avg_10d = metric.get("10DayAverageTradingVolume")
        avg_3m = metric.get("3MonthAverageTradingVolume")
        if avg_10d is None:
            print(f"  [vol] sin 10DayAverageTradingVolume para {symbol} → None", file=sys.stderr)
        enriched.append({
            "ticker": symbol,
            "hour": (row.get("hour") or "").lower(),
            "avg_volume": avg_10d,
            "avg_volume_3m": avg_3m,
            "date": row.get("date"),
        })
    return enriched


# --------------------------------------------------------------------------- #
# Universo opcional (D-POC.5)                                                  #
# --------------------------------------------------------------------------- #
def load_universe(path: Path) -> set[str]:
    """Set de tickers de la primera columna del CSV (salta cabecera 'Symbol' y footers con espacios)."""
    tickers: set[str] = set()
    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            cell = row[0].strip()
            if not cell or " " in cell or cell.lower() == "symbol":
                continue
            tickers.add(cell.upper())
    return tickers


# --------------------------------------------------------------------------- #
# Salida CSV (D-POC.7)                                                         #
# --------------------------------------------------------------------------- #
def write_csv(rows: list[dict], path: Path) -> None:
    """Escribe el CSV canónico `ticker, hour, avg_volume` (avg_volume en millones acciones/día)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ticker", "hour", "avg_volume_10d_millions"])
        for row in rows:
            writer.writerow([row["ticker"], row["hour"], row["avg_volume"]])


def echo_table(rows: list[dict]) -> None:
    """Eco de conveniencia a stdout (mismo contenido que el CSV + 3m como contexto)."""
    print(f"{'ticker':<8} {'hour':<5} {'avg_vol_10d(M)':>15} {'avg_vol_3m(M)':>15}")
    print("-" * 47)
    for row in rows:
        v10 = "None" if row["avg_volume"] is None else f"{row['avg_volume']:.2f}"
        v3m = "None" if row["avg_volume_3m"] is None else f"{row['avg_volume_3m']:.2f}"
        print(f"{row['ticker']:<8} {row['hour']:<5} {v10:>15} {v3m:>15}")


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="POC: earnings BMO/AMC + volumen promedio 10d vía Finnhub (host-side).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--next-week", action="store_true", help="lunes→viernes próximos, sin filtro de bordes")
    group.add_argument("--next-day", action="store_true", help="AMC(hoy) + BMO(mañana)")
    group.add_argument("--range", nargs=2, metavar=("S", "E"), help="rango [S, E] con filtro de bordes")
    group.add_argument("--date", metavar="D", help="AMC(D-1) + BMO(D)")
    parser.add_argument("--universe", metavar="CSV", help="filtra a los tickers del CSV antes del join de volumen")
    parser.add_argument("--min-avg-vol", type=float, metavar="N", help="excluye filas con avg_volume < N (millones)")
    parser.add_argument("--csv", metavar="PATH", help="ruta del CSV de salida (default: scripts/poc/out/...)")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    api_key = get_api_key()
    today = date.today()

    start, end, boundary_filter, label = resolve_window(args, today)

    universe: set[str] | None = None
    if args.universe:
        universe_path = Path(args.universe)
        if not universe_path.is_absolute():
            universe_path = _WORKSPACE / universe_path
        universe = load_universe(universe_path)
        print(f"Universo: {len(universe)} tickers de {args.universe}", file=sys.stderr)

    client = FinnhubClient(api_key)
    print(f"Earnings [{start} → {end}]  filtro_bordes={boundary_filter}", file=sys.stderr)

    try:
        rows = collect(client, start, end, boundary_filter, universe)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace").strip()
        print(f"❌ /calendar/earnings HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"❌ Error de red en /calendar/earnings: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("⚠️  Sin earnings tras el filtro para la ventana dada.", file=sys.stderr)

    if universe is None and len(rows) > 30:
        print(f"⚠️  {len(rows)} símbolos → ~{len(rows)} llamadas a /stock/metric "
              f"(~{len(rows) * _METRIC_THROTTLE_S:.0f}s). Considera --universe.", file=sys.stderr)

    enriched = attach_volume(client, rows)

    if args.min_avg_vol is not None:
        before = len(enriched)
        enriched = [r for r in enriched if r["avg_volume"] is not None and r["avg_volume"] >= args.min_avg_vol]
        print(f"--min-avg-vol {args.min_avg_vol}: {before} → {len(enriched)} filas", file=sys.stderr)

    if args.csv:
        out_path = Path(args.csv)
        if not out_path.is_absolute():
            out_path = _WORKSPACE / out_path
    else:
        out_path = _DEFAULT_OUT_DIR / f"earnings_{label}_{today:%Y%m%d}.csv"

    write_csv(enriched, out_path)
    echo_table(enriched)
    print(f"\n✅ {len(enriched)} filas → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
