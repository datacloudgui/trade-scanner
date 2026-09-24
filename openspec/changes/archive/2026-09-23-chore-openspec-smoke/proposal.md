# Proposal

**Etapa de PLAN.md:** Etapa 12 — Base estable + adopción de OpenSpec, tarea **T8** (spike del ciclo OpenSpec).
**Rama:** `feature/etapa-12-bootstrap-openspec` (la rama de la Etapa 12). Este change es una tarea dentro de la etapa, no una etapa propia: por la regla "una etapa, una rama" de CLAUDE.md no abre `feature/etapa-NN-chore-openspec-smoke`.

## Why

OpenSpec se instaló e inicializó en T4–T5, pero su ciclo completo (`/opsx:propose` → `apply` → `verify` → `sync` → `archive`) nunca se recorrió con los comandos `/opsx:*` dentro de este repo. Antes de que la Etapa 13 dependa de él, hace falta probar de punta a punta que las reglas de `openspec/config.yaml` se aplican, que `sync` + `archive` no duplican requisitos y que CLAUDE.md basta para guiar el ciclo.

## What Changes

- Nueva capability de prueba, `openspec-smoke`, con un único requisito trivial: el repo declara su flujo de trabajo en CLAUDE.md.
- Sin cambios de código, de config (`config/*.json`), de ObjectStore ni de salida del scan.
- Al terminar T8, la capability se retira a mano (`git rm -r openspec/specs/openspec-smoke/`) en un commit aparte; el change archivado queda como historia.

## Capabilities

### New Capabilities
- `openspec-smoke`: capability desechable del spike T8; declara que el flujo de trabajo del repo vive en CLAUDE.md.

### Modified Capabilities
- Ninguna (`openspec/specs/` está vacío).

## Diferencias esperadas en la watchlist

Ninguna. El change no toca el scan, la config de estrategias ni la salida: G4 no aplica.

## Rollback

**R-git.** El único efecto persistente es documental (`openspec/changes/archive/…` y, hasta su retiro, `openspec/specs/openspec-smoke/`). Revertir los commits de T8 en la rama (o, ya integrado, `git revert -m 1` del merge de la Etapa 12) deja el repo exactamente como estaba. No hay config que apagar, así que R-cfg no aplica; y como no cambia código ni datos, el revert basta.

## Impact

- Archivos: solo bajo `openspec/` (change, spec de la capability y su archivo) y la bitácora de la Etapa 12.
- Código, tests, `config/`, `storage/`, `data/`: sin cambios.
- Proceso: los hallazgos del spike (diferencias entre lo que sugieren los `/opsx:*` y CLAUDE.md) se anotan en `bitacora.md` del change y en `etapa-12-decisiones-y-pendientes.md`.
