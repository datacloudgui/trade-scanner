# Propuesta de diseño — #12: el scan cruza universos entre estrategias

**Fecha:** 2026-07-05 · **Estado:** PROPUESTA (sin implementar — requiere aprobación / posible ADR-006)
**Hallazgo:** triaje E1–E8 #12 (ALTO, corroborado por E4/E5/E7/E8)

## Problema

`initialize()` materializa el universo como **unión global** (`tickers: set[str]`, main.py) y
`run_group_scan` pasa `self.symbol_data` (el mapa completo) a CADA pipeline. Consecuencia: una
estrategia long rankea/evalúa también los símbolos de `swing_declines` y viceversa, y E8 lo
propaga a archivos/correo. Viola la entidad `UniverseSpec` (SPECS) y D7.5 (universos disjuntos).
Hoy lo mitigan las rules (precio vs SMA) y la dirección del ranking, pero no lo garantizan; en
dev queda enmascarado porque el override fuerza un único `sample_dev`.

## Diseño propuesto

**Invariante nuevo (candidato a ADR-006):** *cada pipeline escanea exactamente el mapa
`{Symbol: SymbolData}` de SU universo declarado; la unión global existe solo para
suscripción/warmup.*

1. **L2 sin cambios.** Se conserva "un símbolo = un `SymbolData` compartido" (CLAUDE.md): la
   unión global sigue decidiendo `add_equity` + `SymbolData` + plan de warmup (R4: un solo plan).
2. **`initialize()` conserva la pertenencia por estrategia.** Al cargar cada `UniverseSpec`,
   además de `tickers.update(loaded)`, guardar `tickers_by_strategy[name] = set(loaded)`.
   Tras el loop de `add_equity`, materializar UNA vez (los universos son estáticos en V1;
   `refresh_universe` es no-op):
   ```python
   self.symbol_data_by_strategy = {
       name: {s: sd for s, sd in self.symbol_data.items() if s.value in tickers}
       for name, tickers in tickers_by_strategy.items()
   }
   ```
3. **`run_group_scan` recibe el mapa por miembro.** Cambio de firma mínimo:
   `symbol_data_map: dict` → `symbol_data_by_member: dict[str, dict]`; adentro,
   `pipeline.scan(symbol_data_by_member.get(name, {}), ...)`. Un solo `emit` por base se
   mantiene intacto. Cero costo por scan (los mapas se construyen una vez en `initialize()`).
4. **dev no cambia de comportamiento:** el override de environment fuerza el mismo universo
   para todas las estrategias → todos los mapas son idénticos al actual.
5. **Solape entre universos** (un ticker en advances Y declines): permitido y sano — comparte
   `SymbolData` y cada estrategia lo evalúa por estar en SU universo. ADR-005 (no compartir
   snapshots) no se toca.

## Tests que cierran #25 (completo)

- `run_group_scan` con mapas por miembro **disjuntos** + `FakePipeline` que registra
  `scanned_with`: cada pipeline recibe exactamente su mapa, y las secciones long/short del
  emit solo contienen tickers de su universo.
- Test L5-style: `UniverseSpec` + `MockObjectStore` con CSVs advances/declines disjuntos →
  construir los mapas como en `initialize()` → verificar la partición.

## Decisiones abiertas (para Guille antes de implementar)

1. ¿ADR-006 nuevo ("scan acotado al universo declarado") o ampliación de ADR-005?
2. ¿Optimizar el warmup por símbolo (series = unión solo de las estrategias cuyo universo lo
   contiene)? Propongo NO en este ciclo: rompe R4 (un solo plan) por un ahorro marginal.
3. ¿Qué hacer con un miembro cuyo universo quedó vacío post-filtro? Propongo: sección vacía
   (comportamiento actual de "0 candidatos"), sin error.

**Tamaño estimado:** ~15 líneas en `main.py`, ~5 en `core/pipeline.py`, 2 tests nuevos +
ajuste de los tests de `run_group_scan`.
