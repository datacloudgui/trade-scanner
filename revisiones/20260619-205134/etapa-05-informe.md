**Resultado**
Revisión solo lectura de Etapa 5 completada. No modifiqué archivos. No pude ejecutar `bash scripts/run_tests.sh`: Docker no permitió acceder al socket. Tampoco corrí `lean backtest` porque generaría artefactos en `backtests/`/`storage/`, fuera del run estrictamente read-only.

**Hallazgos**

**Alineación / Tests**
1. [etapa-05b.md:159](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-05b.md:159), [PLAN.md:289](/Users/guille/Documents/quant/trade-scanner/PLAN.md:289), [SPECS.md:168](/Users/guille/Documents/quant/trade-scanner/SPECS.md:168) — **ALTO**  
   Etapa 5B no está cerrada contra su propio Done when: siguen pendientes la validación manual ≤0,25% y el fixture autoritativo + test de regresión. El test actual se declara explícitamente “INTERINO” y “NO es la validación manual” en [test_sma_regression.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_sma_regression.py:1).  
   Sugerencia: mantener Etapa 5B abierta hasta congelar valores SPY/AAPL/IBM D/W/M contra TradingView/IBKR y agregar un test no-interino que falle si divergen.

2. [test_sma_regression.py:70](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_sma_regression.py:70), [test_t5_stooq_crosscheck.py:81](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_t5_stooq_crosscheck.py:81) — **ALTO**  
   Los tests de validación crítica se saltan si faltan datos en `data/`, pero `data/` está ignorado por git. En un checkout limpio, la suite puede quedar “verde” sin ejercer el criterio central de Etapa 5.  
   Sugerencia: mover fixtures mínimos a `tests/fixtures/` o añadir un job/preflight de Etapa 5 que falle si faltan los datos requeridos.

**Bugs / Reproducibilidad**
3. [seed_sample_data.sh:52](/Users/guille/Documents/quant/trade-scanner/scripts/seed_sample_data.sh:52), [seed_sample_data.sh:61](/Users/guille/Documents/quant/trade-scanner/scripts/seed_sample_data.sh:61) — **ALTO**  
   El script descarga `aapl.zip`/`ibm.zip` desde el repo público de LEAN, pero luego escribe factor files neutros como si esos zips vinieran del converter Stooq split-only. Eso no reproduce la data validada de T6.1 y puede mezclar fuente/precio/factor de forma incoherente.  
   Sugerencia: separar “seed LEAN sample” de “preparar Stooq validation data”, o hacer que el script ejecute `stooq_to_lean.py` con CSVs explícitos y falle si no están.

**Arquitectura / Corrección funcional**
4. [main.py:415](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:415), [etapa-05a.md:130](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-05a.md:130) — **MEDIO**  
   `_build_requirements()` calcula una unión global de timeframes para todos los símbolos. Etapa 5A define `requirements` como la unión de estrategias que usan ese símbolo. Hoy no rompe porque las estrategias activas comparten requisitos, pero si divergen por universo/timeframe, habrá series extra, warmup extra y posibles fríos falsos.  
   Sugerencia: construir `requirements_by_symbol` al cargar universos por estrategia y pasar a cada `SymbolData` solo su unión real.

**Documentación / Trazabilidad**
5. [docs/DEVLOG.md:37](/Users/guille/Documents/quant/trade-scanner/docs/DEVLOG.md:37), [docs/ROADMAP.md:140](/Users/guille/Documents/quant/trade-scanner/docs/ROADMAP.md:140), [README.md:72](/Users/guille/Documents/quant/trade-scanner/README.md:72) — **BAJO**  
   Hay documentación contradictoria: `DEVLOG` dice que Etapa 5 fue finalizada con validación manual, mientras `PLAN.md` la deja parcial; `ROADMAP` sigue marcando 5B pendiente; `README` describe configuración antigua y afirma que los tests no dependen de datos reales.  
   Sugerencia: alinear esos documentos con `PLAN.md`, que tiene precedencia.

**API LEAN**
No encontré órdenes en el código actual de `trade-scanner/`. La implementación de Etapa 5 usa APIs LEAN reales y coherentes: `set_warm_up`, `add_equity`, `subscription_manager.add_consolidator`, `TradeBarConsolidator(Calendar.WEEKLY/MONTHLY)`, `data_consolidated`, `scan`, `working_data`, `object_store.save` y `schedule.on`. Contrasté contra la documentación oficial de QuantConnect: [Warm Up Periods](https://www.quantconnect.com/docs/v2/writing-algorithms/historical-data/warm-up-periods), [Calendar Consolidators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/calendar-consolidators), [Time Period Consolidators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/time-period-consolidators), [Count Consolidators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/count-consolidators), [Object Store](https://www.quantconnect.com/docs/v2/writing-algorithms/object-store) y [Scheduled Events](https://www.quantconnect.com/docs/v2/writing-algorithms/scheduled-events).

**Trazabilidad Etapa 5**

| Criterio | Código | Test/evidencia | Estado |
|---|---|---|---|
| Fórmula warmup D/W/M | [timeframes.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/timeframes.py:52) | `test_timeframes.py` | ✅ impl/test |
| `SymbolData` con consolidators D/W/M y `scan()` | [symbol_data.py:48](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/symbol_data.py:48), [symbol_data.py:76](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/symbol_data.py:76) | `test_symbol_data.py` | ✅ impl/test |
| Warmup integrado en `main.py` | [main.py:202](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:202), [main.py:230](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:230) | logs históricos; no re-ejecutado | ⚠️ no verificado en run |
| Gate ruta engine vs manual | [main.py:257](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:257) | logs históricos | ⚠️ no re-ejecutado |
| CSV validación K=5 | [main.py:333](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:333) | artefactos en `storage/validation` | ⚠️ artefacto local |
| Converter Stooq | [stooq_to_lean.py:44](/Users/guille/Documents/quant/trade-scanner/scripts/stooq_to_lean.py:44) | `test_t5_stooq_crosscheck.py` | ⚠️ skippable |
| Validación manual + fixture autoritativo | [PLAN.md:289](/Users/guille/Documents/quant/trade-scanner/PLAN.md:289) | no existe test autoritativo | ❌ |

**Top 5**
1. Cerrar T6.3/T6.4: validación manual ≤0,25% y fixture autoritativo.
2. Evitar que tests críticos se salten por falta de `data/`.
3. Corregir la receta de seed para no mezclar zips LEAN con factor files neutros de Stooq.
4. Pasar de requisitos globales a requisitos por símbolo antes de estrategias divergentes.
5. Alinear `DEVLOG`/`ROADMAP`/`README` con `PLAN.md`.