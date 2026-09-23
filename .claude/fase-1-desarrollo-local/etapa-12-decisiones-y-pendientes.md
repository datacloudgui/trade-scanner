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

## T4 — OpenSpec instalado (2026-09-23, ejecutado a mano por el usuario)

- Node **v26.9.0** (Homebrew), npm 11.19.1. `npm view @fission-ai/openspec engines` → `node >=20.19.0`: cumple.
- `@fission-ai/openspec` **1.13.1** global (`/opt/homebrew/bin/openspec`), la última versión publicada.

## T5 — `openspec init` + perfil + `config.yaml` (2026-09-23)

**Lo que generó `init`** (ejecutado a mano, solo Claude Code):
- `openspec/{config.yaml, specs/.gitkeep, changes/archive/.gitkeep}`, más skills y comandos en `.claude/`.
- `git diff` vacío: **no modificó** `CLAUDE.md` ni `AGENTS.md`, y no creó `.cursor` ni `.agents`.

**Primer hallazgo: el perfil `core` no incluye `verify`.** Solo trae propose, explore, apply, update, sync y archive. Sin `verify` no hay G5 ni T8. Acción del usuario:
- `openspec config profile` → `custom` = core + verify, con `delivery: commands`.
- `openspec update` → quedan **7 comandos** en `.claude/commands/opsx/` y las skills se borran. Se eliminó el directorio vacío `.claude/skills/`.
- Es configuración **global** de la máquina (`~/.config/openspec/config.json`).
- La consecuencia de `delivery: commands` es positiva: OpenSpec solo actúa cuando se invoca un `/opsx:*`; las skills se activaban solas.

**Hallazgos en el texto de los comandos generados:**
- `/opsx:archive` archiva con **`mv` directo**, sin `openspec validate`. Con tareas o artefactos incompletos solo pide confirmación, y ofrece "Archive without syncing". → G6 del roadmap corregido; las reglas entran en `config.yaml` y en CLAUDE.md (T7).
- `/opsx:verify` marca como CRITICAL las tareas incompletas y los requisitos no encontrados, y como WARNING los escenarios sin test. **No corre tests**: G2 sigue siendo `run_tests.sh`.

**Pruebas en un repo temporal** (scratchpad, con OpenSpec 1.13.1 y `OPENSPEC_TELEMETRY=0`):

| Prueba | Resultado |
|---|---|
| Archivo extra `bitacora.md` en el change | `validate --strict` OK y se archiva con el change → las bitácoras viven dentro del change desde la Etapa 13 |
| `openspec archive` sobre un requisito ya sincronizado | "Specs already in sync; no files changed" → **no duplica** los ADDED |
| Capability nueva archivada | Queda con `Purpose: TBD`; `validate --all --strict` → **exit 1**; también falla con un Purpose de menos de 50 caracteres; con Purpose adecuado → exit 0 |
| `init --language es` | Solo agrega al `context`: artefactos en español, con encabezados y SHALL/MUST en inglés |
| `operations` en `config.yaml` | Solo existen `apply` y `archive`, y son consejo, no obligan |

**`config.yaml`:**
- Contenido: `context` (idioma, scan-only, precedencia, dónde están las reglas y los gates, tests solo en Docker), `rules` para proposal/design/specs/tasks y `operations.apply/archive.guidance`.
- **Trampa de YAML:** el ítem `- Incluir "Rollback": R-cfg…` se parseaba como mapa. OpenSpec avisó "Rules for 'proposal' must be an array of strings, **ignoring**" y descartó **todas** las reglas de proposal sin fallar. Se corrigió entrecomillando el ítem.
- Verificado con `openspec instructions` en el repo temporal (con este mismo archivo): se inyectan el context, las 4 reglas (sin "ignoring") y las guías de apply y archive.
- Repo: `openspec validate --all --strict` → exit 0; `openspec doctor` → exit 0.

**Telemetría:** activa (solo nombres de comandos y versión, según la documentación). Queda como decisión del usuario apagarla con `openspec config set telemetry.enabled false`.

**Decisiones tomadas en T5 que afectan tareas posteriores:**
- **Disposición de la documentación:** solo se mueve `AGENTS.md`; el resto se queda o se congela. Tabla en la spec, sección *Disposición de la documentación*.
- **T6 ampliado** (aprobado por el usuario): `run_review.sh` acepta `CHANGE=<id>`. El porqué está en la spec, T6: sin esto, las revisiones de la Etapa 13 en adelante caerían en silencio a PLAN.md.
- **T8 con menos riesgo:** la duplicación ya quedó descartada para la CLI; falta probar el flujo con `/opsx:*` en el repo.

## Revisión de alineación T6–T11 (2026-09-23, antes de iniciar T6)

Se contrastó la spec contra el repo y contra lo decidido o hallado en T1–T5. Hubo 8 correcciones:

1. **T6 no se podía verificar tal como estaba escrito:** pedía `DRY_RUN=1`, pero `run_review.sh` no tiene ese modo. Se agregó como paso.
2. **T6 dependía de T8:** verificaba `CHANGE=<id>` "contra el change de T8". Ahora usa dos directorios temporales (uno activo y uno archivado). También se definió la semántica de `CHANGE` (va con un solo número de etapa) y un error explícito si el id no existe.
3. **T6: el prompt movido contradecía el flujo nuevo.** Decía `PLAN > SPECS > CLAUDE` (L23), "etapa en progreso/pendiente" (L33) y "Stooq; Alpaca diferido" (L79). Se alinea sin reescribirlo. Lo mismo para L48 de `run_review.sh`.
4. **T7:** decía "5 reglas de §0.4", pero son 4. Además faltaba tocar secciones que ya existen en CLAUDE.md (*Documentos y precedencia*, pasos 3–5 del *Flujo*, *Gotchas*), no solo agregar una sección nueva.
5. **T8:** la lista de pasos seguía mostrando `openspec archive --yes` en lugar de `validate` → `/opsx:archive`. Decía "exit 0" para comandos `/opsx:*`, que no tienen código de salida. No verificaba que las reglas de `config.yaml` funcionaran en el repo real. El retiro de la capability no estaba definido: ahora es manual y documentado (un change REMOVED exigiría `retire_capabilities`).
6. **T9:** la ventana se commiteaba al final, así que el README del baseline no podía citar el commit con el que se generó. Ahora se commitea **antes** del backtest. Además: fecha genérica en la carpeta y el tag, tag anotado, y el Scope ya no dice "fecha semanal ya editada" (esa edición se descartó).
7. **T10 no tenía commit de cierre:** faltaba pasar a `completada` PLAN, la spec y la bitácora antes del merge. **T11 se ejecuta antes que T10.**
8. **T11:** `docs/ROADMAP.md` no tiene una sección de "candidatos de Fase 2". La entrada va bajo `# Post V1`.

Además: la Fase A se movió al principio del Done when; la lista de commits refleja los reales; la pregunta sobre `--skip-specs` se cerró (resuelta en T5); se agregó la de telemetría. PLAN.md se ajustó en las líneas de T8 y T11.

## Decisión: Codex no disponible → `run_review.sh` opcional (2026-09-23)

- **Hecho:** el usuario ya no tiene Codex (`which codex` → no encontrado).
- **Decisión:** `run_review.sh` y `codex_usage.sh` pasan a ser **opcionales** (solo si se reactiva Codex). La revisión por defecto es `/opsx:verify` (G5) + `/code-review`. Ningún gate depende de Codex.
- **Cambios en T6:**
  - se mantiene el traslado de `AGENTS.md`, porque otras herramientas también leen ese archivo en la raíz;
  - `run_review.sh` recibe solo cambios mínimos: ruta nueva del prompt, guard si falta `codex` (sin crear `revisiones/<stamp>/`) y aviso explícito para etapas ≥13;
  - `CHANGE=<id>` y `DRY_RUN` (aprobados antes) pasan a **diferidos** en el roadmap §4, con el disparador "si se reactiva Codex". Su único beneficiario no se puede ejecutar;
  - se eliminó la mención de T8 como prueba de `CHANGE=<id>`.

## Pendientes

- T6 en adelante. **T6 no se inicia hasta que el usuario lo indique.**
