# Screener de Acciones sobre LEAN

Screener multi-estrategia construido sobre el motor [LEAN](https://github.com/QuantConnect/Lean) de QuantConnect. Carga un universo de tickers desde CSV, mantiene indicadores técnicos en múltiples marcos de tiempo y ejecuta filtros programados para producir watchlists con evidencia. Solo escanea: no coloca órdenes.

---

## Qué hace

- Carga un universo de hasta 200 tickers desde un CSV con un filtro declarativo de columnas.
- Mantiene indicadores (SMA y otros) en los timeframes que cada estrategia declara (día, semana, mes, u otros), con warmup preciso usando consolidators nativos de LEAN.
- Ejecuta estrategias en horarios programados (ej. al cierre del día, 30 min antes del cierre).
- Todas las estrategias corren en un solo nodo.
- Emite una watchlist por estrategia con evidencia: por qué pasó cada ticker (distancia a SMAs, % extensión, % cambio del día).
- Portable entre entorno local y QuantConnect cloud cambiando solo `lean.json`.

## Estrategias V1

| Estrategia | Horario | Descripción |
|---|---|---|
| `swing_eod` | Tras el cierre | Top movers del día que están sobre SMA20 en D/W/M y no extendidos vs SMA8 |
| `market_close` | 15:30 ET | Mismas reglas con barra parcial del día en curso |

## Stack

| Componente | Tecnología |
|---|---|
| Engine | LEAN open source (Python 3.11) |
| Ejecución | `lean backtest` / `lean live` vía CLI (Docker) |
| Datos | Alpaca free (Fase 1) · configurable en `lean.json` |
| IDE | VSCode + LEAN CLI |

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado y corriendo
- Python 3.11+ con `pip`
- Cuenta en [QuantConnect](https://www.quantconnect.com) (gratuita)
- Cuenta en [Alpaca](https://alpaca.markets) con API key/secret (paper trading)

---

## Setup inicial

```bash
# 1. Instalar LEAN CLI
pip install lean

# 2. Inicializar el workspace
mkdir screener-workspace && cd screener-workspace
lean init          # descarga lean.json y data/ de muestra
lean login         # autenticar con QuantConnect

# 3. Clonar el proyecto dentro del workspace
git clone <repo-url> Screener

# 4. Configurar credenciales de Alpaca
#    Editar lean.json y agregar las claves de Alpaca (ver lean.json.example)
#    Nunca comitear credenciales reales

# 5. Sembrar el CSV de universo en ObjectStore
bash Screener/scripts/seed_object_store.sh

# 6. Smoke test
lean backtest "Screener"
```

---

## Configuración de estrategias

Todas las opciones viven en `Screener/config.json`. No hay valores hardcodeados en el código.

```json
{
  "parameters": {
    "strategies": {
      "swing_eod": {
        "universe": "swing",
        "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
        "schedule": "after_close",
        "top_n": 50,
        "max_extension_pct": 0.10
      },
      "market_close": {
        "universe": "swing",
        "timeframes": { "D": [8, 20], "W": [20], "M": [20] },
        "schedule": "before_close_30m",
        "top_n": 50,
        "max_extension_pct": 0.10
      }
    }
  }
}
```

**Cambiar fuente de datos:** solo editar el proveedor en `lean.json` (Alpaca → QC cloud u otro soportado). El código no cambia.

---

## Universo de tickers

El universo se carga desde un CSV en `universes/`. Columnas mínimas:

```csv
ticker,price,avg_dollar_volume
AAPL,232.5,1200000000
MSFT,415.0,950000000
```

Columnas adicionales son ignoradas a menos que el filtro declarativo las use. El filtro se define en `config.json` como string evaluable: `"price > 5 and avg_dollar_volume > 5e6"`. Tope duro: 200 tickers post-filtro.

Para actualizar el universo:
```bash
# 1. Reemplazar universes/swing.csv
# 2. Re-sembrar en ObjectStore
bash Screener/scripts/seed_object_store.sh
```

---

## Salida

Cada ejecución de una estrategia produce un archivo en `storage/results/` (ObjectStore local del CLI):

```
strategy,as_of,ticker,partial_bar,day_change_pct,sma20_d,dist_sma20_d_pct,sma20_w,...,passed_rules
swing_eod,2026-06-09T16:05:00Z,NVDA,false,4.32,105.2,3.1,98.4,...,"AboveSMA20_D|AboveSMA20_W|AboveSMA20_M|NotExtended"
```

- `partial_bar=true` indica que el scan usó la barra del día en curso (market_close).
- `as_of` es el timestamp UTC del snapshot.
- `passed_rules` lista las reglas que el ticker cumplió.

En QuantConnect cloud live, la salida se envía además vía `NotificationManager` (configurar destino en `config.json`).

---

## Tests

```bash
# Correr pytest DENTRO de la imagen LEAN (único modo válido para tests con AlgorithmImports)
bash Screener/scripts/run_tests.sh
```

Los tests usan `TradeBar`s sintéticos con valores de SMA verificables a mano. No dependen de datos reales ni de conexión externa.

---

## Explorar el CSV de universo

```bash
python Screener/scripts/explore_universe.py universes/swing.csv
```

Produce un reporte de columnas, tipos, nulos, duplicados, tickers inválidos y distribución de price/volumen.

---

## Estructura del proyecto

```
screener-workspace/
├── lean.json                    # configuración del engine y proveedor de datos
├── data/                        # datos locales gestionados por LEAN CLI
├── storage/                     # ObjectStore local del CLI (montado en /Storage); gitignoreado
│       ├── config/              # strategies.json sembrado por seed_object_store.sh
│       ├── universes/           # CSVs sembrados por seed_object_store.sh
│       └── results/             # watchlists generadas
├── Screener/
│   ├── main.py                  # algoritmo QCAlgorithm (orquestador)
│   ├── config.json              # parámetros de estrategias
│   ├── core/
│   │   ├── timeframes.py        # D/W/M → consolidators + cálculo de warmup
│   │   ├── symbol_data.py       # indicadores y working bar por símbolo
│   │   ├── features.py          # cómputos reutilizables (posición vs SMA, extensión, etc.)
│   │   ├── rules.py             # reglas componibles con evidencia
│   │   ├── pipeline.py          # ScanPipeline y ScanResult
│   │   ├── universe.py          # carga y filtrado del CSV
│   │   └── output.py            # serialización y notificación por entorno
│   ├── strategies/
│   │   ├── swing_eod.py
│   │   └── market_close.py
│   ├── tests/
│   └── scripts/
└── universes/
    └── swing.csv
```

---

## Documentación de desarrollo

| Archivo | Propósito |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude Code: flujo de trabajo, reglas y gotchas de LEAN |
| `PLAN.md` | Plan por etapas con estado y criterios de aceptación |
| `SPECS.md` | Especificación del producto: entidades, arquitectura, alcance |

---

## Notas sobre Alpaca free (Fase 1)

- Los datos son del feed IEX: el volumen es aproximadamente 2-3% del consolidado. Usar volumen relativo (vs su propia media), no absoluto, en filtros de liquidez.
- El feed tiene 15 min de delay: el scan de 15:30 refleja el mercado de ~15:15. Los resultados se marcan con `as_of` para trazabilidad.
- El warmup de 200 símbolos usa batch requests para respetar el límite de 100 calls/min; el scan en sí no consume la API (lee estado de indicadores ya calculados).

**Upgrade limpio:** cambiar a Alpaca SIP o Polygon elimina el delay y el problema de volumen sin modificar código, solo `lean.json`.

---

## Fuera de alcance (V1)

- Descubrimiento dinámico del universo (se filtra el CSV provisto, no se genera).
- Ejecución de órdenes de ningún tipo.
- Earnings calendar, datos fundamentales, scoring avanzado.

## Licencia

MIT
