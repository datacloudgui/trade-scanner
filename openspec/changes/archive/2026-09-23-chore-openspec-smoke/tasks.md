# Tasks

> Change sin código (Etapa 12, T8). G4 no aplica: no toca el scan ni la salida (proposal, "Diferencias esperadas en la watchlist": ninguna). G2 se corre antes de cada `[x]` y G3 se corre aunque no haya código (design D-5, aprobado en G1).

## 1. Requisito

- [x] 1.1 Verificar el requisito `openspec-smoke` contra el repo: `grep -c "^## Flujo de trabajo" CLAUDE.md` devuelve `1`

## 2. Gates

- [x] 2.1 G2: `bash scripts/run_tests.sh` sale con exit 0 (sin fallos; se anota la cifra de passed)
- [x] 2.2 G3: `source .venv/bin/activate && lean backtest "trade-scanner"` en dev sale con exit 0, sin publicar (no se ejecuta `notify_email.py`) — dev se selecciona con `--parameter env dev` porque el `config.json` versionado trae `env: prod` (ver `bitacora.md`)
- [x] 2.3 G4: no aplica (el change no toca el scan ni la salida); verificar que `git diff --stat develop -- trade-scanner/ config/` no muestra cambios de este change

## 3. Evidencia

- [x] 3.1 Crear `bitacora.md` en el change con los comandos y salidas de 1.1 y 2.1–2.3; verificar con `test -f openspec/changes/chore-openspec-smoke/bitacora.md` y `openspec validate chore-openspec-smoke --strict` en exit 0
