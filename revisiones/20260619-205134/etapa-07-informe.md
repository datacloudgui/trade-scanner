**Hallazgos**

**Corrección Funcional / Arquitectura**

1. [main.py:47](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:47), [main.py:55](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:55), [main.py:379](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:379) — **ALTO**  
   `main.py` carga universos por estrategia, pero los colapsa en `tickers` global y luego cada `ScanPipeline` escanea `self.symbol_data` completo. En `prod`, `swing_eod`/`market_close` deberían escanear `swing_advances` y las variantes short `swing_declines` ([config/strategies.json:20](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:20)-[51](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:51)). Esto rompe la entidad “UniverseSpec = lista de símbolos de una estrategia” y la suposición de Etapa 7 D7.5 de universos long/short disjuntos.  
   **Sugerencia:** conservar `symbols_by_strategy[name] = set(loaded)` en `initialize()` y pasar a `pipeline.scan()` un `symbol_data_map` filtrado por esa estrategia, o hacer que `ScanPipeline` reciba su universo resuelto y filtre internamente. Añadir test de integración con universos long/short disjuntos.

2. [main.py:65](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:65), [main.py:72](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:72), [main.py:136](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:136), [pipeline.py:105](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:105) — **MEDIO**  
   Las series referenciadas por las rules se construyen independientemente del `plan_warmup`. Si el presupuesto excluye por error una serie usada por una rule, `SymbolData` no crea esa SMA, pero el pipeline se construye igual; en el scan, `sd.is_ready(tf, p)` termina en `KeyError`, no en exclusión controlada ni error de configuración en `initialize()`.  
   **Sugerencia:** validar en `initialize()` que `composition.series(side)` esté contenida en las series incluidas por el plan para todos los símbolos de esa estrategia. Si falta una serie referenciada, fallar con `ValueError` claro antes de registrar schedules.

**Tests / Trazabilidad**

3. [test_pipeline.py:160](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:160), [test_pipeline.py:181](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:181), [test_strategies.py:160](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_strategies.py:160) — **MEDIO**  
   La suite cubre `ScanPipeline` con mapas sintéticos ya filtrados y cubre el registro de estrategias, pero no cubre el wiring real `UniverseSpec -> main.py -> pipeline.scan`. Por eso no detecta el hallazgo ALTO de mezcla de universos.  
   **Sugerencia:** agregar un test de integración L5 con ObjectStore mock: `swing_eod` carga `AAA`, `swing_eod_short` carga `BBB`, y verificar que cada pipeline recibe solo su mapa.

4. [.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:20](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:20), [.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:52](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:52) — **BAJO**  
   El backtest ≥3 meses y un candidato real con `working_bar` intradía vivo están explícitamente diferidos a Etapa 9 por datos minute. No es un bug de código, pero la trazabilidad de SPECS DW#4 queda parcial en E7: hay unit tests y probe SPY, pero el candidato IBM documentado ejercita fallback a `close("D")`, no precio intradía vivo.  
   **Sugerencia:** mantenerlo como pendiente de Etapa 9 y convertirlo en prueba/evidencia obligatoria cuando exista data minute multi-símbolo.

**Reglas Duras / API LEAN**

No encontré órdenes ni gestión de portfolio en el código activo (`market_order`, `set_holdings`, `liquidate`, `buy/sell`). L3/L4 (`features`, `rules`, `pipeline`, `strategies`) no importan `AlgorithmImports`. Verifiqué contra stubs locales de LEAN que las APIs usadas por E7 existen en snake_case: `add_equity`, `set_warm_up`, `schedule.on`, `date_rules.every_day`, `time_rules.before_market_close/after_market_close`, `subscription_manager.add_consolidator`, `object_store.read/save`, `utc_time`, `TradeBarConsolidator`, `Calendar.WEEKLY/MONTHLY`, `working_data`, `data_consolidated`, `scan`.

**Trazabilidad Etapa 7**

| Criterio | Código | Test/evidencia | Estado |
|---|---|---|---|
| Precio único: `reference_price`, `position_vs_sma(price)`, snapshot 1 precio | [features.py:96](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:96), [features.py:141](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:141), [features.py:192](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:192) | [test_features.py:105](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:105), [test_features.py:250](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:250), [test_features.py:533](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:533) | ✅ |
| `day_change_pct` ranking | [features.py:111](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:111) | [test_features.py:163](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:163), [test_pipeline.py:176](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:176) | ✅ |
| Composición declarativa + mirror long/short | [swing_eod.py:18](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/swing_eod.py:18), [market_close.py:13](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/market_close.py:13), [__init__.py:10](/Users/guille/Documents/quant/trade-scanner/trade-scanner/strategies/__init__.py:10) | [test_strategies.py:91](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_strategies.py:91), [test_strategies.py:146](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_strategies.py:146) | ✅ |
| Pipeline gate B, ranking, snapshot, cascada, `ScanResult` | [pipeline.py:86](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:86) | [test_pipeline.py:160](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:160), [test_pipeline.py:233](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:233), [test_pipeline.py:290](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pipeline.py:290) | ✅ unit / ⚠️ integración |
| Integración L5 minute + pipelines + schedule | [main.py:86](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:86), [main.py:136](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:136), [main.py:183](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:183), [main.py:379](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:379) | logs existentes + bitácora T6 | ⚠️ por mezcla de universos |
| Backtest reproducible + evidencia | [.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:20](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-07-t6-decisiones-y-pendientes.md:20) | bitácora: 2 corridas, 178 passed | ✅ dev / ⏭️ ≥3m a E9 |

No ejecuté `scripts/run_tests.sh` ni `lean backtest` en esta revisión: el run era de solo lectura y esos comandos pueden escribir cachés/artefactos. Usé inspección estática, stubs locales y evidencia versionada/existente.

**Resumen Ejecutivo**

1. Corregir la mezcla de universos: ahora cada pipeline escanea todos los símbolos cargados.
2. Añadir un test L5 que pruebe universos long/short disjuntos hasta `pipeline.scan`.
3. Validar que las series referenciadas por rules no hayan sido excluidas por `plan_warmup`.
4. Mantener explícito el pendiente E9: backtest ≥3 meses y candidato con working bar intradía vivo.
5. Re-ejecutar suite/backtest en entorno con escritura controlada tras los cambios.