# Screener de Acciones sobre LEAN

Screener multi-estrategia construido sobre el motor [LEAN](https://github.com/QuantConnect/Lean) de QuantConnect. Carga universos de tickers desde CSV (Barchart), mantiene indicadores técnicos en los timeframes que cada estrategia declara y ejecuta filtros programados para producir watchlists con evidencia. **Solo escanea: no coloca órdenes.**

---

## Qué hace

- Carga universos de hasta 200 tickers (tope duro post-filtro) desde CSVs exportados de Barchart, uno por dirección (`swing_advances` / `swing_declines`), con un filtro declarativo de columnas.
- Mantiene SMAs en los timeframes que cada estrategia declara (D/W/M), con consolidators nativos de LEAN y warmup derivado de la config (nunca hardcodeado).
- Ejecuta estrategias en horarios programados (tras el cierre, 30 min antes del cierre).
- Emite por estrategia base un envelope JSON + CSV con evidencia: por qué pasó cada ticker (distancia a SMAs, buckets, % cambio del día).
- Portable entre entorno local y QuantConnect cloud sin cambios de código: la fuente de datos vive en `lean.json` y el switch de canales de salida en `core/output.py`.

## Estrategias V1

| Estrategia | Dirección | Horario | Descripción |
|---|---|---|---|
| `swing_eod` / `swing_eod_short` | long / short | Tras el cierre (`after_close`) | Top movers del día sobre (bajo) SMA20 en D/W/M y no extendidos vs SMA8 |
| `market_close` / `market_close_short` | long / short | 15:30 ET (`before_close_30m`) | Mismas reglas con la barra parcial del día en curso |

Las variantes long/short comparten composición de rules (espejadas automáticamente) y se agrupan por estrategia base en la salida: un solo archivo/correo con secciones LONG y SHORT.

## Stack

| Componente | Tecnología |
|---|---|
| Engine | LEAN open source (Python 3.11) |
| Ejecución | `lean backtest` / `lean live` vía CLI (Docker) |
| Datos | zips diarios locales (converters `scripts/alpaca_to_lean.py`, `scripts/stooq_to_lean.py`) · fuente configurable en `lean.json` |
| IDE | VSCode + LEAN CLI |

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado y corriendo
- Python 3.11 en un virtualenv (`.venv`) con `pip install lean`
- (Solo para `lean live` con broker) cuenta QuantConnect de pago — ver [ADR-002](.claude/decisions/ADR-002-qc-module-auth-constraint.md)

> **No usar `lean init` ni `lean login`**: `lean init` exige seleccionar una organización QC de pago. Este workspace ya trae `lean.json` versionado con un `organization-id` placeholder que el backtest local nunca valida.

## Setup inicial

```bash
# 1. Clonar el workspace (lean.json vive en la raíz)
git clone <repo-url> && cd trade-scanner

# 2. Virtualenv con el CLI de LEAN
python3.11 -m venv .venv
source .venv/bin/activate
pip install lean

# 3. Sembrar config y universos al ObjectStore local (storage/)
bash scripts/seed_object_store.sh

# 4. Sembrar sample data de SPY (el reloj del backtest no avanza sin datos)
bash scripts/seed_sample_data.sh

# 5. Smoke test
lean backtest "trade-scanner"
```

**Credenciales:** nunca van en `lean.json` (está commiteado) ni en ningún archivo del repo. Los campos de credenciales de `lean.json` quedan vacíos; los valores reales viven solo en `.env` (gitignoreado). El CLI no expande `${VAR}` en `lean.json`.

---

## Configuración de estrategias

La config de negocio vive en `config/strategies.json` y se lee en runtime vía ObjectStore (`self.object_store.read("config/strategies.json")`). `seed_object_store.sh` la copia a `storage/config/`, que es el ObjectStore local del CLI. Nada de umbrales, horarios ni universos en código.

```json
{
  "bucket_thresholds": { "near": 0.005, "mild": 0.03, "extended": 0.10 },
  "environments": {
    "dev":  { "top_n": 2,  "max_universe": 4,   "universe": "sample_dev",
              "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20, 200] },
              "warmup_budget": { "daily": 4300 } },
    "prod": { "top_n": 50, "max_universe": 200, "warmup_budget": { "daily": 1100 } }
  },
  "strategies": {
    "swing_eod": {
      "universe": "swing_advances",
      "direction": "long",
      "timeframes": { "D": [8, 20, 200], "W": [8, 20, 200], "M": [8, 20] },
      "schedule": "after_close",
      "universe_filter": "avg_vol > 1e6 and price > 5"
    }
  }
}
```

- El entorno activo (`dev`/`prod`) se lee de `trade-scanner/config.json` → `"parameters": {"env": "dev"}` (único parámetro escalar del algoritmo; `get_parameter` NO lee el `lean.json` de la raíz).
- La notificación se configura en `config/notifications.json` (también ObjectStore): grupos por estrategia base, canales por entorno (`file` / `qc_notify` / `host_email`) y suscriptores.
- La profundidad de warmup se deriva de los `timeframes` declarados acotada por `warmup_budget`; las series fuera de presupuesto se excluyen con warning y las rules que las referencien fallan explícito en `initialize()`.

**Cambiar fuente de datos:** solo editar el proveedor en `lean.json`. El código no cambia.

---

## Universo de tickers

Cada estrategia declara su universo (`swing_advances` para long, `swing_declines` para short). La fuente es un CSV exportado de Barchart con nombre `*-advances-MM-DD-YYYY.csv` / `*-declines-MM-DD-YYYY.csv`, depositado en `data/object-store/`:

```csv
Symbol,Name,5D %Chg,Latest,Change,%Change,5D Chg,5D High,5D Low,5D Avg Vol,Time
AAPL,Apple Inc,+4.10%,232.50,1.20,+0.52%,9.15,234.0,222.1,52000000,06/18/26
```

- `seed_object_store.sh` toma el CSV **más reciente por la fecha del nombre**, lo copia a `storage/universes/swing_advances.csv` (o `swing_declines.csv`) y archiva la fuente en `data/object-store/processed/`.
- Las columnas de periodo (1D/5D/1M/3M `%Chg` / `Avg Vol`) se auto-detectan y se normalizan a los alias `pct_chg` / `avg_vol`; `Latest` → `price`, `%Change` → `pct_chg_1d`.
- El `universe_filter` de `strategies.json` es un string evaluable sobre esos alias: `"avg_vol > 1e6 and price > 5"`.
- El footer de Barchart se descarta automáticamente. Tope duro: 200 tickers post-filtro (se aplica en código además de `max_universe`).

```bash
# Actualizar el universo:
# 1. Exportar el CSV de Barchart a data/object-store/
# 2. Re-sembrar
bash scripts/seed_object_store.sh
```

---

## Operación semanal (correr un scan con universo nuevo)

1. **Docker Desktop debe estar corriendo** (`lean backtest` levanta un contenedor; si no está arriba, falla al iniciar).
2. Exportar el/los CSV de Barchart (advances y/o declines) a `data/object-store/`.
3. Re-sembrar el universo:
   ```bash
   source .venv/bin/activate
   bash scripts/seed_object_store.sh
   ```
4. Ajustar el rango de fechas en `trade-scanner/main.py` (bloque `else` de `prod`, ~líneas 39-40) a la fecha del CSV nuevo. `start_date` no afecta el warmup (se deriva aparte); moverlo cerca de `end_date` solo evita recorrer meses de más y generar resultados intermedios innecesarios — dejar ~5-7 días de margen por si `end_date` cae en fin de semana/feriado:
   ```python
   self.set_start_date(2026, 9, 6)   # end_date menos ~7 días de margen
   self.set_end_date(2026, 9, 13)    # fecha del CSV nuevo
   ```
5. Correr el backtest:
   ```bash
   lean backtest "trade-scanner"
   ```
6. Leer la watchlist en `storage/results/<estrategia>/latest.json` (ver sección Salida más abajo).

---

## Salida

Cada scan de una estrategia base escribe en el ObjectStore (`storage/results/` en local, transparente en cloud):

```
storage/results/<base>/<YYYYMMDD-HHMM>.json   # envelope: metadata + secciones long/short
storage/results/<base>/<YYYYMMDD-HHMM>.csv    # tabla plana (contrato PLAN §5)
storage/results/<base>/latest.json            # puntero fijo al último scan (lo consume el script host)
```

Columnas del CSV: `strategy, as_of, ticker, direction, partial_bar, price, time_frames_evaluated, sma_evidence, passed_rules, rules_passed_count`.

- `partial_bar=True` indica que el scan usó la barra del día en curso (variantes `market_close`).
- `as_of` es el timestamp UTC del snapshot; `sma_evidence` es JSON anidado `{tf: {period: {value, distance_pct, bucket}}}`.
- El archivo se escribe **siempre** (auditoría); los canales de notificación (`qc_notify` vía `NotificationManager` en cloud live, `host_email` vía script host con Gmail) se activan por entorno en `config/notifications.json`.

---

## Tests

```bash
# pytest DENTRO de la imagen LEAN (único modo válido: AlgorithmImports requiere el CLR)
bash scripts/run_tests.sh
```

Los tests usan `TradeBar`s sintéticos con valores de SMA verificables a mano, más tests de regresión sobre data local (`data/`) sembrada por los scripts de seed.

---

## Explorar el CSV de universo

```bash
python scripts/explore_universe.py data/object-store/<export-barchart>.csv
```

Produce un reporte de columnas, tipos, nulos, footer detectado, tickers no estándar y simulación de filtros de volumen.

---

## Estructura del workspace

```
trade-scanner/                   # raíz del workspace (aquí vive lean.json)
├── lean.json                    # configuración del engine y proveedor de datos
├── config/                      # fuente versionada de la config de negocio
│   ├── strategies.json          #   estrategias, entornos, thresholds
│   └── notifications.json       #   grupos, canales por entorno, suscriptores
├── universes/                   # fixtures estáticos (ej. sample_dev.csv)
├── data/
│   ├── equity/usa/              # zips de datos LEAN (gitignoreado)
│   └── object-store/            # drop-dir de CSVs Barchart (+ processed/)
├── storage/                     # ObjectStore local del CLI (montado en /Storage); gitignoreado
│   ├── config/                  #   sembrado por seed_object_store.sh
│   ├── universes/               #   swing_advances.csv / swing_declines.csv / fixtures
│   └── results/<base>/          #   watchlists generadas (json/csv/latest.json)
├── scripts/                     # seed, converters de datos, run_tests.sh
└── trade-scanner/               # proyecto LEAN (pusheable a QC)
    ├── main.py                  # L5: orquestación (schedule, warmup, universo, sink)
    ├── config.json              # SOLO parámetros del algoritmo: {"env": "dev"}
    ├── core/                    # L2–L4: symbol_data, timeframes, features, rules, pipeline, universe, output
    ├── strategies/              # composición declarativa de rules por estrategia
    └── tests/
```

---

## Documentación de desarrollo

| Archivo | Propósito |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude Code: flujo de trabajo, reglas y gotchas de LEAN |
| `PLAN.md` | Plan por etapas con estado y criterios de aceptación (fuente de verdad operativa) |
| `SPECS.md` | Especificación del producto: entidades, arquitectura, alcance |
| `.claude/decisions/` | ADRs (p. ej. ADR-002: `lean live` con broker requiere QC paid) |

---

## Notas sobre Alpaca free (Fase 1)

- Los datos son del feed IEX: el volumen es aproximadamente 2-3% del consolidado. Usar volumen relativo (vs su propia media), no absoluto, en filtros de liquidez.
- El feed tiene 15 min de delay: el scan de 15:30 refleja el mercado de ~15:15. Los resultados se marcan con `as_of` para trazabilidad.
- El warmup usa batch requests para respetar el límite de 100 calls/min; el scan en sí no consume la API (lee estado de indicadores ya calculados).
- Las credenciales de Alpaca viven en `.env` (gitignoreado), consumidas por los scripts host — nunca en `lean.json` ni en el repo.

**Upgrade limpio:** cambiar a Alpaca SIP o Polygon elimina el delay y el problema de volumen sin modificar código, solo `lean.json`.

---

## Fuera de alcance (V1)

- Descubrimiento dinámico del universo (se filtra el CSV provisto, no se genera).
- Ejecución de órdenes de ningún tipo.
- Earnings calendar, datos fundamentales, scoring avanzado.

## Licencia

MIT
