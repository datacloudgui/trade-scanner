"""check_alpaca_credentials.py — Smoke test de las claves de Alpaca (pre-Etapa 9).

POR QUÉ: antes de intentar `lean live` con Alpaca (Etapa 9) conviene confirmar que
`ALPACA_KEY_ID` / `ALPACA_SECRET_KEY` del `.env` son válidas y autentican. Es un script
auxiliar del HOST (como `explore_universe.py` / `notify_email.py`): el algoritmo nunca
habla con SDKs de brokers; esta verificación vive fuera del motor LEAN.

QUÉ HACE: lee las claves del entorno (o del `.env` gitignoreado), llama al endpoint REST
`/v2/account` de Alpaca y reporta si autentican. Por defecto usa el host de PAPER trading
(las claves `PK...` son de paper). Sin dependencias externas: solo stdlib (`urllib`), para
que corra con el Python del `.venv` sin instalar `alpaca-py` ni `requests`.

USO:
    python scripts/check_alpaca_credentials.py            # paper (por defecto)
    python scripts/check_alpaca_credentials.py --live     # cuenta live (api.alpaca.markets)

CREDENCIALES (nunca en el repo): se leen primero de las variables de entorno y, si faltan,
del `.env` de la raíz del workspace (gitignoreado). No se hardcodean ni se imprimen.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent
_ENV_FILE = _WORKSPACE / ".env"

PAPER_HOST = "https://paper-api.alpaca.markets"
LIVE_HOST = "https://api.alpaca.markets"
DATA_HOST = "https://data.alpaca.markets"  # market data (histórico/feed), distinto del host de cuenta


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


def get_credentials() -> tuple[str, str]:
    """Devuelve (key_id, secret), priorizando el entorno sobre el .env."""
    file_env = load_env_file(_ENV_FILE)
    key_id = os.environ.get("ALPACA_KEY_ID") or file_env.get("ALPACA_KEY_ID")
    secret = os.environ.get("ALPACA_SECRET_KEY") or file_env.get("ALPACA_SECRET_KEY")
    if not key_id or not secret:
        print("ERROR: faltan ALPACA_KEY_ID y/o ALPACA_SECRET_KEY (ni en el entorno ni en .env).")
        sys.exit(2)
    return key_id, secret


def check_account(host: str, key_id: str, secret: str) -> int:
    """Llama a /v2/account y reporta el resultado. Devuelve un exit code."""
    masked = f"{key_id[:4]}…{key_id[-2:]}"
    print(f"Probando credenciales ({masked}) contra {host} …")

    request = urllib.request.Request(
        f"{host}/v2/account",
        headers={"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            account = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace").strip()
        if exc.code in (401, 403):
            print(f"❌ Credenciales RECHAZADas (HTTP {exc.code}). Revisa key/secret y paper vs live.")
        else:
            print(f"❌ HTTP {exc.code}: {body}")
        return 1
    except urllib.error.URLError as exc:
        print(f"❌ Error de red: {exc.reason}")
        return 1

    print("✅ Credenciales VÁLIDAS. Detalle de la cuenta:")
    for field in ("account_number", "status", "currency", "cash", "buying_power", "pattern_day_trader"):
        if field in account:
            print(f"   {field:18} = {account[field]}")
    if account.get("status") != "ACTIVE":
        print("⚠️  La cuenta no está ACTIVE; revisa el estado en el dashboard de Alpaca.")
    return 0


def check_market_data(symbol: str, key_id: str, secret: str) -> int:
    """Llama a /v2/stocks/bars (1Day, feed IEX) y verifica que devuelve ≥1 barra.

    POR QUÉ (T2 de Etapa 9A): el endpoint de DATOS es el que usará el downloader (Opción C),
    distinto del de cuenta. Free tier = feed IEX; pedimos `adjustment=split` para casar con la
    referencia (5B). Confirma que la key autentica contra market data y que hay barras diarias.
    """
    # Ventana reciente acotada; IEX free no permite los últimos ~15 min, por eso `end` ayer.
    from datetime import date, timedelta

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=10)
    params = urllib.parse.urlencode(
        {
            "symbols": symbol,
            "timeframe": "1Day",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "adjustment": "split",
            "feed": "iex",
            "limit": "5",
        }
    )
    url = f"{DATA_HOST}/v2/stocks/bars?{params}"
    print(f"Probando market data (1Day, IEX) para {symbol} en {DATA_HOST} …")

    request = urllib.request.Request(
        url, headers={"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace").strip()
        if exc.code in (401, 403):
            print(f"❌ Market data RECHAZADO (HTTP {exc.code}). ¿Key con permiso de datos?")
        else:
            print(f"❌ HTTP {exc.code}: {body}")
        return 1
    except urllib.error.URLError as exc:
        print(f"❌ Error de red: {exc.reason}")
        return 1

    bars = (payload.get("bars") or {}).get(symbol) or []
    if not bars:
        print(f"⚠️  Sin barras para {symbol} en la ventana {start}..{end}. Endpoint OK pero vacío.")
        return 1

    last = bars[-1]
    print(f"✅ Market data OK: {len(bars)} barra(s) diaria(s). Última:")
    print(f"   {last.get('t')}  O={last.get('o')} H={last.get('h')} "
          f"L={last.get('l')} C={last.get('c')} V={last.get('v')}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test de claves Alpaca (paper por defecto).")
    parser.add_argument("--live", action="store_true", help="usa el host de cuenta live en vez de paper")
    parser.add_argument("--data-symbol", default="AAPL", help="símbolo para el chequeo de market data")
    args = parser.parse_args()

    key_id, secret = get_credentials()
    host = LIVE_HOST if args.live else PAPER_HOST

    account_rc = check_account(host, key_id, secret)
    print()
    data_rc = check_market_data(args.data_symbol, key_id, secret)
    # Gate: 0 solo si ambos pasan (cuenta + market data).
    sys.exit(account_rc or data_rc)


if __name__ == "__main__":
    main()
