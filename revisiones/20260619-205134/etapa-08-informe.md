Revisión solo lectura de Etapa 8 completada. No modifiqué archivos. No ejecuté `scripts/run_tests.sh` ni `lean backtest` porque este run es read-only; usé inspección estática, stubs locales de QuantConnect en `.venv`, tests existentes y artefactos ya generados en `storage/results/`.

**Hallazgos**

**Corrección funcional / Dependencia heredada**
1. [main.py:47](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:47), [main.py:379](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:379), [main.py:391](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:391) — **ALTO**  
   Sigue vigente el bug de Etapa 7: los universos por estrategia se colapsan en `tickers` global y cada pipeline escanea `self.symbol_data` completo. Etapa 8 ahora persiste/notifica esos resultados, así que el envelope/correo puede mezclar tickers de `swing_advances` y `swing_declines` en prod.  
   **Sugerencia:** conservar `symbol_data_by_strategy` o `symbols_by_strategy` y pasar a cada `pipeline.scan()` solo su universo. Añadir test L5 con universos long/short disjuntos y verificar el envelope.

**OutputSink / Persistencia**
2. [output.py:214](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:214), [output.py:248](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:248), [output.py:261](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:261), [output.py:287](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:287) — **ALTO**  
   D8.3/SPECS dicen que todo scan escribe archivo siempre, pero `emit()` solo ejecuta `_emit_file` si `channels` contiene `"file"`. Un `channels=[]`, `["qc_notify"]` o `["host_email"]` deja sin JSON/CSV/latest; además `host_email` puede loguear “listo” sin que exista `latest.json`.  
   **Sugerencia:** persistir archivo siempre y primero, fuera de la lista de canales opcionales, o validar fail-fast que `file` esté presente y sea primero. Añadir tests para `channels=[]`, `["qc_notify"]` y `["host_email"]`.

3. [output.py:261](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:261), [output.py:284](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:284) — **MEDIO**  
   `object_store.save(...)` y `notify.email(...)` retornan `bool` en los stubs locales de LEAN, pero el código ignora el resultado y loguea éxito siempre. Un fallo de escritura/notificación quedaría invisible.  
   **Sugerencia:** comprobar los tres `save` y el `email`; si devuelven `False`, levantar error o loguear fallo explícito y no reportar éxito.

**Config / Alineación**
4. [config/notifications.json:7](/Users/guille/Documents/quant/trade-scanner/config/notifications.json:7), [config/notifications.json:8](/Users/guille/Documents/quant/trade-scanner/config/notifications.json:8) — **BAJO**  
   La config versionada solo define `dev=["file"]` y `prod=["file","host_email"]`; no hay entorno listo con `qc_notify`. El handler existe y está testeado, pero si se corre cloud con `env=prod`, no dispara `NotificationManager`, contrario a SPECS #6 salvo que E9 añada/edite config.  
   **Sugerencia:** añadir un entorno explícito tipo `cloud` con `["file","qc_notify"]` o documentar que E9 debe cambiar `env/channels` antes del live cloud.

**Tests**
5. [main.py:164](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:164), [main.py:358](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:358), [test_output.py:260](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_output.py:260), [test_notify_email.py:28](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_notify_email.py:28) — **MEDIO**  
   Hay buena cobertura de serialización/render/dispatch, pero no hay test automatizado del wiring L5: `notification_groups` → un schedule por base → `_scan_group` → un solo `output.emit`. La evidencia es backtest/log, no un test que proteja regresiones.  
   **Sugerencia:** extraer/inyectar el agrupador o usar mocks para verificar miembros activos, invariant schedule/partial_bar, secciones vacías y exactamente un `emit` por base.

**Documentación**
6. [README.md:72](/Users/guille/Documents/quant/trade-scanner/README.md:72), [README.md:124](/Users/guille/Documents/quant/trade-scanner/README.md:124), [README.md:135](/Users/guille/Documents/quant/trade-scanner/README.md:135) — **BAJO**  
   El README sigue describiendo config de negocio en `config.json`, un CSV viejo sin envelope/`direction`, y notificación configurada en `config.json`. Contradice PLAN/SPECS y Etapa 8.  
   **Sugerencia:** actualizar README a `config/strategies.json` + `config/notifications.json`, envelope por base y `storage/results/<base>/latest.json`.

**API LEAN**
Verifiqué contra stubs locales que las APIs usadas por Etapa 8 existen en snake_case: `object_store.read/save`, `notify.email`, `live_mode`, `utc_time`, `schedule.on`, `date_rules.every_day`, `time_rules.before_market_close/after_market_close`, `get_parameter`. No encontré `market_order`, `set_holdings`, `buy/sell` ni `liquidate` en el código activo de Etapa 8.

**Trazabilidad Etapa 8**

| Criterio Done when | Código | Test/evidencia | Estado |
|---|---|---|---|
| CSV/JSON legibles por base, secciones long/short, columna `direction` | [output.py:61](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:61), [output.py:132](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:132), [main.py:391](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:391) | [test_output.py:91](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_output.py:91), `storage/results/swing_eod/latest.json` | Parcial: cumple, pero contaminable por hallazgo 1 |
| Switch por entorno aislado en `output.py` | [output.py:180](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:180), [output.py:242](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:242) | [test_output.py:260](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_output.py:260), grep sin `if env ==` fuera | Parcial: hallazgo 2 |
| Un correo por base, LONG/SHORT, render compartido | [main.py:164](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:164), [email_render.py:55](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/email_render.py:55), [notify_email.py:45](/Users/guille/Documents/quant/trade-scanner/scripts/notify_email.py:45) | [test_email_render.py:73](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_email_render.py:73), [test_notify_email.py:28](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_notify_email.py:28) | OK |
| Dry-run host sin token | [notify_email.py:137](/Users/guille/Documents/quant/trade-scanner/scripts/notify_email.py:137) | [test_notify_email.py:54](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_notify_email.py:54) | OK |
| `notifications.json` sembrado, sin secretos, `SubscriberSource` | [config/notifications.json:1](/Users/guille/Documents/quant/trade-scanner/config/notifications.json:1), [output.py:151](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/output.py:151), [seed_object_store.sh:37](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:37) | [test_output.py:414](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_output.py:414), `storage/config/notifications.json` | OK |
| `run_tests.sh` verde 225 | [run_tests.sh:24](/Users/guille/Documents/quant/trade-scanner/scripts/run_tests.sh:24) | Bitácora Etapa 8; no reejecutado por read-only | Histórico, no verificado en este run |
| Commit y bitácora | [etapa-08-decisiones-y-pendientes.md:281](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-08-decisiones-y-pendientes.md:281) | `git log`: `0cd92e2 add: [Etapa 8]...` | OK |

**Resumen Ejecutivo**
1. Corregir primero la mezcla de universos heredada de E7; ahora afecta directamente los archivos y correos de E8.
2. Hacer que `OutputSink` escriba archivo siempre, independientemente de `channels`.
3. Revisar retornos de `object_store.save` y `notify.email`.
4. Añadir test de integración L5 para `notification_groups` y un solo `emit` por base.
5. Actualizar README y, en E9, dejar config explícita para `qc_notify` cloud.