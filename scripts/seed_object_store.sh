#!/usr/bin/env bash
# seed_object_store.sh — Siembra config y universos al ObjectStore local.
#
# POR QUÉ: la config de estrategias y los CSVs de universo viven en config/ y
#   data/object-store/ respectivamente, y se leen en runtime vía self.object_store.
#   El ObjectStore local del CLI es <workspace>/storage/ (montado en /Storage dentro
#   de Docker). Ver PLAN.md §4 y CLAUDE.md (gotchas Etapa 2).
#
# QUÉ HACE:
#   1. config/*.json   → storage/config/   (idempotente, siempre)
#   2. data/object-store/*-advances-*.csv más reciente (no en processed/)
#      → storage/universes/swing_advances.csv + mueve fuente a processed/
#   3. data/object-store/*-declines-*.csv más reciente (no en processed/)
#      → storage/universes/swing_declines.csv + mueve fuente a processed/
#
# Si no hay archivos nuevos (todos ya en processed/), avisa pero no falla:
#   el archivo previo en storage/universes/ permanece intacto.
#
# IDEMPOTENTE para config: cp sobrescribe. Para universos: un archivo fuente
#   se procesa una sola vez (luego vive en processed/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_CONFIG="$WORKSPACE/config"
DATA_DIR="$WORKSPACE/data/object-store"
PROCESSED_DIR="$DATA_DIR/processed"
DEST="$WORKSPACE/storage"

echo "Sembrando ObjectStore local ($DEST)"
echo ""

# --- 1. config/*.json → storage/config/ ---
mkdir -p "$DEST/config"
for f in "$SRC_CONFIG"/*.json; do
  cp "$f" "$DEST/config/$(basename "$f")"
  echo "  [config] $(basename "$f") → config/$(basename "$f")"
done

echo ""

# --- 2 & 3. CSVs de universo ---
mkdir -p "$DEST/universes"
mkdir -p "$PROCESSED_DIR"

seed_universe() {
  local type="$1"       # "advances" o "declines"
  local dest_key="$2"   # "swing_advances" o "swing_declines"

  # Seleccionar el CSV más reciente no archivado (sort por nombre = sort por fecha en el nombre).
  # find en lugar de ls+glob para que set -eo pipefail no aborte cuando no hay archivos.
  local src
  src=$(find "$DATA_DIR" -maxdepth 1 -name "*-${type}-*.csv" 2>/dev/null | sort | tail -1)

  if [[ -z "$src" ]]; then
    echo "  [universos] ADVERTENCIA: no hay archivos *-${type}-*.csv en $DATA_DIR"
    if [[ -f "$DEST/universes/${dest_key}.csv" ]]; then
      echo "  [universos] Usando archivo previo en storage/universes/${dest_key}.csv (sin cambios)"
    else
      echo "  [universos] No existe archivo previo en storage/universes/${dest_key}.csv"
    fi
    return 0
  fi

  local filename
  filename="$(basename "$src")"
  local lines
  lines=$(wc -l < "$src")

  cp "$src" "$DEST/universes/${dest_key}.csv"
  mv "$src" "$PROCESSED_DIR/$filename"

  echo "  [universos] $filename → universes/${dest_key}.csv ($lines líneas) → archivado en processed/"
}

seed_universe "advances" "swing_advances"
seed_universe "declines" "swing_declines"

echo ""
echo "Listo."
