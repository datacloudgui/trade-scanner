No modifiqué archivos. Revisé Etapa 2 en modo solo lectura; intenté `scripts/run_tests.sh`, pero Docker no permitió conectar al socket local, así que no pude re-ejecutar pytest en esta máquina. Sí verifiqué el código, configs, scripts, logs existentes y stubs locales de LEAN.

**Hallazgos**

**Arquitectura / LEAN API**

1. [trade-scanner/main.py:123](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:123)  
Severidad: **MEDIO**  
El fallback del anchor SPY usa `Resolution.DAILY`. Etapa 2 exige SPY como ancla de calendario/datos intradía para que el reloj avance y los eventos `before/after_market_close` disparen en tiempos reales. Hoy no falla en `dev` porque SPY viene en el universo y se suscribe antes con `Resolution.MINUTE`, pero si SPY sale del universo efectivo, el anchor dedicado deja de ser minuto.  
Sugerencia: asegurar siempre un SPY anchor con `Resolution.MINUTE`; si ya existe la suscripción minuto, reutilizarla.

**Alineación / Documentación**

2. [README.md:72](/Users/guille/Documents/quant/trade-scanner/README.md:72)  
Severidad: **MEDIO**  
El README contradice Etapa 2/PLAN/SPECS: indica que las estrategias viven en `Screener/config.json` y muestra config anidada bajo `parameters`, cuando Etapa 2 congeló `config/strategies.json` vía ObjectStore y `trade-scanner/config.json` solo para escalares como `env`. También repite esa dirección para universo y notificaciones en [README.md:111](/Users/guille/Documents/quant/trade-scanner/README.md:111) y [README.md:135](/Users/guille/Documents/quant/trade-scanner/README.md:135).  
Sugerencia: actualizar README para reflejar `config/strategies.json`/`storage/config/strategies.json`, `universes/*.csv`, y `get_parameter` solo para escalares.

**Tests**

3. [trade-scanner/main.py:431](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:431)  
Severidad: **BAJO**  
La conversión `swing_eod → after_market_close(..., 1)` y `market_close → before_market_close(..., 30)` está implementada y confirmada por logs, pero no hay test automatizado de regresión para proteger el mapeo ni el caso fallback del anchor SPY.  
Sugerencia: añadir un smoke/integration test o comprobación de log que valide explícitamente los eventos programados esperados.

**Notas de Verificación LEAN**

Verifiqué contra stubs locales de QuantConnect que existen y están bien nombrados: `schedule.on`, `date_rules.every_day`, `time_rules.after_market_close`, `time_rules.before_market_close`, `object_store.read`, `add_equity`, `get_parameter`, `set_start_date`, `set_end_date`, `set_cash`, `Resolution.MINUTE/DAILY`, `DataNormalizationMode.SPLIT_ADJUSTED` y `TradeBar`.

No encontré llamadas activas a órdenes (`market_order`, `set_holdings`, `liquidate`, `buy/sell`, etc.) en el código.

**Trazabilidad Etapa 2**

| Criterio Etapa 2 | Código | Test / evidencia | Estado |
|---|---|---|---|
| Paquetes `core/`, `strategies/`, `tests/` importables | [main.py:8](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:8), [main.py:15](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:15), `__init__.py` presentes | Import local read-only exitoso; logs LEAN importan `main` | ✅ |
| SPY sample data 2013 minuto y rango 2013-10-07..11 | [seed_sample_data.sh:21](/Users/guille/Documents/quant/trade-scanner/scripts/seed_sample_data.sh:21), [main.py:30](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:30) | Datos ignorados presentes; backtest log procesó datos | ✅ |
| Config anidada vía ObjectStore, no `config.json` | [main.py:35](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:35), [seed_object_store.sh:37](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:37) | `storage/config/strategies.json` coincide con `config/strategies.json` | ✅ |
| Schedules Etapa 2 | [main.py:183](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:183), [main.py:436](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:436), [main.py:438](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:438) | Logs muestran 15:30 y 16:01 | ✅ con hallazgo MEDIO |
| Tests Docker + pythonnet bridge | [run_tests.sh:24](/Users/guille/Documents/quant/trade-scanner/scripts/run_tests.sh:24), [test_pythonnet_bridge.py:5](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_pythonnet_bridge.py:5) | Script correcto; ejecución actual bloqueada por Docker socket | ⚠️ |
| Sin datos/storage/backtests versionados | [.gitignore:160](/Users/guille/Documents/quant/trade-scanner/.gitignore:160), [.gitignore:168](/Users/guille/Documents/quant/trade-scanner/.gitignore:168) | `git status --ignored` confirma ignorados | ✅ |

**Resumen Ejecutivo**

1. Corregir el fallback de SPY para que siempre sea `Resolution.MINUTE`.
2. Actualizar README: hoy contradice el diseño central de Etapa 2 sobre ObjectStore.
3. Añadir una prueba/regresión para los schedules y anchor SPY.
4. Re-ejecutar `scripts/run_tests.sh` cuando Docker tenga permiso al socket.
5. La restricción V1 “solo scan, cero órdenes” se cumple en el código revisado.