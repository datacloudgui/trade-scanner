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

# Universo dev multi-símbolo (Etapa 5B T5.1): daily + map/factor de AAPL/IBM/FB.
# FB solo tiene historia propia desde la IPO 2012 → M:200 no-ready (decisión 2026-06-11).
for sym in aapl ibm fb; do
  fetch "daily/${sym}.zip"
  fetch "map_files/${sym}.csv"
done
# factor_files reales del repo LEAN para FB (zip LEAN, OK usar factores reales).
fetch "factor_files/fb.csv"

# factor_files NEUTROS para AAPL/IBM (Etapa 5B T5.3): sus zips provienen del converter
# Stooq (split-only adjusted, sin dividendos — descargados con "skip dividends").
# Usar los factores reales del repo LEAN causaría doble ajuste. factor=1 → LEAN sirve
# los precios tal cual, sin re-ajustar. Stooq split-only + factor=1 es coherente con
# DataNormalizationMode.SPLIT_ADJUSTED y con TradingView vista "Adjusted".
for sym_date in "aapl:19840907" "ibm:19620102"; do
  sym="${sym_date%%:*}"
  first_date="${sym_date##*:}"
  dest="$DATA_DIR/factor_files/${sym}.csv"
  echo "  factor_files/${sym}.csv → neutro (${first_date},1,1,1)"
  printf "%s,1,1,1\n" "$first_date" > "$dest"
done

echo "Listo."
