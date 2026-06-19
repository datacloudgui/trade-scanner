"""market_close: misma composición que swing_eod, evaluada ~30 min antes del cierre.

Reusa LAS MISMAS rules de swing_eod (D7.2; PLAN §6), sin lógica nueva: comparte el mismo list
de factories (`swing_eod.rules`), así "mismas reglas" es literal, no una copia que pueda divergir.
Única diferencia: `partial_bar=True`, porque corre con el mercado ABIERTO y su working bar es el
OHLC parcial del día en curso (D7.4). El precio sigue saliendo del working bar (reference_price),
igual que swing_eod — `partial_bar` es solo metadato del horario, no cambia la fuente de precio.
Puro: sin CLR.
"""
from strategies.base import StrategyConfig
from strategies.swing_eod import swing_eod

market_close = StrategyConfig(
    name="market_close",
    partial_bar=True,
    rules=swing_eod.rules,  # mismas factories que swing_eod: "mismas reglas" literal (PLAN §6)
)
