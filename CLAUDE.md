# CLAUDE.md — Screener de Acciones sobre LEAN

Screener multi-estrategia sobre el motor LEAN (QuantConnect, Python 3.11). Carga universos desde CSV (≤200 tickers), mantiene indicadores en los timeframes que cada estrategia declara, evalúa reglas en horarios programados y emite watchlists con evidencia. **Solo escanea: prohibido colocar órdenes en V1.**

## Documentos y precedencia

1. `PLAN.md` — índice operativo: etapas, **Estado**, "Done when" y link al change. **Fuente de verdad operativa.** El Estado de una etapa se cambia solo aquí.
2. **Change activo** — `openspec/changes/<id>/` (`proposal.md`, `design.md`, `tasks.md`, `specs/**`, `bitacora.md`). Desde la Etapa 13, cada etapa se especifica como un change.
3. `openspec/specs/` — comportamiento aceptado, por capability (bootstrap perezoso: cada change agrega la que toca).
4. `SPECS.md` — contexto de producto, entidades, criterios de aceptación (el "por qué").
5. `CLAUDE.md` — este archivo: flujo, reglas duras y convenciones.
6. Comandos `/opsx:*` generados en `.claude/commands/opsx/`.

**Cadena de precedencia** (ante conflicto gana el de la izquierda): `PLAN.md` > change activo > `openspec/specs` > `SPECS.md` > `CLAUDE.md` > `/opsx:*`.

**Excepción:** ningún change ni documento anula las *Reglas duras* ni el *Flujo de trabajo* de este archivo; solo un ADR aprobado más la edición explícita de CLAUDE.md. Si un `/opsx:*` sugiere algo contrario (archivar con tareas abiertas, `--no-validate`, `sync` antes de G4), gana CLAUDE.md.

## Flujo de trabajo (spec-driven, obligatorio)

1. Lee `PLAN.md` §7, tabla **Secuencia del ciclo**: la etapa activa es la **primera fila cuyo Estado no es `completada`** (`pausada` = abierta, con su trabajo restante asignado a una fila posterior). El orden del documento es histórico, no de ejecución.
2. Trabaja SOLO esa etapa. No mezcles alcance de etapas futuras.
3. Al empezar: crea la rama de la etapa desde `develop` (ver *Ramas y commits*) y cambia su Estado a `en progreso` **en PLAN.md** (el Estado vive solo ahí). Progreso:
   - etapa sin change (columna *Forma* de la tabla; en este ciclo, la 12 y la 9): al cumplir cada criterio, marca su checkbox `- [x]` en PLAN.md y, si existe, en `etapa-NN.md`;
   - etapa con change (13, 5B, 11, 14, 15): el progreso granular va en `tasks.md` (cada `[x]` exige G2); los "Done when" de PLAN.md se marcan con evidencia citada en el cierre (G6).
4. Una etapa se cierra solo cuando TODOS sus "Done when" están verificados (no asumidos: ejecutados) y, si es un change, pasó sus gates G0–G5.
5. Cierre, en este orden:
   1. Si es un change: `/opsx:sync` (tras G3/G4/G5) → "Done when" de PLAN con evidencia → `openspec validate <id> --strict` → `/opsx:archive` → verificar el Purpose de cada capability nueva (escribirlo solo si quedó `TBD`) → `openspec validate --all --strict` exit 0.
   2. Estado a `completada` en PLAN.md → commit de cierre en la rama → push.
   3. `git switch develop && git merge --no-ff <rama> -m "[Etapa NN] merge: <resumen>"`.
   4. Promoción: `git switch main && git merge --ff-only develop` + `git tag -a scan/vYYYY.MM.DD-N`.
   5. `git push origin develop main <tag>`; borrar la rama, local y remota.
   6. Resumen breve de lo hecho y qué sigue.
6. Si algo del plan es inviable o ambiguo: detente y pregunta ANTES de desviarte. Si cambia el diseño, propón la edición a PLAN.md (o al change) y espera aprobación.

## OpenSpec y PLAN.md (desde el ciclo 2026-09)

OpenSpec va **anidado** en las etapas de PLAN.md: PLAN es el índice; el change, el detalle. Motivos y detalle: [roadmap §0](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md) y [etapa-12.md](.claude/fase-1-desarrollo-local/etapa-12.md).

### Reglas de convivencia (roadmap §0.4)

1. **Precedencia:** la cadena de *Documentos y precedencia*, con su excepción. No hay otra.
2. **Equivalencias:**
   - etapa `en progreso` ⇔ change activo; "Done when" ⇔ escenarios + gates; `archive` ⇔ cierre de etapa;
   - `etapa-NN.md` ⇔ `proposal.md` + `tasks.md`;
   - `etapa-NN-decisiones-y-pendientes.md` ⇔ `design.md` (decisiones D-n, preguntas abiertas) + `bitacora.md` dentro del change (evidencia y checkpoints);
   - las tareas de proceso (resincronizar PLAN, merges, docs) quedan en PLAN.md, sin change.
3. **Prohibido:**
   - `--no-validate`;
   - `--skip-specs` sin `skip_specs: true` en la metadata del change;
   - `/opsx:sync` sin G3, G4 (si aplica) y G5;
   - archivar con CRITICAL abiertos de `/opsx:verify`;
   - `/opsx:archive` sin `openspec validate <id> --strict` previo en exit 0;
   - confirmar un archive con tareas o artefactos incompletos;
   - elegir "Archive without syncing" si el change tiene delta specs.
4. **Commits:** `[Etapa N][<change-id>] …` en una etapa con change; `[Etapa N] …` en una sin change; `[config] …` en la vía ligera.

### Gates (resumen; definición completa en [roadmap §0.2](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md))

| Gate | Cuándo | Evidencia | Bloquea |
|---|---|---|---|
| **G0** | Cierre de `/opsx:propose` | `openspec validate <id> --strict` exit 0 | `apply` |
| **G1** | Tras G0 | Aprobación humana de `proposal.md` (paso 6 del flujo) | `apply` |
| **G2** | Tras cada tarea | `bash scripts/run_tests.sh` verde | El `[x]` en `tasks.md` |
| **G3** | Antes de `sync` | `lean backtest "trade-scanner" --parameter env dev` (**dev**; el `config.json` versionado es `prod`), exit 0 | `sync` |
| **G4** | Antes de `sync`, si el change toca el scan o la salida | Backtest **prod** con ventana fija y `storage/results/` vaciado; diff contra `baselines/<tag>/` == diferencias declaradas en `proposal.md`. dev no sirve (su override de universo oculta #12) | `sync` |
| **G-data** | Antes de G4 (desde la Etapa 13) | Preflight de cobertura de datos exit 0 | G4 |
| **G5** | Antes de `sync` | `/opsx:verify` sin CRITICAL; cada WARNING corregido o justificado en `design.md` | `sync` y checkboxes de PLAN |
| **G6** | Cierre | Paso 5 del flujo | — |

G2 y G3 aplican **aunque el change no toque código** (requisitos documentales o de proceso): ningún `/opsx:*` ni la CLI de OpenSpec ejecuta tests ni backtests, así que se corren a mano.

### Artefactos de un change

Espejo obligatorio de las reglas de `openspec/config.yaml`:
- Idioma: español; encabezados estructurales de OpenSpec y SHALL/MUST en inglés.
- `proposal.md`:
  - Etapa de PLAN.md y rama `feature/etapa-NN-<change-id>` (o la rama de la etapa si el change es una tarea de una etapa sin change);
  - sección "Diferencias esperadas en la watchlist" (insumo de G4; "ninguna" si no toca el scan);
  - sección "Rollback": R-cfg (`enabled: false` + reseed) o R-git (revert del merge o checkout del tag), y por qué basta ([roadmap §0.3](.claude/fase-1-desarrollo-local/roadmap-definitivo-2026-09.md)).
- `design.md`: decisiones D-1, D-2…; las que cruzan changes van a un ADR en `.claude/decisions/` y se enlazan.
- `specs/**`:
  - cada Scenario es verificable por un test en Docker, por evidencia de backtest citada o por evidencia de comando citada en `bitacora.md` (requisitos documentales o de proceso); en este último caso, el WARNING de `/opsx:verify` se justifica en `design.md`;
  - capability nueva: el delta abre con `## Purpose` (≥50 caracteres); sync y archive lo copian a la spec principal.
- `tasks.md`: cada tarea con criterio de aceptación ejecutable; tareas explícitas de gate (G2, G3 y G4 si toca el scan) y una final de evidencia en `bitacora.md`.
- Durante `/opsx:apply`: ningún `[x]` sin G2; no se toca el Estado en PLAN.md; la evidencia (comandos, hashes, conteos) va en `bitacora.md`.

### Reglas de archive (hallazgos de Etapa 12 T5)

- `/opsx:archive` mueve la carpeta con `mv` y **no valida** (la CLI `openspec archive` sí). Por eso siempre va precedido de `openspec validate <id> --strict`.
- Con tareas o artefactos incompletos, `/opsx:archive` solo pide confirmación: **nunca se confirma**; se detiene y se reporta.
- Nunca se elige "Archive without syncing" si hay delta specs.
- Si las specs ya están sincronizadas, `/opsx:archive` ofrece *Archive now* / *Sync anyway* / *Cancel*: se elige **Archive now**; *Sync anyway* solo si la spec principal difiere del delta.
- Tras archivar una capability nueva se **verifica** su `Purpose` (sync/archive lo copian del delta); solo si quedó `TBD` se escribe uno de ≥50 caracteres: `openspec validate --all --strict` falla con `TBD` o con texto corto.

### `openspec/config.yaml`

- Inyecta contexto y reglas en los artefactos, pero **es consejo, no obliga**. Toda regla que viva ahí debe estar también en CLAUDE.md (hoy: *Artefactos de un change* y *Reglas de archive*).
- Tras editarlo: `openspec instructions <artefacto> --change <id>` no debe avisar "ignoring".
- Los archivos de `.claude/commands/opsx/` los genera `openspec update`: **no se editan a mano**.

### Disposición de la documentación

Casi nada se mueve: lo existente sigue activo en su sitio o queda congelado como historia.

| Ubicación | Qué contiene | Desde la Etapa 13 |
|---|---|---|
| `PLAN.md` | Índice operativo + §1–§6 | Se queda. Los contratos de §5 migran a `openspec/specs/<capability>` la primera vez que un change los toca; §5 queda con un link (nunca dos fuentes) |
| `SPECS.md` | Producto: por qué, entidades, criterios | Se queda, sin migrarse entero: el "qué hace" pasa a `openspec/specs` capability por capability |
| `CLAUDE.md`, `README.md` | Convenciones; runbook | Se quedan |
| `openspec/changes/<id>/` | `proposal`, `design`, `tasks`, `specs/**`, `bitacora.md` | Al archivar, todo junto a `openspec/changes/archive/AAAA-MM-DD-<id>/` |
| `.claude/decisions/` | ADRs | Se queda: decisiones que cruzan changes (ADR-006 en la E14, enmienda a ADR-005 en la E15) |
| `.claude/fase-1-desarrollo-local/` | Specs y bitácoras E0–E12, roadmaps | Historia; **se congela al cerrar la Etapa 12**: no se crean más `etapa-NN.md` |
| `docs/conceptos/`, `docs/research/` | Explicaciones y research | Se quedan |
| `docs/ROADMAP.md`, `docs/DEVLOG.md` | Fases y diario | Se quedan; una entrada por etapa con link al change archivado (se ponen al día al cerrar la Etapa 11) |
| `docs/review/codex-review-prompt.md`, `revisiones/` | Prompt e informes de Codex | Opcionales; `revisiones/` solo crece si se reactiva Codex |
| `scripts/poc/` | POC Finnhub | Diferido |

### Ramas y commits

| Rama | Rol | Cómo avanza |
|---|---|---|
| `main` | **Producción:** la versión con la que se corre la watchlist semanal real y se envía el correo | Solo fast-forward desde `develop` + tag anotado `scan/vYYYY.MM.DD-N`. Nunca recibe commits propios |
| `develop` | **Integración:** solo etapas cerradas | Un merge `--no-ff` por etapa; `git revert -m 1 <merge>` la revierte entera (R-git) |
| `feature/etapa-NN-<change-id>` | Una rama por etapa, creada desde `develop` | Commits de la etapa; push tras cada commit |
| `config/<slug>` | Vía ligera `[config]` | Igual que una rama de etapa |
| `hotfix/<slug>` | Rollback urgente de producción, solo si `develop` tiene trabajo sin promover | Sale de `main`; `main` avanza por fast-forward hasta el hotfix; después `main` se mergea en `develop` |

1. **Una etapa, una rama.** Ninguna rama acumula varias etapas.
2. **Cierre** = paso 5 del flujo. Toda etapa pasó sus gates antes de cerrarse, así que se promueve al cerrar: después de cada cierre, `main` == `develop`.
3. **La corrida semanal real sale siempre de `main`, con reseed:** `git switch main && bash scripts/seed_object_store.sh` antes de `lean backtest`. `storage/` y `data/` están gitignoreados: `git switch` no los cambia y, sin reseed, la corrida usa la config de la última rama sembrada.
   - Mientras la Etapa 11 no cierre, la edición semanal de `end_date` en `main.py` no se commitea: se corre y después `git restore trade-scanner/main.py`, antes de cambiar de rama.
   - Las corridas de revisión de una etapa en curso se hacen en su rama y **no se publican** (no se ejecuta `notify_email.py`). Solo lo que sale de `main` llega al correo.
   - Un G3 (dev) sobreescribe `storage/results/` (p. ej. `latest.json`): tras un G3 **no se ejecuta `notify_email.py` sin re-correr prod**; la corrida semanal desde `main` lo regenera.
4. **Push:** rama de etapa tras cada commit; `develop`, `main` y tags en cada cierre; tags siempre anotados (`-a`).
5. **No se reescribe historia publicada:** nada de `rebase` ni `push --force` sobre `develop`, `main` o una rama ya pusheada.
6. **Merges locales** (no hay `gh`). La revisión antes del merge es la de por defecto: `/opsx:verify` + `/code-review`.

**Vía ligera `[config]`** (sin OpenSpec): ajustes que solo tocan `config/strategies.json` o `config/notifications.json` sin cambiar ningún requisito (umbrales, `top_n`, `filters` ya soportados, `enabled`). Flujo: rama `config/<slug>` → G3/G4 → commit `[config] …` → cierre como una etapa. Un cambio de config que modifica semántica (p. ej. el vocabulario de `filters`) no es vía ligera: es un change.

## Comandos

```bash
lean backtest "trade-scanner"            # backtest local (Docker)
lean live "trade-scanner"                # paper live local (requiere QC paid — ver ADR-002)
lean research "trade-scanner"            # Jupyter para exploración
bash scripts/run_tests.sh                # pytest DENTRO de la imagen LEAN (único modo válido)
bash scripts/seed_object_store.sh        # config/*.json (+ universes/*.csv) → storage/ (ObjectStore real)
bash scripts/seed_sample_data.sh         # SPY sample data libre → data/equity/ (avanza el reloj del backtest)
python scripts/explore_universe.py <csv> # perfilado del CSV de universo

# OpenSpec (CLI 1.13.1; Node ≥ 20.19)
openspec validate <id> --strict          # G0, y siempre antes de /opsx:archive
openspec validate --all --strict         # tras archivar (sin Purpose `TBD`)
openspec instructions <artefacto> --change <id>   # tras editar config.yaml: no debe decir "ignoring"
openspec update                          # regenera .claude/commands/opsx/ (no se editan a mano)

bash scripts/run_review.sh <N>           # OPCIONAL: requiere Codex CLI (no instalado desde 2026-09-23)
```

Ejecuta todos los comandos `lean` desde la raíz del workspace (donde vive `lean.json`).
Activa el virtualenv antes de cualquier comando lean: `source .venv/bin/activate`.

Comandos de sesión de OpenSpec: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:verify` (G5), `/opsx:sync`, `/opsx:archive`, `/opsx:update`. Úsalos siempre dentro de las reglas de *OpenSpec y PLAN.md*.

**Revisión por defecto:** `/opsx:verify` (G5) + `/code-review`. `run_review.sh` (Codex, prompt en `docs/review/codex-review-prompt.md`) es opcional: sin Codex sale con exit 1 sin crear nada, y todavía no soporta changes de OpenSpec (etapas ≥13).

## Arquitectura (resumen; detalle en PLAN.md §2–§4)

```
L6 lean backtest | lean live (Docker)   boundary de runtime/deploy; el código no la toca
L5 main.py        orquestación: config → universos → SymbolData+warmup → schedule → output
L4 strategies/ + core/{pipeline,rules}.py   estrategias = composición declarativa de Rules
L3 core/features.py    cómputos reutilizables sobre SymbolData
L2 core/{symbol_data,timeframes}.py   consolidators + indicadores + working bar + warmup
L1 lean.json · ObjectStore (config/strategies.json + universos CSV)
```

Restricciones entre capas — verifícalas en cada cambio:
- L3/L4 leen estado de `SymbolData`; NUNCA piden datos ni calculan indicadores.
- Solo `main.py` usa `self.schedule`, `self.history`, `self.add_equity`, `self.object_store`, `self.notify`.
- Un símbolo = un `SymbolData` compartido (unión de timeframes de todas las estrategias que lo usan).
- El switch local/cloud vive SOLO en `core/output.py`.

## Reglas duras (violarlas = PR rechazado)

- El código solo habla con la API de `QCAlgorithm`. Sin SDKs de Alpaca/brokers/datos.
- Portable local ↔ QC cloud sin cambios de código. Fuente de datos = solo `lean.json`.
- Barras y SMAs de W/M/etc. con consolidators e indicadores de LEAN (`Calendar.WEEKLY`, `Calendar.MONTHLY`, `register_indicator`). PROHIBIDO resampling manual con pandas dentro del algoritmo.
- Timeframes NO fijos: cada estrategia los declara en `config/strategies.json` (ObjectStore); consolidators y profundidad de warmup se derivan de ahí (fórmula en PLAN.md §4). Nunca un número de warmup hardcodeado.
- Umbrales, horarios, top_n, archivos de universo: en `config/strategies.json` (ObjectStore), jamás en código ni en el `config.json` del proyecto (solo archivo de LEAN). Ver PLAN.md §4.
- Universo: tope duro 200 tickers post-filtro.
- Cero órdenes: nada de `self.market_order` ni similares.
- Credenciales (QC, Alpaca) fuera del repo siempre.

## Convenciones de código

- API Python moderna de LEAN en snake_case (`self.schedule.on`, `self.add_equity`, `register_indicator`).
- Patrón `SymbolData` por símbolo; features como propiedades/métodos de lectura.
- Type hints en todo `core/` y `strategies/`. Docstrings cortos: qué y por qué, no cómo.
- Tests: pytest con `TradeBar`s sintéticos construidos a mano (valores de SMA verificables manualmente). Corren dentro de la imagen LEAN vía `scripts/run_tests.sh` — nunca asumas que pytest local fuera de Docker tiene `AlgorithmImports`.
- Commits: uno por unidad coherente, mensaje imperativo, con el prefijo de la regla 4 de *Reglas de convivencia* (`[Etapa N] …`, `[Etapa N][<change-id>] …` o `[config] …`).

## Gotchas de LEAN (memorízalos)

- `Calendar.WEEKLY` agrupa lunes→domingo (cierre efectivo viernes); `Calendar.MONTHLY` mes calendario. Las SMAs deben cuadrar con la plataforma de referencia del trader (validación en Etapa 5).
- Warmup: pide historia en batch (`self.history(symbols, n, Resolution.DAILY)`) y empuja cada barra a los consolidators del símbolo; los indicadores registrados se actualizan solos.
- Barra parcial del día = `working_bar` del consolidator diario (requiere suscripción `Resolution.MINUTE`). Los indicadores W/M NO incluyen la barra en curso: eso es correcto y deseado (SMAs estables intradía).
- ObjectStore local vive en `storage/` del workspace (el CLI lo monta en `/Storage` dentro de Docker); **no** es `data/object-store/`. La key `config/strategies.json` se lee desde `storage/config/strategies.json`. En cloud es transparente. Lee siempre vía `self.object_store`, nunca con `open()` a rutas absolutas.
- Entorno: `self.live_mode` + parámetro de entorno deciden el sink de salida (solo dentro de `output.py`).
- Alpaca free: datos IEX (volumen subestimado → usa volumen relativo, no absoluto), 15 min de delay, 100 calls/min (afecta warmup, no el scan).
- Símbolos con warmup incompleto: excluir del scan y loguear, nunca evaluar reglas con indicadores fríos (`is_ready()`).
- Python del host: el CLI y scripts auxiliares corren sobre Python 3.11 del virtualenv (`.venv`). El engine y los tests corren siempre dentro de la imagen Docker (`quantconnect/lean`). `python3` del sistema puede ser una versión diferente — nunca lo uses directamente.

## Gotchas del workspace (descubiertos en Etapa 1)

- **`lean init` requiere QC pago.** Pide seleccionar una organización vía API. En su lugar: descargar `Launcher/config.json` del repo público de LEAN en GitHub, aplicar `clean_lean_config()`, y añadir `"organization-id"` en `lean.json`.
- **`organization-id` obligatorio en lean.json.** El CLI v1.0.x lanza error si el campo es nulo. Para backtest local usar placeholder `"00000000000000000000000000000000"` — nunca se valida contra QC. Reemplazar con org-id real antes de `lean live`.
- **El CLI reformatea lean.json a JSON estándar.** Elimina comentarios `//` en la primera escritura. Comportamiento esperado; el engine lo acepta igual.
- **`lean project-create` requiere `--language python` explícito** si `default-language` no está seteado en la config del CLI.
- **`${VAR}` NO se expande en lean.json.** El CLI no hace sustitución de variables de entorno. Credenciales en campos vacíos en lean.json (commiteado) + valores reales solo en `.env` (gitignoreado).
- **`lean live` con Alpaca requiere QC paid (plan Researcher).** AlpacaBrokerage tiene `installs: true` → el CLI intenta descargar un módulo NuGet via API de QC. Sin licencia falla. Ver [ADR-002](.claude/decisions/ADR-002-qc-module-auth-constraint.md) y el flag en Etapa 9 de PLAN.md.
- **Gitignore para artefactos del CLI:** añadir `**/backtests/`, `**/.idea/`, `**/.vscode/`, `**/research.ipynb` — el CLI los genera automáticamente y no deben commitearse.

### Descubiertos en Etapa 2

- **El ObjectStore local del CLI es `storage/`, NO `data/object-store/`.** El CLI monta `<workspace>/storage/` en `/Storage` (`lean_runner.py`: `storage_dir = cli_root/"storage"`). Sembrar en `data/object-store/` da `Object with path '...' was not found`. `storage/` está gitignoreado (copia regenerable; la fuente versionada vive en `config/`).
- **Tests en Docker = receta pythonnet.** La imagen embebe Python en .NET y no trae pytest ni pythonnet standalone. `run_tests.sh`: `--entrypoint bash`, `pip install clr_loader pytest`, `PYTHONNET_RUNTIME=coreclr` + `PYTHONNET_CORECLR_RUNTIME_CONFIG=<Launcher.runtimeconfig.json>`, y `cd /Lean/Launcher/bin/Debug` (donde viven `AlgorithmImports.py` y los DLLs).
- **El reloj del backtest no avanza sin datos.** Sin sample data el engine procesa "1 data point" y los `ScheduledEvents` no disparan. SPY como ancla de calendario (`Resolution.MINUTE`) + `seed_sample_data.sh` resuelven esto.

### Descubiertos en Etapa 4

- **`self.get_parameter()` lee de `trade-scanner/config.json`, NO de `lean.json`.** El campo `"parameters"` en `lean.json` (raíz del workspace) es configuración del engine LEAN y es ignorado por `get_parameter()`. Los parámetros escalares del algoritmo (ej. `"env": "dev"`) deben estar en `trade-scanner/config.json["parameters"]`. Config de negocio anidada sigue yendo a ObjectStore.
- **`core/universe.py` no debe importar `AlgorithmImports`.** Mantenerlo libre de imports LEAN permite testearlo con `MockObjectStore` simple (sin CLR) y usarlo desde scripts del host. `main.py` pasa `self.object_store` en runtime; los tests pasan su propio mock.

### Descubiertos en Etapa 5A

- **La emisión del consolidator es perezosa SIEMPRE.** Incluso una barra diaria que llena exactamente el periodo `timedelta(days=1)` queda en `working_data` hasta que llega una barra posterior o un `scan(time)`; el lag se encadena a W/M. Consecuencia: el warmup debe cerrar con `SymbolData.scan(end_time de la última barra)` y los tests flushean con trailing bar o `scan()`.
- **`scan()` también emite en consolidators de calendario** (`Calendar.WEEKLY`/`MONTHLY`): permite refrescar SMAs W/M el mismo día del cierre de periodo en runtime, sin esperar la primera barra diaria del periodo siguiente.
- **Equivalencia exacta warmup/runtime verificada (T3.9).** El consolidator diario redondea `time` a 00:00: la barra construida desde minutos es idéntica a la diaria directa, y la cadena W/M hereda la identidad. No hay asimetría que compensar en `main.py`.
- **`Symbol.create(..., EQUITY, ...)` fuera del engine lanza NullReference** (exige map file provider). En tests: `Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")`. Para scripts directos en la imagen (no `python -m pytest`), añadir `/Lean/Launcher/bin/Debug` al `PYTHONPATH`.

### Descubiertos en Etapa 12 (OpenSpec 1.13.1)

- **`/opsx:archive` archiva con `mv` y no valida.** Solo la CLI `openspec archive` valida. Por eso existe la regla de `validate --strict` antes (ver *Reglas de archive*).
- **`Purpose: TBD` aparece solo si el delta de una capability nueva no trae `## Purpose`** (#1413, OpenSpec 1.13.1): con él, sync y archive lo copian literal. Si queda `TBD`, `openspec validate --all --strict` sale con exit 1 hasta que se escribe un Purpose de ≥50 caracteres.
- **Trampa de YAML en `openspec/config.yaml`:** un ítem con `": "` sin comillas se parsea como mapa y OpenSpec **descarta sin fallar todas las reglas** de ese artefacto (solo avisa "must be an array of strings, ignoring"). Entrecomillar el ítem.
- **El perfil `core` no incluye `verify`** (sin él no hay G5). La máquina usa el perfil global `custom` = core + verify con `delivery: commands` (`~/.config/openspec/config.json`). En otra máquina: `openspec config profile` + `openspec update`.
- **`/opsx:verify` no corre tests:** G2 sigue siendo `bash scripts/run_tests.sh`.
- **`lean backtest` reescribe `lean.json`** (`file-database-last-update`) en cada corrida: `git restore lean.json` antes de commitear.

## Definición de "verificado"

Un checkbox de PLAN.md se marca solo si:
1. `bash scripts/run_tests.sh` pasa, y
2. cuando aplica, `lean backtest "trade-scanner"` corre sin errores y los logs/archivos demuestran el criterio (cita la evidencia en el resumen de cierre de etapa).

En una etapa con change rige lo mismo para cada `[x]` de `tasks.md` (G2), y la evidencia se cita en `bitacora.md`.
