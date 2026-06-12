# Checkpoint T5.1 — seed de sample data multi-símbolo (2026-06-11)

Sesión interrumpible: este archivo registra cada paso. Retomar desde el primer paso sin ✅.

**Instrucción del usuario:** usar fb.zip, aapl.zip y spy.zip ya descargados (en vez de
AAPL+IBM del spec). OJO: ibm.zip TAMBIÉN está presente en data/equity/usa/daily/.

## Plan de pasos

1. ✅ Inventario de data/ y lectura de seed_sample_data.sh — los 4 zips presentes en `daily/`
2. ✅ Cobertura de fechas: aapl/ibm/spy 1998-01-02→2021-03-31 (5848 barras, M:200 ✅);
   fb 1999-09-29→2021-03-31 (2946 barras; historia propia de Facebook solo desde IPO 2012 → M:200 ❌)
3. ✅ Decisión de símbolos — **usuario eligió los 4 (SPY/AAPL/IBM/FB)** (2026-06-11):
   FB queda como caso real de serie M:200 no-ready; implica ajustar el Done-when F2
4. ✅ Paths verificados en repo público LEAN: map_files/ y factor_files/ de aapl, ibm, fb → HTTP 200
5. ✅ seed_sample_data.sh extendido: loop `aapl ibm fb` → daily/<sym>.zip + map + factor (idempotente)
6. ✅ Seed ejecutado: map/factor de los 3 en data/equity/usa/{map_files,factor_files}/;
   `sample_dev.csv` (4 filas) sembrado a storage/universes/; `dev.max_universe` 2→4
   (con 2, UniverseSpec truncaría a [AAPL, FB]); UniverseSpec dev → `["AAPL","FB","IBM","SPY"]` ✅
7. ✅ run_tests.sh → 33 passed (sanidad, core intacto)
8. ✅ Decisiones/pendientes actualizados + commit `[Etapa 5B] T5.1`

## Resultado

T5.1 cumplido (criterio adaptado a 4 símbolos): universo dev = SPY/AAPL/IBM/FB con data
diaria LEAN local, map/factor sembrados, filtro dev pasado por los 4. Sigue T6.1 (batch
multi-símbolo en backtest) con la salvedad FB→M:200 no-ready esperado.
