"""swing_eod: estrategia swing evaluada tras el cierre (long/short según `direction`).

Composición declarativa (D7.2), sin lógica nueva: precio sobre SMA20 en D, W y M (una rule
por-tf, R2), precio sobre SMA8 diaria, y no-extendido sobre la SMA8 diaria. Las rules se
autoran en vocabulario canónico "above"; el pipeline inyecta el `side` (D7.3). `partial_bar=False`:
corre con el mercado ya cerrado, su working bar es la sesión completa aún no consolidada (D7.4).
market_close (T3.3) reusa estas mismas rules con `partial_bar=True`. Puro: sin CLR.
"""
from core.rules import NotExtended, SMAPositionRule
from strategies.base import StrategyConfig

# "above" ESTRICTO: `near` excluido — perseguir solo lo claramente sobre la SMA, no lo que está
# pegado a ella. La inclusión de `near` en "above" es calibración de Etapa 9 (ADR-005 §9.2); el
# default de V1 es estricto. Local a la estrategia: el seam natural si E9 calibra por estrategia.
# También el fallback cuando `filters` (R2, config `strategies.json["filters"]`) no trae una
# clave `"tf:period"` para el (tf, period) de esa rule.
ABOVE = frozenset({"above_mild", "above_strong", "extended_above"})


swing_eod = StrategyConfig(
    name="swing_eod",
    partial_bar=False,
    rules=[
        # SMA20 en D/W/M: una rule por-tf (no una multi-tf) para que R2 pueda calibrar
        # `buckets_allowed` distinto por (tf, period) desde config `filters`.
        lambda side, f: [
            SMAPositionRule(20, [tf], f.get((tf, 20), ABOVE), side, label="SMA")
            for tf in ("D", "W", "M")
        ],
        lambda side, f: [
            SMAPositionRule(8, ["D"], f.get(("D", 8), ABOVE), side, label="SMA", required=False)
        ],
        lambda side, f: [NotExtended(8, "D", side)],  # concepto fijo, no configurable por filters
    ],
)
