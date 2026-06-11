# SPECS — Screener de Acciones sobre LEAN

**Versión:** 0.1 (V1) · **Fecha:** 2026-06-10 · **Estado:** borrador para desarrollo

---

## 1. Contexto

**Problema.** Los traders manejan un universo de ideas (tickers) demasiado amplio para revisar manualmente. Necesitan filtrarlo con criterios técnicos (y a futuro fundamentales) de forma sistemática, repetible y programada, en los momentos del día que cada estrategia exige.

**Solución.** Un screener construido sobre el motor LEAN que carga un universo desde CSV, mantiene indicadores precisos en tres marcos de tiempo (día, semana, mes), valida reglas por estrategia en horarios programados, y entrega una watchlist con evidencia de por qué cada ticker pasó los filtros.

**Usuario.** Traders discrecionales que operan una o más estrategias (swing, earnings, etc.) y usan el screener como primer filtro antes de su análisis manual. El screener **no decide ni ejecuta**: propone candidatos.

---

## 2. Stack tecnológico

| Componente | Elección |
|---|---|
| Engine | LEAN open source (Python 3.11) |
| Lenguaje | Python |
| IDE / Dev | VSCode + LEAN CLI (local desde día uno) |
| Python host | pyenv + Python 3.11; virtualenv `.venv` por proyecto |
| Contenerización | Docker Desktop; imagen oficial `quantconnect/lean` para engine y tests |
| Ejecución | `lean backtest` / `lean live` vía CLI |
| Datos Fase 1 | Alpaca free (IEX, 15 min delay, 100 calls/min) |
| Datos backtest | Flexible: `lean data download` (Alpaca u otro provider soportado) |
| Notificación | `NotificationManager` (QC cloud) / archivo + sink local |

**Principio rector:** el código solo habla con la API de `QCAlgorithm`. La fuente de datos, el broker y el entorno son configuración externa (`lean.json` / parámetros), nunca lógica.

---

## 3. Arquitectura por capas

```
┌─────────────────────────────────────────────────────────┐
│ L6 · EJECUCIÓN                                          │
│   lean backtest | lean live (Docker quantconnect/lean)  │
│   Fase 1: local · Fase 2: VPS · portable a QC cloud     │
├─────────────────────────────────────────────────────────┤
│ L5 · ORQUESTACIÓN (main.py — QCAlgorithm)               │
│   initialize → carga config → carga universos →         │
│   crea SymbolData + warmup → registra ScheduledEvents   │
│   Un solo nodo, todas las estrategias por schedule      │
├─────────────────────────────────────────────────────────┤
│ L4 · ESTRATEGIAS (ScanPipeline)                         │
│   universo asignado + lista de Rules + schedule         │
│   V1: swing_eod (fin de día) · market_close (15:30 ET)  │
├─────────────────────────────────────────────────────────┤
│ L3 · FEATURES / PRIMITIVAS (LEAN-nativas, reutilizables)│
│   Cómputos reutilizables sobre SymbolData               │
│   Features: posición vs SMA(n) por timeframe,           │
│   extensión vs SMA(8), pullback, % cambio, barra        │
│   parcial del día (working bar)                         │
├─────────────────────────────────────────────────────────┤
│ L2 · DATOS DERIVADOS (SymbolData)                       │
│   SymbolData: consolidators D/W/M + indicadores         │
│   TradeBarConsolidator diario · Calendar.WEEKLY ·       │
│   Calendar.MONTHLY · working_bar                        │
│   Warmup derivado de timeframes declarados (PLAN §4)    │
├─────────────────────────────────────────────────────────┤
│ L1 · DATOS Y CONFIG EXTERNA                             │
│   lean.json (provider: Alpaca | QC cloud | otro)        │
│   CSV de universo(s) vía ObjectStore (portable)         │
│   Parámetros de estrategia (umbrales, horarios)         │
└─────────────────────────────────────────────────────────┘
```

**Reglas entre capas:**
- L3 y L4 nunca consultan la fuente de datos directamente: consumen el estado de `SymbolData`, que el engine mantiene actualizado.
- L4 no calcula indicadores: solo evalúa predicados (Rules) sobre features ya computadas. El scan es lectura, no cómputo.
- L5 es el único lugar con `self.schedule`, `self.history`, `self.add_equity`, `self.notify`.

---

## 4. Entidades core

| Entidad | Responsabilidad | Notas de implementación |
|---|---|---|
| `UniverseSpec` | Lista de símbolos de una estrategia, cargada de CSV + filtro simple de columnas (ej. `price > 5`, `avg_volume > X`). Expone `refresh_universe()` (no-op en V1, punto de extensión). | CSV leído vía ObjectStore para portabilidad local/cloud. Máx ~200 tickers por universo. Cada estrategia puede tener su variante de universo. |
| `SymbolData` | Estado técnico de un símbolo: consolidators D/W/M, indicadores registrados, barra parcial del día. | Patrón idiomático LEAN. SMAs vía `register_indicator` sobre cada consolidator. Warmup en construcción. |
| `Feature` | Cómputo reutilizable y nombrado sobre `SymbolData`. Ej.: `position_vs_sma(n, timeframe)`, `extension_pct(n)`, `is_pullback()`, `day_change_pct()`. | Funciones/propiedades puras de lectura. Compartidas por todas las estrategias. |
| `Rule` | Predicado parametrizado que combina features y devuelve pasa/no-pasa + evidencia. Ej.: `AboveSMA(20, ["D","W","M"])`, `NotExtended(sma=8, max_pct=0.10)`. | Componibles con AND/NOT. Parámetros desde config, no hardcoded. |
| `ScanPipeline` | Una estrategia: `UniverseSpec` + lista de `Rules` + `ScheduleSpec`. Ejecuta el scan y produce `ScanResult`. | V1: `swing_eod`, `market_close`. |
| `ScheduleSpec` | Cuándo corre cada pipeline. Ej.: `swing_eod` → tras el cierre; `market_close` → 30 min antes del cierre. | Implementado con `self.schedule.on(date_rules, time_rules)` sobre el calendario del mercado. |
| `ScanResult` | Watchlist: lista de candidatos con evidencia por regla (valores de SMAs, % extensión, % cambio, timestamp `as_of`, flag `partial_bar`). | Serializable a CSV/JSON. |
| `OutputSink` | Persistencia + notificación según entorno: ObjectStore + `NotificationManager` en QC cloud; archivo CSV/JSON (+ log) en local/VPS. | Selección por detección de entorno (`self.live_mode` + config), no por ramas de lógica de negocio. |

---

## 5. Decisiones técnicas consolidadas

1. **Barras y SMAs de semana y mes se calculan dentro de LEAN** con la mejor configuración del framework: `TradeBarConsolidator(Calendar.WEEKLY)` y `Calendar.MONTHLY`, con los indicadores registrados sobre el consolidator. Nada de resampling manual con pandas.
2. **Warmup explícito y verificable.** Al crear cada `SymbolData`, se pide la historia necesaria (`self.history`) y se empuja a los consolidators. La profundidad se deriva dinámicamente de los timeframes declarados (ver fórmula en PLAN.md §4): `D:n → n+5` barras diarias; `W:n → n×5+10`; `M:n → n×21+21`. Ej.: `M:[20]` → ~441 barras. El número no es fijo.
3. **SMAs estables intradía.** Los indicadores W/M solo se actualizan al cierre de su barra (comportamiento natural del consolidator). En el scan intradía, el precio actual se compara contra medias del último cierre.
4. **Barra parcial del día en el scan intradía.** Suscripción en `Resolution.MINUTE`; el OHLC en curso del día se lee del `working_bar` del consolidator diario (mecanismo LEAN-nativo, agnóstico de la fuente). El `ScanResult` la marca como `partial_bar=True` con su `as_of`.
5. **Un nodo, múltiples estrategias.** Un solo algoritmo registra todos los `ScheduledEvents`. Las estrategias comparten los `SymbolData` de los símbolos que tengan en común (un símbolo = un `SymbolData`, aunque esté en varios universos).
6. **Fuente de datos = configuración.** Cambiar Alpaca ↔ QC cloud ↔ otro provider solo toca `lean.json` (y credenciales). El algoritmo no contiene referencias a la fuente.
7. **Portabilidad local/cloud.** Solo API `QCAlgorithm`, universos vía ObjectStore, parámetros vía `self.get_parameter`. El mismo proyecto debe correr en LEAN CLI local y en QC cloud sin cambios de código.
8. **Solo escaneo en V1.** Cero órdenes. El diseño deja el punto de extensión: un `ScanResult` validado por expertos podrá alimentar un módulo de ejecución futuro sin reestructurar las capas (L4 produce candidatos; un futuro L4.5 los consumiría).

---

## 6. Alcance V1

1. Cargar universo principal desde **archivo CSV**, aplicar un **filtro simple** sobre sus columnas y extraer los tickers (máx ~200). Soporte para variantes de universo por estrategia.
2. Conexión a datos **live o backtest** con **Alpaca o QuantConnect cloud**, configurable **solo modificando `lean.json`**.
3. **Programación por horas del día**: ej. *Swing* al final del día; *Cierre de mercado* 30 min antes del cierre. Todas las estrategias en un mismo nodo vía schedule.
4. **Features reutilizables** entre estrategias (ej. detección de posición respecto a SMA), implementadas con indicadores y consolidators de LEAN.
5. **Filtro técnico en tres marcos de tiempo** (día, semana, mes) sobre el universo.
6. **Archivo de salida + notificación según el ambiente**: `NotificationManager` en QC cloud; archivo/log en local.

### Estrategia de referencia V1 (refinada)

**`swing_eod`** — corre tras el cierre:
1. Universo: CSV swing (≤200), filtro simple de liquidez/precio del propio CSV.
2. Ranking interno: top N por `day_change_pct` (gainers; losers como variante con reglas propias a definir).
3. Regla: precio > SMA20 en D, W y M.
4. Regla: NO extendida — `(close − SMA8_D) / SMA8_D ≤ umbral` (umbral parametrizado, default propuesto 10%, **a calibrar**).
5. Salida: watchlist con evidencia.

**`market_close`** — corre 15:30 ET (mismas reglas que swing_eod):
- Usa la barra parcial del día (working bar) como precio/OHLC actual.
- SMAs del último cierre (decisión 3). Resultado marcado provisional.

---

## 7. Fases

**FASE 1 — Desarrollo local ($0/mes)**
- LEAN CLI + VSCode en máquina local, Docker.
- Datos: Alpaca free (100 calls/min, IEX, 15 min delay).
- Backtest + paper trading local (paper solo valida el flujo de datos live; no ejecuta órdenes).

**FASE 2 — Validación en servidor (~$25/mes)**
- LEAN self-hosted en VPS cloud, mismo proyecto sin cambios de código.
- Datos: Alpaca free (igual que Fase 1).
- Paper trading live en servidor; salida y notificación operando de forma desatendida.

---

## 8. Fuera de alcance (V1)

- **Definición/descubrimiento del universo inicial**: solo se filtra un CSV provisto. La fuente del CSV de "best market movers" está **A DEFINIR** (ver §11).
- **Ejecución de órdenes**: ninguna orden, ni paper. Se habilitará tras validación con expertos.
- Datos fundamentales, earnings calendar, scoring/ranking avanzado, persistencia histórica de scans (candidatos a V2).

---

## 9. Restricciones

- Desarrollo local de algoritmos con **LEAN CLI** exclusivamente.
- El código **solo habla con la API de `QCAlgorithm`** (sin SDKs de brokers/datos embebidos).
- **Portable** a QuantConnect cloud o local sin cambios.
- **Todas las estrategias corren en un mismo nodo** con schedule.
- **Flexibilidad en fuentes de datos**: la fuente es configuración externa (`lean.json`).
- Universo fijo en primeras versiones, con `refresh_universe()` como punto de extensión.

---

## 10. DONE WHEN (criterios de aceptación)

El V1 está terminado cuando, en un mismo proyecto LEAN:

1. **Carga y warmup precisos.** `lean backtest` carga el universo desde CSV (≤200 símbolos), construye los `SymbolData` y completa el warmup; las SMA20 D/W/M de una muestra de símbolos **cuadran contra valores de referencia** (test de validación contra plataforma de charting acordada).
2. **Filtrado correcto.** Las reglas de `swing_eod` producen una watchlist reproducible en backtest sobre fechas conocidas, con evidencia por candidato.
3. **Schedule operativo.** `swing_eod` y `market_close` disparan a sus horas configuradas (verificado en backtest por timestamps y en `lean live` paper local).
4. **Barra parcial funcional.** El scan de `market_close` reporta OHLC del día en curso vía working bar, marcado `partial_bar=True`.
5. **Fuente intercambiable.** Cambiar entre datos Alpaca y QC cloud requiere tocar únicamente `lean.json`/credenciales.
6. **Salida por entorno.** En local se genera archivo CSV/JSON; en QC cloud se dispara `NotificationManager`. Sin ramas de negocio por entorno.

---

## 11. Pendientes y riesgos

**Pendientes de definición (bloquean calibración, no el desarrollo):**
- Fuente del CSV de universo "best market movers" (≤200).
- Umbral de "extendida" (% sobre SMA8 vs alternativa con ATR).
- Definición operativa de *pullback* (feature prevista, sin regla en V1 hasta definirla).
- Reglas específicas para *top losers*.
- Plataforma de referencia para validar SMAs W/M (convención de semana de `Calendar.WEEKLY`: lunes→domingo, cierre efectivo viernes).

**Riesgos conocidos:**
- **Alpaca free = IEX**: volumen muy subestimado (usar volumen relativo, no absoluto, en filtros) y 15 min de delay (el scan de 15:30 ve ~15:15; documentado en `as_of`).
- **Rate limit 100 calls/min**: warmup de 200 símbolos debe ir en batch/escalonado; el scan en sí no consume API (lee estado).
- **Memoria/CPU con 200 símbolos en `Resolution.MINUTE`**: viable en un nodo, pero medir en Fase 1 antes del VPS.
- **Equivalencia de barras W/M** con la plataforma del trader: validar antes de confiar en los filtros (criterio DONE #1).
