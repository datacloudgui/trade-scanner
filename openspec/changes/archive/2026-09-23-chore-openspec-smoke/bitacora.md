# Bitácora — chore-openspec-smoke (Etapa 12, T8)

Rama `feature/etapa-12-bootstrap-openspec`, base `643f71b`. OpenSpec 1.13.1, perfil `custom` (core + verify), `delivery: commands`.

## Propose (G0) y G1 — 2026-09-23

- `openspec new change "chore-openspec-smoke"` → scaffold con `.openspec.yaml` (`schema: spec-driven`).
- `openspec instructions <artefacto> --change chore-openspec-smoke --json`: llegaron el `context` y las reglas de los 4 artefactos (3 de proposal, 1 de specs, 1 de design, 2 de tasks), **sin ningún aviso "ignoring"**.
- `openspec validate chore-openspec-smoke --strict` → `Change 'chore-openspec-smoke' is valid`, **exit 0** (G0). Se repitió tras actualizar el design en G1: exit 0.
- G1 aprobado por el usuario con dos decisiones: `## Purpose` en el delta (D-3) y G2 + G3 aunque no haya código (D-5).

## Apply — evidencia por tarea (2026-09-23)

| Tarea | Comando | Salida |
|---|---|---|
| 1.1 Requisito | `grep -c "^## Flujo de trabajo" CLAUDE.md` | `1` (L18: `## Flujo de trabajo (spec-driven, obligatorio)`) |
| 2.1 G2 | `bash scripts/run_tests.sh` | **exit 0**, `304 passed, 13 warnings in 5.31s` |
| 2.2 G3 | `DOCKER_HOST=unix://$HOME/.docker/run/docker.sock lean backtest "trade-scanner" --parameter env dev` | **exit 0**; `Successfully ran 'trade-scanner'…` → `trade-scanner/backtests/2026-09-23_19-41-41`. Log: `universe loaded: 4 tickers (env=dev, max=4, key=universes/sample_dev.csv)`, `gate dev OK: set_warm_up ADOPTADO — 36/36 series exactas`, `[swing_eod] final: 0 candidatos`. No se ejecutó `notify_email.py` |
| 2.2 → G2 | `bash scripts/run_tests.sh` (antes de marcar 2.2) | **exit 0**, `304 passed, 13 warnings in 5.49s` |
| 2.3 G4 N/A | `git diff --stat develop -- trade-scanner/ config/` | salida vacía (0 líneas), exit 0 |

**Notas de G3:**
- El `trade-scanner/config.json` versionado tiene `"env": "prod"`, mientras que el README (L93, L204) dice `dev`. G3 exige dev y no dice cómo elegirlo. Se usó `--parameter env dev` del CLI para no tocar archivos versionados.
- El primer intento falló con `Error: Please make sure Docker is installed and running` aunque `docker info` respondía: el CLI de `lean` busca `/var/run/docker.sock`, que no existe; Docker Desktop expone `~/.docker/run/docker.sock` (contexto `desktop-linux`). Se resolvió con `DOCKER_HOST` solo en ese comando.
- Efectos colaterales:
  - el CLI reescribió `file-database-last-update` en `lean.json` → `git restore lean.json`;
  - la corrida dev escribió `storage/results/swing_eod/20131007-2001.{json,csv}` y **sobreescribió `latest.json`**. `storage/` está gitignoreado y T9 vacía `storage/results/` antes del baseline.
- Series `M:200` frías en dev (`ready: 0/4`): es el comportamiento conocido del sample de 2013 (la historia empieza en 1998), no una regresión.

## Hallazgos del spike (para CLAUDE.md / §0.4)

1. **Purpose (D-3):** en 1.13.1 el `## Purpose` del delta de una capability nueva se copia literal a la spec principal (CLI `archive` #1413; `/opsx:sync` paso 4d). La regla de CLAUDE.md "tras archivar se escribe su Purpose" pasa a ser "se verifica, y se escribe solo si quedó `TBD`".
2. **Regla de specs de `config.yaml`:** "test en Docker o evidencia de backtest" no cubre un requisito documental; se usó evidencia de comando (D-2).
3. **Rama:** `config.yaml` sugiere `feature/etapa-NN-<change-id>`; con un change como tarea de una etapa sin change, gana "una etapa, una rama" (D-4).
4. **Gates en un change sin código:** ningún `/opsx:*` ni la CLI ejecuta tests o backtests (`verify` solo lee; `allowed-tools: Bash(openspec:*)`). G2/G3 se corren a mano (D-5).
5. **G3 no define cómo seleccionar dev**, y `config.json` versionado está en `prod` (ver notas de G3).
6. **`lean` + Docker Desktop:** hace falta `DOCKER_HOST=unix://$HOME/.docker/run/docker.sock` si no existe `/var/run/docker.sock`.

## Cierre de apply

| Tarea | Comando | Salida |
|---|---|---|
| 3.1 Evidencia | `test -f …/bitacora.md` · `openspec validate chore-openspec-smoke --strict` · `bash scripts/run_tests.sh` | exit 0 · `is valid`, exit 0 · exit 0, `304 passed` |

## Verify (G5), sync y archive — 2026-09-23

| Paso | Comando / acción | Salida |
|---|---|---|
| `/opsx:verify` (G5) | Completitud, correctitud, coherencia | 5/5 tareas, 1/1 requisito, D-1…D-5 cumplidas; **0 CRITICAL**, 1 WARNING ("scenario sin test") justificado en design D-2 |
| `/opsx:sync` | Crea `openspec/specs/openspec-smoke/spec.md` con el Purpose del delta copiado literal | `openspec validate --specs --strict` → `1 passed, 0 failed`, exit 0 |
| Pre-archive | `openspec validate chore-openspec-smoke --strict` | `is valid`, exit 0 |
| `/opsx:archive` | Estado detectado "already synced"; opciones ofrecidas: *Archive now* / *Sync anyway* / *Cancel*. El usuario eligió **Archive now** | `mv` → `openspec/changes/archive/2026-09-23-chore-openspec-smoke/` |
| Purpose | Spec principal tras archive | 134 caracteres, sin `TBD` → **no hubo que escribirlo** (D-3 confirmada) |
| Duplicación | `grep -rc "### Requirement: El repo declara su flujo" openspec/specs/` | **1** (solo `openspec-smoke/spec.md`) |
| Post-archive | `openspec validate --all --strict` | `1 passed, 0 failed`, exit 0 |

Hallazgo adicional: cuando ya está sincronizado, `/opsx:archive` ofrece *Archive now* / *Sync anyway* / *Cancel*; las reglas de CLAUDE.md solo cubren "Archive without syncing".
