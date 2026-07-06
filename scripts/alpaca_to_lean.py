"""alpaca_to_lean.py — Downloader host-side: barras diarias de Alpaca REST → zips LEAN.

POR QUÉ (Opción C de ADR-002, T3 de Etapa 9A): el screener necesita historia DIARIA real
(de ahí salen las SMAs D/W/M vía consolidators). Alpaca la entrega por REST con la sola API
key —sin QC, sin módulo NuGet—. Este script es el lado PRODUCTOR (data-prep fuera del motor,
como stooq_to_lean.py y seed_sample_data.sh): descarga, escribe `data/equity/usa/daily/<sym>.zip`
y termina. `main.py`/`core/*` NUNCA hablan con Alpaca; en runtime solo leen el zip vía el
DefaultDataProvider de lean.json (D9A.1).

DISEÑO:
- El formato LEAN no se reimplementa: se reusa el emisor compartido `lean_daily.py` (D9A.3).
- `adjustment=split` para casar con el split-only adjusted de Stooq (5B) y la referencia (D9A.3).
- Multi-símbolo + paginación + throttle viven AQUÍ, no en el algoritmo (D9-1).
- Credenciales: mismo loader que check_alpaca_credentials.py; solo `.env`/entorno (D9A.4).
- Sin SDK de Alpaca: stdlib pura (urllib). El fetch HTTP está aislado en `_get` (mockeable).

USO:
  python scripts/alpaca_to_lean.py --universe universes/sample_dev.csv
  python scripts/alpaca_to_lean.py --symbols SPY,AAPL --start 2016-01-01 --out data/alpaca_lean/daily
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from check_alpaca_credentials import get_credentials  # loader de credenciales (D9A.4)
from lean_daily import DailyBar, to_lean_rows, write_lean_zip  # emisor LEAN compartido (D9A.3)

DATA_HOST = "https://data.alpaca.markets"
_TICKER_RE = re.compile(r"^[A-Z]{1,5}$")  # mismo criterio que core/universe.py (strip de footer)
_MAX_SYMBOLS_PER_REQUEST = 100  # ≤200 admite Alpaca; 100 mantiene la URL acotada
_PAGE_LIMIT = 10000             # máx. de barras por página que devuelve Alpaca
_REQUEST_PAUSE = 0.35           # ~3 req/s < 200 req/min de free tier (throttle, D9-1)


def read_universe_symbols(csv_path: Path) -> list[str]:
    """Extrae los tickers de la columna `Symbol`, descartando el footer (no-ticker)."""
    text = csv_path.read_text()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or "Symbol" not in reader.fieldnames:
        raise ValueError(f"{csv_path}: falta la columna 'Symbol' (header={reader.fieldnames})")
    symbols: list[str] = []
    for rec in reader:
        sym = (rec.get("Symbol") or "").strip().upper()
        if _TICKER_RE.match(sym):
            symbols.append(sym)
    # Dedup preservando orden, luego alfabético para reproducibilidad.
    return sorted(dict.fromkeys(symbols))


def _get(url: str, headers: dict[str, str]) -> dict:
    """Único punto de red (aislado para poder mockearlo en tests). GET → JSON."""
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def alpaca_bars_to_rows(bars: list[dict]) -> list[DailyBar]:
    """Barras Alpaca [{t,o,h,l,c,v}, ...] → tuplas LEAN (date 'YYYY-MM-DD', o,h,l,c,v).

    El `t` de una barra diaria es ISO (`2026-06-15T04:00:00Z`); la fecha de sesión es `t[:10]`.
    Filas con campos faltantes o no numéricos se descartan (robustez ante días sin dato).
    """
    rows: list[DailyBar] = []
    for bar in bars:
        try:
            day = str(bar["t"])[:10]
            o, h, low, c = float(bar["o"]), float(bar["h"]), float(bar["l"]), float(bar["c"])
            v = int(round(float(bar["v"])))
        except (KeyError, ValueError, TypeError):
            continue
        rows.append((day, o, h, low, c, v))
    rows.sort(key=lambda r: r[0])  # ascendente por fecha (no asumimos orden de la API)
    return rows


def _chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_daily_bars(
    symbols: list[str],
    start: str,
    end: str,
    key_id: str,
    secret: str,
    *,
    feed: str = "iex",
    adjustment: str = "split",
    sleep=time.sleep,
) -> dict[str, list[DailyBar]]:
    """Descarga barras diarias de Alpaca para `symbols` en [start, end].

    Resuelve multi-símbolo (chunks ≤100), paginación (`next_page_token`) y throttle
    (~200 req/min) — todo en la capa de descarga, fuera del algoritmo (D9-1).
    """
    headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}
    out: dict[str, list[dict]] = {sym: [] for sym in symbols}

    for chunk in _chunks(symbols, _MAX_SYMBOLS_PER_REQUEST):
        page_token: str | None = None
        while True:
            params = {
                "symbols": ",".join(chunk),
                "timeframe": "1Day",
                "start": start,
                "end": end,
                "adjustment": adjustment,
                "feed": feed,
                "limit": str(_PAGE_LIMIT),
            }
            if page_token:
                params["page_token"] = page_token
            url = f"{DATA_HOST}/v2/stocks/bars?{urllib.parse.urlencode(params)}"
            payload = _get(url, headers)
            for sym, bars in (payload.get("bars") or {}).items():
                out.setdefault(sym, []).extend(bars or [])
            page_token = payload.get("next_page_token")
            if not page_token:
                break
            sleep(_REQUEST_PAUSE)  # throttle entre páginas
        sleep(_REQUEST_PAUSE)      # throttle entre chunks

    return {sym: alpaca_bars_to_rows(bars) for sym, bars in out.items()}


def download(
    symbols: list[str],
    out_dir: Path,
    start: str,
    end: str,
    key_id: str,
    secret: str,
    *,
    feed: str = "iex",
    adjustment: str = "split",
) -> dict[str, Path | None]:
    """Descarga y escribe un zip LEAN por símbolo. Devuelve {sym: ruta | None si sin datos}."""
    by_symbol = fetch_daily_bars(symbols, start, end, key_id, secret, feed=feed, adjustment=adjustment)
    written: dict[str, Path | None] = {}
    for sym in symbols:
        rows = by_symbol.get(sym) or []
        if not rows:
            print(f"  [alpaca→lean] {sym}: SIN barras en [{start}..{end}] — omitido (¿delisted/IEX?)")
            written[sym] = None
            continue
        zip_path = write_lean_zip(sym, to_lean_rows(rows), out_dir)
        print(f"  [alpaca→lean] {sym}: {len(rows)} barras ({rows[0][0]}..{rows[-1][0]}) → {zip_path}")
        written[sym] = zip_path
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description="Descarga barras diarias de Alpaca a formato LEAN.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--universe", type=Path, help="CSV de universo (columna Symbol)")
    src.add_argument("--symbols", help="lista de tickers separados por coma (ej. SPY,AAPL)")
    ap.add_argument("--start", default="2016-01-01", help="fecha inicio YYYY-MM-DD (default 2016-01-01)")
    ap.add_argument("--end", default=None, help="fecha fin YYYY-MM-DD (default: ayer)")
    ap.add_argument("--out", type=Path, default=Path("data/equity/usa/daily"), help="directorio destino")
    ap.add_argument("--feed", default="iex", help="feed Alpaca (iex free | sip pago)")
    ap.add_argument("--adjustment", default="split", help="ajuste de precios (split | raw | all | dividend)")
    args = ap.parse_args()

    if args.universe:
        symbols = read_universe_symbols(args.universe)
    else:
        symbols = sorted(dict.fromkeys(s.strip().upper() for s in args.symbols.split(",") if s.strip()))
    if not symbols:
        print("ERROR: universo vacío (sin tickers válidos).")
        sys.exit(2)

    end = args.end or (date.today() - timedelta(days=1)).isoformat()
    key_id, secret = get_credentials()

    print(f"Descargando {len(symbols)} símbolo(s) 1Day [{args.start}..{end}] feed={args.feed} → {args.out}")
    written = download(symbols, args.out, args.start, end, key_id, secret, feed=args.feed, adjustment=args.adjustment)

    ok = sum(1 for p in written.values() if p is not None)
    empty = [s for s, p in written.items() if p is None]
    print(f"Listo: {ok}/{len(symbols)} con datos." + (f" Sin datos: {', '.join(empty)}" if empty else ""))
    # Gate: ≠0 solo si NINGÚN símbolo trajo datos (fallo total de conectividad/credenciales).
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
