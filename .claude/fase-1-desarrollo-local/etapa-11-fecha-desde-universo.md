# Etapa 11 — Fecha del backtest derivada del archivo de universo + `latest` por fecha

**Estado:** pendiente
**Depende de:** Etapa 4 (UniverseSpec), Etapa 8 (OutputSink), Etapa 9A (datos diarios reales)
**Rama:** `feature/etapa-6-features-rules`
**Estimado:** 3–5 horas

> ⚠️ **Superseded en parte (2026-09-23).** Se re-especifica como change de OpenSpec `derive-backtest-range-from-universe`
> (orden 4 del ciclo; ver [roadmap-definitivo-2026-09.md](roadmap-definitivo-2026-09.md) U2). Dos premisas quedaron refutadas:
> (1) **`end_date = asof` no escanea la última sesión**: el backtest prod del 2026-09-20 terminó el 09-18 a las 16:00 y el
> scan `after_close` de ese día nunca disparó (H4); (2) **el footer es la fecha de descarga** (sábado 09-19), no la sesión;
> la fecha de sesión es `max(Time)` (H4b). La rama indicada abajo ya no aplica.

---

## Objetivo

Hoy el rango del backtest está hardcodeado en `main.py:initialize()` (`set_start_date`/`set_end_date` por entorno, [main.py:35-40](../../trade-scanner/main.py#L35-L40)). Correr el screener contra un export de Barchart **de una fecha pasada** produce resultados de la fecha equivocada: el reloj del backtest no coincide con el estado de mercado que el CSV retrata.

Al cerrar la etapa, en **`prod`** el rango del backtest se **deriva de la fecha que trae el propio archivo de universo** (footer `"Downloaded from Barchart.com as of MM-DD-YYYY"` / columna `Time`). Correr un CSV viejo reproduce la watchlist **de ese día**. Además, la salida `latest` deja de ser un puntero único global y pasa a vivir bajo **una carpeta por fecha**, de modo que corridas de fechas distintas coexisten sin pisarse.

`dev` queda **intacto** (anclado a su sample data 2013-10): su `sample_dev.csv` tiene fecha ficticia y no hay minute data 2026.

---

## Decisiones de diseño (ratificadas con el usuario)

| Pregunta | Decisión | Razón |
|---|---|---|
| ¿A qué entorno aplica? | **Solo `prod`** | `dev` está anclado a sample data 2013-10; su CSV tiene fecha ficticia. Menor superficie de riesgo. |
| ¿Fechas discrepantes entre `swing_advances` y `swing_declines`? | **Error explícito** (`ValueError` en `initialize`) | Un run = un único estado de mercado coherente. Reproducibilidad > tolerancia. |
| ¿Ventana antes de `asof` para `start_date`? | **Buffer pequeño configurable** (`backtest_start_buffer_days` en `strategies.json`) | Garantiza que el ScheduledEvent de cierre dispare aunque `asof` caiga cerca de fin de semana/feriado. Cumple la regla "ventanas/umbrales van a config, no a código". |

**Fuente de la fecha (prioridad):** footer `"as of MM-DD-YYYY"` (autoritativo: es el timestamp real de descarga) → fallback a `max(columna Time)` si no hay footer → `ValueError` si no hay ninguna.

**Por qué `end_date = asof` y no `asof + N`:** el warmup (`set_warm_up(depth, DAILY)`, [main.py:234](../../trade-scanner/main.py#L234)) tira la historia previa a `start_date` automáticamente. Solo se necesita que el reloj alcance el cierre de mercado de `asof` para que dispare el scan. `start_date = asof − buffer` da margen; `end_date = asof` cierra el mismo día del CSV.

---

## Tareas

### T1 — `core/universe.py`: parser de la fecha del export (sin imports LEAN)

Nueva función de módulo (mantiene el módulo libre de `AlgorithmImports`, precedente §Etapa 4 / D-E4 — testeable con mock/host).

```python
from datetime import date

def parse_asof_date(raw_csv: str) -> date:
    """Fecha del export Barchart.

    1. Footer 'Downloaded from Barchart.com as of MM-DD-YYYY ...' (autoritativo).
    2. Fallback: max de la columna 'Time' (YYYY-MM-DD) si no hay footer.
    3. ValueError claro si no hay ninguna fecha parseable.
    """
```

Además, un accesor de conveniencia que lee del ObjectStore y parsea, para que `main.py` no duplique el `read`:

```python
def read_asof_date(object_store, universe_key: str) -> date:
    return parse_asof_date(object_store.read(universe_key))
```

**Criterio de aceptación:**
- Con `storage/universes/swing_advances.csv` real → `date(2026, 7, 1)` (footer `07-01-2026`).
- Footer ausente pero columna `Time` presente → `max(Time)`.
- Ni footer ni `Time` → `ValueError` con mensaje que nombra la clave del CSV.
- No importa `AlgorithmImports` (`grep -n AlgorithmImports core/universe.py` → vacío).

**Notas técnicas:**
- Regex sobre el string crudo (`re.search(r"as of (\d{2})-(\d{2})-(\d{4})", raw_csv)`): el footer se pierde tras el `read_csv`+footer-strip de `load()`, así que se parsea **antes** de pandas, sobre el texto original.
- El footer usa `MM-DD-YYYY`; la columna `Time` usa `YYYY-MM-DD`. No confundir el orden.

---

### T2 — `config/strategies.json`: buffer de arranque en `prod`

```json
"environments": {
  "prod": {
    "top_n": 50,
    "max_universe": 200,
    "warmup_budget": { "daily": 1100 },
    "backtest_start_buffer_days": 5
  }
}
```

- Ausente → default en código `5` (retrocompatible).
- No se añade a `dev` (no aplica).
- Resembrar con `bash scripts/seed_object_store.sh` tras editar.

---

### T3 — `main.py`: derivar el rango de la fecha del universo (prod)

Reordenar `initialize()`: leer config y resolver los `universe_key` **antes** del bloque `set_*_date`, de modo que la fecha del CSV esté disponible al fijar el rango. `object_store` ya está disponible al inicio de `initialize()`.

**Boceto:**
```python
env = self.get_parameter("env", "prod")
raw = self.object_store.read("config/strategies.json")
full_config = json.loads(raw)
env_cfg = full_config["environments"][env]
strategies_config = { ... }  # filtro enabled (igual que hoy)

if env == "dev":
    self.set_start_date(2013, 10, 7)
    self.set_end_date(2013, 10, 11)
    self._feed_resolution = Resolution.MINUTE
else:
    # Recolecta la asof de CADA universe_key usado; discrepancia → ValueError.
    universe_override = env_cfg.get("universe")
    keys = {
        f"universes/{universe_override or cfg['universe']}.csv"
        for cfg in strategies_config.values()
    }
    dates = {k: read_asof_date(self.object_store, k) for k in keys}
    distinct = set(dates.values())
    if len(distinct) > 1:
        raise ValueError(
            f"[fecha-universo] archivos con fechas discrepantes: {dates}"
        )
    asof = distinct.pop()
    buffer = env_cfg.get("backtest_start_buffer_days", 5)
    start = asof - timedelta(days=buffer)
    self.set_start_date(start.year, start.month, start.day)
    self.set_end_date(asof.year, asof.month, asof.day)
    self._feed_resolution = Resolution.DAILY
    self.log(f"[fecha-universo] asof={asof} start={start} (buffer={buffer}d)")
```

El resto de `initialize()` (universo, warmup, pipelines, schedule) queda igual: reusa `full_config`/`strategies_config`/`env_cfg` ya leídos (evita releer el ObjectStore).

**Criterio de aceptación:**
- Con `swing_advances.csv`+`swing_declines.csv` de la misma fecha → log `asof=<fecha>` y el backtest corre ese rango.
- Con dos CSV de fechas distintas → `ValueError` en `initialize` con el detalle de cada archivo.
- `dev` inalterado: mismo rango 2013-10, mismo minute feed.
- Los resultados quedan fechados en `asof` (la salida ya usa `self.time` / `as_of`).

**Notas técnicas:**
- `set_start_date`/`set_end_date` deben llamarse en `initialize` antes de `add_equity`; el reorden lo respeta (el bloque de fechas sigue arriba de la creación de `SymbolData`).
- Importar `from datetime import timedelta` (o `date`) en `main.py`.

---

### T4 — `core/output.py`: `latest` bajo carpeta por fecha

Hoy `_emit_file` ([output.py:259-268](../../trade-scanner/core/output.py#L259-L268)) escribe:
```
results/{base}/{ts}.json
results/{base}/{ts}.csv
results/{base}/latest.json      ← puntero único global (se pisa cada run)
```

El `latest.json` global se sobrescribe en cada corrida, así que un backtest de una **fecha pasada** pisaría el `latest` de la fecha vigente. Mover `latest` a una carpeta por fecha ("la fecha hasta la cual se calculó la estrategia") permite que corridas de fechas distintas coexistan.

**Cambio (layout propuesto):**
```
results/{base}/{YYYYMMDD}/{ts}.json
results/{base}/{YYYYMMDD}/{ts}.csv
results/{base}/{YYYYMMDD}/latest.json
```
donde `{YYYYMMDD}` = fecha de `as_of` del envelope (la fecha hasta la cual se calculó). `{ts}` sigue siendo `YYYYMMDD-HHMM` (redundante con la carpeta pero mantiene unicidad intradía y no rompe el patrón existente).

**Criterio de aceptación:**
- Un scan con `as_of` = 2026-07-01 escribe `results/swing_eod/20260701/latest.json` (+ `.json`/`.csv` timestamped en la misma carpeta).
- Correr dos fechas distintas produce dos carpetas; ninguna pisa a la otra.
- El `_save` sigue chequeando `is False` (persistencia fallida visible, #22).

**Notas técnicas / consideración abierta:** `latest.json` era el "puntero fijo del script host" (opción A, D8.3). Con `latest` bajo carpeta por fecha, el script host debe conocer la fecha objetivo para leer `results/{base}/{YYYYMMDD}/latest.json` (p. ej. la más reciente por orden lexicográfico de carpeta, que es cronológico con `YYYYMMDD`). Ver Preguntas abiertas.

---

### T5 — Tests (dentro de Docker)

**Parser de fecha (`tests/test_universe.py` o nuevo `test_asof.py`):**
- `parse_asof_date` con footer válido → `date` correcta.
- Sin footer, con columna `Time` → `max(Time)`.
- Footer y `Time` presentes y coherentes → footer gana (misma fecha).
- Ni footer ni `Time` → `ValueError`.

**Reconciliación (test de `main`-nivel o helper puro):**
- Dos CSV con fechas distintas → la lógica de reconciliación lanza `ValueError` con el detalle.

**Output (`tests/test_output.py`):**
- `_emit_file` con `as_of=2026-07-01` escribe las tres claves bajo `results/{base}/20260701/`.
- El mock de ObjectStore captura las keys y verifica el prefijo de carpeta por fecha.

**Criterio:** `bash scripts/run_tests.sh` verde (conteo previo + los nuevos).

---

## Scope

✅ Entra:
- `core/universe.py`: `parse_asof_date` + `read_asof_date`.
- `config/strategies.json`: `backtest_start_buffer_days` en `prod`.
- `main.py`: reorden del bloque de fechas + derivación `asof` (solo prod) + reconciliación con error.
- `core/output.py`: `_emit_file` escribe bajo carpeta por fecha.
- Tests T5.

❌ No entra:
- **`dev`** — sigue anclado a 2013-10 con sample data.
- **Descarga automática de datos diarios** para fechas fuera del rango ya sembrado (prerequisito operativo, no código — ver abajo).
- **Migración del script host** a la nueva ruta de `latest` (queda como pregunta abierta / etapa siguiente si se decide).
- **Refactor del formato `{ts}`** (se conserva).

---

## Prerequisito operativo (no es código)

Para backtestear una fecha antigua, los zips diarios de `prod` deben cubrir `asof` **+ el runway del warmup** previo. Los datos reales de 9A son "2020+". Si la fecha pedida cae fuera del rango sembrado, no habrá barras → warmup frío (símbolos excluidos del scan, logueados). Sembrar el rango con `scripts/stooq_to_lean.py` / `scripts/alpaca_to_lean.py` antes de la corrida.

---

## Done when

- [ ] `core/universe.py` exporta `parse_asof_date` y `read_asof_date`; sin `AlgorithmImports`.
- [ ] `config/strategies.json` tiene `backtest_start_buffer_days` en `prod`; resembrado a `storage/`.
- [ ] `main.py` en `prod` deriva `start`/`end` de la fecha del universo y loguea `asof=...`; `dev` inalterado.
- [ ] Dos CSV con fechas distintas → `ValueError` explícito en `initialize` (verificado).
- [ ] `lean backtest "trade-scanner"` (prod) corre con el rango derivado y escribe `results/{base}/{YYYYMMDD}/latest.json` (evidencia: listar `storage/results/`).
- [ ] `bash scripts/run_tests.sh` verde con los tests nuevos (parser, reconciliación, output por fecha).
- [ ] Commit `[Etapa 11] ...`.

---

## Preguntas abiertas

- [ ] **Layout exacto de la carpeta por fecha.** Propuesto `results/{base}/{YYYYMMDD}/...`. Alternativa `results/{YYYYMMDD}/{base}/...` (agrupa por corrida antes que por estrategia). ¿Cuál encaja mejor con cómo consumirá el script host y el humano?
- [ ] **Puntero para el script host.** Con `latest` bajo fecha, el host debe resolver "la última fecha" (carpeta `YYYYMMDD` máxima) o recibir la fecha por parámetro. ¿Se ajusta el host en esta etapa o en la siguiente?
- [ ] **`asof` en día no hábil.** Si el CSV se descargó un sábado, el cierre de mercado de `asof` no dispara. El buffer da margen hacia atrás pero el scan caería en el último día hábil ≤ `asof`. ¿Basta con el buffer o hay que "snap" explícito al último trading day?
- [ ] **Múltiples universos con la misma fecha pero distinto horario de descarga.** Hoy se compara solo la fecha (día). Si en el futuro importa la hora, ampliar a timestamp.
