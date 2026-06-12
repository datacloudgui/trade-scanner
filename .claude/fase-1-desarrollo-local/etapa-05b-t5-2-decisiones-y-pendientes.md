# T5.2 — Núcleo del converter Stooq→LEAN (2026-06-11)

## Resultado contra el criterio de aceptación

T5.2 (núcleo: `parsear fecha + OHLC×10000 → ordenar ascendente → escribir <sym>.csv en <sym>.zip`):

| Criterio T5.2 | Estado | Evidencia |
|---|---|---|
| Parseo de fecha + OHLC | ✅ | `parse_stooq_csv` lee header Stooq (tolerante a mayúsc./columnas extra) |
| OHLC×10000 entero | ✅ | round-trip exacto vs `spy.zip` (5849 filas, byte-a-byte en valores) |
| Ordenar ascendente | ✅ | CSV de entrada desordenado (descendente) → salida ascendente verificada |
| Escribir `<sym>.csv` dentro de `<sym>.zip` | ✅ | `write_lean_zip` → `/tmp/stooq_staging/spy.zip` válido |
| `requests` crudo, sin SDK (D3) | ✅ | el script no depende de pandas ni SDK; stdlib (`csv`+`zipfile`). El fetch (T5.4) está bloqueado → se separó del núcleo (ver abajo) |
| Sanidad | ✅ | `run_tests.sh` → 33 passed; `spy.zip` de referencia intacto (md5 sin cambios) |

**Veredicto: ✅ T5.2 (núcleo) cumplido.** Entregable: [scripts/stooq_to_lean.py](../../scripts/stooq_to_lean.py).

## Decisiones tomadas

### D-T5.2.1 — Fetch automatizado de Stooq separado del núcleo (decisión del usuario)

Confirmación empírica del endpoint Stooq (era la pregunta abierta nº2 del spec, prerequisito
de T5.2/T5.4): `https://stooq.com/q/d/l/?s=spy.us&i=d` **ya no sirve a clientes
programáticos**. Devuelve un **proof-of-work JavaScript** (anti-bot); resuelto el PoW
(`n=98860`, cookie `auth`), la descarga responde **`Access denied`** (cuota diaria de
descargas CSV por IP). La página HTML de la cotización sí carga, pero el endpoint de
descarga está vedado.

**Decisión del usuario (2026-06-11):** construir el **converter agnóstico que consume un CSV
en formato Stooq desde un path local** (`--input`). Los CSV se bajan **manualmente** del
navegador (Stooq lo permite) y se pasan al converter. El fetch automatizado se **difiere a
Etapa 9** (coherente con ADR-003, que ya cuestiona la fiabilidad de Stooq a escala). El
converter es agnóstico a CÓMO llegó el CSV → respeta D3 sin atarse al transporte.

### D-T5.2.2 — Verificación por round-trip (sin esperar data live)

El núcleo se verificó con un **round-trip contra el `spy.zip` de referencia**: se generó un
CSV en formato Stooq DESDE el zip LEAN conocido (reverso ×10000), **desordenado a propósito**
(descendente), se pasó por el converter, y la salida reprodujo el formato LEAN **byte-a-byte
en valores** (5849/5849 filas, primera/última correctas). Esto valida el núcleo sin depender
del fetch bloqueado. Es independiente del cross-check SPY de T5.3 (que compara converter vs
zip sobre data real Stooq, aún pendiente de los CSV manuales).

### D-T5.2.3 — Escritura a staging en la verificación (no pisar el zip de referencia)

El fixture de regresión T4 lee `data/equity/usa/daily/spy.zip` (reference LEAN). La
verificación de T5.2 escribió a `/tmp/stooq_staging/` para NO clobberear ese zip. El default
de `--out` es `data/equity/usa/daily`, que SÍ reemplazaría zips en una corrida real con CSV
de Stooq; cuando eso pase (T5.3+), el cross-check SPY debe correr ANTES de sobrescribir, o
escribir SPY-Stooq a otro nombre/ruta para comparar contra el reference. Anotar en T5.3.

## Pendiente (para cerrar T5 / continuar F2)

- **CSV manuales de Stooq** (insumo de T5.3/T5.4): bajar del navegador SPY/AAPL/IBM (FB
  opcional) en formato daily CSV y pasarlos por el converter. Patrón de URL de descarga
  manual: `https://stooq.com/q/d/?s=spy.us` → botón de descarga, o el endpoint
  `q/d/l/?s=<sym>.us&i=d` desde el navegador con sesión válida. Confirmar el toggle de
  ajuste por splits en la UI (debe ser split-adjusted para cuadrar con el zip LEAN).
- **T5.3** — factor_files neutros + map_files + cross-check SPY-only (converter-Stooq ==
  zip en fechas solapadas). Ojo D-T5.2.3: no sobrescribir el reference antes de comparar.
- **T5.4** — el fetcher automatizado queda como pregunta de Etapa 9 (anti-bot + cuota).
  El núcleo del converter ya está listo para recibir el CSV venga de donde venga.
- **AAPL/IBM/FB con splits:** su factor file real (no neutro) importa para el modo de
  normalización; el converter escribe precios tal cual del CSV Stooq (split-adjusted) →
  con factor neutro (=1) el reader los sirve sin reajuste (D3). Verificar en T5.3.
