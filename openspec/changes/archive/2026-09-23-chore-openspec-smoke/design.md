# Design

## Context

Ver proposal.md (Why). `openspec/specs/` está vacío, OpenSpec 1.13.1 corre con el perfil `custom` (core + verify) y `delivery: commands`. El detalle del spike (pasos y criterios) está en `.claude/fase-1-desarrollo-local/etapa-12.md`, T8.

## Goals / Non-Goals

**Goals:**
- Recorrer `propose → validate → apply → verify → sync → validate → archive` con los `/opsx:*` del repo, sin `--no-validate` ni `--skip-specs`.
- Registrar cada punto donde un `/opsx:*` sugiera algo distinto de CLAUDE.md (hallazgo, no error).

**Non-Goals:**
- Tocar código, tests, `config/`, `storage/` o la salida del scan.
- Probar el retiro de una capability con un delta REMOVED (exigiría `retire_capabilities: true`, un camino que el ciclo no usa).

## Decisions

- **D-1 — Capability propia y desechable (`openspec-smoke`).** No se reutiliza ni se inventa una capability "real" (p. ej. `workflow`): la Etapa 13 hará el bootstrap de las capabilities de verdad, y una capability de prueba con nombre explícito no se confunde con ellas. Alternativa descartada: `skip_specs: true`, porque no ejercitaría `sync` ni la duplicación de requisitos, que es lo que se quiere probar.
- **D-2 — Scenario verificado por evidencia de comando, no por test en Docker ni por backtest.** La regla de `config.yaml` para specs pide "test en Docker o evidencia de backtest citada", pero el requisito es documental: un test en Docker sería código nuevo (fuera del alcance de T8) y un backtest no demuestra nada sobre CLAUDE.md. Se usa `grep -c` citado en `bitacora.md`. Queda como hallazgo de T8: la regla no cubre changes sin código.
- **D-3 — `## Purpose` dentro del delta.** Verificado contra OpenSpec 1.13.1 instalado: en la spec **principal** el `## Purpose` es obligatorio (sin la sección → ERROR; `TBD` o <50 caracteres → WARNING, que `--strict` convierte en fallo: `validation/constants.js`, `validator.js`). En el **delta** es opcional pero el schema lo pide para capabilities nuevas (`schemas/spec-driven/schema.yaml:98-105`), y si está se copia literal a la spec nueva: la CLI `archive` (`buildSpecSkeleton`, #1413) y `/opsx:sync` (`sync.md:169`); solo si falta se escribe `TBD`. En este repo `/opsx:archive` hace `mv`, así que quien lo copia es `/opsx:sync`. Se incluye en el delta; el paso 5 de T8 pasa a ser verificar que la spec principal no quedó con `TBD`, y escribirlo solo si quedó.
- **D-4 — Rama de la etapa, no una rama propia.** El change vive en `feature/etapa-12-bootstrap-openspec` ("una etapa, una rama", CLAUDE.md). El patrón `feature/etapa-NN-<change-id>` de `config.yaml` presupone un change por etapa; aquí el change es una tarea (T8) de una etapa sin change.
- **D-5 — G2 y G3 se corren aunque no haya código; G4 no aplica** (aprobado en G1). CLAUDE.md exige G2 para todo `[x]` de `tasks.md` y prohíbe `/opsx:sync` sin G3; el spec de T8 decía "no aplican". Ningún `/opsx:*` ni la CLI ejecuta tests o backtests (`/opsx:verify` solo lee checkboxes y busca por palabras clave; los 7 comandos declaran solo `allowed-tools: Bash(openspec:*)`), así que los gates no se pueden delegar en OpenSpec: se corren a mano como tareas explícitas. G3 = `lean backtest` en dev, sin publicar. G4 no aplica: no toca el scan ni la salida.

## Risks / Trade-offs

- [`/opsx:sync` lo hace el agente, no la CLI: podría escribir el requisito con otro formato que `archive` no reconozca como "ya sincronizado" y lo duplique] → Tras `archive` se cuenta el requisito en `openspec/specs/` (debe ser 1). Si duplica, se detiene la etapa (nota de T8).
- [`/opsx:archive` mueve con `mv` sin validar] → `openspec validate chore-openspec-smoke --strict` inmediatamente antes (CLAUDE.md, *Reglas de archive*).
- [La capability queda en `openspec/specs/` después del spike] → Retiro manual en un commit aparte (`git rm -r openspec/specs/openspec-smoke/`) y `openspec validate --all --strict` en exit 0.

## Migration Plan

No hay despliegue. Rollback: ver proposal.md (R-git).
