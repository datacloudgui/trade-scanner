"""Estrategias declarativas: composición de Rules sobre SymbolData (L4)."""

from strategies.base import StrategyConfig
from strategies.market_close import market_close
from strategies.swing_eod import swing_eod

# Registro nombre-de-config (clave en strategies.json) → StrategyConfig (D7.9-C3). Las variantes
# `*_short` apuntan a la MISMA instancia que su long: el `side` se resuelve aparte vía `direction`
# (SIDE_BY_DIRECTION) en main.py, no por stripping de sufijo. 4 claves → 2 instancias.
STRATEGIES: dict[str, StrategyConfig] = {
    "swing_eod": swing_eod,
    "swing_eod_short": swing_eod,
    "market_close": market_close,
    "market_close_short": market_close,
}

__all__ = ["STRATEGIES", "StrategyConfig", "market_close", "swing_eod"]
