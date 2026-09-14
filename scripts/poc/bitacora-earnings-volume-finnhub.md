# Bitácora — POC earnings + volumen promedio vía Finnhub

Implementación de [SPEC-earnings-volume-finnhub.md](SPEC-earnings-volume-finnhub.md).
Fecha: 2026-07-09. Estado: **implementado y verificado (T1–T4 verdes)**.

---

## Qué se construyó

| Archivo | Rol |
|---|---|
| [earnings_volume.py](earnings_volume.py) | Script host-side (stdlib only). CLI + `FinnhubClient` + núcleo `collect` + join de volumen + CSV. |
| [test_earnings_volume.py](test_earnings_volume.py) | Test offline con `StubClient` (sin red). Corre con el Python del `.venv`. |
| `out/earnings_<sel>_<YYYYMMDD>.csv` | Salida canónica (gitignoreada). |

Sin dependencias nuevas: solo `urllib`/`csv`/`json` de stdlib (D-POC.6). Ningún import de Finnhub
entra al algoritmo LEAN — `grep -rli finnhub` sobre `trade-scanner/`, `core/`, `main.py`,
`strategies/` → **vacío**.

---

## Decisiones de la spec y cómo se materializaron

- **D-POC.1** — Una sola `collect(client, start, end, boundary_filter, universe)`. Las 4 opciones
  del CLI son solo cómo se calcula `(start, end, boundary_filter)` en `resolve_window()`.
- **D-POC.2** — `_apply_boundary_filter()`: día `start` → solo `amc`; día `end` → solo `bmo`;
  interior → todo. Rango de 2 días contiguos = AMC(start)+BMO(end) sin interior. `--range S==E` se
  reduce a `--date S`. Filas de borde con hora desconocida (`∅`/`dmh`) se descartan con warning en
  stderr (respondiendo la pregunta abierta: warning sí, no en la tabla).
- **D-POC.3** — `attach_volume()` usa `10DayAverageTradingVolume` de `/stock/metric?metric=all`.
  `3MonthAverageTradingVolume` se captura como columna secundaria (solo en el eco a stdout, no en el
  CSV canónico). Símbolo sin métrica → `avg_volume=None` + warning.
- **D-POC.4** — Días naturales. `_next_monday()` salta estrictamente al lunes siguiente.
- **D-POC.5** — `--universe <csv>` filtra **antes** del join (menos llamadas a metric). `FinnhubClient`
  cachea por símbolo y aplica throttle de 1.1 s (~60 req/min). Warning si >30 símbolos sin universo.
- **D-POC.6** — stdlib pura.
- **D-POC.7** — CSV con `ticker, hour, avg_volume_10d_millions` (unidad en el nombre de columna).
  Eco a stdout con contexto extra (3m). Default `scripts/poc/out/earnings_<label>_<YYYYMMDD>.csv`.

**Cliente inyectable:** `collect`/`attach_volume` reciben el cliente por parámetro → el test usa
`StubClient` sin tocar la red (satisface el CA de T2 "verificable con stub").

---

## Verificación (evidencia)

### T1 — Credenciales + smoke de las dos APIs ✅
- Loader `get_api_key()` lee `FINNHUB_API_KEY` de entorno/`.env` (mismo patrón que
  `check_alpaca_credentials.py`). Sin clave → exit 2. La clave nunca se imprime (va como query param
  `token`, jamás logueada).
- Smoke real: `/calendar/earnings [2026-07-06..2026-07-09]` → 92 filas; `/stock/metric AAPL`
  `10DayAverageTradingVolume = 81.16` M.

### T2 — Núcleo + 4 opciones (stub, sin red) ✅
`python scripts/poc/test_earnings_volume.py` → 7/7 tests verdes:
resolución de las 4 ventanas, filtro de bordes en rango ≥3 días, `--date` de 2 días (AMC+BMO),
`--next-week` sin filtro, filtro de universo, join de volumen con `None`, y `--min-avg-vol`.

### T3 — Join de volumen + throttle + caché ✅
Cada símbolo único recibe `avg_volume`; `None`+warning si falta; caché por símbolo evita recomputar;
`sleep` de 1.1 s entre llamadas a metric.

### T4 — CSV + filtros (corrida real) ✅
`python scripts/poc/earnings_volume.py --date 2026-07-09` → **9 filas** (5 AMC del 2026-07-08 +
4 BMO del 2026-07-09), archivo `out/earnings_date_20260709.csv`:

```
ticker,hour,avg_volume_10d_millions
BYRN,bmo,0.89897
NTIC,bmo,0.00702
PEP,bmo,9.92819
SMPL,bmo,2.45006
AZZ,amc,0.37185
CAG,amc,30.71947
LEVI,amc,3.48115
PCYO,amc,0.0727
PSMT,amc,0.4222
```

`--min-avg-vol 5` sobre la misma fecha: **9 → 2 filas** (PEP 9.93, CAG 30.72). CSV parseable, columnas
exactas `ticker, hour, avg_volume`.

---

## Desviaciones / notas para el usuario

1. **Nombre de la clave en `.env`:** estaba como `FINHUB_API_KEY` (faltaba una N); se renombró a
   `FINNHUB_API_KEY` para coincidir con la spec. El `.env` sigue gitignoreado.
2. **Nombre de columna del CSV:** la spec pide `avg_volume`; se usó `avg_volume_10d_millions` para
   documentar la unidad en la propia cabecera (D-POC.7 permite "unidad indicada en el nombre de
   columna o cabecera"). Si prefieres el nombre literal `avg_volume`, es un cambio de una línea en
   `write_csv()`.
3. **`out/` gitignoreado:** los CSV de salida son artefactos regenerables → se añadió
   `scripts/poc/out/` al `.gitignore`.
4. **Test host-side, no en Docker:** al ser stdlib puro y no importar `AlgorithmImports`, el test
   corre con el Python del `.venv` (`python scripts/poc/test_earnings_volume.py`), no con
   `run_tests.sh` (que es para el algoritmo dentro de la imagen LEAN).

## Preguntas abiertas de la spec (para una iteración futura, NO abordadas aquí)
- Volumen **del día** del earnings (vs. promedio 10d) → requeriría join con Alpaca/Yahoo.
- Calendario de trading NYSE (hoy: días naturales; `--next-day` un viernes deja BMO vacío).
- Validación de cobertura Finnhub vs. Finviz para la misma fecha (criterio de confianza antes de
  sustituir el flujo manual).
