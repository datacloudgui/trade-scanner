# Etapa 12 — Decisiones y pendientes (bitácora)

Spec: [etapa-12.md](etapa-12.md) · Rama: `feature/etapa-12-bootstrap-openspec`

## Fase A — transición de ramas (2026-09-23, ejecutada a mano por el usuario)

- `develop` y `main` avanzaron por fast-forward hasta `f8ded63` y se pushearon. `origin/main` recibió además los 10 commits que tenía pendientes.
- Tag anotado `scan/v2026.09.23-pre-ciclo` → `f8ded63`, publicado en `origin`.
- Rama `feature/etapa-12-bootstrap-openspec` creada desde `develop`. Primer commit `9e5125f`: spec y roadmaps.
- Antes de la Fase A, el usuario descartó con `git restore` los cambios sin commitear: `enabled: true` del short, `end_date` 2026-09-18 y el timestamp de `lean.json`.

## T1 — Suite y entorno (2026-09-23)

- `docker run hello-world` → OK.
- `bash scripts/run_tests.sh` → **304 passed**, 0 failed, 0 skipped, 13 warnings, en 5,84 s. Las cifras históricas eran 225 en E8, 238 en 9A y 284 en 9B; esta es la primera verificación del ciclo.
- Entorno Etapa 0: Python 3.11.11 (`.venv`), `lean 1.0.225`, `.python-version` en el repo, `.venv` gitignoreado.

## T2 — ObjectStore sincronizado (2026-09-23)

- `bash scripts/seed_object_store.sh`: resembró `config/{strategies,notifications}.json`. Como no había CSV nuevos, **conservó** `storage/universes/swing_{advances,declines}.csv` (los del 09-19).
- `shasum -a 256`: `config/strategies.json` = `storage/config/strategies.json` = `1be6104e…4560`.
- `storage`: `swing_eod_short.enabled` = `false`. Termina la contaminación H1 en las corridas locales.

## Pendientes

- T3 en adelante.
