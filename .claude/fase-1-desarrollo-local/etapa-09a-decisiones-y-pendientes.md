# Etapa 9A — Decisiones y pendientes

Bitácora de decisiones tomadas durante la implementación y deferrals abiertos. Complementa el
spec [etapa-09a-conexion-alpaca.md](etapa-09a-conexion-alpaca.md).

---

## T3 — Downloader Alpaca REST → zips LEAN diarios *(2026-06-20)*

### Decisiones tomadas

- **D-T3.1 — Emisor LEAN extraído a `scripts/lean_daily.py` (módulo compartido).** Para no duplicar
  el formato LEAN entre el converter Stooq (5B) y el downloader Alpaca (9A), `to_lean_rows` /
  `write_lean_zip` / `_PRICE_SCALE` se movieron **verbatim** de `stooq_to_lean.py` a `lean_daily.py`;
  ambos productores lo importan. `stooq_to_lean.py` queda bit-idéntico en comportamiento (solo cambia
  dónde viven las funciones). Verificado: el round-trip de 5B (`test_t5_stooq_crosscheck`) sigue verde.
  Razón: evita que dos copias del emisor diverjan y rompan el cross-check de T4 sin avisar (D9A.3).

- **D-T3.2 — La red vive solo en `_get` (aislada y mockeable).** Todo el acceso HTTP pasa por una
  única función `alpaca_to_lean._get(url, headers) -> dict`. `fetch_daily_bars` recibe `sleep` como
  parámetro. Así los tests cubren paginación, chunking y parseo **sin red** (monkeypatch de `_get`,
  `sleep` no-op). Cumple el contrato de tests de la etapa (respuestas Alpaca sintéticas en Docker).

- **D-T3.3 — Multi-símbolo + paginación + throttle en la capa de descarga (D9-1).** Chunks de ≤100
  símbolos por request (Alpaca admite ≤200; 100 mantiene la URL acotada), paginación por
  `next_page_token`, y pausa de `0.35s` entre requests (~3 req/s < 200 req/min del free tier). Nada de
  esto toca `main.py`: el algoritmo solo lee zips vía `DefaultDataProvider`.

- **D-T3.4 — Directorio de salida del demo: `data/alpaca_lean/daily/`.** El default del script es
  `data/equity/usa/daily` (ruta runtime que lee el backtest, fiel al spec), pero la corrida de
  verificación de T3 se hizo a `data/alpaca_lean/daily/` (espejo de `data/stooq_lean/daily/`) para
  **no pisar** las sample data existentes (spy/aapl/ibm/fb) usadas por backtests previos. La
  "promoción" de los zips Alpaca a `data/equity/usa/daily` se decide en T5/T6 (cuando se quiera correr
  el backtest sobre datos Alpaca reales).

- **D-T3.5 — `adjustment=split` + `feed=iex` por defecto.** Split-only adjusted para casar con Stooq
  (5B) y la referencia del trader (D9A.3). IEX por ser el feed del free tier (volumen subestimado →
  regla de volumen relativo, ya asumida).

- **D-T3.6 — Símbolos sin barras se omiten (sin zip), no abortan la corrida.** El gate de salida es
  `≠0` solo si **ningún** símbolo trajo datos (fallo total de credenciales/conectividad); símbolos
  individuales vacíos se loguean y se saltan.

### Hallazgos

- **El ticker "FB" en Alpaca devuelve datos desde 2025-06-26, NO el histórico de Meta.** En
  `universes/sample_dev.csv`, "FB" representa a Meta (ticker histórico, renombrado a META en 2022).
  Alpaca hoy sirve "FB" como un símbolo **reasignado** a otra entidad, con ~1 año de historia. No es
  un fallo del downloader (escribe lo que la API entrega), pero **FB no sirve como proxy de Meta** para
  validar SMAs largas. Acción en T4/T5: usar SPY/AAPL/IBM para el cross-check de fidelidad; si se
  necesita Meta, usar el ticker `META`.

- **Cobertura IEX aparentemente completa en líquidos.** SPY/AAPL/IBM devolvieron 618 barras
  (2024-01-02 → 2026-06-18), coherente con los días de trading del rango. El caveat IEX (volumen ~2,5%)
  aplica al **volumen**, no a la presencia de barras OHLC en símbolos líquidos.

### Evidencia de verificación

- **Tests Docker:** `bash scripts/run_tests.sh` → **234 passed** (225 previos + 9 nuevos de
  `test_alpaca_to_lean.py`); round-trip de 5B verde tras el refactor.
- **Descarga real:** `python scripts/alpaca_to_lean.py --universe universes/sample_dev.csv
  --start 2024-01-01 --out data/alpaca_lean/daily` → 4/4 con datos, EXIT=0.
- **Idempotencia:** re-correr el mismo rango deja el contenido CSV byte-idéntico (hashes `shasum`
  iguales antes/después para spy/aapl/ibm).
- **Formato LEAN:** `20240102 00:00,4721500,4736400,4704900,4726600,1982936` (deci-centavos ×10000).
- **Agnosticismo:** `grep` de `alpaca` en `core/`/`strategies/`/`main.py` **vacío**. Los únicos matches
  en `trade-scanner/` son el test del downloader host-side (esperado, como `test_notify_email`) y los
  tests-guardián de `test_email_render`/`test_output` que **afirman la ausencia** de Alpaca en el
  algoritmo.

### Pendiente / para etapas siguientes

- **T4:** cross-check de fidelidad Alpaca↔referencia con SPY/AAPL/IBM (no FB); fixture autoritativo +
  test de regresión. Documentar discrepancias de volumen por IEX.
- **T5/T6:** decidir promoción de zips Alpaca a `data/equity/usa/daily`; warmup real + backtest
  multi-mes. Nota de historia: el demo bajó desde 2024; para SMA larga (W:200/M:200) habrá que bajar
  desde ~2016 (límite de historia de Alpaca) y validar el budget prod.
- **Universo prod:** `read_universe_symbols` usa el mismo criterio de ticker (`^[A-Z]{1,5}$`) que
  `core/universe.py`, pero **no aplica el filtro declarativo** (precio/volumen) — descarga todos los
  tickers del CSV. Si el CSV prod trae >200, conviene pre-filtrar antes de descargar (no es bloqueante
  para sample_dev).

---

## T4 — Cross-check de fidelidad + SMAs coherentes *(2026-06-20)*

### Decisiones tomadas

- **D-T4.1 — Stooq como referencia automatizable del cross-check.** La CA admite "TradingView/Stooq".
  TradingView es manual; Stooq ya fue validado vs TradingView por el usuario en 5B (T6.3). Por eso el
  cross-check automatizado es **Alpaca↔Stooq** vía `SymbolData`: ambas fuentes son split-only adjusted
  (Alpaca `adjustment=split`, Stooq skip-dividends), así que sus SMAs deben cuadrar salvo ruido IEX.

- **D-T4.2 — Comparar solo (tf,período) ready en AMBAS fuentes.** Los zips Alpaca del demo cubren
  2024-01-02.. → W:200 y M:200 no están ready (historia insuficiente) y se **omiten** del cross-check
  (ya cubiertos por Stooq/5B). El cross-check exige que el set común incluya al menos
  D:8/20/200 + W:8/20 (guardia contra un set vacío por bug de carga).

- **D-T4.3 — `COMPARE_AT = 2026-06-01`.** Dentro del overlap Alpaca(2024-)↔Stooq(..2026-06-11) y deja
  ready D:8/20/200, W:8/20, M:8/20 desde el rango Alpaca corto del demo.

- **D-T4.4 — Fixture autoritativo congelado de SPY-Alpaca** (`FROZEN_SPY_ALPACA`), extiende el de 5B:
  valor exacto (rel=1e-12) + samples + end_time, para detectar cualquier regresión del downloader o
  del emisor compartido. Las discrepancias IEX **no se "corrigen" en código** (regla dura): se
  documentan aquí.

### Evidencia de verificación

- **Tests Docker:** `bash scripts/run_tests.sh` → **238 passed** (234 previos + 4 de
  `test_t4_alpaca_crosscheck.py`: 3 cross-checks parametrizados SPY/AAPL/IBM + 1 regresión SPY).
- **Discrepancias Alpaca↔Stooq medidas** (n=7 series comunes por símbolo):

  | Símbolo | Máx. discrepancia | Mediana |
  |---|---|---|
  | SPY  | 0,0190% (M:20) | 0,0062% |
  | AAPL | **0,2259% (M:20)** | 0,0172% |
  | IBM  | 0,0562% (W:20) | 0,0072% |

  Todas ≤0,25%. El caso más estrecho es **AAPL M:20 (0,2259%)**: el ruido IEX (close IEX vs
  consolidado) se acumula en la ventana mensual larga. Fidelidad excelente en la mayoría (mediana
  <0,02%); el margen de AAPL conviene vigilarlo si en prod se baja la tolerancia.

### Pendiente / para etapas siguientes

- **AAPL M:20 al filo (0,2259% vs 0,25%):** si T5/T6 amplían el rango Alpaca a 2016, recomputar y
  confirmar que sigue dentro de tolerancia con más historia (más meses promediados).
- **Fixture ligado al rango del demo (2024-):** si en T5 se re-descarga SPY desde 2016, los valores
  congelados de `FROZEN_SPY_ALPACA` cambian (más samples) → recongelar a propósito y anotarlo.

---

## T5 + T6 — Warmup real y backtest multi-mes reproducible *(2026-06-21)*

### Decisiones tomadas

- **D-T5.1 — Rango de backtest env-condicional en `main.py`.** dev mantiene la ventana 2013-10 (ancla
  SPY-minute); prod usa rango real (T5: 2026-06-12..19; T6: **2026-01-02..06-19**). Sin esto el warmup
  pedía historia antes de 2013 (datos reales empiezan 2020) → todo frío. Cambio mínimo, dev intacto,
  no afecta tests (los tests no corren `initialize`).
- **D-T5.2 — Resolución de feed env-condicional.** dev=`MINUTE` (working_bar con SPY sample);
  **prod=`DAILY`** porque la historia real de 9A es diaria (sin minute). Con `MINUTE` el reloj no
  avanzaba y los `ScheduledEvents` no disparaban. El `working_bar` minute real queda como rebanada
  live (T9), por diseño (D9A.2).
- **D-T5.3 — Fix en `core/universe.py`: separador de miles de Barchart.** `_parse_pct` y las columnas
  numéricas (`avg_vol_5d`, `price`) quitan comas antes de `float()`/`to_numeric`. Datos reales traen
  `"+1,153.11%"` y volúmenes `"101,584,617"`; reventaba `initialize`. Test de regresión en
  `test_universe.py`. (Etapa 4 — no es features/rules/pipeline congelados de 6B.)
- **D-T6.1 — Tests actualizados a la nueva regla `D+W+M` del usuario** (cambio en `swing_eod.py`:
  `SMAPositionRule(20,[D,W,M])` + `SMAPositionRule(8,[D],required=False)`). 4 tests reflejaban la regla
  vieja `W+M`+`20,D`; se actualizaron a `AboveSMA(20,D+W+M)`/`AboveSMA(8,D)` y al embudo con la línea
  `optional` (la rule `required=False` informa sin descartar; `rules_passed_count` cuenta solo
  required → 2). Solo expectativas; cero cambio de lógica.

### Hallazgo (corrige expectativa del spec sobre M:200)
En **prod las estrategias declaran hasta W:200 y M:20** (no M:200) → el plan (depth 1010) cabe entero
en budget 1100 y **no hay exclusión ni warning en prod**. El guardrail "M:200 excluida con warning"
es del **superset dev/5B**. El límite de historia real (~2020) se manifiesta como **W:200 fría por
símbolo** (necesita ~1010 barras ≈ 4 años) — 29/141 no-ready, 2 totalmente fríos (gate B los excluye).

### Validación T1→T6 (✅/⚠️/❌ contra CA)

| Tarea | CA | Estado | Evidencia |
|---|---|---|---|
| **T1** | ADR-002 Opción C adoptada + costo + comandos | ✅ | ADR ampliado 2026-06-20 |
| **T2** | smoke test cuenta paper **y** market data, exit gate | ✅ | re-verificado 2026-06-21: EXIT=0 |
| **T3** | downloader zips válidos, idempotente, grep limpio, reusa emisor 5B | ✅ | 195 zips; grep algoritmo limpio; emisor compartido `lean_daily.py` |
| **T4** | cross-check ≤0,25% ≥3 símbolos + fixture regresión | ✅ | máx 0,2259% (AAPL M:20); en suite 239 passed |
| **T5** | warmup real, filas/duración/ready, budget coherente | ✅ | 122.669 barras/8.69s, ready 112/141, depth 1010 |
| **T6** | backtest multi-mes, watchlists reproducibles con evidencia | ✅ | 2026-01-02..06-19, 462 scans, **482 archivos byte-idénticos** ×2 corridas |

Regla dura **cero órdenes**: `grep` de `market_order`/`set_holdings`/`set_quantity`/`limit_order` en
algoritmo → vacío. Agnosticismo: `grep alpaca` en `core/`/`strategies/`/`main.py` → limpio (comentarios
de `main.py` reescritos para no nombrar al proveedor).

### Pendiente / para cerrar la etapa
- **T7 (portabilidad, DoD nº5):** correr el mismo algoritmo bajo dos fuentes (zips locales ↔ QC cloud
  free) cambiando solo config; `git diff` de `.py` vacío.
- **T8 (matriz de proveedor):** tabla de referencia con limitaciones Alpaca free.
- **Rango operativo vs. de validación:** prod quedó en 2026-01-02..06-19 (rango de **validación** T6,
  ~5,5 meses). Para la corrida **semanal** real conviene un rango corto o parametrizarlo (no se hace
  un backtest de 5 meses cada fin de semana). Decisión de diseño abierta.
- **`config.json` quedó en `env=prod`** (toggle de runtime). Para volver al harness dev: `env=dev`.
- **`main.py` ahora env-condicional** (fechas + resolución): cualquier cambio futuro de rango prod se
  edita ahí. Considerar parametrizar fechas vía `config.json` en lugar de hardcodear.
- **Survivorship:** el universo Barchart es point-in-time (movers de 2026-06-18); un backtest multi-mes
  scanea esos mismos tickers en fechas pasadas. Válido para ejercitar el pipeline; NO es un estudio
  histórico libre de sesgo (fuera de scope de 9A).
