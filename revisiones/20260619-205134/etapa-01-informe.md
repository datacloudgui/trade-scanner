**Alcance**
Revisé solo Etapa 1: `lean.json`, `.gitignore`, `.env` sin exponer valores, proyecto LEAN creado, commits `[Etapa 1]`, evidencia local de backtests ignorados, `PLAN.md`, `SPECS.md`, `CLAUDE.md`, ADR-001/002 y README. No modifiqué archivos. No ejecuté `lean backtest` ni pytest porque escriben artefactos; usé evidencia existente de solo lectura.

**Hallazgos**
**Reglas Duras**

1. [trade-scanner/backtests/2026-06-11_00-47-42/code/main.py:20](/Users/guille/Documents/quant/trade-scanner/trade-scanner/backtests/2026-06-11_00-47-42/code/main.py:20) — **CRÍTICO**  
   El template commiteado/ejecutado en Etapa 1 contiene `self.set_holdings("SPY", 1)`. Esto viola el invariante “solo escanea, cero órdenes” de [PLAN.md:5](/Users/guille/Documents/quant/trade-scanner/PLAN.md:5), [SPECS.md:102](/Users/guille/Documents/quant/trade-scanner/SPECS.md:102) y [CLAUDE.md:60](/Users/guille/Documents/quant/trade-scanner/CLAUDE.md:60). Además, al haber datos disponibles, el backtest sí generó una orden: [log.txt:58](/Users/guille/Documents/quant/trade-scanner/trade-scanner/backtests/2026-06-11_01-27-02/log.txt:58), [1845843718-order-events.json:1](/Users/guille/Documents/quant/trade-scanner/trade-scanner/backtests/2026-06-11_01-27-02/1845843718-order-events.json:1).  
   Sugerencia: reemplazar el algoritmo de smoke por uno no operativo: `initialize()` con fechas/suscripción y `on_data()` vacío o solo log, sin `portfolio`, `set_holdings`, `market_order`, etc.; repetir el smoke y conservar evidencia de `Total Orders 0`.

**Seguridad / Alineación**

2. [README.md:49](/Users/guille/Documents/quant/trade-scanner/README.md:49) — **ALTO**  
   El README sigue instruyendo `lean init`, `lean login`, proyecto `Screener` y “editar `lean.json` y agregar claves de Alpaca” en [README.md:58](/Users/guille/Documents/quant/trade-scanner/README.md:58). Contradice Etapa 1 ([etapa-01.md:66](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-01.md:66), [etapa-01.md:72](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-01.md:72)), PLAN ([PLAN.md:186](/Users/guille/Documents/quant/trade-scanner/PLAN.md:186)) y ADR-002 ([ADR-002:50](/Users/guille/Documents/quant/trade-scanner/.claude/decisions/ADR-002-qc-module-auth-constraint.md:50)). Es una ruta directa a fuga de secretos.  
   Sugerencia: actualizar README al flujo real: repo root como workspace, `lean.json` con credenciales vacías, claves reales solo en `.env`, sin `lean login` para Fase 1, proyecto `trade-scanner`.

**Tests / Evidencia**

3. [trade-scanner/backtests/2026-06-11_00-47-42/log.txt:58](/Users/guille/Documents/quant/trade-scanner/trade-scanner/backtests/2026-06-11_00-47-42/log.txt:58) — **MEDIO**  
   El Done when dice backtest “sin errores”, pero la evidencia local sin datos tiene `ERROR:: BacktestingResultHandler.SendFinalResult(): Sequence contains no elements` ([log.txt:58](/Users/guille/Documents/quant/trade-scanner/trade-scanner/backtests/2026-06-11_00-47-42/log.txt:58)). La evidencia de “Successfully ran” no aparece versionada; solo está declarada en [etapa-01.md:58](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-01.md:58).  
   Sugerencia: repetir un smoke no-operativo y guardar una evidencia mínima sanitizada: comando, exit code, líneas clave del log, `Total Orders 0`.

**Reproducibilidad**

4. [etapa-01.md:30](/Users/guille/Documents/quant/trade-scanner/.claude/fase-1-desarrollo-local/etapa-01.md:30) — **BAJO**  
   El criterio dice que `data/object-store/` existe, y [.gitignore:160](/Users/guille/Documents/quant/trade-scanner/.gitignore:160)-[161](/Users/guille/Documents/quant/trade-scanner/.gitignore:161) lo exceptúa, pero un directorio vacío no queda preservado por Git; no aparece en `git ls-files`. En un clon limpio esa parte de Etapa 1 no queda demostrada.  
   Sugerencia: si el criterio sigue vigente, añadir un `.gitkeep` permitido o documentar un comando de bootstrap. Si Etapa 2 ya reemplazó esto por `storage/`, actualizar Etapa 1 para evitar la ambigüedad.

**Trazabilidad**

| Criterio Etapa 1 / diseño | Código/evidencia | Test/evidencia | Estado |
|---|---|---:|---:|
| `lean backtest "trade-scanner"` corre sin errores | logs locales muestran ejecución, pero también error sin datos y orden con datos | no hay evidencia versionada limpia | ❌ |
| Credenciales Alpaca en `.env`; `lean.json` sin valores reales | [lean.json:135](/Users/guille/Documents/quant/trade-scanner/lean.json:135)-[138](/Users/guille/Documents/quant/trade-scanner/lean.json:138), [.gitignore:171](/Users/guille/Documents/quant/trade-scanner/.gitignore:171) | audit local redacted: variables existen; valores no aparecen fuera de `.env` | ✅ |
| Grep de claves reales cero hits | `.env` no trackeado; scan local no encontró rutas con valores reales | no hay script/evidencia versionada | ✅/⚠️ |
| `lean.json`, `.gitignore`, proyecto commiteados con `[Etapa 1]` | commits `7d87275`, `ebf1a71`; `git ls-files` incluye archivos | evidencia git local | ✅ |
| V1 solo escanea, cero órdenes | template de etapa ejecuta `set_holdings` | order events con `buy` llenado | ❌ |

**API LEAN**
Verifiqué contra stubs locales: `QCAlgorithm` existe ([__init__.pyi:3076](/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3076)), `add_equity` ([3718](/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:3718)), `set_cash`, `set_end_date`, `debug`, `Resolution.MINUTE`, `Slice` y `set_holdings` ([7224](/Users/guille/Documents/quant/trade-scanner/.venv/lib/python3.11/site-packages/QuantConnect/Algorithm/__init__.pyi:7224)). No hay nombre LEAN inventado en Etapa 1; el problema es que `set_holdings` es real y está prohibido para V1.

**Resumen Ejecutivo**
Top 5 a corregir: quitar el `set_holdings` del smoke histórico, repetir el backtest con `Total Orders 0`, actualizar README para no pedir secretos en `lean.json`, guardar evidencia sanitizada de Etapa 1, y resolver/documentar la reproducibilidad de `data/object-store/`.