# Etapa 10 — Refinamiento post-9B

**Fecha:** 2026-07-08 · **Rama:** `feature/etapa-6-features-rules`

Mejoras puntuales de ergonomía y operabilidad aplicadas sobre la base consolidada de E1–E9B. Ningún cambio afecta lógica de scan, reglas, indicadores ni persistencia.

---

## R1 — Toggle de estrategias (`enabled` en `strategies.json`)

**Motivación:** para probar una estrategia en aislamiento había que comentar entradas en el JSON o tocar `main.py`. Con cuatro estrategias activas el backtest es más lento y los logs más ruidosos.

**Cambio:**
- `config/strategies.json`: campo `"enabled": true/false` en cada entrada de `strategies`. Default implícito `true` (retrocompatible con configs sin el campo).
- `trade-scanner/main.py` (línea ~56): `strategies_config` se filtra al cargarse — `{name: cfg for name, cfg in ... if cfg.get("enabled", True)}`. Todos los loops posteriores (universo, requirements de warmup, pipelines, schedule) heredan el filtro sin cambios adicionales. La validación de grupos en `notifications.json` ya filtraba por `m in self.pipelines`, así que resiste sin modificación.

**Estado actual:** solo `swing_eod` habilitada.

**Cómo togglear:** editar `"enabled"` en `config/strategies.json` + resembrar con `bash scripts/seed_object_store.sh`.

**Archivos tocados:**
- `config/strategies.json`
- `trade-scanner/main.py`

---

## R2 — `buckets_allowed` por (TF, periodo) desde config

**Motivación:** hoy `buckets_allowed` está hardcodeado en `strategies/swing_eod.py` (`ABOVE = {"above_mild", "above_strong", "extended_above"}`) y se aplica igual a todos los timeframes y periodos. Para calibrar criterios de entrada sin tocar código —p. ej. SMA8-W solo acepta `near`, SMA20-W acepta `near` y `mild`, SMA20-D es más permisiva— hace falta exponer ese set en config.

**Estado:** implementado y testeado (T1–T5).

**Diseño:**

El cambio raíz es dividir `SMAPositionRule(20, ["D","W","M"])` (una regla, mismo set para los 3 TFs) en tres reglas por-TF independientes. Eso permite que cada `(tf, period)` tenga su propio `buckets_allowed` leído de config.

### Config — nuevo bloque `"filters"` en `strategies.json`

```json
"swing_eod": {
  "filters": {
    "W:8":  ["near"],
    "W:20": ["near", "above_mild"],
    "M:20": ["near", "above_mild"],
    "D:8":  ["near", "above_mild"],
    "D:20": ["near", "above_mild", "above_strong", "extended_above"]
  }
}
```

- Vocabulario canónico `"above"`; el espejo al `side` short se aplica en `build_rules`, igual que hoy.
- Clave `"tf:period"` ausente → la rule usa el default del código (`ABOVE`).
- Bloque `"filters"` ausente → todo usa defaults (retrocompatible).

### Tareas de implementación

**T1 — `config/strategies.json`:** añadir bloque `"filters"` opcional a cada estrategia.

**T2 — `core/features.py`:** función nueva `resolve_filters(full_config, strategy_name) -> dict[tuple[str,int], frozenset[str]]`. Parsea `"W:20"` → `("W", 20)`, valida que cada bucket ∈ `BUCKETS`, lanza `ValueError` claro ante nombres desconocidos. Análoga a `resolve_bucket_thresholds`.

**T3 — `strategies/base.py`:** cambiar tipo de factories y firmas:
```python
# Antes
rules: list[Callable[[str], SMAPositionRule]]
def build_rules(self, side: str) -> list[SMAPositionRule]

# Después
rules: list[Callable[[str, dict], list[SMAPositionRule]]]
def build_rules(self, side: str, filters: dict = {}) -> list[SMAPositionRule]
def series(self, side: str, filters: dict = {}) -> set[tuple[str, int]]
```
`build_rules` aplana lista-de-listas (cada factory devuelve una lista de rules por-TF).

**T4 — `strategies/swing_eod.py`:** factories divididas por TF; `ABOVE` queda como fallback:
```python
lambda side, f: [
    SMAPositionRule(20, [tf], f.get((tf, 20), ABOVE), side)
    for tf in ["D", "W", "M"]
],
lambda side, f: [SMAPositionRule(8, ["D"], f.get(("D", 8), ABOVE), side, required=False)],
lambda side, f: [NotExtended(8, "D", side)],   # concepto fijo, no configurable
```
`market_close` hereda el cambio gratis (comparte `swing_eod.rules` por referencia).

**T5 — `main.py`:** llamar `resolve_filters` por estrategia y pasar a `build_rules`/`series`:
```python
filters = resolve_filters(full_config, name)
series = composition.series(side, filters)
...
rules=composition.build_rules(side, filters),
```

### Archivos tocados

| Archivo | Cambio |
|---|---|
| `config/strategies.json` | bloque `"filters"` opcional |
| `core/features.py` | `resolve_filters()` nueva |
| `strategies/base.py` | tipo de factory + firmas `build_rules`/`series` |
| `strategies/swing_eod.py` | factories divididas por TF |
| `main.py` | llamada a `resolve_filters` + pasar a `build_rules`/`series` |
| `strategies/market_close.py` | sin cambios |
| `core/rules.py` | sin cambios |
| `core/pipeline.py` | sin cambios |

### Efecto secundario conocido

Dividir la regla SMA20-multi-TF en 3 reglas sube `rules_passed_count` de 1 a 3 para esa regla. Los criterios de pase (AND sobre todos los TFs) se preservan. El campo es informativo para el trader, no una condición de filtrado.
