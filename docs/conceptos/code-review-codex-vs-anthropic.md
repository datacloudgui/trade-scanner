# Cápsula: code review — Codex vs Anthropic

**Tipo:** material de estudio (cápsula breve). Para entender los dos flujos de revisión del proyecto y cuándo usar cada uno.
**Relacionado:** `scripts/run_review.sh`, `scripts/codex_usage.sh`, skill `/code-review`, AGENTS.md, PLAN.md (Done when por etapa).

---

## La idea en una frase

- **Codex (`run_review.sh`)** = auditor **externo, spec-driven, por etapa**. Otro modelo (gpt-5.5) da una segunda opinión independiente contra los "Done when".
- **`/code-review` (Anthropic)** = reviewer **inline, diff-driven, del día a día**, integrado en la sesión de Claude Code, y que además puede **corregir**.
- **`codex_usage.sh`** = NO es un reviewer. Es el cuentakilómetros de Codex (rate limits / tokens).

No compiten: son dos capas distintas del mismo proceso de calidad.

---

## Qué hace cada pieza

| Pieza | Rol real |
|---|---|
| `scripts/codex_usage.sh` | **Telemetría.** Lee el último snapshot de rate limits / tokens de la sesión de Codex. Existe porque Codex se corre como proceso externo a ciegas; en el flujo de Claude no hace falta (el harness gestiona el uso). |
| `scripts/run_review.sh` | **El code review con Codex.** Orquesta `codex exec` (gpt-5.5, read-only) etapa por etapa, usa `etapa-NN.md` / PLAN.md / AGENTS.md como criterio, escribe informes a `revisiones/`. |
| Skill `/code-review` | **El reviewer de Anthropic**, integrado en la sesión de Claude Code. |

La comparación real es **`run_review.sh` vs `/code-review`**.

---

## Cómo es el flujo de Anthropic (`/code-review`)

Skill que corre **dentro de la sesión** de Claude Code, no un proceso externo lanzado con bash:

1. Se invoca con `/code-review [effort]` — niveles `low | medium | high | max | ultra`.
2. Toma el **diff actual** como unidad de revisión (branch vs `main`, o un PR: `/code-review ultra <PR#>`).
3. Busca **bugs de correctitud** + limpiezas de **reuse / simplificación / eficiencia**. Hereda contexto automáticamente: CLAUDE.md, AGENTS.md y la conversación en curso (conoce reglas duras de capas, "cero órdenes", etc. sin explicárselo).
4. Salida según flags:
   - sin flag → lista hallazgos en el chat,
   - `--comment` → los postea como **inline comments en el PR**,
   - `--fix` → **aplica las correcciones** al working tree.
5. `ultra` ("ultrareview") → revisión **multi-agente en la cloud** sobre todo el branch. Es facturada y la dispara el usuario; Claude no puede lanzarla.

**Eje clave:** Codex revisa **contra spec** (etapa → código → test, orientado a "Done when"); Claude revisa **contra diff** (qué cambió y si está bien/limpio).

---

## Diferencias y separación de roles

**run_review.sh / Codex**
- Modelo **distinto** (gpt-5.5) → segunda opinión independiente; pilla cosas que Opus podría pasar por alto. La diversidad de modelo es el mayor valor.
- **Spec-driven y por etapa**: traza cada criterio de aceptación, lee informes previos para contexto cruzado. Ideal como auditoría de cierre de etapa contra PLAN.md.
- Read-only puro; deja artefactos versionables en `revisiones/`.
- Costo: rate limits gestionados a mano (de ahí `codex_usage.sh` y el `SLEEP`).

**/code-review / Claude**
- **Integrado en el loop**: se corre antes del commit/PR, sin salir de la sesión, con todo el contexto cargado.
- **Accionable**: `--fix` aplica, `--comment` comenta en el PR. Codex solo reporta.
- **Diff-centric**: óptimo para "esto que toqué, ¿está bien?", no para "¿la etapa 6 cumple todos sus Done when?".
- Effort escalable hasta `ultra` (multi-agente cloud).

---

## Recomendación de uso combinado

Dos capas, no redundantes:

- **Durante el desarrollo de la etapa** → `/code-review` (rápido, con contexto, puede arreglar en el sitio). Antes de commitear.
- **Al cerrar la etapa, como auditoría independiente** → `run_review.sh` con Codex, que valida etapa → test → Done when con otro modelo. El valor es que *no* es Claude.
- **Antes de mergear algo grande** → `/code-review ultra` (multi-agente) y/o el informe de Codex como segundo par de ojos.

En una frase: Codex es el **auditor externo spec-driven de cierre de etapa**; `/code-review` es el **reviewer inline diff-driven del día a día que además corrige**; y `codex_usage.sh` es solo el cuentakilómetros de Codex.
