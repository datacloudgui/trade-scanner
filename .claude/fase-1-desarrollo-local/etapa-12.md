# Etapa 12 — Base estable + adopción de OpenSpec (bootstrap del ciclo 2026-09)

**Estado:** en progreso (desde 2026-09-23; Fase A completada)
**Depende de:** ninguna etapa de código. Entrada: [roadmap-definitivo-2026-09.md](roadmap-definitivo-2026-09.md) (U0), aprobado.
**Rama:** `feature/etapa-12-bootstrap-openspec`, creada desde `develop` en la Fase A (ver *Manejo de ramas*)
**Estimado:** 3–4 h (más la instalación de Node si hace falta)

> **Última etapa en formato `etapa-NN.md`.** Desde la Etapa 13, cada unidad del roadmap se especifica como un change
> de OpenSpec (`openspec/changes/<id>/`). Esta etapa no puede serlo: es la que instala y valida OpenSpec (bootstrap).

---

## Objetivo

Al terminar hay cuatro cosas que hoy no existen:
- **Config sembrada == config versionada.** El working tree ya se limpió el 2026-09-23 (`git restore`), pero el ObjectStore `storage/` **sigue sembrado con `swing_eod_short: true`**: está gitignoreado y `git restore` no lo toca. Cualquier backtest que se corra antes de T2 sigue publicando watchlists que cruzan universos (hallazgo H1 del roadmap).
- **PLAN.md vuelve a ser fuente de verdad.** Refleja el estado real de todas las etapas y el orden del ciclo.
- **OpenSpec instalado y probado.** Su ciclo completo quedó validado de punta a punta y ya no contradice CLAUDE.md ni AGENTS.md.
- **Baseline reproducible de la watchlist long.** Es la referencia del gate G4 para las Etapas 13–15.

## Decisiones de diseño

| Decisión | Elección | Por qué |
|---|---|---|
| ¿U0 como etapa numerada o como tarea suelta? | **Etapa 12 numerada** | Genera commits (config, CLAUDE.md, AGENTS.md, baseline). El flujo de CLAUDE.md exige que cada commit lleve el tag `[Etapa N]` y que se pueda rastrear en PLAN |
| ¿Formato? | **`etapa-12.md` clásico**, nombre con 2 dígitos | Bootstrap: OpenSpec todavía no existe. El nombre `etapa-NN.md` es el que busca `scripts/run_review.sh` (L35) |
| Numeración del resto del ciclo | Ver la tabla "Secuencia del ciclo" (T3) | Las etapas que ya tienen número lo conservan: 5B, 9 y 11. Solo el trabajo nuevo recibe número (13, 14, 15) |
| ¿Cómo se desactiva el short? | **R-cfg** (`enabled: false` + reseed) | Frena la contaminación sin revertir código. Todavía no es un rollback limpio: lo será después de la Etapa 14 (roadmap, U3b §Rollback) |
| ¿Qué pasa con la documentación existente? | **Solo se mueve `AGENTS.md`**; todo lo demás se queda donde está (ver *Disposición de la documentación*) | Mover carpetas rompe links (43 referencias a `.claude/fase-1-desarrollo-local`, 15 a `.claude/decisions`, 27 a `SPECS.md`), rompe `run_review.sh` y rompe `git blame`. OpenSpec no exige migrar la historia |
| ¿Dónde quedan los datos del baseline? | Resultados y manifiesto **en git** (`baselines/<tag>/`); zips y CSV en un **tarball fuera del repo** | `data/*`, `storage/` y los CSV de Barchart están gitignoreados por diseño (la licencia de Barchart no permite versionarlos). El manifiesto permite verificar el snapshot y el tarball permite restaurarlo |

### Secuencia del ciclo (se copia a PLAN §7 en T3)

| Orden | Etapa | Unidad del roadmap | Forma |
|---|---|---|---|
| 1 | **12** | U0 | `etapa-12.md` (este documento) |
| 2 | **13** | U1 `add-data-coverage-gate` | change de OpenSpec |
| 3 | **5B** (cierre de F3) | U1b `close-5b-reference-fixture` | change de OpenSpec que cierra una etapa existente |
| 4 | **11** (re-scope) | U2 `derive-backtest-range-from-universe` | change de OpenSpec; supersede a `etapa-11-fecha-desde-universo.md` |
| 5 | **14** | U3a `partition-scan-universe-per-strategy` + ADR-006 | change de OpenSpec |
| 6 | **15** | U3b `enable-short-side` + enmienda a ADR-005 | change de OpenSpec |
| 7 | **9** (+ 9A T7/T8) | U4 | tarea de PLAN, sin change |

---

## Manejo de ramas (vale desde este ciclo; T7 lo resume en CLAUDE.md)

### Modelo

| Rama | Rol | Cómo avanza |
|---|---|---|
| `main` | **Producción:** la versión con la que se corre la watchlist semanal real y se envía el correo | Solo **fast-forward** desde `develop` al promover, más un tag anotado `scan/vYYYY.MM.DD-N`. Nunca recibe commits propios |
| `develop` | **Integración:** solo etapas cerradas | Un merge **`--no-ff`** por etapa. Así cada etapa queda en un único merge commit, y `git revert -m 1 <merge>` la revierte entera (es la primitiva R-git del roadmap) |
| `feature/etapa-NN-<change-id>` | **Una rama por etapa**, creada desde `develop`. Desde la 13, el sufijo es el id del change de OpenSpec | Commits `[Etapa NN] …`; push después de cada commit (respaldo) |
| `config/<slug>` | Vía ligera `[config]` | Igual que una rama de etapa |
| `hotfix/<slug>` | Rollback urgente de producción, solo si `develop` tiene trabajo sin promover | Sale de `main`; `main` avanza por fast-forward hasta el hotfix; después `main` se mergea en `develop` |

Ramas previstas en el ciclo:
- `feature/etapa-12-bootstrap-openspec`
- `feature/etapa-13-add-data-coverage-gate`
- `feature/etapa-05b-close-reference-fixture`
- `feature/etapa-11-derive-backtest-range-from-universe`
- `feature/etapa-14-partition-scan-universe-per-strategy`
- `feature/etapa-15-enable-short-side`

### Reglas

1. **Una etapa, una rama.** Ninguna rama acumula varias etapas: `feature/etapa-6-features-rules` terminó conteniendo siete.
2. **Cierre de etapa, en este orden:**
   1. Done when verificado (y `openspec archive` desde la 13).
   2. Commit de cierre en la rama.
   3. `git switch develop && git merge --no-ff <rama> -m "[Etapa NN] merge: <resumen>"`.
   4. **Promoción:** `git switch main && git merge --ff-only develop`, más `git tag -a scan/vYYYY.MM.DD-N`.
   5. `git push origin develop main <tag>`.
   6. Borrar la rama, local y remota: su historia queda completa en el merge commit.

   Como toda etapa ya pasó sus gates (G4 incluido) antes de cerrarse, se promueve al cerrar. Después de cada cierre, `main` == `develop`.
3. **La corrida semanal real se hace siempre desde `main`:** `git switch main && bash scripts/seed_object_store.sh` antes de `lean backtest`. `storage/` y `data/` están gitignoreados, así que `git switch` **no** los cambia: sin reseed, la corrida usa la config de la última rama que se sembró.
   - Mientras la Etapa 11 no esté cerrada, la edición semanal de `end_date` en `main.py` **no se commitea**: se corre y después `git restore trade-scanner/main.py`, antes de cambiar de rama.
   - Las **corridas de revisión** de una etapa en curso (p. ej. las ≥3 semanales del short en la Etapa 15) se hacen en su rama. **No se publican**: no se ejecuta `notify_email.py` con ellas. Solo lo que sale de `main` llega al correo.
4. **Push:**
   - rama de etapa: después de cada commit;
   - `develop`, `main` y tags: en cada cierre;
   - tags siempre anotados (`-a`).
5. **No se reescribe historia publicada:** nada de `rebase` ni `push --force` sobre `develop`, `main` o una rama ya pusheada.
6. **Merges locales** (no hay `gh` instalado). Si se quiere revisión antes del merge: `/code-review` sobre la rama.

### Fase A — transición desde el estado actual (antes de T1, **sin commits**)

Estado verificado el 2026-09-23:
- `feature/etapa-6-features-rules` está sincronizada con `origin` y le lleva 16 commits a `develop`.
- `develop` está sincronizada con `origin` y le lleva 14 commits a `main`.
- `main` local le lleva 10 commits a `origin/main`.
- No hay merge commits ni tags.
- Working tree: **solo 3 documentos sin versionar** (los dos roadmaps y esta spec). Los cambios de `config/strategies.json`, `lean.json` y `trade-scanner/main.py` se descartaron el 2026-09-23.
- `storage/config/strategies.json` todavía tiene `swing_eod_short.enabled: true` (se corrige en T2, no en la Fase A).

| Paso | Comando | Por qué |
|---|---|---|
| A1 | `git fetch . feature/etapa-6-features-rules:develop` | Fast-forward de `develop` sin checkout: sin saltar de rama, no hace falta volver después. Si no fuera fast-forward, falla solo (no puede pasar: `develop` no tiene commits propios) |
| A2 | `git fetch . develop:main` | `main` alcanza el estado operativo actual (fast-forward; `main` no tiene commits propios) |
| A3 | `git tag -a scan/v2026.09.23-pre-ciclo develop -m "Estado operativo antes del ciclo 2026-09 (f8ded63)"` | Ancla de rollback de código para todo el ciclo |
| A4 | `git push origin develop main scan/v2026.09.23-pre-ciclo` | Publica los tres. `main` sube también sus 10 commits pendientes |
| A5 | `git switch -c feature/etapa-12-bootstrap-openspec develop` | Los 3 documentos sin versionar pasan a la rama nueva; `develop` ya tiene el mismo árbol que la rama vieja |
| A6 | `git add` de los dos roadmaps + `etapa-12.md` → commit `[Etapa 12] spec: roadmap consolidado del ciclo 2026-09 + etapa-12` → `git push -u origin feature/etapa-12-bootstrap-openspec` | **La spec se commitea primero y en su propia rama**, no en la vieja |

**Por qué no se commitea el plan en la rama vieja antes del merge:**
- `feature/etapa-6-features-rules` se cierra exactamente con lo que contiene: E6B–E10 y la spec de E11.
- La Etapa 12 arranca con su spec como primer commit.
- Ya no hay cambios de código ni de config pendientes (se descartaron), así que la rama vieja se integra sin tocarla. Los únicos cambios de estado que quedan son el reseed de `storage/` (T2, sin commit) y la ventana fija del baseline (T9, commit `[Etapa 12]`).

---

## Disposición de la documentación (vale desde este ciclo; T7 la copia a CLAUDE.md)

Principio: **casi nada se mueve.** Solo cambia de lugar lo que choca con OpenSpec (`AGENTS.md`). Lo demás o sigue
activo en su sitio o queda congelado como historia.

| Ubicación | Qué contiene | Decisión | Por qué |
|---|---|---|---|
| `AGENTS.md` (raíz) | Prompt del revisor Codex, de solo lectura | **Se mueve** a `docs/review/codex-review-prompt.md` (T6) | Codex y otros agentes leen solos el `AGENTS.md` de la raíz, y su "NUNCA modifiques archivos" choca con `/opsx:apply` |
| `PLAN.md` | Índice operativo + §1–§6 | Se queda | Fuente de verdad. Los contratos de §5 se migran a `openspec/specs/<capability>` **la primera vez que un change los toca**, y §5 queda con un link (nunca dos fuentes) |
| `SPECS.md` | Producto: por qué, entidades, criterios de cierre | Se queda; no se migra entero | Es el "por qué". El "qué hace" pasa a `openspec/specs` capability por capability |
| `CLAUDE.md`, `README.md` | Convenciones; runbook | Se quedan | CLAUDE.md suma la sección OpenSpec (T7); el README cambia en la Etapa 13 |
| `.claude/decisions/` | ADR-001…005 | Se queda; ADR-006 (E14) y la enmienda a ADR-005 (E15) se escriben aquí | Una decisión que cruza changes sobrevive a un `design.md`; convención del 2026-06-14 |
| `.claude/fase-1-desarrollo-local/` | Specs y bitácoras E0–E12, roadmaps | Se queda y **se congela al cerrar la Etapa 12** | Es historia, sin formato OpenSpec. Desde la Etapa 13 no se crean más `etapa-NN.md` |
| `docs/conceptos/`, `docs/research/` | Explicaciones y research | Se quedan | OpenSpec no cubre documentación explicativa |
| `docs/ROADMAP.md`, `docs/DEVLOG.md` | Fases y diario | Se quedan | Se ponen al día al cerrar la Etapa 11 (una entrada por etapa, con link al change archivado) |
| `revisiones/` | Informes y logs de Codex (17 MB) | Se queda; solo crece si se reactiva Codex | La referencian la triage y PLAN 9B |
| `scripts/poc/` | Spec y bitácora del POC Finnhub | Se queda | Diferido (roadmap §6) |

**Equivalencias desde la Etapa 13:**
- `etapa-NN.md` → `proposal.md` + `tasks.md`.
- `etapa-NN-decisiones-y-pendientes.md` se divide en `design.md` (decisiones D-n, preguntas abiertas) y `bitacora.md` **dentro del change** (evidencia de ejecución y checkpoints).
- Todo se archiva junto en `openspec/changes/archive/AAAA-MM-DD-<id>/`. Probado el 2026-09-23 en un repo temporal: un archivo extra en el change pasa `validate --strict` y se archiva con él.

**Capabilities previstas** (se crean a medida que llegan los changes):
- E13: `data-coverage`, `scan-output` (envelope y ScanResult, desde PLAN §5)
- 5B: `sma-accuracy`
- E11: `backtest-range` (+ MODIFIED sobre `scan-output`)
- E14: `scan-scope`
- E15: `strategy-filters`

---

## Tareas

### T1 — Verificar la suite y el entorno (Etapa 0 real)

Levantar Docker Desktop. Correr `docker run hello-world` y `bash scripts/run_tests.sh`. Registrar la cifra de passed.

**Criterio de aceptación:** `run_tests.sh` sale con exit 0; la cifra (p. ej. `N passed`) queda anotada para T3. `hello-world` OK.
**Notas:**
- Ya verificado el 2026-09-23: Python 3.11.11 en `.venv`, `lean 1.0.225`, existe `.python-version` y `.venv` está en `.gitignore`.
- Falta `hello-world`: Docker estaba apagado. Si la suite falla, **se detiene la etapa** y se arregla primero.

### T2 — Sincronizar el ObjectStore con la config versionada (H5)

El working tree ya está limpio: el 2026-09-23 se descartaron `enabled`, `end_date` y `lean.json`. Lo único que queda
es `storage/`: sigue sembrado con el short activo. Correr `bash scripts/seed_object_store.sh`. Es R-cfg sin commit:
la config versionada ya tiene `false`.

**No correr `lean backtest` antes de este paso.** T1 solo corre tests.

**Nota (verificado 2026-09-23):** si no hay CSV nuevos en `data/object-store/`, el script **conserva** los `storage/universes/*.csv` ya sembrados (los del 09-19) y solo resiembra `config/*.json` (L72-80). No hace falta exportar nada de Barchart. Los CSV fuente están en `data/object-store/processed/`.

**Criterio de aceptación:**
- `shasum -a 256 config/strategies.json storage/config/strategies.json` da dos hashes iguales.
- `jq '.strategies.swing_eod_short.enabled' storage/config/strategies.json` → `false`.
- No hay commit: `git status --short` sigue vacío.

### T3 — Resincronizar PLAN.md §7 y el flujo de CLAUDE.md

**Estados que se corrigen en PLAN.md:**
- **Etapa 0** → `completada`, con los checks de T1 como evidencia.
- **5B** → sigue `en progreso`, con la nota "F2 cerrada; F3 (T6.3 y T6.4) se reanuda en el orden 3 del ciclo".
- **6B** → `completada` (commits `dd44dfb` y `03880f2`).

**Entradas nuevas en PLAN.md:**
- **9A:** en progreso; T7/T8 → Etapa 9; T9 diferida.
- **9B:** completada, 19/20; #12 → Etapa 14.
- **10:** completada, `8b0afc2`.
- **11:** pendiente, re-scope según U2.
- **12:** en progreso.
- **13, 14, 15:** pendientes, cada una con link al roadmap y sus "Done when" copiados de ahí.
- Tabla **"Secuencia del ciclo"** al inicio de §7.

**Cambio en CLAUDE.md, paso 1 del flujo:** "Lee PLAN.md y localiza la etapa `en progreso`; si no hay, la siguiente pendiente según la tabla *Secuencia del ciclo* de §7". Sin este cambio, un agente que siga la regla actual ("la primera etapa pendiente o en progreso") escogería la 5B antes que la 13.

**Nota de supersesión** en el encabezado de `etapa-11-fecha-desde-universo.md`: la premisa `end_date = asof` y la prioridad del footer quedaron refutadas (roadmap H4/H4b).

**Criterio de aceptación:**
- `grep -nE "Etapa (9A|9B|10|11|12|13|14|15)" PLAN.md` encuentra cada una.
- La tabla de secuencia existe.
- Etapa 0 y 6B aparecen como `completada`.
- CLAUDE.md, paso 1, contiene la regla nueva.

### T4 — Instalar OpenSpec

`brew install node` (Homebrew disponible; hoy no hay Node ni nvm). Después `npm i -g @fission-ai/openspec`.

**Criterio de aceptación:**
- `node --version` cumple el `engines` del paquete (verificar con `npm view @fission-ai/openspec engines`; se espera Node ≥ 20.19).
- `openspec --version` responde. Ambas versiones quedan anotadas en la bitácora.

**Notas:** si Homebrew instala una versión de Node menor que la exigida, usar `brew install node@22` y fijarla en el PATH.

### T5 — `openspec init` solo para Claude Code

Correr `openspec init` en la raíz eligiendo **únicamente** Claude Code. Antes de commitear, revisar el diff completo: `git status` más `git diff`.

**Criterio de aceptación:**
- Existe `openspec/` con `specs/`, `changes/` y `config.yaml`.
- Las skills y comandos generados viven bajo `.claude/`.
- **Ningún archivo existente se modificó sin revisión.** Si `init` tocó `CLAUDE.md` o creó `AGENTS.md`, se conserva solo su bloque gestionado y el cambio se deja explícito en la bitácora.
- `openspec validate --all --strict` sale con exit 0 (repo vacío de changes).

**Notas:** en `openspec/config.yaml`, el contexto del proyecto apunta a CLAUDE.md, PLAN.md y SPECS.md en vez de duplicar su contenido.

**Ejecución real (2026-09-23; detalle en la bitácora):**
- Perfil global `custom` = core + **`verify`**: `core` no trae `verify`, y de él dependen G5 y T8.
- `delivery: commands`: solo los 7 comandos `.claude/commands/opsx/*`, sin skills. OpenSpec actúa solo cuando se lo invoca. Esos archivos los genera `openspec update` y **no se editan a mano**.
- `config.yaml` escrito con `context` (idioma es, con encabezados y SHALL/MUST en inglés), `rules` para los 4 artefactos y `operations.apply/archive.guidance`. Verificado con `openspec instructions`: se inyectan context, las 4 reglas y las dos guías.
- **Trampa de YAML encontrada:** un ítem con `": "` sin comillas se parsea como mapa, y OpenSpec **descarta sin fallar todas las reglas** de ese artefacto (avisa "must be an array of strings, ignoring"). Solución: entrecomillar. Para verificar tras cualquier edición: `openspec instructions <artefacto> --change <id>` no debe decir "ignoring".

### T6 — Retirar el `AGENTS.md` de solo lectura (H10) y dejar `run_review.sh` como opcional

**Contexto (2026-09-23):** Codex ya no está disponible (`which codex` → no encontrado). `run_review.sh` deja de ser
parte del ciclo y pasa a ser **opcional**: solo se usa si se vuelve a habilitar Codex. **La revisión por defecto es
`/opsx:verify` (gate G5) más `/code-review`** (regla 6 de *Manejo de ramas*). Ningún gate depende de Codex.

1. `git mv AGENTS.md docs/review/codex-review-prompt.md`.
2. `run_review.sh`, cambios mínimos (sin funciones nuevas):
   - cabecera: "OPCIONAL — requiere Codex CLI; la revisión por defecto es `/opsx:verify` + `/code-review`";
   - **guard al inicio**, antes del `mkdir` de `OUTDIR` (L28): si `command -v codex` falla, mensaje claro y `exit 1`, **sin crear** `revisiones/<stamp>/`;
   - L47: "los criterios de AGENTS.md" → la ruta nueva, explícita (Codex solo lee `AGENTS.md` de la raíz). El modo de solo lectura lo sigue garantizando `--sandbox read-only` (L55);
   - L39: corregir la ruta en el comentario;
   - L40-43: si no existe `etapa-NN.md`, el aviso dice explícitamente que desde la Etapa 13 el alcance vive en `openspec/changes/<id>/` y que el script **todavía no lo soporta** (ver diferido abajo). Así no cae en silencio a PLAN.md.
3. **Alinear el prompt movido** (`docs/review/codex-review-prompt.md`) con el flujo nuevo, sin reescribirlo, para que no contradiga CLAUDE.md si Codex vuelve:
   - L23 (fuentes de verdad `PLAN.md > SPECS.md > CLAUDE.md`) → remite a la cadena de precedencia de CLAUDE.md;
   - L33 (paso 1 de la metodología, "etapa en progreso/pendiente") → "la etapa activa según la tabla *Secuencia del ciclo* de PLAN §7 y, si el alcance es un change, sus `proposal`/`design`/`tasks`/`specs`";
   - L79 ("Datos Fase 1: Stooq → LEAN; Alpaca diferido") → refleja la Opción C de 9A;
   - L48 de `run_review.sh` ("PLAN.md/SPECS.md como fuentes de verdad") igual.
4. [docs/conceptos/code-review-codex-vs-anthropic.md](../../docs/conceptos/code-review-codex-vs-anthropic.md): actualizar la mención de `AGENTS.md` y marcar Codex como **opcional (no instalado desde 2026-09-23)**. La recomendación "al cerrar la etapa → `run_review.sh`" (L68) pasa a "`/opsx:verify` (G5) + `/code-review`; `run_review.sh` solo si Codex está habilitado".

**Por qué se sigue moviendo `AGENTS.md` aunque no haya Codex:** varias herramientas de agentes (Codex, Cursor, Copilot y otras) leen el `AGENTS.md` de la raíz como instrucciones generales. Dejarlo es un riesgo latente: el día que se use cualquiera de ellas, recibe "NUNCA modifiques archivos", que choca con `/opsx:apply`. Moverlo cuesta un `git mv` y deja el prompt junto a la herramienta opcional que lo usa.

**Por qué `CHANGE=<id>` y `DRY_RUN` se difieren** (se habían aprobado para T6 antes de saber que Codex no está):
- su único beneficiario es `run_review.sh`, que hoy no se puede ejecutar;
- construirlos ahora sería código sin uso ni forma real de probarlo;
- el aviso explícito del paso 2 evita el único riesgo que motivaba la ampliación: que la revisión caiga en silencio a PLAN.md;
- quedan registrados en *Diferidos* (roadmap §4) con su disparador: "si se reactiva Codex, implementar `CHANGE=<id>` + `DRY_RUN` antes de revisar una etapa ≥13".

**Criterio de aceptación:**
- `test ! -f AGENTS.md` y `test -f docs/review/codex-review-prompt.md`.
- `grep -n "AGENTS.md" scripts/*.sh` = 0 resultados.
- `bash -n scripts/run_review.sh` OK.
- Sin Codex instalado: `bash scripts/run_review.sh 5` imprime el mensaje de opcional, sale con exit 1 y **no crea** ningún directorio nuevo en `revisiones/` (se compara `ls revisiones` antes y después).
- En `docs/review/codex-review-prompt.md`: el párrafo de fuentes de verdad remite a la cadena de CLAUDE.md (`grep -c "precedencia de CLAUDE.md"` ≥ 1), ya no aparece "máxima precedencia" junto a `PLAN.md` (`grep -c "máxima precedencia"` = 0) y la fila de datos menciona la Opción C (`grep -c "Opción C"` ≥ 1).
- `docs/conceptos/code-review-codex-vs-anthropic.md` marca Codex como opcional y nombra la revisión por defecto.

**Notas:** las menciones dentro de `revisiones/2026*/…` son históricas y no se tocan. `scripts/codex_usage.sh` queda igual (también opcional; solo lee `~/.codex/sessions` si existe).

### T7 — CLAUDE.md: reglas de convivencia con OpenSpec (roadmap §0.4)

Añadir una sección "OpenSpec y PLAN.md" con:
- **Precedencia**, con la excepción de que ningún change anula las reglas duras ni el flujo.
- **Equivalencias:** etapa ⇔ change; "Done when" ⇔ escenarios + gates; archive ⇔ cierre.
- **Gates G0–G6** (resumen y link al roadmap §0.2).
- **Prohibiciones:** `--no-validate`; `--skip-specs` sin metadata; `sync` sin G3/G4/G5; archive con CRITICAL abiertos.
- **Reglas de archive (hallazgos de T5):**
  - `/opsx:archive` mueve la carpeta con `mv` y **no valida**, así que siempre va precedido de `openspec validate <id> --strict`.
  - Nunca se confirma un archive con tareas o artefactos incompletos.
  - Nunca se elige "Archive without syncing" si hay delta specs.
  - Tras archivar una capability nueva, se escribe su Purpose (≥50 caracteres), porque `validate --all --strict` falla con `TBD` o con texto corto.
- **`config.yaml`:** es consejo, no obliga. Toda regla que viva ahí debe estar también en CLAUDE.md. Tras editarlo, `openspec instructions <artefacto>` no debe avisar "ignoring".
- **Disposición de la documentación:** la tabla de esta spec (dónde va cada tipo de documento desde la Etapa 13).
- **Convención de commits:** `[Etapa N][<change-id>]` y `[config]`.
- **Modelo de ramas:** resumen de las 6 reglas de *Manejo de ramas*, en particular la corrida semanal desde `main` con reseed.
- Los comandos `openspec` y `/opsx:*` en la sección Comandos, más la revisión por defecto (`/opsx:verify` + `/code-review`) y `run_review.sh` marcado como opcional (requiere Codex), más la regla "los archivos de `.claude/commands/opsx/` los genera `openspec update`; no se editan a mano".
- **Secciones existentes que hay que tocar** (no basta con agregar una sección nueva):
  - *Documentos y precedencia* (L5-9): la lista y la regla de conflicto pasan a la cadena nueva;
  - *Flujo de trabajo*, pasos 3–5: el Estado se cambia solo en PLAN.md; desde la Etapa 13 el progreso granular va en `tasks.md`; el cierre incluye `archive` (cuando aplica), merge `--no-ff` a `develop` y promoción a `main`;
  - *Gotchas*: agregar los de OpenSpec (archive con `mv`, Purpose, YAML "ignoring").

**Criterio de aceptación:** la sección existe, las 4 reglas de §0.4 (con las prohibiciones ampliadas en T5), el modelo de ramas y la tabla de disposición aparecen; los pasos 3–5 del flujo describen el cierre nuevo; y la precedencia de CLAUDE.md (`PLAN.md > SPECS.md > este archivo`) se reemplaza por la cadena nueva **sin dejar dos versiones**: `grep -n "PLAN.md > SPECS.md" CLAUDE.md` = 0.

### T8 — Spike del ciclo OpenSpec con un change de prueba

Recorrer el ciclo completo con `chore-openspec-smoke`:
1. `/opsx:propose` → `openspec validate chore-openspec-smoke --strict` (G0)
2. `/opsx:apply` (sin código: G2/G3/G4 no aplican y se anota así en `tasks.md`)
3. `/opsx:verify` (G5) → `/opsx:sync`
4. `openspec validate chore-openspec-smoke --strict` → `/opsx:archive`
5. Escribir el Purpose de la capability creada (≥50 caracteres) → `openspec validate --all --strict`
6. Commit aparte: **retirar la capability a mano** (`git rm -r openspec/specs/<capability>/`) → `openspec validate --all --strict`. Se hace a mano, no con un change REMOVED, porque retirar la última requirement de una capability exige `retire_capabilities: true`: sería probar un camino que el ciclo no usa. El change archivado queda como historia.

El change agrega un requisito trivial, p. ej. "el repo declara su flujo en CLAUDE.md".

**Criterio de aceptación:**
- Los comandos de CLI (`openspec validate`) salen con exit 0; los `/opsx:*` terminan sin errores y `/opsx:verify` sin CRITICAL. Nunca se usa `--no-validate` ni `--skip-specs`.
- **Las reglas de `config.yaml` funcionan en el repo real:** el `proposal.md` generado trae Etapa y rama, "Diferencias esperadas en la watchlist" y "Rollback", y los artefactos están en español con SHALL/MUST en inglés.
- El requisito aparece **una sola vez** en `openspec/specs/` después de sync + archive.
- El change queda en `openspec/changes/archive/AAAA-MM-DD-chore-openspec-smoke/`.
- Con `Purpose` escrito, `validate --all --strict` → exit 0; tras el retiro manual, también exit 0.

**Notas:** si `archive` después de `sync` duplica deltas o exige `--skip-specs`, **se detiene la etapa** y se propone el ajuste de §0.4 y de CLAUDE.md antes de seguir (paso 6 del flujo).

**Riesgo reducido por la prueba de T5 (2026-09-23):** en un repo temporal, la CLI `openspec archive` sobre un requisito ya sincronizado respondió "Specs already in sync; no files changed". **No duplica** requisitos ADDED. T8 se mantiene porque lo que falta probar es el flujo **con los comandos `/opsx:*` dentro de este repo**:
- el sync lo hace el agente, no la CLI;
- `/opsx:archive` archiva con `mv`, así que el paso 4 queda: `openspec validate chore-openspec-smoke --strict` → `/opsx:archive`;
- la regla del Purpose, al retirar el requisito trivial.


### T9 — Baseline long para G4 (roadmap §0.5)

1. Apartar los resultados viejos: `mv storage/results storage/results.bak-20260923`. Contienen corridas dev de 2013 y un `latest copy.json`; no se borran.
2. Fijar la ventana del baseline: `set_end_date(2026, 9, 18)` en la rama prod de [main.py:40](../../trade-scanner/main.py#L40); hoy dice 2026-09-01 porque la edición se descartó. **Esta edición sí se commitea en esta rama**, como "ventana fija de G4": los G4 de las Etapas 13 y 5B deben correr sobre la misma ventana hasta que la Etapa 11 elimine las fechas hardcodeadas. Es la misma ventana de la corrida del 20-sep, así se puede comparar con H1/H2.
   **Commit de la ventana antes de correr** (`[Etapa 12] T9: ventana fija de G4 (2026-04-02 → 2026-09-18)`), para que el README del baseline cite el commit exacto con el que se generó.
   Después, `lean backtest "trade-scanner"`. `trade-scanner/config.json` ya tiene `"env": "prod"` versionado (`5d1c429`), así que no hay que tocar nada. Solo long.
3. Copiar `storage/results/swing_eod/2026*.json` a `baselines/scan-vYYYY.MM.DD-baseline/results/` (fecha real de ejecución de T9).
4. Generar `baselines/…/manifest.sha256`. Cubre:
   - todos los `data/equity/usa/daily/*.zip`;
   - `storage/config/*.json`;
   - `storage/universes/*.csv`.
5. Crear el tarball **fuera del repo** con esos mismos archivos (p. ej. `~/trade-scanner-snapshots/scan-vYYYY.MM.DD-baseline.tar.gz`).
6. Escribir `baselines/…/README.md` con: ruta del tarball, ventana, **commit de la ventana** (paso 2), `config_sha256`, el comando de verificación de tickers y el comando para restaurar.
7. Commit del baseline y tag **anotado** `scan/vYYYY.MM.DD-baseline` (`git tag -a`), pusheado.

**Criterio de aceptación:**
- `shasum -a 256 -c manifest.sha256` → OK sobre el working tree.
- **Ningún** JSON del baseline contiene tickers fuera de `swing_advances`. Verificación ad hoc con el comando que se registra en el README del baseline: cruzar `sections.long.candidates[].ticker` contra la columna `Symbol` del CSV. Es la misma técnica que produjo H1.
- Ningún JSON trae sección `short` con candidatos.
- El tag existe.

**Notas:**
- El script permanente de verificación (`check_watchlist_universe.py`) es alcance de la Etapa 14, no de esta.
- Para correr el harness dev (G3) hay que cambiar `env` a `dev` de forma temporal, **sin commitear**. El valor versionado es `prod`.

### T10 — Cierre: merge a `develop`, promoción a `main` y limpieza de ramas

**Orden:** T10 es la última tarea; **T11 se ejecuta antes**.

0. **Commit de cierre** en la rama:
   - PLAN.md: Etapa 12 y su fila de la tabla → `completada`, con evidencia;
   - spec: Estado `completada` y todos los Done when marcados;
   - bitácora: sección de cierre (qué quedó, qué sigue: Etapa 13);
   - push.

Después, aplicar la regla 2 de *Manejo de ramas*: `git merge --no-ff` de `feature/etapa-12-bootstrap-openspec` en `develop`
→ `main` fast-forward → tag `scan/v2026.09.DD-1` → push de `develop`, `main` y los tags. Después, borrar local y
remotamente las ramas ya integradas en `develop`:
- `feature/etapa-3-universe-contract`
- `feature/etapa-4-universe-creation`
- `feature/etapa-5B-warmup-validacion-precision`
- `feature/etapa-6-features-rules`
- `feature/etapa-12-bootstrap-openspec`

**Criterio de aceptación:**
- `git log --merges -1 --format=%s develop` empieza por `[Etapa 12] merge:`.
- `git rev-parse main` == `git rev-parse develop`.
- `git ls-remote --heads origin` solo lista `main` y `develop`.
- `git ls-remote --tags origin` incluye `scan/v2026.09.23-pre-ciclo`, el tag del baseline de T9 (`scan/vYYYY.MM.DD-baseline`, con la fecha real de T9) y el tag de promoción.
- Antes de borrar cada rama, `git branch --merged develop` la lista.

**Notas:** la rama de la Etapa 13 se crea al **empezar** la Etapa 13, no aquí. Borrado remoto: `git push origin --delete <rama>`. El remoto se borra con autorización del usuario (dada el 2026-09-23 al aprobar el modelo de ramas).

### T11 — Cerrar la pregunta del POC Finnhub

**Se ejecuta antes de T10.** Añadir en `docs/ROADMAP.md`, bajo `# Post V1` (hoy tiene `## Universo`, `## Estrategias`, `## Datos fundamentales` y `## Ejecución futura`; no existe una sección de "candidatos de Fase 2"), una entrada con las dos vías de integración (roadmap §6). Registrar la decisión "diferido a post-V1, sin archivar" para que la pregunta del commit `f8ded63` quede cerrada.

**Criterio de aceptación:** `grep -n "Finnhub" docs/ROADMAP.md` ≥ 1, con la decisión escrita.

---

## Scope

✅ **Entra:**
- Limpieza del working tree y desactivación del short por config.
- Resincronización de PLAN.md y ajustes de CLAUDE.md.
- Instalación, inicialización y spike de OpenSpec.
- Retiro de `AGENTS.md` y adaptación mínima de `run_review.sh` como herramienta opcional (Codex no disponible).
- Baseline de G4 (resultados, manifiesto y tarball).
- Fase A (transición de ramas) y el modelo de ramas en CLAUDE.md.
- Merge a `develop`, promoción a `main` y borrado de las ramas ya integradas.
- Una línea sobre Finnhub en `docs/ROADMAP.md`.

❌ **No entra, aunque parezca relacionado:**
- Ningún cambio en `trade-scanner/core/`, `strategies/` ni en la lógica de `main.py`; la única edición de `main.py` es la ventana fija de T9 (`set_end_date`).
- El preflight de cobertura y `session_date` (Etapa 13).
- La partición de universos / #12 (Etapa 14).
- Los `filters` del short, SSR y el vocabulario absoluto (Etapa 15).
- El script `check_watchlist_universe.py` (Etapa 14).
- Borrar `trade-scanner/backtests/2026-06-11_*` (diferido, roadmap §4).
- Actualizar `docs/DEVLOG.md` y el encabezado de `docs/ROADMAP.md` (se hace al cerrar la Etapa 11, roadmap §7.2).

## Done when

- [x] Fase A: `develop` y `main` avanzados por fast-forward y pusheados; tag `scan/v2026.09.23-pre-ciclo` en `origin`; rama de la etapa creada con la spec como primer commit *(verificado 2026-09-23: `main` = `develop` = `origin/*` = `f8ded63`; tag anotado → `f8ded63` en `origin`; `origin/feature/etapa-12-bootstrap-openspec` = `9e5125f`)*
- [x] T1: `run_tests.sh` verde; cifra registrada en PLAN; `docker run hello-world` OK *(2026-09-23: **304 passed**, 0 failed, 0 skipped, 13 warnings; hello-world OK. El registro en PLAN se hace en T3)*
- [x] T2: config sembrada == config versionada (hashes iguales); short `false` en `storage/`; sin commit *(2026-09-23: sha256 `1be6104e…` en ambos; universos del 09-19 conservados)*
- [x] T3: PLAN §7 con 0/5B/6B/9A/9B/10/11/12/13/14/15 en su estado real y la tabla de secuencia; CLAUDE.md, paso 1, actualizado; nota de supersesión en `etapa-11-…md` *(2026-09-23: 8 entradas nuevas + tabla de 7 filas; estados 0/6B `completada`, 5B/9A `pausada`; link roto de etapa-04 corregido)*
- [x] T4: `node` y `openspec` instalados; versiones anotadas y compatibles con `engines` *(2026-09-23: Node v26.9.0 ≥ 20.19.0; openspec 1.13.1, la última publicada)*
- [x] T5: `openspec/` inicializado solo para Claude Code; diff revisado; `openspec validate --all --strict` exit 0 *(2026-09-23: perfil custom core+verify, delivery commands, 7 comandos, 0 archivos versionados modificados; `config.yaml` verificado con `openspec instructions`)*
- [x] T6: sin `AGENTS.md` de solo lectura en la raíz; `run_review.sh` opcional, apunta a `docs/review/codex-review-prompt.md` y, sin Codex, sale con mensaje y exit 1 sin crear directorios; prompt y concepto alineados; `bash -n` OK *(2026-09-23: `test ! -f AGENTS.md` y `test -f docs/review/codex-review-prompt.md` OK; `grep AGENTS.md scripts/*.sh` = 0; `bash -n` OK; `run_review.sh 5` → mensaje de opcional, exit 1, `ls revisiones` = `20260619-205134` antes y después; prompt: "precedencia de CLAUDE.md" = 1, "máxima precedencia" = 0, "Opción C" = 1; cápsula marca Codex opcional y nombra `/opsx:verify` + `/code-review`)*
- [ ] T7: CLAUDE.md con la sección de OpenSpec y una única cadena de precedencia
- [ ] T8: `chore-openspec-smoke` recorrió propose→validate→apply→verify→sync→validate→archive sin errores ni flags prohibidos; reglas de `config.yaml` presentes en el proposal; requisito sin duplicar; Purpose escrito; capability retirada a mano y `validate --all --strict` exit 0
- [ ] T9: ventana commiteada antes del backtest; `baselines/scan-vYYYY.MM.DD-baseline/` versionado; `shasum -c` OK; tarball fuera del repo; 0 tickers fuera de `swing_advances`; tag anotado pusheado
- [ ] T10: commit de cierre (PLAN, spec y bitácora → `completada`); merge `--no-ff` `[Etapa 12] merge:` en `develop`; `main` == `develop`; tag de promoción pusheado; en `origin` solo quedan `main` y `develop`
- [ ] T11: decisión sobre Finnhub escrita en `docs/ROADMAP.md`
- [ ] Commits `[Etapa 12] …`, uno por unidad coherente (spec en A6, T1–T2, T3, T4–T5, T6, T7, T8 (+ retiro), T9 ventana + T9 baseline, T11, cierre T10); bitácora `etapa-12-decisiones-y-pendientes.md` con versiones, hashes y hallazgos

## Preguntas abiertas

- [ ] **Ventana del baseline:** se propone 2026-04-02 → 2026-09-18 (la misma que la corrida del 20-sep, para comparar con H1/H2). ¿Otra?
- [ ] **Ubicación del tarball:** se propone `~/trade-scanner-snapshots/`. ¿Otra (disco externo, Drive)?
- [x] ~~Si `archive` exige `--skip-specs` después de `sync`~~ — **resuelto en T5**: en el repo temporal, `archive` tras `sync` responde "Specs already in sync" y no duplica. T8 lo confirma con `/opsx:*`.
- [ ] **Telemetría de OpenSpec** (configuración global de la máquina): ¿se apaga con `openspec config set telemetry.enabled false`? No bloquea.
