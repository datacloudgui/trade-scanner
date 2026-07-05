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
#   4. universes/*.csv fixtures estáticos (ej. sample_dev) → storage/universes/
#      (cp directo, idempotente; versionados, sin lógica de processed/)
#
# Si no hay archivos nuevos (todos ya en processed/), avisa pero no falla:
#   el archivo previo en storage/universes/ permanece intacto.
#
# IDEMPOTENTE para config: cp sobrescribe. Para universos: un archivo fuente
#   se procesa una sola vez (luego vive en processed/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
# Overrides por env var: permiten testear el script con dirs temporales (test_seed_object_store.py).
SRC_CONFIG="${TRADE_SCANNER_CONFIG_SRC:-$WORKSPACE/config}"
SRC_UNIVERSES="${TRADE_SCANNER_UNIVERSES_SRC:-$WORKSPACE/universes}"
DATA_DIR="${TRADE_SCANNER_OBJECT_STORE_SRC:-$WORKSPACE/data/object-store}"
PROCESSED_DIR="$DATA_DIR/processed"
DEST="${TRADE_SCANNER_STORAGE:-$WORKSPACE/storage}"

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

  # Seleccionar el CSV más reciente no archivado. La fecha del nombre es MM-DD-YYYY
  # (PLAN §5), así que ordenar por nombre es lexicográfico y elige MAL al cruzar
  # mes/año (12-31-2025 > 01-02-2026): se antepone la clave YYYYMMDD y se ordena por
  # ella (triaje E1–E8 #7). Nombres sin fecha parseable pierden contra cualquier fecha.
  # find en lugar de ls+glob para que set -eo pipefail no aborte cuando no hay archivos.
  local src
  src=$(
    find "$DATA_DIR" -maxdepth 1 -name "*-${type}-*.csv" 2>/dev/null | while IFS= read -r f; do
      name="$(basename "$f" .csv)"
      if [[ "$name" =~ ([0-9]{2})-([0-9]{2})-([0-9]{4})$ ]]; then
        printf '%s%s%s\t%s\n' "${BASH_REMATCH[3]}" "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "$f"
      else
        printf '00000000\t%s\n' "$f"
      fi
    done | sort | tail -1 | cut -f2-
  )

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

# --- 4. Fixtures estáticos versionados (universes/*.csv) → storage/universes/ ---
if [[ -d "$SRC_UNIVERSES" ]]; then
  shopt -s nullglob
  for f in "$SRC_UNIVERSES"/*.csv; do
    cp "$f" "$DEST/universes/$(basename "$f")"
    echo "  [universos] $(basename "$f") → universes/$(basename "$f") (fixture estático)"
  done
  shopt -u nullglob
fi

echo ""
echo "Listo."
