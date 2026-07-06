# ADR-002 — Constraint de autenticación QC para módulos de brokerage

**Estado:** aceptado  
**Fecha:** 2026-06-11  
**Supersede a:** —  
**Supersedido por:** —

---

## Contexto

Durante la Etapa 1 se investigó si la ausencia de credenciales de QuantConnect (QC) afecta alguna etapa del plan. La investigación se hizo leyendo el código fuente del LEAN CLI v1.0.225.

### Mecanismo de módulos del CLI

`lean live` y `lean data download` usan un sistema de módulos NuGet. Para cada brokerage/data-provider con `"installs": true` en `modules-1.14.json`, el CLI llama:

```
POST modules/list   { productId, organizationId }   → lista de paquetes NuGet
POST modules/read   { productId, organizationId }   → link de descarga
```

Ambas llamadas requieren credenciales QC válidas **y** que la organización tenga licencia para el módulo. El check es **server-side**; el CLI no lo valida localmente.

### Hallazgo sobre AlpacaBrokerage

```json
{
  "id": "AlpacaBrokerage",
  "installs": true,
  "minimum-seat": "Researcher",
  "product-id": "347",
  "platform": ["cloud", "local", "cli"]
}
```

- `installs: true` → el CLI intenta descargar el módulo antes de arrancar el engine.
- `minimum-seat: "Researcher"` → requiere al menos el plan Researcher de QC (de pago). El CLI almacena este valor pero **no lo verifica localmente**; el servidor lo rechaza si la org no tiene esa suscripción.

### Hallazgo sobre `lean backtest`

`lean backtest` también llama `ensure_module_installed()`, pero para el data provider por defecto (`Local`, `DefaultDataProvider`) el flag `installs` es `False`. Por eso los backtests con datos locales **no necesitan credenciales QC**.

---

## Comandos afectados vs. no afectados

| Comando | Necesita QC auth | Motivo |
|---|---|---|
| `lean backtest "trade-scanner"` (data local) | ❌ No | `DefaultDataProvider` → `installs: false` |
| `lean project-create` | ❌ No | Operación local |
| `pytest` en Docker | ❌ No | Sin CLI, sin módulos |
| `lean live "trade-scanner"` con Alpaca | ✅ Sí | `AlpacaBrokerage` → `installs: true` |
| `lean data download` con Alpaca | ✅ Sí | mismo mecanismo de módulos |

**Impacto por etapa:**
- Etapas 2–8: no afectadas (todo corre vía `lean backtest` con data local).
- **Etapa 9: bloqueada** en `lean live` y en `lean data download` si no se resuelve antes.

---

## Opciones para Etapa 9

### Opción A — Suscripción QC Researcher (pago)
Contratar el plan mínimo de QC que incluye el módulo de Alpaca. El CLI descarga el .dll automáticamente.

**Pro:** sin trabajo extra, flujo estándar.
**Contra:** costo mensual recurrente; no alineado con el objetivo "$0/mes en Fase 1" de SPECS §7.

### Opción B — Compilar e instalar el módulo manualmente ($0)
El brokerage de Alpaca para LEAN es open source (`QuantConnect/Lean.Brokerages.Alpaca`, Apache-2.0). Se puede compilar el .dll y montarlo en el contenedor Docker con `--volume`, saltando el sistema de módulos del CLI.

**Pro:** $0; control total sobre la versión.
**Contra:** requiere compilar C# (.NET SDK) y configurar el mount manualmente; más frágil ante actualizaciones del engine. **El módulo es brokerage-only** (order routing + contexto de cuenta); el feed de datos se configura aparte. Útil **solo** para `lean live` paper con feed en tiempo real.

### Opción C — Script de descarga directa de datos desde Alpaca REST API ($0)
Para el problema de datos históricos (backtest 6–12 meses): escribir un script Python que use la API REST de Alpaca (accesible solo con la API key, sin QC) y genere archivos en el formato LEAN (`data/equity/usa/daily/<ticker>.zip`). Para `lean live`, combinar con Opción A o B.

**Pro:** $0 para datos históricos; usa las mismas credenciales Alpaca ya configuradas. **Reusa el converter ya construido en Etapa 5B (F3, Stooq→zip):** la mecánica CSV-OHLCV→zip LEAN ya existe y está testeada; cambiar la fuente de filas de Stooq a Alpaca REST es incremental.
**Contra:** requiere entender el formato interno de datos LEAN (ya resuelto en 5B); no resuelve `lean live` (feed en tiempo real).

---

## Ampliación (investigación 2026-06-20)

### Hallazgo decisivo: la pantalla solo necesita barras DIARIAS como input
Las SMAs de W/M se construyen con consolidators de calendario de LEAN a partir de barras **diarias** (regla dura CLAUDE.md; verificado en Etapa 5A T3.9). Consecuencia para esta decisión:

- **Todo el backtest de marcos D/W/M —incluida la validación de 6–12 meses (Etapa 9)— necesita únicamente historia diaria.** No hace falta minute ni un feed en vivo para validar la lógica D/W/M.
- El **único** consumidor que exige un feed en tiempo real es `lean live` paper con `working_bar` intradía (`partial_bar=True`, Etapa 9A T7) — y eso requiere suscripción `Resolution.MINUTE` viva.

Esto separa limpiamente el problema en dos: **(1) datos históricos D/W/M** (cubierto 100% por Opción C, $0) y **(2) feed live intradía** (lo único que necesita B o A).

### Local vs cloud para D/W/M
- **Local ($0):** zips diarios generados por Opción C + `DefaultDataProvider`. Es la **misma ruta ya probada** en Etapas 2–8 (data local sin auth QC; el converter de 5B ya emite zips válidos). Cubre D/W/M y backtests largos.
- **Cloud ($0):** el **free tier de QC incluye backtesting cloud ilimitado con datos** (resoluciones minute→daily) sin costo. En cloud **no se necesita Alpaca**: el mismo `main.py`/`core/*` corre con el data provider de QC. El free tier **no** permite live/paper (eso arranca en ~$60/mes, plan Quant Researcher).

→ El criterio nº5 del SPECS (cambiar fuente en `lean.json` sin tocar código) se cumple de forma natural con **zips Alpaca/Stooq (local) ↔ data provider QC (cloud)** — sin depender del módulo live de Alpaca para demostrar portabilidad.

### Realidad del módulo Alpaca y de `lean data download`
- El data/history provider de Alpaca en `lean.json` y `lean data download` **disparan el mismo sistema de módulos NuGet** (`installs: true`) → auth QC server-side. No hay flag local que lo salte salvo compilar el módulo (B).
- `lean data download` desde el dataset de QC pide aceptar términos y gastar **QCC (créditos)** → no es la vía $0.
- `Lean.Brokerages.Alpaca` es **brokerage-only**: aunque se compile (B), el feed de datos sigue configurándose por separado.

### Método más usado en la comunidad
1. **Pagar QC (cloud)** — la vía estándar para usuarios serios/live; sin fricción, pero con costo. Es lo que QC empuja.
2. **Para $0 local: scripts de descarga que escriben formato LEAN** — el patrón dominante. Existen downloaders comunitarios de Alpaca (p. ej. `sneilan/alpaca-historical-data-downloader`, sincroniza barras diarias de todo el universo) y los downloaders del antiguo *LEAN Toolbox*. Es **exactamente la Opción C**.
3. **Compilar módulos de brokerage (B)** es comparativamente **raro y frágil**; se usa cuando se necesita `lean live` $0 con un broker específico, no para datos.

→ El método más usado para datos $0 en local **es la Opción C**. B es un nicho para live sin pagar.

---

## Decisión (recomendación de criterio)

**Postura recomendada — C como columna vertebral de datos; cloud QC free para portabilidad; B solo como escape de "live a $0".**

1. **Datos D/W/M (local, $0) → Opción C.** Extender el converter de 5B a un downloader Alpaca REST que emita zips diarios LEAN. Cubre warmup + backtest 6–12 meses + toda la lógica D/W/M. Sin C#, sin mounts, sin auth QC, sin fragilidad ante updates del engine.
2. **Cloud D/W/M + portabilidad (criterio nº5) → free tier de QC.** Correr el mismo algoritmo en QC cloud con su data provider ($0, datos incluidos). La demostración de "fuente = solo `lean.json`" se hace zips-locales ↔ QC-cloud, sin el módulo live de Alpaca.
3. **`lean live` paper con working bar intradía (Etapa 9A T7) → diferir.** Es el único criterio que exige feed en tiempo real. Si se quiere a $0, **Opción B** (compilar + montar el .dll); si el presupuesto lo permite, **Opción A** es la ruta estándar y no frágil. Tratar este punto como rebanada aparte: la validación D/W/M (lo importante del screener) no depende de él.
4. **No elegir A ahora** (rompe el objetivo $0/mes). Revisar solo si el live paper se vuelve requisito firme.

**Por qué C sobre B como elección primaria:** B es más esfuerzo (toolchain .NET), más frágil (rompe con cada bump del engine), y **no resuelve datos** (es brokerage-only) — su único dominio es el feed live, que ni siquiera es necesario para validar D/W/M. C es $0, reusa código ya probado, y resuelve el 100% de lo que la pantalla necesita para sus marcos diario/semanal/mensual, tanto en local como (vía QC free) en cloud.

**Nota para Etapa 9A:** el spec actual asume Alpaca como data+broker provider vía `lean.json`. Esta ampliación sugiere que la **demostración de portabilidad (T6)** y la **validación D/W/M (T5)** se hagan con C + QC-cloud, reservando el módulo live de Alpaca (T4/T7) como rebanada opcional. Si se adopta, proponer la edición correspondiente a [etapa-09a](../fase-1-desarrollo-local/etapa-09a-conexion-alpaca.md) antes de implementar.

---

## Fuentes consultadas
- [Lean.Brokerages.Alpaca (GitHub)](https://github.com/QuantConnect/Lean.Brokerages.Alpaca) — Apache-2.0, brokerage-only, data feed aparte.
- [Alpaca brokerage — docs LEAN CLI](https://www.lean.io/docs/v2/lean-cli/live-trading/brokerages/alpaca)
- [QuantConnect Pricing](https://www.quantconnect.com/pricing/) y [Tier Features](https://www.quantconnect.com/docs/v2/cloud-platform/organizations/tier-features) — free tier: backtest cloud ilimitado con datos; live desde ~$60/mes.
- [lean data download — docs](https://www.quantconnect.com/docs/v2/lean-cli/api-reference/lean-data-download) — términos + QCC.
- [sneilan/alpaca-historical-data-downloader](https://github.com/sneilan/alpaca-historical-data-downloader) — patrón comunitario de descarga de barras diarias Alpaca.

---

## Consecuencias inmediatas

- `lean init` también requería credenciales QC (para seleccionar organización). Se resolvió descargando `config.json` directamente del repo público de GitHub y aplicando la transformación `clean_lean_config` del CLI. Ver [etapa-01.md](../fase-1-desarrollo-local/etapa-01.md).
- Etapa 1 queda completable sin credenciales QC.
- El flag en Etapa 9 de PLAN.md apunta a este ADR.

---

## Revisión futura

Revisar si QC agrega un tier gratuito para módulos locales, o si el módulo de Alpaca pasa a estar incluido en la imagen Docker base (`quantconnect/lean`).
