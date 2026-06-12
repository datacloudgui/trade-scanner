#!/usr/bin/env bash
# run_tests.sh — Corre pytest DENTRO de la imagen quantconnect/lean (ÚNICO modo válido).
#
# POR QUÉ: los tests importan AlgorithmImports y construyen objetos LEAN (TradeBar, etc.),
#   que requieren el CLR de .NET + los assemblies de QuantConnect cargados vía pythonnet.
#   El pytest del host NO resuelve AlgorithmImports. Este script monta el proyecto en la
#   imagen LEAN y corre pytest allí. Contrato para todas las etapas siguientes.
#
# CÓMO: la imagen embebe Python dentro de .NET; para arrancar pythonnet en modo standalone
#   hay que (1) instalar clr_loader, (2) forzar el runtime coreclr con el runtimeconfig de
#   Lean, y (3) ubicarse en el dir Debug (donde viven AlgorithmImports.py, clr.py y los DLLs).
#   El ENTRYPOINT de la imagen arranca el engine, por eso se sobreescribe con `bash`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="$WORKSPACE/trade-scanner"   # proyecto pusheable: core/, strategies/, tests/

IMAGE="quantconnect/lean:latest"
DEBUG_DIR="/Lean/Launcher/bin/Debug"
RUNTIME_CONFIG="$DEBUG_DIR/QuantConnect.Lean.Launcher.runtimeconfig.json"

docker run --rm --entrypoint bash \
  -e PYTHONNET_RUNTIME=coreclr \
  -e PYTHONNET_CORECLR_RUNTIME_CONFIG="$RUNTIME_CONFIG" \
  -e PYTHONPATH=/Project \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e TRADE_SCANNER_DATA=/Data \
  -v "$PROJECT":/Project \
  -v "$WORKSPACE/data":/Data:ro \
  "$IMAGE" -c "
    set -e
    pip install -q --root-user-action=ignore clr_loader pytest
    cd '$DEBUG_DIR'
    python -m pytest /Project/tests -q -p no:cacheprovider
  "
