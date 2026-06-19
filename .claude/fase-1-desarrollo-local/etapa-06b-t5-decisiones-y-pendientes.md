# T5 (Etapa 6B) — Retirar `max_extension_pct` de la config (2026-06-18)

`config/strategies.json` (fuente versionada) + `storage/config/strategies.json` (artefacto sembrado,
gitignoreado). **D6B.8:** `max_extension_pct` es redundante con `bucket_thresholds.extended` (ambos
`0.10` en las 4 estrategias). El corte "extendido" es único y compartido; ya lo consume
`NotExtended` vía el snapshot (T4). Sembrado en Etapa 3 (`64a39cd`), **sin ningún consumidor en
código** → retiro limpio, sin regresión funcional.

## Resultado contra el criterio de aceptación (T5, criterios a–c)

| Criterio T5 | Estado | Evidencia |
|---|---|---|
| (a) `grep max_extension_pct` en `.py` vacío + clave ausente en `config/` y (tras seed) en `storage/` | ✅ | `grep --include=*.py` → exit 1; `grep config/ storage/` → exit 1 (vacío) tras la edición + reseed |
| (b) `diff config/strategies.json storage/config/strategies.json` vacío (round-trip) | ✅ | `diff` → **vacío** tras `bash scripts/seed_object_store.sh` |
| (c) `resolve_bucket_thresholds` resuelve `{near,mild,extended}` para las 4 estrategias desde el artefacto sembrado | ✅ | Las 4 (`swing_eod`, `swing_eod_short`, `market_close`, `market_close_short`) → `{near:0.005, mild:0.03, extended:0.1}` desde `storage/config/strategies.json` |

**Veredicto: ✅ T5 cerrado** (a–c). "Done when" #5 marcado `[x]`; **#7 (cero código muerto) cerrado**
(la parte de `rules.py`/tests venía de T3; T5 cierra la de `max_extension_pct`).

## Cambios

**`config/strategies.json`:**
- Eliminada la clave `"max_extension_pct": 0.10` de los **4** bloques de estrategia (`swing_eod`,
  `swing_eod_short`, `market_close`, `market_close_short`). Era la última clave de cada bloque, así que
  también se quitó la coma final del `universe_filter` precedente. JSON válido tras la edición.
- **Sin cambio de código** (`.py`) ni de `seed_object_store.sh`.

**Artefacto sembrado:** `bash scripts/seed_object_store.sh` copió `config/strategies.json` →
`storage/config/strategies.json` (`cp` directo, idempotente). La ausencia de la clave viaja sola.

## Verificación (comandos)

```
grep -rn "max_extension_pct" --include="*.py" .        → exit 1 (ya estaba limpio: cero consumidor)
grep -rn "max_extension_pct" config/ storage/          → exit 1 (clave ausente en fuente y artefacto)
diff config/strategies.json storage/config/strategies.json → vacío (round-trip idéntico)
resolve_bucket_thresholds(artefacto, <estrategia>)     → {near,mild,extended} para las 4 (sin cambio)
```

> Nota de método para (c): `core/__init__.py` importa `symbol_data` (CLR), así que `core.features` no
> se puede importar tal cual desde el host. `resolve_bucket_thresholds` es Python puro (sin LEAN) y
> `features.py` solo importa stdlib en runtime (el import de `SymbolData` está bajo `TYPE_CHECKING`),
> así que se cargó el módulo standalone vía `importlib.util.spec_from_file_location` para resolver
> contra `storage/config/strategies.json`. Los tests unitarios de `resolve_bucket_thresholds`
> (`test_features.py`, T2.2) siguen verdes desde T4 (135 passed); T5 no toca `.py`, no hay regresión.

## Decisiones tomadas

### D-T5.1 — Retiro de la clave, no comentada (consideración técnica #9)
Cero código muerto: la clave se **borra** de los 4 bloques, no se deja comentada ni con valor `null`.
La trazabilidad (origen E3 `64a39cd` → retiro 6B/D6B.8) queda en esta bitácora, no en el JSON.

### D-T5.2 — `seed_object_store.sh` sin cambios (validación de "viaja solo")
El criterio pide verificar que la ausencia viaja vía el seed **sin cambiar el script**. El `cp` de
`config/*.json → storage/config/` ya es agnóstico al contenido; reseed + `diff` vacío lo confirma.

## Pendiente (Etapa 6B)

- **T6** — Formateador de log (`format_filter_line`/`format_final_line`); decidir `rules.py` vs
  `pipeline.py` (preferencia `pipeline.py`). Reproduce **literalmente** las 4 líneas del ejemplo.
- **T7** — `ScanResult` (contrato mínimo en `core/pipeline.py`: `rules_passed_count`, `sma_evidence`)
  + alinear nota §5 de PLAN.md ("proyección del snapshot único").
- **Done when:** marcados #1 (T1), #2 (T2), #3 (T3), #4 (T4), **#5 (T5)**, **#7 (cero código muerto)**.
  Faltan #6 (formateador, T6) y el contrato de `ScanResult` (T7).
- **Commit:** acumulado sin commitear: T4 (rules+tests) + T5 (config) + ediciones de spec + bitácoras
  T4/T5 + (de T3) los dos docs de conceptos. T5 es commiteable como unidad
  (`[Etapa 6B] T5 retirar max_extension_pct de la config`). `storage/` está gitignoreado (no entra al
  commit; se regenera con el seed).
