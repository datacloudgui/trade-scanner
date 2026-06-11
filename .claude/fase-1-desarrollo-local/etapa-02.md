# Etapa 2 — Esqueleto del proyecto (walking skeleton)

**Estado:** completada
**Depende de:** Etapa 1 (workspace LEAN operativo, `lean backtest "trade-scanner"` corre en Docker, `data/object-store/` existe, `.env` con Alpaca paper)
**Estimado:** 3–5 horas (el grueso es de-riesgar el reloj del backtest y el puente pythonnet en Docker)

## Objetivo

Validar **temprano y de punta a punta el plumbing** del proyecto, sin una sola línea de lógica de negocio. Al cerrar la etapa debe estar demostrado que:

1. Los paquetes `core/`, `strategies/`, `tests/` son importables dentro del engine.
2. `main.py` carga la config de negocio desde **ObjectStore** (no desde `config.json` ni `get_parameter`).
3. Un `ScheduledEvent` por estrategia **dispara a su hora real** según el calendario del mercado.
4. `pytest` corre **dentro de la imagen `quantconnect/lean`** con el puente pythonnet funcionando.

Esto es un *walking skeleton*: el esqueleto camina (el reloj avanza, los eventos disparan, los tests pasan) pero todavía no hace nada útil. Las features, reglas, universos y SymbolData llegan en Etapas 4+.

> **Hallazgo que define el alcance (verificado en log de Etapa 1).** Un backtest **sin datos no avanza el reloj**: el motor procesa "1 data point" y dispara `OnEndOfAlgorithm` de inmediato; los `ScheduledEvents` **nunca corren**. Doc QC: *"in backtests, the algorithm clock only advances when new data arrives."* Por eso esta etapa **siembra sample data libre** y **ancla las time-rules a un símbolo de referencia (SPY)**. Sin estos dos elementos, el criterio de "los scans disparan a su hora" es inverificable.

> **Por qué la config va en ObjectStore y no en `config.json`/`get_parameter`.** `self.get_parameter` solo devuelve strings planos y la UI de parámetros de QC cloud es plana; no expresa el mapa anidado `timeframes`. ObjectStore es el único canal portable local↔cloud que soporta estructura anidada y mantiene la config fuera del código (mismo mecanismo que los universos CSV). Ver PLAN.md §4.

---

## Tareas

### T1 — Estructura mínima de paquetes importables

**Criterio de aceptación:** `core/`, `strategies/` y `tests/` existen dentro de `trade-scanner/` con su `__init__.py`; un `import core` y `import strategies` desde `main.py` no lanza `ModuleNotFoundError` al correr el backtest. El árbol coincide con PLAN.md §3 **solo para los archivos que esta etapa ejercita** — nada de stubs muertos.

**Notas:**
- Crear únicamente: `core/__init__.py`, `strategies/__init__.py`, `tests/__init__.py`. Los módulos de negocio (`symbol_data.py`, `features.py`, `rules.py`, etc.) **no se crean en esta etapa**; cada uno nace en su etapa correspondiente.
- `config/`, `universes/`, `scripts/` viven en la **raíz del workspace** (`trade-scanner/`, junto a `lean.json`), **fuera** del proyecto pusheable `trade-scanner/trade-scanner/`. No llevan `__init__.py`.
- Regla de oro: si un archivo no se importa ni se ejecuta en esta etapa, no se crea todavía.

---

### T2 — `scripts/seed_sample_data.sh` (sample data para avanzar el reloj)

**Criterio de aceptación:** tras correr el script, `data/equity/usa/minute/spy/` (o la ruta equivalente que use el sample) contiene barras de SPY; `lean backtest` sobre esa ventana procesa **más de "1 data point"** y el reloj recorre el día de trading completo.

**Notas:**
- Baja la **sample data libre de SPY** (~2013, `Resolution.MINUTE`) del **repo público de LEAN en GitHub** (`Data/equity/usa/...`), sin auth QC. Es la misma data de ejemplo que QuantConnect distribuye abierta — ver ADR-002 (restricción de módulos que sí requieren licencia; esta data **no** la requiere).
- El backtest se configura para correr sobre la ventana que cubra la sample data (fijar `set_start_date`/`set_end_date` en `main.py` a un rango dentro de 2013 donde haya barras de SPY).
- Idempotente: si la data ya existe, no la vuelve a bajar (o la sobrescribe sin romper).
- El script documenta en un comentario de cabecera **de dónde** baja la data y **por qué** (avanzar el reloj del backtest).

---

### T3 — `config/strategies.json` + seed a ObjectStore

**Criterio de aceptación:** `config/strategies.json` existe versionado en la raíz; `scripts/seed_object_store.sh` lo copia a `data/object-store/`; tras correr el seed, `main.py` puede leerlo vía `self.object_store.read("config/strategies.json")` (o la key acordada) sin error.

**Notas:**
- Estructura **mínima** de PLAN.md §4: las dos estrategias (`swing_eod`, `market_close`) con al menos `schedule` y `universe`. El resto de campos (`timeframes`, `top_n`, `max_extension_pct`) pueden ir como placeholder en esta etapa — no se consumen todavía.
  ```json
  {
    "strategies": {
      "swing_eod":    { "universe": "swing", "schedule": "after_close" },
      "market_close": { "universe": "swing", "schedule": "before_close_30m" }
    }
  }
  ```
- `seed_object_store.sh` copia `config/*.json` (y, en etapas futuras, `universes/*.csv`) a `data/object-store/`. Idempotente.
- **Decisión a fijar en T4/T3:** la *key* exacta con la que `main.py` lee del ObjectStore (p. ej. `config/strategies.json`) y cómo se mapea al archivo físico en `data/object-store/`. Documentarla aquí una vez resuelta.

---

### T4 — `main.py` esqueleto (L5): ancla de calendario, carga de config, schedule

**Criterio de aceptación:** `lean backtest` corre y el log muestra **una línea `scan <estrategia> @ <hora>` por estrategia, a la hora correcta** del calendario del mercado (después del cierre para `swing_eod`; 30 min antes del cierre para `market_close`), verificado por los timestamps del log.

**Notas:**
- `self.add_equity("SPY", Resolution.MINUTE)` como **ancla de calendario** (provee data → avanza el reloj; provee market hours → fija las time-rules). Guardar el `Symbol` para las reglas.
- Leer `config/strategies.json` vía `self.object_store` + `json.loads`. **Cero config de negocio hardcodeada** en `main.py`.
- Mapear los strings de `schedule` a reglas LEAN:
  - `after_close` → `self.time_rules.after_market_close(spy, <min>)`
  - `before_close_30m` → `self.time_rules.before_market_close(spy, 30)`
  - fecha → `self.date_rules.every_day(spy)`
- Registrar **un `ScheduledEvent` por estrategia** cuyo callback **solo loguea** `f"scan {nombre} @ {self.time}"`. Nada más: ni reglas, ni universos, ni SymbolData.
- El mapeo string→time_rule es un punto de extensión; en esta etapa basta con cubrir los dos strings que usa la config. Si aparece un string desconocido, loguear y omitir (no crashear).

---

### T5 — `scripts/run_tests.sh` + test que de-riesga pythonnet

**Criterio de aceptación:** `bash scripts/run_tests.sh` corre `pytest` **dentro de la imagen `quantconnect/lean`** y termina verde con al menos un test que **importa `AlgorithmImports` y construye un objeto LEAN** (p. ej. un `TradeBar`), comprobando un atributo de ese objeto.

**Notas:**
- El test **no es trivial a propósito**: importar `AlgorithmImports` y construir un `TradeBar` ejercita el puente **pythonnet** en Docker, que es el verdadero *unknown* de la etapa. Un test que solo haga `assert True` no cumple el criterio.
- Ejemplo de test válido:
  ```python
  from AlgorithmImports import TradeBar, Symbol, Resolution
  from datetime import datetime

  def test_pythonnet_bridge_builds_lean_object():
      bar = TradeBar()
      bar.close = 100.0
      assert bar.close == 100.0
  ```
- `run_tests.sh` monta el proyecto dentro de la imagen y lanza `pytest` allí. **Nunca** asumir que `pytest` del host (fuera de Docker) tiene `AlgorithmImports` disponible — no lo tiene.
- Este es el **único modo válido** de correr tests en el proyecto (queda como contrato para todas las etapas siguientes).

---

### T6 — `.gitignore`, commit y limpieza

**Criterio de aceptación:** `git status` no muestra `data/equity/` como trackeable; el commit `[Etapa 2] ...` incluye estructura de paquetes, `main.py`, `config/strategies.json`, los tres scripts y el test; **excluye** la sample data.

**Notas:**
- Añadir `data/equity/` (o el subárbol de sample data) a `.gitignore` — es data descargable, no se versiona. La excepción `!data/object-store/` de Etapa 1 se mantiene; **no** versionar el contenido sembrado al ObjectStore que provenga de archivos ya versionados en `config/`.
- Verificar que `config/strategies.json` (fuente versionada) **sí** entra al commit, pero su copia sembrada en `data/object-store/` **no** (se regenera con el seed).
- Commit imperativo con referencia a la etapa.

---

## Consideraciones técnicas específicas al stack

| Punto | Detalle |
|---|---|
| **Reloj del backtest** | Sin data, el reloj no avanza y los `ScheduledEvents` no disparan (verificado en Etapa 1: "1 data point" → `OnEndOfAlgorithm`). SPY en `Resolution.MINUTE` + sample data es lo que hace caminar al esqueleto. |
| **Ancla de calendario** | Las time-rules `after_market_close`/`before_market_close` requieren un `Symbol` con market hours conocidas. SPY (equity US) las provee. Las reglas se anclan a SPY aunque las estrategias reales scaneen otro universo. |
| **ObjectStore como canal de config** | Estructura anidada (`timeframes`) no es expresable con `get_parameter` (strings planos) ni portable a la UI plana de QC cloud. ObjectStore es el único mecanismo portable local↔cloud para config anidada. Leer siempre vía `self.object_store`, nunca `open()` a rutas absolutas. |
| **pythonnet en Docker** | El verdadero riesgo de la etapa: que `import AlgorithmImports` y la construcción de objetos LEAN funcionen dentro de la imagen. Por eso el test los ejercita explícitamente. |
| **Tests solo en Docker** | `quantconnect/lean` trae el runtime .NET + pythonnet. El `pytest` del host no resuelve `AlgorithmImports`. `run_tests.sh` es el único modo válido y queda como contrato para etapas futuras. |
| **Sample data y ADR-002** | La sample data de SPY es libre y se baja de GitHub sin auth. **No** confundir con `lean data download` ni con `AlpacaBrokerage`, que sí requieren licencia QC (ADR-002, relevante en Etapa 9, no aquí). |
| **Capas** | `main.py` (L5) es el **único** lugar que toca `self.schedule`, `self.add_equity`, `self.object_store`. En esta etapa no hay L2–L4, así que el callback de scan solo loguea: no hay nada que leer todavía. |

---

## Scope

✅ Paquetes `core/`, `strategies/`, `tests/` con `__init__.py` (importables)
✅ `scripts/seed_sample_data.sh` baja SPY sample data → reloj del backtest avanza
✅ `config/strategies.json` mínimo + `scripts/seed_object_store.sh` lo siembra a ObjectStore
✅ `main.py` esqueleto: ancla SPY, lee config de ObjectStore, registra un ScheduledEvent por estrategia que **solo loguea**
✅ `scripts/run_tests.sh` corre pytest en Docker; test verde que importa `AlgorithmImports` y construye un objeto LEAN
✅ Commit `[Etapa 2] ...`; sample data gitignoreada

❌ **Cualquier lógica de negocio**: features, rules, ranking, evidencia (→ Etapas 6–7)
❌ `SymbolData`, consolidators, indicadores, warmup (→ Etapa 5)
❌ `UniverseSpec` / carga real de CSV de universo (→ Etapas 3–4)
❌ `OutputSink` / serialización de ScanResult (→ Etapa 8)
❌ Campos `timeframes`/`top_n`/`max_extension_pct` consumidos por código (placeholders no se leen aún)
❌ `lean live` / Alpaca / datos reales de mercado (→ Etapa 9)
❌ Calibración de horarios, umbrales o validación de SMAs (→ Etapas 5+)

---

## Done when

- [x] `lean backtest` recorre la ventana con sample data y loguea cada `scan <estrategia> @ <hora>` **a la hora correcta** según el calendario del mercado (`after_close`, `before_close_30m`) — verificado por timestamps en el log, no asumido
- [x] `main.py` carga `strategies.json` desde ObjectStore (no desde `config.json` ni `get_parameter`); cero config de negocio hardcodeada
- [x] `bash scripts/run_tests.sh` corre pytest dentro de la imagen LEAN con un test verde que importa `AlgorithmImports` y construye un objeto LEAN
- [x] `core/`, `strategies/`, `tests/` son paquetes importables (`__init__.py`); el árbol coincide con PLAN.md §3 para los archivos creados en esta etapa
- [x] Commit `[Etapa 2] ...`; sample data (`data/equity/`) gitignoreada

---

## Preguntas abiertas

- [ ] **Key del ObjectStore:** ¿`main.py` lee con key `config/strategies.json` o una key plana (`strategies.json`)? Fijar la convención y reflejarla en `seed_object_store.sh` (T3).
- [ ] **Ventana del backtest:** ¿qué rango exacto de 2013 cubre la sample data de SPY del repo público? Confirmar al correr T2 y fijar `set_start_date`/`set_end_date` a ese rango.
- [ ] **`after_close` → minutos:** ¿`after_market_close(spy, 0)` o un offset (p. ej. 1–5 min) para asegurar que la barra de cierre ya consolidó? Decidir al implementar T4.
- [ ] **SPY ancla vs universo real:** SPY se usa solo como ancla de calendario en esta etapa. Confirmar que en Etapas 4+ el ancla siga siendo SPY (o un símbolo de calendario dedicado) y no uno del universo escaneado.
</content>
</invoke>
