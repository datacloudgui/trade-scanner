**Hallazgos**

**Alineación / Dependencias**
1. [PLAN.md:296](/Users/guille/Documents/quant/trade-scanner/PLAN.md:296), [PLAN.md:289](/Users/guille/Documents/quant/trade-scanner/PLAN.md:289), [etapa-05-informe.md:6](/Users/guille/Documents/quant/trade-scanner/revisiones/20260619-205134/etapa-05-informe.md:6) — **ALTO**  
   Etapa 6 depende de Etapa 5B, pero 5B sigue sin cerrar la validación manual ≤0,25% y el fixture autoritativo. Esto deja `position_vs_sma` bien testeado sintéticamente, pero sin base end-to-end cerrada sobre SMAs reales validadas.  
   Sugerencia: cerrar T6.3/T6.4 de 5B antes de dar por completamente trazable el flujo feature→SMA real.

**Corrección funcional**
2. [rules.py:54](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:54), [rules.py:73](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:73) — **MEDIO**  
   `SMAPositionRule` acepta `tfs=[]`; `evaluate()` no itera y devuelve `passed=True` con evidencia vacía. El contrato de Etapa 6/T3 es AND sobre todos los `tf` declarados, no una regla vacía que deja pasar símbolos por error de configuración.  
   Sugerencia: validar en constructor `tfs` no vacío, y añadir test de construcción que espere `ValueError`.

**Config / Validación**
3. [features.py:258](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:258), [features.py:265](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:265) — **MEDIO**  
   `resolve_bucket_thresholds()` valida el orden, pero asume que `bucket_thresholds` es dict y que sus valores son numéricos. Config malformada como `"near": "0.005"` o `bucket_thresholds: []` termina en `TypeError`/`AttributeError`, no en un `ValueError` claro de configuración.  
   Sugerencia: validar mapping, convertir a `float`, rechazar booleanos/NaN/inf, y cubrir esos casos con tests.

**Reglas duras**
No encontré órdenes (`market_order`, `set_holdings`, `liquidate`, `buy/sell`) en el código revisado de Etapa 6 ni en el camino relacionado.

**API LEAN**
Etapa 6 L3/L4 está pura: [features.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:1) y [rules.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:1) no importan `AlgorithmImports`. Verifiqué contra docs oficiales que los nombres de dependencia usados por L2/L5 son reales: `TradeBarConsolidator(Calendar.WEEKLY)`, `data_consolidated`, `SimpleMovingAverage.current.value`, y `self.object_store.read`. Fuentes: [Calendar Consolidators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/consolidator-types/calendar-consolidators), [Updating Indicators](https://www.quantconnect.com/docs/v2/writing-algorithms/consolidating-data/updating-indicators), [Simple Moving Average](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/simple-moving-average), [Object Store](https://www.quantconnect.com/docs/v2/writing-algorithms/object-store).

Nota: aunque SPECS/AGENTS mencionan `register_indicator`, [PLAN.md:263](/Users/guille/Documents/quant/trade-scanner/PLAN.md:263) congela explícitamente el cableado manual por `data_consolidated` como decisión aceptada para `SymbolData`; no lo reporto como bug.

**Trazabilidad Etapa 6**

| Criterio | Código | Test | Estado |
|---|---|---|---|
| `PositionResult` frozen, side derivado, igualdad | [features.py:79](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:79) | [test_features.py:36](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:36) | ✅ |
| `position_vs_sma` frío/SMA 0/distancia/bucket | [features.py:141](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:141) | [test_features.py:233](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:233) | ✅ |
| 7 buckets, 6 cortes, segundo threshold set | [features.py:165](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:165) | [test_features.py:287](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:287) | ✅ |
| `resolve_bucket_thresholds` global/override/defaults | [features.py:244](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:244), [main.py:142](/Users/guille/Documents/quant/trade-scanner/trade-scanner/main.py:142) | [test_features.py:373](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_features.py:373) | ⚠️ hallazgo 3 |
| `bucket_thresholds` en ObjectStore seed | [config/strategies.json:2](/Users/guille/Documents/quant/trade-scanner/config/strategies.json:2), [storage/config/strategies.json:2](/Users/guille/Documents/quant/trade-scanner/storage/config/strategies.json:2), [seed_object_store.sh:37](/Users/guille/Documents/quant/trade-scanner/scripts/seed_object_store.sh:37) | verificación estática | ✅ |
| `SymbolData.close(tf)` lectura L2 para L3 | [symbol_data.py:121](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/symbol_data.py:121) | [test_symbol_data.py:289](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_symbol_data.py:289) | ✅ |
| `AboveSMA` rediseñado como `SMAPositionRule` + `RuleResult` | [rules.py:12](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:12), [rules.py:27](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:27) | [test_rules.py:58](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_rules.py:58) | ⚠️ hallazgo 2 |
| Evidencia `{tf:{period:{value,distance_pct,bucket}}}` | [features.py:222](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:222) | [test_rules.py:22](/Users/guille/Documents/quant/trade-scanner/trade-scanner/tests/test_rules.py:22) | ✅ |
| Sin `QCAlgorithm`/`history` en L3/L4 | [features.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/features.py:1), [rules.py:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/core/rules.py:1) | import/tests sintéticos | ✅ |

No modifiqué archivos. No ejecuté `scripts/run_tests.sh` porque el run solicitado es de solo lectura y ese script puede instalar dependencias/escribir artefactos.

**Resumen Ejecutivo**

1. Cerrar Etapa 5B: es el bloqueo real de confianza end-to-end.
2. Evitar que `SMAPositionRule([])` pase todo silenciosamente.
3. Endurecer `resolve_bucket_thresholds()` contra config malformada.
4. Reejecutar la suite Docker en un entorno con escritura controlada.
5. Mantener PLAN/SPECS alineados sobre el cableado manual de SMAs para no reabrir una decisión ya congelada.