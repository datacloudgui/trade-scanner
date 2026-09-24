# openspec-smoke Specification

## Purpose
Capability desechable del spike de la Etapa 12 (T8): prueba el ciclo completo de OpenSpec en este repo y se retira a mano al terminar.

## Requirements

### Requirement: El repo declara su flujo de trabajo en CLAUDE.md
El repositorio SHALL declarar su flujo de trabajo spec-driven en `CLAUDE.md`, en una única sección de nivel 2 titulada "Flujo de trabajo".

#### Scenario: La sección de flujo existe una sola vez
- **WHEN** se ejecuta `grep -c "^## Flujo de trabajo" CLAUDE.md` en la raíz del repo
- **THEN** la salida es `1`, y la evidencia (comando y salida) queda citada en `bitacora.md` del change
