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

## T3 — PLAN.md resincronizado (2026-09-23)

- **Tabla "Secuencia del ciclo 2026-09"** al inicio de §7, con 7 filas. Regla: la etapa activa es la primera fila cuyo Estado no es `completada`. El orden del documento queda como histórico.
- **Estado nuevo `pausada`:** una etapa abierta cuyo trabajo restante está asignado a una fila posterior. Se aplica a **5B** (F3 → orden 3) y **9A** (T7/T8 → Etapa 9). Sin este estado habría tres etapas `en progreso` a la vez (5B, 9A y 12) y la regla del paso 1 sería ambigua.
- **Estados corregidos:**
  - Etapa 0 → `completada`, con la evidencia de T1.
  - 6B → `completada`: T6/T7 están en `03880f2` (formateadores de `pipeline.py` y sus tests).
- **Entradas nuevas:** 9A, 9B, 10, 11 (re-scope), 12, 13, 14 y 15. Los "Done when" de 11/13/14/15 se copiaron literalmente del roadmap (U2/U1/U3a/U3b).
- **CLAUDE.md:** solo el paso 1 del flujo apunta a la tabla. La cadena de precedencia se deja para T7.
- **etapa-11-fecha-desde-universo.md:** nota de supersesión en la cabecera, con H4 (la última sesión no se escanea) y H4b (el footer es la fecha de descarga).
- **Hallazgo lateral corregido:** el link a `etapa-04-decisiones-y-pendientes-md` (sin punto) estaba roto desde la Etapa 4.
- **Verificación:** las 8 etapas aparecen 1 vez cada una en `grep "^## Etapa N —"`; la tabla tiene 7 filas; todos los links locales de PLAN.md resuelven.

## Pendientes

- T4 en adelante. **T4 no se inicia hasta que el usuario lo indique.**
