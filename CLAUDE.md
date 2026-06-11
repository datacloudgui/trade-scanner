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
lean backtest "Screener"                 # backtest local (Docker)
lean live "Screener"                     # paper live local
lean research "Screener"                 # Jupyter para exploración
bash scripts/run_tests.sh                # pytest DENTRO de la imagen LEAN (único modo válido)
bash scripts/seed_object_store.sh        # universes/*.csv → data/object-store/
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
L1 lean.json · config.json · ObjectStore (CSVs)
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
- Timeframes NO fijos: cada estrategia los declara en `config.json`; consolidators y profundidad de warmup se derivan de ahí (fórmula en PLAN.md §4). Nunca un número de warmup hardcodeado.
- Umbrales, horarios, top_n, archivos de universo: en `config.json`, jamás en código.
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
- ObjectStore local vive en `data/object-store/` del workspace; en cloud es transparente. Lee siempre vía `self.object_store`, nunca con `open()` a rutas absolutas.
- Entorno: `self.live_mode` + parámetro de entorno deciden el sink de salida (solo dentro de `output.py`).
- Alpaca free: datos IEX (volumen subestimado → usa volumen relativo, no absoluto), 15 min de delay, 100 calls/min (afecta warmup, no el scan).
- Símbolos con warmup incompleto: excluir del scan y loguear, nunca evaluar reglas con indicadores fríos (`is_ready()`).
- Python del host: el CLI y scripts auxiliares corren sobre Python 3.11 del virtualenv (`.venv`). El engine y los tests corren siempre dentro de la imagen Docker (`quantconnect/lean`). `python3` del sistema puede ser una versión diferente — nunca lo uses directamente.

## Definición de "verificado"

Un checkbox de PLAN.md se marca solo si:
1. `bash scripts/run_tests.sh` pasa, y
2. cuando aplica, `lean backtest "Screener"` corre sin errores y los logs/archivos demuestran el criterio (cita la evidencia en el resumen de cierre de etapa).
