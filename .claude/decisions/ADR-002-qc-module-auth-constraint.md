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
| `lean backtest "Screener"` (data local) | ❌ No | `DefaultDataProvider` → `installs: false` |
| `lean project-create` | ❌ No | Operación local |
| `pytest` en Docker | ❌ No | Sin CLI, sin módulos |
| `lean live "Screener"` con Alpaca | ✅ Sí | `AlpacaBrokerage` → `installs: true` |
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
El brokerage de Alpaca para LEAN es open source (`QuantConnect/Lean.Brokerages.Alpaca`). Se puede compilar el .dll y montarlo en el contenedor Docker con `--volume`, saltando el sistema de módulos del CLI.

**Pro:** $0; control total sobre la versión.  
**Contra:** requiere compilar C# (.NET SDK) y configurar el mount manualmente; más frágil ante actualizaciones del engine.

### Opción C — Script de descarga directa de datos desde Alpaca REST API ($0)
Para el problema de datos históricos (backtest 6–12 meses): escribir un script Python que use la API REST de Alpaca (accesible solo con la API key, sin QC) y genere archivos en el formato LEAN (`data/equity/usa/daily/<ticker>.zip`). Para `lean live`, combinar con Opción A o B.

**Pro:** $0 para datos históricos; usa las mismas credenciales Alpaca ya configuradas.  
**Contra:** requiere entender el formato interno de datos LEAN; no resuelve `lean live`.

---

## Decisión

**Diferida hasta el inicio de Etapa 9.** Las Etapas 2–8 no están bloqueadas. Antes de comenzar Etapa 9, elegir entre Opción A, B o C (o combinación) y actualizar este ADR con la elección.

La Opción C (script de datos) es independiente y puede implementarse antes de Etapa 9 si se necesitan datos históricos reales para backtests largos (Etapa 9, criterio "backtest 6–12 meses").

---

## Consecuencias inmediatas

- `lean init` también requería credenciales QC (para seleccionar organización). Se resolvió descargando `config.json` directamente del repo público de GitHub y aplicando la transformación `clean_lean_config` del CLI. Ver [etapa-01.md](../fase-1-desarrollo-local/etapa-01.md).
- Etapa 1 queda completable sin credenciales QC.
- El flag en Etapa 9 de PLAN.md apunta a este ADR.

---

## Revisión futura

Revisar si QC agrega un tier gratuito para módulos locales, o si el módulo de Alpaca pasa a estar incluido en la imagen Docker base (`quantconnect/lean`).
