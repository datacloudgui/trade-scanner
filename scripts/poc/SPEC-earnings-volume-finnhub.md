# POC — Earnings + volumen promedio vía Finnhub

**Estado:** implementado y verificado 2026-07-09 (ver [bitácora](bitacora-earnings-volume-finnhub.md))
**Ubicación:** `scripts/poc/earnings_volume.py` (host-side, fuera del algoritmo LEAN)
**Fuentes de datos:** Finnhub `/calendar/earnings` (fecha + BMO/AMC) + Finnhub `/stock/metric` (`10DayAverageTradingVolume`).
**Referencia:** [docs/research/fuentes-datos-movers-earnings.md](../../docs/research/fuentes-datos-movers-earnings.md) (caso 3).

---

## Objetivo

Prototipo host-side que reemplaza el flujo manual actual de Finviz (earnings + filtro volumen + AMC/BMO + próxima semana) por una llamada programática a **Finnhub free tier**. Dada una de cuatro selecciones de fecha, produce la lista de earnings **US** con su etiqueta **BMO/AMC** y les adjunta el **volumen promedio diario a 10 días** (`10DayAverageTradingVolume`) por *join* por símbolo.

Es un **POC exploratorio**: valida cobertura, exactitud de la etiqueta BMO/AMC y utilidad del volumen promedio antes de decidir si se integra al pipeline de universo. No forma parte del algoritmo LEAN.

---

## Contexto y límites

- **Host-side, no toca `main.py`/`core/*`.** La regla dura "el código solo habla con `QCAlgorithm`, sin SDKs de datos" aplica al **algoritmo**, no a los scripts de `scripts/`. Este POC es análogo a [alpaca_to_lean.py](../alpaca_to_lean.py) / [check_alpaca_credentials.py](../check_alpaca_credentials.py): vive en el lado PRODUCTOR y solo emite datos (tabla/CSV). Ningún import de Finnhub entra al algoritmo.
- **Credenciales fuera del repo.** `FINNHUB_API_KEY` se lee del entorno o del `.env` gitignoreado, con el mismo loader que [check_alpaca_credentials.py](../check_alpaca_credentials.py). Nunca hardcodeado ni impreso.
- **Free tier Finnhub:** earnings calendar US y `stock/metric` están en free (~60 req/min). `stock/candle` NO (pasó a premium) → por eso el volumen sale de `stock/metric`, no de calcularlo desde velas.

---

## Decisiones de diseño (D-POC.x)

### D-POC.1 — Las 4 selecciones se reducen a UNA función de ventana `[start, end]`
El núcleo es una sola función `collect(start, end, boundary_filter: bool)`:
1. pide `/calendar/earnings?from=start&to=end` (1 sola llamada para todo el rango),
2. si `boundary_filter`: aplica el filtro de bordes (abajo); si no: devuelve todo.

Las cuatro opciones del CLI son solo cómo se calculan `(start, end, boundary_filter)`:

| Opción CLI | start | end | boundary_filter | Resultado efectivo |
|---|---|---|---|---|
| `--date D` | `D-1` | `D` | ✅ | AMC(D-1) + BMO(D) |
| `--next-day` | `today` | `today+1` | ✅ | AMC(hoy) + BMO(mañana) |
| `--range S E` | `S` | `E` | ✅ | AMC(S) + interior completo + BMO(E) |
| `--next-week` | próximo lunes | próximo viernes | ❌ | toda la semana, todas las etiquetas |

> **Hallazgo:** `--date D` ≡ `--range (D-1) D`, y `--next-day` ≡ `--range today (today+1)`. Los tres modos con filtro son el mismo `collect(..., boundary_filter=True)`; solo cambian las fechas. Esto es lo que hay que implementar una vez.

### D-POC.2 — Filtro de bordes (cuando `boundary_filter=True`)
Sobre las filas devueltas por Finnhub en `[start, end]`, cada fila tiene `hour ∈ {bmo, amc, dmh, ""}`:
- **día `start`** → conservar **solo** filas con `hour == "amc"`.
- **días interiores** (`start < d < end`) → conservar **todas** las filas (BMO + AMC + dmh + desconocidas). *(decisión del usuario: "intermedios completos" — ventana de tenencia continua.)*
- **día `end`** → conservar **solo** filas con `hour == "bmo"`.
- En un rango de exactamente 2 días (`start`, `end` contiguos) no hay interior: resultado = AMC(start) + BMO(end).
- Si `start == end` en `--range`: se trata como `--date start` (equivale a `range(start-1, start)`).

### D-POC.3 — Volumen = `10DayAverageTradingVolume` de `stock/metric`
Para cada símbolo **único** del resultado ya filtrado: `GET /stock/metric?symbol=SYM&metric=all` → `metric["10DayAverageTradingVolume"]`.
- **Unidad: millones de acciones/día** (p. ej. `64.76` = ~64,7 M). Documentar la unidad en la cabecera de salida.
- Cachear por símbolo (un earnings puede repetir símbolo entre corridas; dentro de una corrida cada símbolo es único, pero la caché evita recomputar si se reusa).
- Símbolo sin métrica / `None` → fila incluida con `avg_vol_10d = None` + warning en stderr.
- `3MonthAverageTradingVolume` se captura también como columna secundaria (tiene reportes de valores raros → no usar como principal).

### D-POC.4 — Fechas = días naturales (sin calendario de trading)
Aritmética simple de calendario (opción "más sencilla de implementar", decisión del usuario). Consecuencia asumida: `--next-day` un **viernes** pide `mañana = sábado` → BMO vacío; una `--date` en lunes usa `domingo` como AMC → vacío. Aceptable para el POC; un calendario NYSE queda como mejora futura (Preguntas abiertas).

### D-POC.5 — Restricción de universo opcional (control de rate-limit)
`/calendar/earnings` con `symbol=""` devuelve **todos** los earnings US del rango (pueden ser cientos → cientos de llamadas a `stock/metric`). Para acotar:
- `--universe <csv>` (opcional): filtra el resultado a los tickers del CSV **antes** del join de volumen. Reusa el lector de universos si aplica, o un `set()` simple del CSV.
- Sin `--universe`: procesa todo el rango, con warning del nº de llamadas de métrica estimadas.
- Throttle: `sleep` ~1,1 s entre llamadas a `stock/metric` para respetar ~60 req/min.

### D-POC.6 — Dependencias mínimas (stdlib)
Usar `urllib.request` de stdlib (como [check_alpaca_credentials.py](../check_alpaca_credentials.py)), sin añadir `finnhub-python` ni `requests` al `.venv`. Mantiene el POC autocontenido.

### D-POC.7 — El entregable es un CSV con tres columnas
La salida canónica del POC es un **CSV** con exactamente: **`ticker`, `hour`, `avg_volume`** (una fila por earnings tras el filtrado). `hour` ∈ `{bmo, amc}` (y `dmh`/desconocida solo si vienen de días interiores). `avg_volume` = `10DayAverageTradingVolume` en **millones de acciones/día** (unidad indicada en el nombre de columna o cabecera). Ruta: `--csv <path>`; si se omite, escribe en `scripts/poc/out/earnings_<selección>_<YYYYMMDD>.csv`. La tabla a stdout es solo eco de conveniencia (mismo contenido).

---

## CLI

```
python scripts/poc/earnings_volume.py (--next-week | --next-day | --range S E | --date D)
                                        [--universe config/universes/<u>.csv]
                                        [--min-avg-vol N]   # filtra avg_volume >= N (millones)
                                        [--csv out.csv]     # ruta del CSV (default: scripts/poc/out/...)
```

- Las 4 selecciones de fecha son **mutuamente excluyentes** y exactamente una es obligatoria.
- `--min-avg-vol` replica el "filtro de volumen" del flujo Finviz actual (umbral en millones).
- **Salida canónica: CSV con `ticker, hour, avg_volume`** (D-POC.7); `avg_volume` en millones de acciones/día. La tabla a stdout es solo eco.
- Exit code ≠ 0 si falta credencial o falla la llamada de calendario (usable como gate).

---

## Tareas (con criterio de aceptación)

### T1 — Credenciales + smoke de las dos APIs
Loader de `FINNHUB_API_KEY` (env/`.env`) + una llamada de prueba a `/calendar/earnings` (rango corto) y a `/stock/metric` (1 símbolo).
- **CA:** con clave válida imprime ≥1 fila de earnings y el `10DayAverageTradingVolume` de 1 símbolo; sin clave → exit ≠ 0 con mensaje claro; la clave nunca se imprime.

### T2 — Núcleo `collect(start, end, boundary_filter)` + resolución de las 4 opciones
Implementa D-POC.1/D-POC.2/D-POC.4: cálculo de `(start, end, boundary_filter)` por opción y el filtro de bordes.
- **CA:** para un mismo día conocido con earnings AMC y BMO, `--date D` devuelve AMC(D-1)+BMO(D); `--range S E` (≥3 días) incluye interior completo y filtra bordes; `--next-week` no filtra bordes. Verificable con un stub de respuesta Finnhub (sin red).

### T3 — Join de volumen `stock/metric` + throttle + caché
Implementa D-POC.3/D-POC.5.
- **CA:** cada símbolo único recibe `avg_vol_10d`; símbolos sin métrica → `None` + warning; `--universe` reduce el nº de llamadas; throttle respeta ~60 req/min.

### T4 — Salida CSV (`ticker, hour, avg_volume`) + filtros
CSV canónico (D-POC.7) + eco a stdout + `--min-avg-vol`.
- **CA:** el CSV tiene exactamente las columnas `ticker, hour, avg_volume` (unidad M acciones indicada), una fila por earnings tras el filtrado, parseable; `--min-avg-vol N` excluye filas bajo el umbral; corrida real de una fecha reciente citada como evidencia (nº de filas, símbolos, rango).

---

## Qué NO hacer (fuera de scope)

- **NO** importar Finnhub ni ninguna red en `main.py`/`core/*`. El POC vive en `scripts/poc/`. `grep -ri finnhub trade-scanner/**/*.py` vacío.
- **NO** usar `stock/candle` para el volumen (premium). El volumen sale de `stock/metric`.
- **NO** hardcodear la API key ni commitearla; solo `.env` gitignoreado.
- **NO** implementar calendario de trading NYSE (días naturales, D-POC.4).
- **NO** integrar aún al pipeline de universo ni escribir CSV de universo LEAN — es un POC de validación, no producción.
- **NO** colocar órdenes ni tocar el algoritmo (regla dura V1).

---

## Done when

- [x] **T1:** credenciales + smoke de `/calendar/earnings` (92 filas) y `/stock/metric` (AAPL 10d=81.16M); exit≠0 sin clave; clave nunca impresa.
- [x] **T2:** `collect()` y las 4 opciones resuelven start/end/filtro de bordes (7/7 tests con stub sin red).
- [x] **T3:** join de `10DayAverageTradingVolume` por símbolo con throttle (1.1s), caché y `None`+warning.
- [x] **T4:** CSV `ticker, hour, avg_volume` + `--min-avg-vol`; corrida real `--date 2026-07-09` → 9 filas (`--min-avg-vol 5` → 2).
- [x] `.env` gitignoreado verificado; `grep -rli finnhub` sobre el algoritmo → vacío.

---

## Preguntas abiertas

- **Filas con `hour == ""` o `"dmh"`:** en bordes se excluyen (solo se conserva bmo/amc explícito); en interior se incluyen. ¿Emitir warning cuando una fila de borde queda descartada por hora desconocida? *(default asumido: warning en stderr, no en la tabla.)*
- **Volumen del día vs. promedio:** este POC usa promedio 10d. Si en la validación se quiere el volumen **del día del earnings**, habría que un *join* extra con Alpaca/Yahoo (fuera de scope de este POC).
- **Calendario de trading:** días naturales elegido para el POC; si los huecos de fin de semana molestan en uso real, evaluar `pandas_market_calendars`/calendario NYSE en una iteración posterior.
- **Cobertura Finnhub vs. Finviz:** validar en la corrida real que la etiqueta BMO/AMC y el set de símbolos coinciden con lo que hoy ves en Finviz para la misma fecha (criterio de confianza antes de sustituir el flujo manual).
