#!/usr/bin/env bash
# OPCIONAL — requiere Codex CLI; la revisión por defecto es /opsx:verify + /code-review.
# Revisión exhaustiva etapa por etapa con Codex (solo lectura).
# Una corrida enfocada por etapa rinde hallazgos más finos que una sola pasada global.
#
# Para no agotar la ventana de rate limit, conviene correr por tramos:
#   bash scripts/run_review.sh 1 4        # primer tramo
#   bash scripts/run_review.sh 5 8        # segundo tramo (otro día / otra ventana)
#
# Uso:
#   bash scripts/run_review.sh            # etapas 1..8 de corrido
#   bash scripts/run_review.sh 5          # solo la etapa 5
#   bash scripts/run_review.sh 5 8        # rango: etapas 5..8
#   EFFORT=high bash scripts/run_review.sh 1 4    # baja el esfuerzo (default: xhigh)
#   SLEEP=120 bash scripts/run_review.sh 1 8      # pausa 120s entre etapas
#   OUTDIR=revisiones/mi-corrida bash scripts/run_review.sh 5 8  # continúa en una carpeta previa
set -euo pipefail

# Guard: sin Codex no se crea nada en revisiones/.
if ! command -v codex >/dev/null 2>&1; then
  echo "run_review.sh es OPCIONAL y requiere Codex CLI (no encontrado en PATH)." >&2
  echo "La revisión por defecto es /opsx:verify (G5) + /code-review." >&2
  exit 1
fi

START="${1:-1}"
END="${2:-${1:-8}}"               # un solo arg = esa única etapa; sin args = 1..8
EFFORT="${EFFORT:-xhigh}"          # low | medium | high | xhigh
MODEL="${MODEL:-gpt-5.5}"
SLEEP="${SLEEP:-0}"                # segundos de pausa entre etapas

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USAGE="$ROOT/scripts/codex_usage.sh"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="${OUTDIR:-$ROOT/revisiones/$STAMP}"   # override para continuar un tramo previo
mkdir -p "$OUTDIR"

echo "Revisión etapas $START..$END | modelo=$MODEL | effort=$EFFORT | sleep=${SLEEP}s"
echo "Salida → $OUTDIR"

for n in $(seq "$START" "$END"); do
  etapa="$(printf '%02d' "$n")"
  spec="$ROOT/.claude/fase-1-desarrollo-local/etapa-$etapa.md"
  echo
  echo "==================== ETAPA $etapa ===================="

  # Aviso si no existe el doc de la etapa (la revisión sigue, apoyada en PLAN.md y
  # docs/review/codex-review-prompt.md).
  ref="el documento .claude/fase-1-desarrollo-local/etapa-$etapa.md"
  if [[ ! -f "$spec" ]]; then
    echo "  (aviso: no existe $spec — usa PLAN.md como referencia de la etapa)"
    echo "  (aviso: desde la Etapa 13 el alcance vive en openspec/changes/<id>/ y este script" \
         "todavía NO lo soporta — la revisión de una etapa ≥13 quedaría incompleta)"
    ref="la sección de la Etapa $n en PLAN.md"
  fi

  prompt="Revisa exhaustivamente SOLO la Etapa $n del proyecto, siguiendo la metodología y \
los criterios de docs/review/codex-review-prompt.md (léelo primero). Usa $ref como definición \
del alcance y los criterios de aceptación (Done when) de esta etapa, y la cadena de \
precedencia de CLAUDE.md como fuentes de verdad del diseño. Traza objetivo->codigo->test para cada criterio de la etapa, verifica la API de \
LEAN y la corrección funcional de las funciones tocadas y que se relacionen en la etapa (dependencias de etapas previas) en esta etapa. \
Si necesitas contexto de etapas previas, los informes ya generados están en $OUTDIR/etapa-*-informe.md (puedes leerlos). \
Reporta hallazgos con archivo:linea, severidad y sugerencia. No modifiques archivos."

  caffeinate -i codex exec \
    --sandbox read-only \
    -C "$ROOT" \
    -m "$MODEL" \
    -c model_reasoning_effort="$EFFORT" \
    -c model_reasoning_summary="detailed" \
    -o "$OUTDIR/etapa-$etapa-informe.md" \
    "$prompt" \
    2>&1 | tee "$OUTDIR/etapa-$etapa-log.md"

  # Uso tras la etapa (el snapshot acaba de refrescarse con los requests de esta corrida).
  [[ -x "$USAGE" ]] && { echo "--- uso tras etapa $etapa ---"; bash "$USAGE" || true; }

  # Pausa entre etapas (no tras la última) para dar aire a la ventana de rate limit.
  if [[ "$SLEEP" -gt 0 && "$n" -lt "$END" ]]; then
    echo "Pausa ${SLEEP}s antes de la etapa siguiente…"
    sleep "$SLEEP"
  fi
done

echo
echo "Listo. Informes limpios: $OUTDIR/etapa-*-informe.md"
echo "Logs completos:          $OUTDIR/etapa-*-log.md"
