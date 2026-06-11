#!/usr/bin/env bash
# seed_object_store.sh — Siembra la config de negocio versionada al ObjectStore local.
#
# POR QUÉ: la config de estrategias (umbrales, horarios, universos, timeframes) vive en
#   config/strategies.json y se lee en runtime vía self.object_store, NO desde el
#   config.json del proyecto ni get_parameter. Ver PLAN.md §4 y etapa-02.md (T3).
#
# DÓNDE: el ObjectStore local del CLI de LEAN es <workspace>/storage/ (se monta en
#   /Storage dentro de Docker; ver lean_runner.py: storage_dir = cli_root/"storage").
#   NO es data/object-store/ (eso era una suposición incorrecta de Etapa 1). El root
#   mapea cada key a una ruta relativa, así que la key "config/strategies.json" se lee
#   desde storage/config/strategies.json. Por eso se preserva el prefijo config/.
#
# QUÉ COPIA: config/*.json -> storage/config/  (en etapas futuras también
#   universes/*.csv -> storage/universes/).
#
# IDEMPOTENTE: cp sobrescribe; la fuente versionada en config/ es la verdad, la copia
#   sembrada se regenera y NO se versiona.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_CONFIG="$WORKSPACE/config"
DEST="$WORKSPACE/storage"

echo "Sembrando config -> ObjectStore local ($DEST)"

mkdir -p "$DEST/config"
for f in "$SRC_CONFIG"/*.json; do
  cp "$f" "$DEST/config/$(basename "$f")"
  echo "  $(basename "$f") -> config/$(basename "$f")"
done

echo "Listo."
