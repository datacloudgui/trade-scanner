# Etapa 2 — Bitácora de decisiones reversibles y pendientes

> **Propósito:** dejar a mano las decisiones tácticas (reversibles) y los pendientes
> de la Etapa 2, para consultarlas rápido si un backtest falla o si hay que cambiar algo.
> No son ADRs (eso vive en `.claude/decisions/`); son notas operativas acotadas a esta etapa.
>
> Spec de la etapa: [etapa-02.md](etapa-02.md). Última actualización: 2026-06-11.

---

## Decisiones reversibles tomadas

### D1 — Ventana del backtest: 2013-10-07 a 2013-10-11 (default de `main.py`)
- **Qué:** se mantiene el rango `set_start_date(2013,10,7)` / `set_end_date(2013,10,11)` del scaffold.
- **Por qué:** la sample data libre de SPY en el repo público de LEAN cubre minute en
  2013-10-04 y 2013-10-07..11. Ese rango cae dentro de la data disponible → el reloj avanza.
- **Resuelve** la pregunta abierta "Ventana del backtest" del spec (T2).
- **Cómo revertir/cambiar:** editar `set_start_date/end_date` en
  [trade-scanner/main.py](../../trade-scanner/main.py). Si se amplía el rango, sembrar las
  fechas nuevas en [scripts/seed_sample_data.sh](../../scripts/seed_sample_data.sh)
  (añadirlas al loop de `for d in ...`). Fechas no disponibles en el repo → vuelven al
  síntoma "1 data point" + requests fallidos.

### D2 — Sembrar también hour/daily/map_files/factor_files, no solo minute
- **Qué:** el seed baja `minute/spy/*`, `hour/spy.zip`, `daily/spy.zip`,
  `map_files/spy.csv` y `factor_files/spy.csv`.
- **Por qué:** LEAN necesita map/factor files para resolver el símbolo de equity US;
  hour/daily quedan listos para las consolidaciones W/M de etapas futuras (Etapa 5).
- **Cómo revertir:** quitar las líneas `fetch "hour/..."` etc. del script. Quitar map/factor
  rompe la resolución del símbolo (no recomendado).

### D6 — Receta para correr pytest en la imagen LEAN (puente pythonnet)
- **Qué:** la imagen `quantconnect/lean` embebe Python dentro de .NET; no trae pytest ni
  pythonnet importable standalone. `run_tests.sh` arranca el puente así:
  1. `--entrypoint bash` (el ENTRYPOINT por defecto arranca el engine).
  2. `pip install clr_loader pytest` (no vienen en la imagen).
  3. `PYTHONNET_RUNTIME=coreclr` + `PYTHONNET_CORECLR_RUNTIME_CONFIG=<...Launcher.runtimeconfig.json>`
     (sin esto, pythonnet intenta "mono" y falla).
  4. `cd /Lean/Launcher/bin/Debug` (ahí viven `AlgorithmImports.py`, `clr.py` y los DLLs).
  5. `PYTHONPATH=/Project` para que los tests importen `core`/`strategies`.
- **Por qué importa:** este era el verdadero *unknown* de la etapa. Verificado:
  `1 passed` construyendo un `TradeBar`.
- **Caveat:** el `pip install` requiere red en cada corrida (~pocos seg). Si se necesita
  offline o más rápido en CI, cachear con una imagen derivada (`FROM quantconnect/lean` +
  `pip install`). Ver P8.
- **Dónde:** [scripts/run_tests.sh](../../scripts/run_tests.sh).

### D5 — `after_close` → `after_market_close(spy, 1)` (offset de 1 min)
- **Qué:** el schedule `after_close` se mapea a `after_market_close(self.spy, 1)`, no a `0`.
- **Por qué:** +1 min asegura que la barra de cierre ya consolidó antes de scanear (evita leer
  un working_bar a medio formar en etapas con SymbolData). Resuelve la pregunta abierta
  "`after_close` → minutos" del spec. Verificado: `swing_eod` dispara 16:01 (cierre 16:00).
- **Cómo cambiar:** ajustar el offset en `_time_rule_for` de
  [trade-scanner/main.py](../../trade-scanner/main.py).

### D4 — ⚠️ El ObjectStore local es `storage/`, NO `data/object-store/` (corrige doc)
- **Qué:** el CLI de LEAN monta `<workspace>/storage/` en `/Storage` dentro de Docker
  (verificado en `.venv/.../lean/components/docker/lean_runner.py:410`,
  `storage_dir = cli_root / "storage"`). `self.object_store.read("config/strategies.json")`
  lee desde `storage/config/strategies.json`. Sembrar en `data/object-store/` dio
  `Object with path 'config/strategies.json' was not found`.
- **Por qué importa:** CLAUDE.md ("ObjectStore local vive en `data/object-store/`"),
  PLAN.md §3 y el spec T3 dicen `data/object-store/` — es una suposición incorrecta de
  Etapa 1. La key documentada (`config/strategies.json`) sí es correcta; solo el directorio
  destino del seed cambió a `storage/`.
- **Decisión de key (P5 resuelta):** key = `config/strategies.json` (con prefijo `config/`),
  archivo en `storage/config/strategies.json`.
- **Cómo revertir/cambiar:** la key se elige en
  [trade-scanner/main.py](../../trade-scanner/main.py) y debe casar con la ruta destino de
  [scripts/seed_object_store.sh](../../scripts/seed_object_store.sh). Si se cambia la key,
  cambiar ambos.
- **Pendiente de doc:** ver P6 (actualizar CLAUDE.md / PLAN.md §3 / spec T3 / gotcha Etapa 1).

### D3 — Imports en `main.py` para validar T1, cuerpo aún es scaffold
- **Qué:** `main.py` tiene `import core` / `import strategies` (T1) pero conserva el cuerpo
  por defecto con `set_holdings("SPY", 1)` (una orden).
- **Por qué:** validar que los paquetes importan sin reescribir el algoritmo; **T4** reemplaza
  el cuerpo por el esqueleto real (ancla SPY + ScheduledEvents que solo loguean).
- **Cómo revertir:** N/A — se sobrescribe en T4. ⚠️ Mientras tanto viola la regla dura
  "cero órdenes" de CLAUDE.md; es temporal y conocido.

---

## Pendientes

| # | Pendiente | Estado | Disparador / cuándo actuar |
|---|---|---|---|
| P1 | Request fallido `/alternative/interest-rate/usa/interest-rate.csv` (tasa libre de riesgo de la Fed, dataset *alternative*) | Aceptado, sin acción | Solo actuar si una métrica que dependa del risk-free rate da raro. LEAN usa un default; no es precio de SPY. Para silenciarlo: sembrar ese CSV desde el repo de LEAN. |
| P2 | `data/equity/` debe ir a `.gitignore` (data descargable, no se versiona) | ✅ Resuelto (T6) | ya cubierto por `data/*` en `.gitignore` (`git check-ignore data/equity` ✔) |
| P3 | Cuerpo de `main.py` sigue siendo scaffold con orden `set_holdings` | ✅ Resuelto (T4) | scaffold/orden eliminado; ancla SPY + ScheduledEvent que solo loguea |
| P4 | Commit `[Etapa 2] ...` (paquetes, main.py, scripts, config, test; excluye sample data) | ✅ Resuelto (T6) | commit con artefactos de Etapa 2; docs CLAUDE/PLAN/SPECS quedan sin stagear (van con P6) |
| P5 | Definir la *key* exacta del ObjectStore para `strategies.json` | ✅ Resuelto (D4) | key = `config/strategies.json` |
| P6 | Corregir la doc: el ObjectStore local es `storage/`, no `data/object-store/` (CLAUDE.md, PLAN.md §3, spec T3, gotcha Etapa 1) | ✅ Resuelto | CLAUDE.md (gotcha + comandos + nuevo gotcha Etapa 2), PLAN.md (§3 tree, Et.2/Et.4, estado completada), README.md, nota D4 en spec T3. `.gitignore`: exención `!data/object-store/` se deja (un-ignora dir vacío sin uso; inofensiva) |
| P7 | `storage/` (copia sembrada, regenerable) debe ir a `.gitignore`; revisar si `data/object-store/` sigue mencionado | ✅ Resuelto (T6) | `storage/` añadido a `.gitignore`. La excepción `!data/object-store/` se dejó intacta (la revisa P6 al corregir doc) |
| P8 | `run_tests.sh` hace `pip install clr_loader pytest` en cada corrida (requiere red). Opcional: imagen derivada con deps precacheadas | Aceptado, opcional | Solo si molesta la latencia o se va a CI offline |

---

## Síntomas → causa probable (referencia rápida de depuración)

- **`Processing total of 1 data points` + `OnEndOfAlgorithm` inmediato** → falta sample data
  para la ventana del backtest. Correr `bash scripts/seed_sample_data.sh` y verificar que
  las fechas del loop cubren `set_start_date/end_date`.
- **`Failed data requests percentage 100%`** → mismo caso anterior (no hay barras de SPY).
- **`Failed data requests` ~8% con SPY OK** → es el `interest-rate.csv` (P1), inofensivo.
- **`ModuleNotFoundError: core/strategies`** → falta `__init__.py` en el paquete o el proyecto
  pusheable no es `trade-scanner/trade-scanner/`.
- **`Object with path '...' was not found in the current project`** → la config no está
  sembrada en el ObjectStore real (`storage/`, NO `data/object-store/`; ver D4). Correr
  `bash scripts/seed_object_store.sh` y verificar que la key de `main.py` casa con la ruta
  bajo `storage/`.
