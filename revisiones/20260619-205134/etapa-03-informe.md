Revisión de Etapa 3 completada en modo solo lectura. No modifiqué archivos. No encontré órdenes ni gestión de portfolio, así que no hay hallazgos CRÍTICOS por la regla V1 “solo escanea”.

No pude ejecutar la suite en Docker: `scripts/run_tests.sh` falla por permiso al socket Docker (`permission denied ... /Users/guille/.docker/run/docker.sock`). La verificación de API LEAN quedó por inspección estática y documentación local del proyecto; no pude contrastar contra stubs dentro de `/Lean/Launcher/bin/Debug`.

**Hallazgos**

**Bugs / Corrección Funcional**

1. [scripts/seed_object_store.sh:57](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:57) - **ALTO**  
   El script selecciona el CSV “más reciente” con `sort | tail -1` sobre nombres `MM-DD-YYYY`. Eso falla al cruzar años o meses: `12-31-2025` ordena después de `01-02-2026`, aunque es más antiguo. Viola el criterio de Etapa 3 de sembrar los CSV más recientes.  
   Sugerencia: extraer la fecha del filename y ordenar por clave `YYYYMMDD`, o usar un helper Python que parseé la fecha explícitamente. Añadir una prueba con `12-31-2025` vs `01-02-2026`.

2. [scripts/explore_universe.py:52](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:52) - **MEDIO**  
   El script clasifica cualquier símbolo que no cumpla `^[A-Z]{1,5}$` como footer. Luego [scripts/explore_universe.py:137](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:137) calcula `non_standard` solo sobre `data_rows`, así que nunca reporta tickers no estándar reales como `BRK.B`; los oculta como “footer”. Esto debilita el reporte exploratorio que Etapa 3 exige para validar el universo.  
   Sugerencia: detectar el footer de Barchart por patrón específico, por ejemplo `Downloaded from Barchart.com`, y reportar el resto de símbolos inválidos como no estándar.

3. [scripts/explore_universe.py:93](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:93) - **BAJO**  
   Si una columna porcentual existe pero todos sus valores son vacíos/no parseables, `min(valid)` y `max(valid)` lanzan excepción. El script debería producir diagnóstico, no abortar, ante CSV parcialmente sucio.  
   Sugerencia: aplicar el mismo guard que ya existe para columnas numéricas: si `valid` está vacío, mostrar `n/a`.

**Alineación / Contrato Etapa 3**

4. [trade-scanner/core/universe.py:10](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/universe.py:10) - **MEDIO**  
   `COLUMN_ALIASES` no implementa todo el contrato de columnas documentado para Etapa 3 / PLAN. Solo mapea `Symbol`, `5D Avg Vol`, `Latest`, `5D %Chg`, `%Change`; faltan aliases como `Name`, `Change`, `5D Chg`, `5D High`, `5D Low`, `Time`. Esto rompe filtros declarativos futuros o documentados como `high_5d > X`.  
   Sugerencia: completar la tabla de aliases y parsear como numéricas las columnas numéricas documentadas. Añadir tests para al menos `chg_5d`, `high_5d`, `low_5d`, `chg_1d` y `date`.

5. [README.md:72](/Users/guille/Documents/quant/trade-scanner/README.md:72) - **MEDIO**  
   El README contradice el contrato de Etapa 3: apunta a `Screener/config.json`, conserva `max_extension_pct`, describe universos como `ticker,price,avg_dollar_volume` y muestra rutas antiguas. La fuente de verdad actual usa ObjectStore con `config/strategies.json` y CSV Barchart normalizados a keys estables.  
   Sugerencia: actualizar README para reflejar `config/strategies.json`, `universes/swing_advances.csv`, `universes/swing_declines.csv`, columnas Barchart y el contrato actual de salida.

**Tests**

6. [scripts/seed_object_store.sh:50](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:50) - **MEDIO**  
   No hay tests automatizados para el seeding de ObjectStore, precisamente donde aparece el bug de selección de fecha. La Etapa 3 depende de este script para dejar `storage/` listo, pero la regresión solo se detecta manualmente.  
   Sugerencia: extraer la selección de CSV a una función testeable o añadir test shell con directorio temporal y filenames controlados.

7. [scripts/explore_universe.py:34](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:34) - **BAJO**  
   No hay test para el análisis exploratorio de universos. Etapa 3 lo usa como criterio de aceptación operativo, pero no hay cobertura para footer, columnas faltantes, tickers no estándar, filtros de volumen/precio o porcentajes malformados.  
   Sugerencia: añadir tests unitarios sobre fixtures pequeños y salida esperada, especialmente para footer Barchart y símbolos no estándar.

**API LEAN / Arquitectura**

No encontré violaciones específicas de Etapa 3. Las llamadas LEAN relevantes están confinadas a `main.py` y capas L2, usan snake_case actual por inspección (`object_store`, `add_equity`, `schedule.on`, `history`, `set_warm_up`) y no hay órdenes. Los scripts de Etapa 3 no usan LEAN API directamente.

**Trazabilidad Etapa 3**

| Criterio Etapa 3 | Código / evidencia | Test | Estado |
|---|---|---:|---:|
| Explorar ambos CSV con reporte usable | [scripts/explore_universe.py:34](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:34). Ejecutado manualmente sobre advances y declines: ambos OK | Sin test | ⚠️ |
| Reportar tickers no estándar | [scripts/explore_universe.py:137](/Users/guille/Documents/quant/trade-scanner/scripts/explore_universe.py:137) | Sin test | ❌ |
| Contrato input Barchart actualizado en PLAN | [PLAN.md:102](/Users/guille/Documents/quant/trade-scanner/PLAN.md:102) | [test_universe.py:37](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_universe.py:37) parcial | ⚠️ |
| Contrato output `ScanResult` actualizado | [PLAN.md:128](/Users/guille/Documents/quant/trade-scanner/PLAN.md:128), [core/pipeline.py:29](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/pipeline.py:29) | [test_output.py:91](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_output.py:91) | ✅ |
| `strategies.json` con env dev/prod y 4 estrategias | [config/strategies.json:3](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:3), [config/strategies.json:19](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:19) | [test_strategies.py:160](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_strategies.py:160) parcial | ⚠️ |
| `env=dev` configurado | [lean.json:669](/Users/guille/Documents/quant/trade-scanner/lean.json:669), [trade-scanner/config.json:3](/Users/guille/Documents/quant/trade-scanner/trade-scanner/config.json:3) | Sin test | ✅ |
| Seed ObjectStore con latest CSV y keys estables | [scripts/seed_object_store.sh:37](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:37), [scripts/seed_object_store.sh:57](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:57) | Sin test | ❌ |
| `storage/universes` poblado con 200 tickers por lado | Estado actual verificado: storage coincide con processed, 202 líneas por archivo | Sin test | ✅ manual |
| Backtest local con 4 estrategias | No ejecutado por falta de Docker socket | `run_tests.sh` no ejecutable aquí | ⚠️ |

**Resumen Ejecutivo**

1. Corregir la selección de CSV “más reciente” en `seed_object_store.sh`; ahora puede sembrar un universo antiguo.
2. Arreglar `explore_universe.py` para no esconder tickers no estándar como footer.
3. Completar el contrato de aliases de Barchart en `core/universe.py`.
4. Añadir tests para los scripts de Etapa 3, especialmente seeding y exploración.
5. Actualizar el README, que todavía describe contratos y rutas anteriores a Etapa 3.