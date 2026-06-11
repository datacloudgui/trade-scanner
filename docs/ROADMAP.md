# ROADMAP — Screener de Acciones sobre LEAN

Estado actual: FASE 1 en desarrollo  
Última etapa cerrada: Etapa 5A  
Siguiente etapa: Etapa 5B  

---

# FASE 1 — Desarrollo local

## Etapa 0 — Entorno de desarrollo

Estado: pendiente  
Objetivo: máquina lista para correr LEAN CLI en local.

### Alcance
- [ ] Docker Desktop instalado y validado
- [ ] Python 3.11 vía pyenv
- [ ] Virtualenv .venv
- [ ] LEAN CLI instalado
- [ ] .venv/ en .gitignore
- [ ] .python-version versionado

### Done when
- [ ] docker run hello-world pasa
- [ ] python --version muestra 3.11.x
- [ ] lean --version pasa
- [ ] .venv/ ignorado y .python-version commiteado

---

## Etapa 1 — Workspace LEAN, cuentas y credenciales

Estado: completada  
Objetivo: entorno local LEAN corriendo en Docker con credenciales listas.

### Alcance
- [x] Credenciales Alpaca paper en .env
- [x] lean.json sin secretos reales
- [x] Proyecto LEAN trade-scanner
- [x] Smoke test con lean backtest

### Done when
- [x] lean backtest "trade-scanner" corre sin errores
- [x] .env gitignoreado
- [x] lean.json, .gitignore y proyecto commiteados

---

## Etapa 2 — Esqueleto del proyecto

Estado: completada  
Objetivo: walking skeleton end-to-end sin lógica de negocio.

### Alcance
- [x] Paquetes core/, strategies/, tests/
- [x] Sample data SPY para avanzar el reloj del backtest
- [x] config/strategies.json leído desde ObjectStore
- [x] ScheduledEvents por estrategia
- [x] Test Docker con AlgorithmImports

### Done when
- [x] Backtest avanza el reloj y dispara schedules
- [x] Config cargada desde ObjectStore
- [x] scripts/run_tests.sh verde
- [x] Paquetes importables
- [x] Sample data gitignoreada

---

## Etapa 3 — Exploración y contrato del archivo de entrada

Estado: completada  
Objetivo: CSV real perfilado y contratos de entrada/salida definidos.

### Alcance
- [x] Script explore_universe.py
- [x] Contrato CSV Barchart ratificado
- [x] Contrato ScanResult definido
- [x] strategies.json con environments y 4 estrategias
- [x] Seed de CSVs a ObjectStore
- [x] Archivo de fuentes procesadas

### Done when
- [x] Reporte de ambos CSVs generado
- [x] Contrato de entrada actualizado
- [x] Contrato de salida actualizado
- [x] ObjectStore sembrado correctamente
- [x] Backtest dispara las 4 estrategias

---

## Etapa 4 — UniverseSpec

Estado: completada  
Objetivo: cargar universos por estrategia desde ObjectStore con filtro declarativo.

### Alcance
- [x] core/universe.py
- [x] Alias normalizados de columnas
- [x] Footer strip
- [x] Filtro vía df.query()
- [x] Tope duro de 200 símbolos
- [x] refresh_universe() no-op
- [x] Tests de universo

### Done when
- [x] Backtest loguea conteo por estrategia
- [x] Tests de filtro, tope y CSV malformado verdes
- [x] Sin imports de AlgorithmImports

---

## Etapa 5A — TimeframeSpec + SymbolData

Estado: completada  
Objetivo: consolidators, indicadores y warmup plan construidos dinámicamente según timeframes declarados.

### Alcance
- [x] core/timeframes.py
- [x] Registro declarativo TimeframeSpec
- [x] Fórmula generalizada de warmup
- [x] plan_warmup() con presupuesto
- [x] core/symbol_data.py
- [x] Consolidators D/W/M
- [x] SMAs cableadas a consolidators
- [x] working_bar
- [x] Tests sintéticos

### Done when
- [x] Tests de consolidators e indicadores verdes
- [x] Solo se crean timeframes declarados
- [x] Warmup derivado por fórmula
- [x] Timeframe nuevo registrable sin tocar fórmula
- [x] Equivalencia daily directo vs minute encadenado
- [x] SymbolData no depende de instancia QCAlgorithm

---

## Etapa 5B — Warmup integrado + datos de muestra + validación de precisión

Estado: pendiente  
Objetivo: integrar warmup real en main.py, validar SMAs contra referencia externa y cerrar el criterio de precisión.

### Alcance
- [ ] Extender seed_sample_data.sh con ~5 símbolos diarios largos
- [ ] Incluir factor_files y map_files
- [ ] Crear un SymbolData por símbolo
- [ ] Calcular unión de timeframes por símbolo
- [ ] Warmup con self.history batch agrupado por resolución
- [ ] Log de profundidad, duración y ready/no-ready
- [ ] Guardrail warmup_budget
- [ ] Usar SPLIT_ADJUSTED
- [ ] Actualizar strategies.json prod con SMA 200 en marcos menores
- [ ] Generar validation/sma_validation_<fecha>.csv
- [ ] Validar manualmente contra TradingView o IBKR
- [ ] Congelar valores como fixture de regresión

### Done when
- [ ] Backtest con ≥5 símbolos completa warmup
- [ ] Se genera storage/validation/sma_validation_*.csv
- [ ] Desviaciones ≤0,25% registradas como fixture
- [ ] Test de regresión verde
- [ ] Viabilidad de SMA 200 en marco mayor documentada
- [ ] Backtest con config prod corre sin errores

---

## Etapa 6 — Features y Rules

Estado: pendiente  
Objetivo: implementar features reutilizables y reglas parametrizadas con evidencia.

### Alcance
- [ ] core/features.py
- [ ] position_vs_sma(n, tf)
- [ ] extension_pct(n, tf)
- [ ] day_change_pct()
- [ ] is_ready()
- [ ] core/rules.py
- [ ] AboveSMA(n, tfs)
- [ ] NotExtended(n, max_pct)
- [ ] Combinadores AND/NOT
- [ ] Evidencia por regla

### Done when
- [ ] Tests de features verdes
- [ ] Tests de rules verdes
- [ ] Features y rules solo leen SymbolData
- [ ] Respeto de capas verificado

---

## Etapa 7 — ScanPipeline + estrategias + schedule

Estado: pendiente  
Objetivo: correr estrategias V1 end-to-end en un solo nodo y producir ScanResult.

### Alcance
- [ ] core/pipeline.py
- [ ] Ranking top_n
- [ ] Evaluación de reglas
- [ ] Construcción de ScanResult
- [ ] strategies/swing_eod.py
- [ ] strategies/market_close.py
- [ ] Pipelines instanciados desde config
- [ ] Exclusión/log de símbolos no ready

### Done when
- [ ] Backtest ≥3 meses genera ScanResult reproducible
- [ ] market_close usa working bar
- [ ] partial_bar=True en scan intradía
- [ ] Símbolos con warmup incompleto son excluidos y logueados

---

## Etapa 8 — OutputSink y notificación por entorno

Estado: pendiente  
Objetivo: serializar resultados y seleccionar destino según entorno sin mezclar lógica de negocio.

### Alcance
- [ ] core/output.py
- [ ] Serialización CSV
- [ ] Serialización JSON
- [ ] Output local en ObjectStore/carpeta de resultados
- [ ] Logging local
- [ ] NotificationManager / self.notify para QC cloud live
- [ ] Switch por self.live_mode + entorno

### Done when
- [ ] Backtest produce CSV/JSON legibles
- [ ] Switch de destino está aislado en output.py
- [ ] No hay ramas de negocio por entorno fuera de output.py

---

## Etapa 9 — Validación integral FASE 1

Estado: pendiente  
Objetivo: cerrar FASE 1 cumpliendo los criterios globales de V1 local.

### Prerrequisito bloqueante
- [ ] Resolver restricción de credenciales QC / módulo Alpaca:
  - [ ] Opción A: QC Researcher
  - [ ] Opción B: compilar módulo Alpaca open source
  - [ ] Opción C: descarga directa REST Alpaca para históricos

### Alcance
- [ ] Backtest 6–12 meses
- [ ] Revisión manual de watchlists
- [ ] Sesión live paper local
- [ ] Verificación de ambos scans
- [ ] Working bar real
- [ ] Salida y logs correctos
- [ ] Cambio de provider solo vía lean.json

### Done when
- [ ] Watchlists revisadas manualmente
- [ ] Una sesión live paper completa validada
- [ ] Cambio Alpaca ↔ QC verificado sin tocar código
- [ ] Checklist global firmado
- [ ] FASE 1 cerrada

---

# FASE 2 — Validación en servidor

Estado: futura  
Objetivo: ejecutar el mismo proyecto de forma desatendida en VPS.

### Alcance inicial
- [ ] VPS cloud
- [ ] Docker + LEAN CLI
- [ ] Seed de ObjectStore
- [ ] Ejecución programada
- [ ] Logs persistentes
- [ ] Notificaciones operativas
- [ ] Monitoreo básico

### Done when
- [ ] El screener corre desatendido
- [ ] Genera watchlists en horario real
- [ ] Notifica resultados
- [ ] No requiere cambios de código frente a FASE 1

---

# Post V1

## Universo
- [ ] Fuente automática de market movers
- [ ] refresh_universe() real
- [ ] Universos dinámicos
- [ ] Persistencia histórica de universos

## Estrategias
- [ ] Reglas específicas para top losers
- [ ] Pullback strategy
- [ ] ATR-based extension filter
- [ ] Ranking avanzado
- [ ] Market breadth

## Datos fundamentales
- [ ] Earnings calendar
- [ ] Filtros fundamentales
- [ ] Scoring compuesto

## Ejecución futura
- [ ] Módulo de órdenes
- [ ] Position sizing
- [ ] Risk management
- [ ] Paper trading con órdenes
- [ ] Live trading real

---

# Definition of Done global de FASE 1

- [ ] Warmup preciso: SMAs por timeframe cuadran con referencia
- [ ] Watchlists reproducibles con evidencia por candidato
- [ ] Schedules disparan según calendario de mercado en un solo nodo
- [ ] Working bar funcional en scan intradía
- [ ] Cambio de fuente de datos tocando solo lean.json
- [ ] Salida/notificación por entorno aislada en output.py