# CLAUDE.md — Screener de Acciones sobre LEAN

Screener multi-estrategia sobre el motor LEAN (QuantConnect, Python 3.11). Carga universos desde CSV (≤200 tickers), mantiene indicadores en los timeframes que cada estrategia declara, evalúa reglas en horarios programados y emite watchlists con evidencia. **Solo escanea: prohibido colocar órdenes en V1.**

## Documentos y precedencia

1. `PLAN.md` — plan de trabajo por etapas con estado y checkboxes. **Fuente de verdad operativa.**
2. `SPECS.md` — contexto de producto, entidades, criterios de aceptación.
3. Ante conflicto: PLAN.md > SPECS.md > este archivo.

## Flujo de trabajo (spec-driven, obligatorio)

1. Lee `PLAN.md` y localiza la primera etapa con **Estado: pendiente** o **en progreso**.
2. Trabaja SOLO esa etapa. No mezcles alcance de etapas futuras.
3. Al empezar: cambia su Estado a `en progreso`. Al cumplir cada criterio: marca su checkbox `- [x]`.
4. Una etapa se cierra solo cuando TODOS sus "Done when" están verificados (no asumidos: ejecutados).
5. Cierre: Estado a `completada`, commit, resumen breve de lo hecho y qué sigue.
6. Si algo del plan es inviable o ambiguo: detente y pregunta ANTES de desviarte. Si cambia el diseño, propón la edición a PLAN.md y espera aprobación.

## Comandos

```bash
lean backtest "trade-scanner"            # backtest local (Docker)
lean live "trade-scanner"                # paper live local (requiere QC paid — ver ADR-002)
lean research "trade-scanner"            # Jupyter para exploración
bash scripts/run_tests.sh                # pytest DENTRO de la imagen LEAN (único modo válido)
bash scripts/seed_object_store.sh        # config/*.json (+ universes/*.csv) → storage/ (ObjectStore real)
bash scripts/seed_sample_data.sh         # SPY sample data libre → data/equity/ (avanza el reloj del backtest)
python scripts/explore_universe.py <csv> # perfilado del CSV de universo
```

Ejecuta todos los comandos `lean` desde la raíz del workspace (donde vive `lean.json`).
Activa el virtualenv antes de cualquier comando lean: `source .venv/bin/activate`.

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
- Commits: uno por unidad coherente, mensaje imperativo, referencia a la etapa (`[Etapa 5] ...`).

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

## Definición de "verificado"

Un checkbox de PLAN.md se marca solo si:
1. `bash scripts/run_tests.sh` pasa, y
2. cuando aplica, `lean backtest "trade-scanner"` corre sin errores y los logs/archivos demuestran el criterio (cita la evidencia en el resumen de cierre de etapa).
