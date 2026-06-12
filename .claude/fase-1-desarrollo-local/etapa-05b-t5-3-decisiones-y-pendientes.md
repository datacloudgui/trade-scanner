# T5.3 — factor_files neutros + map_files + cross-check SPY (2026-06-11)

## Resultado contra el criterio de aceptación

| Criterio T5.3 | Estado | Evidencia |
|---|---|---|
| factor_files neutros para zips Stooq | ✅ | `factor_files/aapl.csv` → `19840907,1,1,1`; `factor_files/ibm.csv` → `19620102,1,1,1` (LEAN no re-ajusta precios ya ajustados de Stooq) |
| map_files presentes | ✅ | Reutilizados del repo LEAN (`map_files/aapl.csv`, `map_files/ibm.csv`); correctos para resolver el símbolo |
| Verificar precios sin re-ajuste (agnóstico al modo) | ✅ | factor=1 → SPLIT_ADJUSTED == RAW == ADJUSTED para los zips Stooq (D3) |
| Cross-check SPY (converter == zip en fechas solapadas) | ✅ redefinido | El cross-check original (Stooq vs LEAN zip) no es válido — hallazgo crítico: Stooq da precios total-return adjusted (ver abajo). Cross-check redefinido: fidelidad de precios CSV→zip (20 fechas, tolerancia ±1 unidad ×10000) + SMAs coherentes vía SymbolData. 2 tests nuevos, 35 passed total. |
| Sanidad | ✅ | `run_tests.sh` → 35 passed; spy.zip de referencia intacto (T4 verde) |

**Veredicto: ✅ T5.3 cumplido (con hallazgo documentado y cross-check redefinido).**

---

## Hallazgo crítico: Stooq provee precios total-return adjusted (no split-only)

### Diagnóstico (2026-06-11)

Comparación de `spy.zip` (LEAN, raw, SPY sin splits 1998-2021) vs converter Stooq SPY:

- Close 2005-02-25 LEAN: **$121.38** (precio real de mercado — SPY sin splits, raw == split-adjusted)
- Close 2005-02-25 Stooq: **$93.69** (22.81% por debajo del precio real)
- Diferencia SMA D:8 en 2020-06-01: LEAN $298.64 vs Stooq $277.65 (7.03% — menos dividendos acumulados en esa ventana)

El precio de Stooq es menor porque **ajusta histórico hacia atrás por dividendos acumulados**:
precio_stooq(t) = precio_real(t) / factor_dividendos_acumulados(t, hoy). A medida que el punto t se aleja más en el pasado, más dividendos se han acumulado → mayor diferencia.

**Stooq = total-return adjusted ≠ split-only adjusted** (como LEAN SPLIT_ADJUSTED).

### Impacto en el proyecto

| Aspecto | Impacto |
|---|---|
| **Converter T5.2** | Ninguno: el converter transcribe fielmente los precios de Stooq → zip LEAN |
| **Cross-check T5.3** | El diseño original (Stooq vs LEAN zip) no es válido; redefinido por fidelidad de precios |
| **Backtest LEAN con Stooq + factor neutro** | Precios son total-return adjusted; SMAs reflejan serie total-return |
| **Validación TradingView (T6.3)** | ⚠️ **Usar vista "Adjusted" en TradingView** (checkbox "Adj" o modo precio ajustado); la vista default (split-only) difiere ~7-22% según el horizonte. El criterio ≤0.25% aplica comparando total-return vs total-return |
| **Factor file neutro (factor=1)** | Correcto: LEAN no re-ajusta, sirve los precios total-return as-is |
| **AAPL/IBM** | Misma convención que SPY (total-return adjusted en Stooq) |

### Acción tomada

- Factor files de AAPL/IBM reemplazados por neutros (`factor=1`) para evitar doble ajuste
- map_files de LEAN reutilizados (no afectados por el ajuste de precios)
- AAPL/IBM zips (1984/1962 → 2026) reemplazaron los zips LEAN (que terminaban en 2021-03-31)
- SPY en `data/equity/usa/daily/spy.zip` se conserva LEAN (1998-2021, raw) para que el fixture T4 siga verde. El zip Stooq SPY (2005-2026) vive en `data/stooq_lean/daily/spy.zip` y es usado por los tests T5.3

---

## SPY para el backtest F2 (pendiente T6.1)

El backtest de T6.1 necesita decidir qué datos usar para SPY:

| Opción | Pro | Contra |
|---|---|---|
| **Mantener spy.zip LEAN (1998-2021)** | T4 sigue verde sin cambios; start_date 2016 funciona | SMAs de SPY en 2021 (no recientes para T6.3) |
| **Reemplazar con Stooq SPY (2005-2026)** | Data reciente para T6.3; coherencia con AAPL/IBM | M:200 de SPY no-ready hasta ~dic 2021 si start_date < 2022; hay que actualizar T4 para que use spy_lean_ref.zip y regenerar valores congelados con data Stooq |

**Recomendación:** usar Stooq SPY para el backtest de F2 (alineado con el objetivo "data reciente"), actualizar el start_date a 2022, y actualizar T4 en T6.4 (el fixture autoritativo reemplazará T4 de todas formas). Decidir en T6.1.

## Pendiente

- **T6.1** (siguiente): backtest dev con 4 símbolos usando Stooq AAPL/IBM + decidir SPY + verificar batch agrupado en logs
- **T6.3**: usuario compara en TradingView con vista **"Adjusted"** (total-return) para ≤0.25%
