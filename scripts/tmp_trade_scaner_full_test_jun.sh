#!/usr/bin/env bash
# tmp_trade_scaner_full_test_jun.sh — Prueba completa end-to-end del screener (env=prod, datos Alpaca reales).
#
# POR QUÉ: reproduce, de principio a fin y "a la fecha", la corrida manual de la Etapa 9A:
#   ObjectStore → credenciales → descarga diaria Alpaca → backtest prod → watchlists.
# Script TEMPORAL de conveniencia (prefijo tmp_): orquesta scripts existentes, no añade lógica nueva.
#
# REQUISITOS:
#   - Ejecutar desde la raíz del workspace (donde vive lean.json).
#   - .venv creado y credenciales Alpaca en .env (ALPACA_KEY_ID / ALPACA_SECRET_KEY).
#   - Docker corriendo (lean backtest usa la imagen quantconnect/lean).
#   - trade-scanner/config.json con parameters.env = "prod".
#
# USO:
#   bash scripts/tmp_trade_scaner_full_test_jun.sh
#
# ─── ARCHIVOS DE ENTRADA (dónde ponerlos antes de correr) ─────────────────────────────────────
#   Credenciales Alpaca .......... .env                         (raíz; gitignoreado. Claves ALPACA_KEY_ID / ALPACA_SECRET_KEY)
#   Config de estrategias ........ config/strategies.json       (versionado; el seed lo copia a storage/config/)
#   Config de notificaciones ..... config/notifications.json    (versionado; idem)
#   Universo Barchart (NUEVO) .... data/object-store/*-advances-*.csv
#                                  data/object-store/*-declines-*.csv
#                                  (deja aquí el export CRUDO de Barchart; el seed toma el más
#                                   reciente, lo copia a storage/universes/ y mueve el original
#                                   a data/object-store/processed/. Si no hay archivo nuevo, se
#                                   reutiliza el que ya esté en storage/universes/.)
#   Universos fixtures estáticos . universes/*.csv              (ej. sample_dev.csv; cp directo al seed)
#   Parámetro de entorno ......... trade-scanner/config.json → parameters.env = "prod"
#
# ─── ARCHIVOS DE SALIDA (dónde quedan los resultados) ─────────────────────────────────────────
#   Universos efectivos .......... storage/universes/swing_advances.csv, swing_declines.csv   (que lee el motor)
#   Config en ObjectStore ........ storage/config/strategies.json, notifications.json
#   Barras diarias descargadas ... data/equity/usa/daily/<sym>.zip                            (una por ticker)
#   Log del backtest ............. trade-scanner/backtests/<timestamp>/log.txt                (warmup, funnel, errores)
#   Watchlists (resultado final) . storage/results/swing_eod/latest.json  (+ un JSON/CSV por scan/día)
#                                  storage/results/market_close/latest.json
set -euo pipefail

# --- Raíz del workspace (carpeta padre de scripts/) -------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UNIVERSE_ADV="storage/universes/swing_advances.csv"
UNIVERSE_DEC="storage/universes/swing_declines.csv"
DATA_OUT="data/equity/usa/daily"
START="2016-01-01"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

# --- 0. Virtualenv ----------------------------------------------------------------------------
step "Activando virtualenv (.venv)"
# shellcheck disable=SC1091
source .venv/bin/activate

# --- 1. Sembrar ObjectStore (config + universos) ----------------------------------------------
step "Sembrando ObjectStore: config/*.json + universes/*.csv → storage/"
bash scripts/seed_object_store.sh

# --- 2. Verificar credenciales Alpaca (smoke test rápido) -------------------------------------
step "Verificando credenciales Alpaca (paper)"
python scripts/check_alpaca_credentials.py

# --- 3. Descargar historia diaria Alpaca del universo (host-side, $0) --------------------------
step "Descargando barras diarias Alpaca → $DATA_OUT (advances)"
python scripts/alpaca_to_lean.py --universe "$UNIVERSE_ADV" --start "$START" --out "$DATA_OUT"

step "Descargando barras diarias Alpaca → $DATA_OUT (declines)"
python scripts/alpaca_to_lean.py --universe "$UNIVERSE_DEC" --start "$START" --out "$DATA_OUT"

# --- 4. Backtest prod (lean lee los zips vía lean.json; el código nunca toca Alpaca) -----------
step "Corriendo backtest prod (Docker)"
lean backtest "trade-scanner"

# --- 5. Watchlists materializadas -------------------------------------------------------------
step "Watchlists resultantes (storage/results/*/latest.json)"
for base in swing_eod market_close; do
  f="storage/results/${base}/latest.json"
  [ -f "$f" ] || { echo "  (sin resultado para $base)"; continue; }
  echo "--- $base ---"
  for side in long short; do
    echo -n "  $side: "
    python - "$f" "$side" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(', '.join(c['ticker'] for c in d['sections'].get(sys.argv[2], {}).get('candidates', [])))
PY
  done
done

step "Prueba completa terminada."
