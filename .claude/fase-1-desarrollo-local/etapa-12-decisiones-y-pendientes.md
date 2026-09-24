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

**Telemetría:** activa (solo nombres de comandos y versión, según la documentación). ~~Queda como decisión del usuario apagarla con `openspec config set telemetry.enabled false`.~~ **Decisión (2026-09-23): se deja activa.**

**Decisiones tomadas en T5 que afectan tareas posteriores:**
- **Disposición de la documentación:** solo se mueve `AGENTS.md`; el resto se queda o se congela. Tabla en la spec, sección *Disposición de la documentación*.
- ~~**T6 ampliado** (aprobado por el usuario): `run_review.sh` acepta `CHANGE=<id>`. El porqué está en la spec, T6: sin esto, las revisiones de la Etapa 13 en adelante caerían en silencio a PLAN.md.~~ *(superado: ver "Decisión: Codex no disponible"; `CHANGE=<id>` y `DRY_RUN` diferidos al roadmap §4)*
- **T8 con menos riesgo:** la duplicación ya quedó descartada para la CLI; falta probar el flujo con `/opsx:*` en el repo.

## Revisión de alineación T6–T11 (2026-09-23, antes de iniciar T6)

Se contrastó la spec contra el repo y contra lo decidido o hallado en T1–T5. Hubo 8 correcciones:

1. ~~**T6 no se podía verificar tal como estaba escrito:** pedía `DRY_RUN=1`, pero `run_review.sh` no tiene ese modo. Se agregó como paso.~~ *(superado: ver "Decisión: Codex no disponible"; `CHANGE=<id>` y `DRY_RUN` diferidos al roadmap §4)*
2. ~~**T6 dependía de T8:** verificaba `CHANGE=<id>` "contra el change de T8". Ahora usa dos directorios temporales (uno activo y uno archivado). También se definió la semántica de `CHANGE` (va con un solo número de etapa) y un error explícito si el id no existe.~~ *(superado: ver "Decisión: Codex no disponible"; `CHANGE=<id>` y `DRY_RUN` diferidos al roadmap §4)*
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

## T6 — `AGENTS.md` → `docs/review/`, `run_review.sh` opcional (2026-09-23)

**Cambios:**
- `git mv AGENTS.md docs/review/codex-review-prompt.md`: ya no hay prompt de solo lectura en la raíz.
- `scripts/run_review.sh`, cambios mínimos:
  - cabecera "OPCIONAL — requiere Codex CLI…";
  - guard `command -v codex` **antes** del `mkdir -p "$OUTDIR"`: mensaje a stderr y `exit 1`;
  - L39/L47-48: ruta nueva del prompt y "cadena de precedencia de CLAUDE.md" en lugar de "PLAN.md/SPECS.md como fuentes de verdad";
  - si no existe `etapa-NN.md`, un segundo aviso dice que desde la Etapa 13 el alcance vive en `openspec/changes/<id>/` y que el script todavía no lo soporta.
- Prompt movido, alineado sin reescribirlo:
  - L23: remite a la cadena de precedencia de CLAUDE.md (desaparece "máxima precedencia");
  - L33: la etapa activa sale de la tabla *Secuencia del ciclo* de PLAN §7 y, si es un change, de sus `proposal`/`design`/`tasks`/`specs`;
  - L79: fila de datos → Opción C de ADR-002 (9A); Stooq queda como fuente previa.
- `docs/conceptos/code-review-codex-vs-anthropic.md`: aviso de estado (Codex opcional, no instalado) y revisión por defecto `/opsx:verify` (G5) + `/code-review` al cerrar etapa. Se quitó `AGENTS.md` del contexto que hereda `/code-review`.

**Evidencia (criterios de aceptación):**

| Criterio | Salida |
|---|---|
| `test ! -f AGENTS.md` / `test -f docs/review/codex-review-prompt.md` | OK / OK |
| `grep -n "AGENTS.md" scripts/*.sh` | 0 resultados |
| `bash -n scripts/run_review.sh` | OK |
| `bash scripts/run_review.sh 5` sin Codex | "run_review.sh es OPCIONAL y requiere Codex CLI (no encontrado en PATH)." + "La revisión por defecto es /opsx:verify (G5) + /code-review."; **exit 1** |
| `ls revisiones` antes / después | `20260619-205134` / `20260619-205134` (`diff` vacío) |
| `grep -c` en el prompt | "precedencia de CLAUDE.md" = 1; "máxima precedencia" = 0; "Opción C" = 1 |
| Cápsula | L6 marca Codex **OPCIONAL** y nombra `/opsx:verify` + `/code-review`; L70 lo repite para el cierre de etapa |

**Notas:**
- Las menciones restantes de `AGENTS.md` (`git grep`, sin `revisiones/`) son narrativas: esta spec, esta bitácora, el roadmap y PLAN. No queda ningún link roto.
- `scripts/codex_usage.sh` y `revisiones/` no se tocaron.
- `CHANGE=<id>` y `DRY_RUN` siguen diferidos (roadmap §4).

## T7 — CLAUDE.md: convivencia con OpenSpec (2026-09-23)

**Secciones existentes que se tocaron:**
- *Documentos y precedencia*:
  - la lista pasa a 6 fuentes (PLAN, change activo, `openspec/specs`, SPECS, CLAUDE, `/opsx:*`);
  - **una sola cadena**: `PLAN.md` > change activo > `openspec/specs` > `SPECS.md` > `CLAUDE.md` > `/opsx:*`, con la excepción de §0.4 (reglas duras y flujo solo cambian con ADR + edición de CLAUDE.md).
  - Se conservó el nombre de la sección, porque el prompt de revisión (T6) la cita.
- *Flujo de trabajo*:
  - el paso 1 no cambia (PLAN §7 L169 lo cita);
  - paso 3: rama desde `develop`; Estado solo en PLAN.md; progreso por checkbox (etapa sin change) o por `tasks.md` + G2 (etapa con change). El criterio es la columna *Forma* de la tabla del ciclo, no el número: 5B y 11 son < 12 pero serán changes;
  - paso 4: suma G0–G5;
  - paso 5: cierre ordenado (sync → Done when → validate → `/opsx:archive` → Purpose → validate --all → commit → merge `--no-ff` → ff de `main` + tag → push → borrar rama);
  - paso 6: "o al change".
- *Comandos*: bloque `openspec` (validate, instructions, update), `run_review.sh` marcado OPCIONAL, lista de `/opsx:*`, revisión por defecto `/opsx:verify` + `/code-review` y la regla de no editar `.claude/commands/opsx/` a mano.
- *Convenciones*: la línea de commits remite a la regla 4 (`[Etapa N]`, `[Etapa N][<change-id>]`, `[config]`).
- *Gotchas*: subsección "Descubiertos en Etapa 12": archive con `mv`, `Purpose: TBD`, YAML "ignoring", perfil `core` sin `verify` y `/opsx:verify` sin tests.
- *Definición de "verificado"*: rige igual para cada `[x]` de `tasks.md`.

**Sección nueva "OpenSpec y PLAN.md":**
- reglas de convivencia §0.4 (1 precedencia → remite a la cadena única; 2 equivalencias; 3 prohibiciones ampliadas en T5; 4 commits);
- tabla de gates G0–G6 + G-data;
- artefactos de un change, que replican **todas** las reglas de `config.yaml` (proposal/design/specs/tasks y guía de apply);
- reglas de archive;
- `config.yaml` como consejo;
- tabla de disposición de la documentación;
- ramas y commits: modelo de 5 ramas, 6 reglas y la vía ligera `[config]`.

**Evidencia (criterios de aceptación):**

| Criterio | Salida |
|---|---|
| `grep -n "PLAN.md > SPECS.md" CLAUDE.md` | 0 resultados |
| Cadena única | 1 sola línea con `> change activo` (L14) |
| Sección y subsecciones | `## OpenSpec y PLAN.md` (L35) con *Reglas de convivencia*, *Gates*, *Artefactos de un change*, *Reglas de archive*, *`openspec/config.yaml`*, *Disposición de la documentación*, *Ramas y commits* |
| 4 reglas de §0.4 | L41 Precedencia, L42 Equivalencias, L47 Prohibido, L55 Commits |
| 7 prohibiciones | `--no-validate`, `--skip-specs`, sync sin G3/G4/G5, CRITICAL abiertos, archive sin `validate --strict`, tareas/artefactos incompletos, "Archive without syncing": todas presentes |
| Modelo de ramas / disposición / corrida semanal | 5 filas de ramas; "se congela al cerrar la Etapa 12" = 1; reseed antes de `lean backtest` = 1 |
| Pasos 3–5 del flujo | `tasks.md`, archive, `--no-ff` y `--ff-only` presentes |
| `bash scripts/run_tests.sh` | **exit 0, 304 passed**, 13 warnings (sin cambios de código en T6/T7) |
| `openspec validate --all --strict` | exit 0 ("No items found to validate") |

**Tachado en esta bitácora** (pedido del usuario): la línea "T6 ampliado" de T5 y los puntos 1–2 de la *Revisión de alineación*, que describían `CHANGE=<id>`/`DRY_RUN` en T6. Quedaron superados por la decisión "Codex no disponible".

## T8 — Spike `chore-openspec-smoke` (2026-09-23)

Primera vez que se recorre el ciclo `/opsx:*` en el repo. La evidencia detallada vive en el change archivado: [bitacora.md](../../openspec/changes/archive/2026-09-23-chore-openspec-smoke/bitacora.md) (y sus `proposal`, `design` D-1…D-5, `tasks`).

**Recorrido y evidencia (criterios de aceptación):**

| Paso | Salida |
|---|---|
| `/opsx:propose` → G0 `openspec validate chore-openspec-smoke --strict` | `is valid`, **exit 0**. Reglas de `config.yaml` inyectadas en los 4 artefactos, sin "ignoring" |
| G1 | Aprobado por el usuario tras dos decisiones: `## Purpose` en el delta (D-3) y G2 + G3 aunque no haya código (D-5). Re-validación: exit 0 |
| `proposal.md` | Trae Etapa 12 T8 + rama, "Diferencias esperadas en la watchlist" (ninguna) y "Rollback" (R-git); artefactos en español, encabezados y SHALL en inglés |
| `/opsx:apply` | 5/5 tareas. G2 `run_tests.sh` exit 0 ×3 (**304 passed**); G3 `lean backtest "trade-scanner" --parameter env dev` **exit 0** (`env=dev`, `gate dev OK 36/36`); G4 N/A (`git diff --stat develop -- trade-scanner/ config/` vacío) |
| `/opsx:verify` (G5) | **0 CRITICAL**; 1 WARNING ("scenario sin test") justificado en design D-2 |
| `/opsx:sync` | Creó `openspec/specs/openspec-smoke/spec.md`; `validate --specs --strict` exit 0 |
| `validate --strict` → `/opsx:archive` | exit 0 → "already synced"; opciones *Archive now* / *Sync anyway* / *Cancel* pasadas al usuario, que eligió **Archive now** → `openspec/changes/archive/2026-09-23-chore-openspec-smoke/` |
| Requisito sin duplicar | `grep -rc` en `openspec/specs/` = **1** |
| Purpose | Copiado literal del delta por sync: 134 caracteres, sin `TBD` → no hubo que escribirlo |
| `validate --all --strict` | Con la capability: exit 0 (1 passed). Tras `git rm -r openspec/specs/openspec-smoke/`: exit 0 ("No items found to validate") |
| Flags prohibidos | Nunca `--no-validate` ni `--skip-specs` |

Commits: `9a9784a` (spike archivado con Purpose) y `56738ed` (retiro manual + T8 marcado).

**Hallazgos** (dónde un `/opsx:*` o el repo difiere de CLAUDE.md; se alinean en **T8b**):

1. **Purpose — `/opsx:propose` (instrucción de specs) vs CLAUDE.md.** El schema 1.13.1 pide `## Purpose` en el delta de una capability nueva, y `/opsx:sync` (paso 4d) y la CLI `archive` (#1413) lo copian literal a la spec principal. CLAUDE.md (L27, L88, L147, gotcha L239), `config.yaml` L47 y roadmap §0.2 G6 dan por hecho un `TBD` que hay que escribir. **Qué hice:** seguí al generador (D-3); el paso 5 quedó como verificación. El `TBD` de T5 venía de un delta sin Purpose.
2. **Gates en un change sin código — spec T8 vs CLAUDE.md.** El spec decía que G2/G3/G4 "no aplican"; CLAUDE.md exige G2 para cada `[x]` y prohíbe `sync` sin G3. Ningún `/opsx:*` ni la CLI ejecuta tests o backtests (`verify` solo lee; los 7 comandos declaran `allowed-tools: Bash(openspec:*)`). **Qué hice:** se corrieron G2 y G3 a mano (D-5, aprobado en G1).
3. **G3 no define cómo se elige dev.** `trade-scanner/config.json` versionado = `env: prod`; el README (L93, L204) dice `dev`. **Qué hice:** `--parameter env dev` sin tocar archivos versionados; verificado en el log (`env=dev`).
4. **`lean` no encuentra Docker:** busca `/var/run/docker.sock`, que no existe con Docker Desktop (`~/.docker/run/docker.sock`); `run_tests.sh` sí funciona porque usa el CLI `docker`. **Qué hice:** `DOCKER_HOST=unix://$HOME/.docker/run/docker.sock` solo en ese comando. **Cerrado 2026-09-23:** socket por defecto habilitado en Docker Desktop; sale de T8b.
5. **G3 contamina `storage/results/`:** la corrida dev sobreescribió `storage/results/swing_eod/latest.json`. Gitignoreado; G4/T9 vacían la carpeta, pero falta una regla que impida publicar tras un G3 sin re-correr prod.
6. **Regla de Scenarios de `config.yaml`** ("test en Docker o evidencia de backtest") no cubre requisitos documentales. **Qué hice:** evidencia de comando citada en la bitácora (D-2); `verify` lo reporta como WARNING.
7. **`/opsx:archive` con specs ya sincronizadas** ofrece *Archive now* / *Sync anyway* / *Cancel*; CLAUDE.md solo regula "Archive without syncing".
8. **Rama:** `config.yaml` sugiere `feature/etapa-NN-<change-id>`; como el spike es una tarea de una etapa sin change, ganó "una etapa, una rama" (D-4). En los ciclos normales el patrón encaja; solo se registra.
9. **Lateral (conocido):** el CLI reescribe `file-database-last-update` en `lean.json` en cada backtest → `git restore lean.json` antes de commitear.

**Decisión posterior (usuario, 2026-09-23):** cerrar T8 con CLAUDE.md tal como se probó y alinear después en una tarea nueva, **T8b**, antes de T9.

## T8b — Alineación con los hallazgos de T8 (2026-09-23)

Edición explícita de CLAUDE.md aprobada por el usuario (paso 6 del flujo). Solo se tocaron las líneas que nombra el spec; `.claude/commands/opsx/` y `etapa-12.md` T8 quedan sin cambios.

**Ediciones (hallazgo → dónde):**

| Hallazgo | CLAUDE.md | Otros |
|---|---|---|
| 1 Purpose en el delta, verificado tras archive | paso 5.1 (L27); *Artefactos*, `specs/**` (L83, regla nueva); *Reglas de archive* (L93); *Comandos* (L153, "sin Purpose `TBD`"); gotcha (L245, #1413) | `config.yaml`: `rules.specs` (regla nueva, entrecomillada por `": "` y `#`) y `operations.archive.guidance`; roadmap §0.2 G6 |
| 2 G2/G3 en changes sin código | nota bajo la tabla de gates (L70) | — |
| 3 G3 con `--parameter env dev` | tabla de gates, G3 (L64) | roadmap §0.2 G3; README L93 y L204 (`config.json` versionado = `prod`) |
| 5 G3 contamina `storage/results/` | *Ramas y commits*, regla 3 (L133) | — |
| 6 Regla de Scenarios | *Artefactos*, `specs/**` (L82) | `config.yaml` `rules.specs` |
| 7 *Archive now* | *Reglas de archive* (L92) | — |
| 8 Rama (aclaración) | *Artefactos*, `proposal.md` (L77) | `config.yaml` `context` y `rules.proposal` |
| 9 `lean.json` | gotcha *Descubiertos en Etapa 12* (L249) | — |

**Evidencia (criterios de aceptación):**

| Criterio | Salida |
|---|---|
| `grep -c "se escribe su \`Purpose\`\|con el Purpose escrito\|se archiva con \`Purpose: TBD\`" CLAUDE.md` | **0** |
| `grep -c "escribir su Purpose" openspec/config.yaml` | **0** |
| `grep -c "## Purpose" openspec/config.yaml` | **1**; misma regla en CLAUDE.md L83 |
| `grep -c -- "--parameter env dev"` CLAUDE.md / roadmap | **1** / **1** |
| `grep -c '{"env": "dev"}' README.md` | **0** |
| Reglas en CLAUDE.md | no publicar tras G3 (L133), G2/G3 sin código (L70), Scenarios ampliada (L82), *Archive now* (L92), rama (L77), gotcha `lean.json` (L249) |
| `openspec new change tmp-t8b-check` → `openspec instructions specs --change tmp-t8b-check` | exit 0; "ignoring" = **0**; muestra la regla de Scenarios ampliada, la de `## Purpose` y la aclaración de rama (en el `context`) |
| `openspec instructions proposal --change tmp-t8b-check` | exit 0; "ignoring" = **0**; muestra la aclaración de rama en `context` y en `rules.proposal` |
| Change temporal | `rm -rf openspec/changes/tmp-t8b-check`; `git status` sin rastro; nunca commiteado |
| `openspec validate --all --strict` | **exit 0** ("No items found to validate") |
| `bash scripts/run_tests.sh` | **exit 0, 304 passed**, 13 warnings |

**Nota:** `openspec instructions specs` sin `--change` (forma literal del criterio) sale con "Missing required option --change" en 1.13.1: la instrucción de cualquier artefacto exige un change. Se verificó con `--change tmp-t8b-check`, que es lo que el criterio pretende.

## Pendientes

- **Cerrados (2026-09-23):** Docker Desktop con socket por defecto habilitado (`/var/run/docker.sock` → `~/.docker/run/docker.sock`; `lean` ya no necesita `DOCKER_HOST`); telemetría de OpenSpec activa por decisión del usuario.
- **T8b** cerrada (2026-09-23). **T9** no se inicia hasta que el usuario lo indique.
