#!/usr/bin/env bash
# seed_sample_data.sh — Siembra la sample data libre de SPY en data/equity/usa/.
#
# POR QUÉ: un backtest SIN data no avanza el reloj (procesa "1 data point" y dispara
#   OnEndOfAlgorithm de inmediato; los ScheduledEvents nunca corren). SPY como ancla
#   de calendario necesita estas barras para que el esqueleto "camine". Ver el hallazgo
#   del reloj en .claude/fase-1-desarrollo-local/etapa-02.md y CLAUDE.md.
#
# DE DÓNDE: repo público de LEAN en GitHub (Data/equity/usa/...), vía raw, sin auth QC.
#   Es la misma sample data abierta (SPY ~2013, minute/hour/daily) que QuantConnect
#   distribuye libremente; NO requiere licencia. No confundir con `lean data download`
#   ni AlpacaBrokerage, que sí la requieren (ADR-002, relevante en Etapa 9, no aquí).
#
# IDEMPOTENTE: si el archivo destino ya existe, no lo vuelve a bajar.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$WORKSPACE/data/equity/usa"
BASE_URL="https://raw.githubusercontent.com/QuantConnect/Lean/master/Data/equity/usa"

fetch() {
  # fetch <ruta-relativa-a-equity/usa>
  local rel="$1"
  local dest="$DATA_DIR/$rel"
  if [[ -f "$dest" ]]; then
    echo "  skip (ya existe): $rel"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  echo "  bajando: $rel"
  curl -fsSL "$BASE_URL/$rel" -o "$dest"
}

echo "Sembrando sample data de SPY desde el repo público de LEAN -> $DATA_DIR"

# Minute: trade + quote. Cubre la ventana por defecto del backtest (2013-10-07..11).
for d in 20131004 20131007 20131008 20131009 20131010 20131011; do
  fetch "minute/spy/${d}_trade.zip"
  fetch "minute/spy/${d}_quote.zip"
done

# Resoluciones superiores (consolidación W/M parte de barras diarias en etapas futuras).
fetch "hour/spy.zip"
fetch "daily/spy.zip"

# Map y factor files: LEAN los necesita para resolver el símbolo de equity US.
fetch "map_files/spy.csv"
fetch "factor_files/spy.csv"

echo "Listo."
