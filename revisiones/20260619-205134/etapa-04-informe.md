**Hallazgos**

**Corrección Funcional**
1. [trade-scanner/core/universe.py:76](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:76)  
Severidad: **ALTO**  
`max_tickers` no valida el tope duro de producto `≤200`. Si `config/strategies.json` define por error `max_universe=500`, `UniverseSpec` puede devolver más de 200 tickers, violando PLAN/SPECS y AGENTS.  
Sugerencia: validar en `__init__` que `1 <= max_tickers <= 200` o truncar siempre con `min(max_tickers, 200)` y fallar si la config intenta superar 200.

2. [trade-scanner/main.py:47](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:47), [trade-scanner/main.py:55](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:55), [trade-scanner/core/pipeline.py:100](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:100)  
Severidad: **ALTO**  
La carga por estrategia se convierte en una unión global de tickers y no queda persistida como universo por estrategia. En el estado actual posterior, `ScanPipeline.scan()` recibe todo `symbol_data_map`, así que una estrategia long puede evaluar símbolos de `swing_declines` y una short símbolos de `swing_advances`. Esto rompe la entidad `UniverseSpec` de SPECS: “lista de símbolos de una estrategia”.  
Sugerencia: conservar `self.universe_by_strategy[name] = set(loaded)` en `main.py` y pasar al pipeline un mapa filtrado por esa estrategia, o hacer que `ScanPipeline` reciba explícitamente su universo.

3. [trade-scanner/core/universe.py:10](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:10)  
Severidad: **MEDIO**  
`COLUMN_ALIASES` solo normaliza una parte del contrato de PLAN §5. Faltan aliases como `Name→name`, `Change→chg_1d`, `5D Chg→chg_5d`, `5D High→high_5d`, `5D Low→low_5d`, `Time→date`. Hoy el filtro usa `avg_vol_5d` y `price`, pero el contrato dice que `UniverseSpec` normaliza el mapa de columnas ratificado.  
Sugerencia: completar `COLUMN_ALIASES` con todo el contrato §5 y parsear numéricos/porcentajes de esas columnas cuando existan.

4. [trade-scanner/core/universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:52)  
Severidad: **MEDIO**  
La validación de columnas requeridas está hardcodeada a `avg_vol_5d` y `price`, no a las columnas realmente usadas por `filter_expr`. Un filtro futuro sobre `pct_chg_5d` exigiría columnas que no usa; un filtro sobre un alias no mapeado fallaría tarde en `df.query()` con poco contexto.  
Sugerencia: validar contra un allowlist de aliases soportados y envolver errores de `df.query()` con `universe_key` y `filter_expr`.

**Tests**
5. [trade-scanner/tests/test_universe.py:52](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:52)  
Severidad: **MEDIO**  
No hay test que demuestre el tope duro absoluto de 200 cuando `max_tickers` viene mal configurado, ni test del alias map completo del contrato PLAN §5. Los tests cubren el caso feliz actual, pero no blindan los invariantes más importantes de Etapa 4.  
Sugerencia: añadir casos `max_tickers=201`/CSV >200, alias completo, y filtro que use un alias distinto a `avg_vol_5d`/`price`.

**Alineación / Documentación**
6. [README.md:103](/Users/guille/Documents/quant/trade-scanner/README.md:103), [README.md:111](/Users/guille/Documents/quant/trade-scanner/README.md:111)  
Severidad: **BAJO**  
README aún describe un CSV `ticker,price,avg_dollar_volume` y dice que el filtro vive en `config.json`. Eso contradice PLAN/SPECS de Etapa 4: CSV Barchart vía ObjectStore y filtro en `config/strategies.json`.  
Sugerencia: actualizar README al contrato real de `UniverseSpec`.

**API LEAN / Reglas Duras**
No encontré órdenes en código ejecutable. `UniverseSpec` no importa `AlgorithmImports`. Los métodos LEAN relevantes de Etapa 4 están en snake_case y confirmados en stubs locales: `QCAlgorithm.object_store`, `ObjectStore.read(path) -> str`, `get_parameter()`, `log()`, `schedule.on`, `date_rules.every_day`, `time_rules.after_market_close/before_market_close`.

**Trazabilidad Etapa 4**

| Criterio | Código | Test / evidencia | Estado |
|---|---|---|---|
| `core/universe.py` existe y exporta `UniverseSpec` | [universe.py:27](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:27), [__init__.py:5](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/__init__.py:5) | import en [test_universe.py:8](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:8) | ✅ |
| Lee CSV desde ObjectStore, footer strip, alias, filtro, orden, tope | [universe.py:43](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:43) | `test_universe.py` 5 tests pasan | ✅ parcial: falta hard cap 200 |
| Con CSV real: advances≈74, declines≈68 | [config/strategies.json:21](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:21) | Validé localmente `storage`: 74 / 68 | ✅ |
| `main.py` loguea universo por 4 estrategias | [main.py:48](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:48), [main.py:57](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:57) | No re-ejecuté `lean backtest` en este sandbox | ⚠️ |
| `env=dev` usa `max_universe` | [config.json:3](/Users/guille/Documents/quant/trade-scanner/trade-scanner/config.json:3), [strategies.json:4](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:4), [main.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:38) | Validé `sample_dev` devuelve 4 | ✅ |
| `UniverseSpec` sin `AlgorithmImports` | [universe.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:1) | `rg AlgorithmImports trade-scanner/core/universe.py` sin import real | ✅ |
| Tests T3.1–T3.5 verdes | [test_universe.py:38](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:38) | `5 passed in 0.35s` con pytest host sin captura | ✅ |

**Verificación Ejecutada**

Ejecuté `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -s -p no:cacheprovider trade-scanner/tests/test_universe.py`: `5 passed`.

No ejecuté `bash scripts/run_tests.sh` completo ni `lean backtest` porque este entorno está en sandbox de solo lectura y red restringida; el runner Docker instala paquetes dentro del contenedor.

**Resumen Ejecutivo**

1. Cerrar el agujero del tope duro `≤200`; hoy depende de que la config nunca se equivoque.  
2. No perder el universo por estrategia: ahora se mezcla en una unión global y el pipeline puede escanear símbolos del universo equivocado.  
3. Completar el alias map de PLAN §5 y validar `filter_expr` contra aliases soportados.  
4. Añadir tests para hard cap 200, alias completo y reproducibilidad explícita.  
5. Actualizar README para no documentar un contrato de universo obsoleto.