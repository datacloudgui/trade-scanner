#!/usr/bin/env bash
# Muestra el último snapshot de rate limits / tokens de la sesión Codex más reciente.
# El snapshot solo se refresca cuando Codex hace un request; entre turnos queda congelado.
#
# Uso:
#   bash scripts/codex_usage.sh            # sesión más reciente
#   bash scripts/codex_usage.sh <archivo.jsonl>   # una sesión concreta
set -euo pipefail

session="${1:-$(find "$HOME/.codex/sessions" -name '*.jsonl' -type f 2>/dev/null -exec stat -f '%m %N' {} + | sort -rn | head -1 | cut -d' ' -f2-)}"
if [[ -z "${session:-}" || ! -f "$session" ]]; then
  echo "No encontré sesiones en ~/.codex/sessions/" >&2
  exit 1
fi

python3 - "$session" <<'PY'
import json, sys, os, time
path = sys.argv[1]
last_rl = last_tok = None
for line in open(path):
    try: ev = json.loads(line)
    except: continue
    s = json.dumps(ev)
    if '"rate_limits"' in s: last_rl = ev
    if '"total_tokens"' in s: last_tok = ev

def find(d, key):
    if isinstance(d, dict):
        if key in d: return d[key]
        for v in d.values():
            r = find(v, key)
            if r is not None: return r
    elif isinstance(d, list):
        for v in d:
            r = find(v, key)
            if r is not None: return r
    return None

def fmt_reset(secs):
    if secs in (None, ""): return "n/d"
    secs = int(secs)
    h, m = divmod(secs // 60, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"

print(f"Sesión: {os.path.basename(path)}")
mtime = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(path)))
print(f"Último evento: {mtime}\n")

rl = find(last_rl, "rate_limits")
if rl:
    labels = {"primary": "5h ", "secondary": "sem"}
    print("RATE LIMITS")
    for name in ("primary", "secondary"):
        w = rl.get(name)
        if w:
            win = w.get("window_minutes")
            print(f"  [{labels.get(name,name)}] {w.get('used_percent')}% usado"
                  f" | ventana {win} min | reset en {fmt_reset(w.get('resets_in_seconds'))}")
else:
    print("RATE LIMITS: sin snapshot todavía (aún no hubo request).")

print("\nTOKENS (último request)")
print(f"  total {find(last_tok,'total_tokens')}"
      f" (in {find(last_tok,'input_tokens')} / out {find(last_tok,'output_tokens')})")
PY