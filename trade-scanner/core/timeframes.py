"""Registro declarativo de timeframes + fórmula de warmup + plan con presupuesto.

Sin imports de AlgorithmImports a nivel de módulo (patrón universe.py): el CLR
solo se carga dentro de las factories de consolidator, así el módulo es usable
desde tests de host y scripts sin Docker.
"""
from dataclasses import dataclass
from typing import Callable


def _daily_consolidator():
    from datetime import timedelta

    from AlgorithmImports import TradeBarConsolidator

    return TradeBarConsolidator(timedelta(days=1))


def _weekly_consolidator():
    from AlgorithmImports import Calendar, TradeBarConsolidator

    return TradeBarConsolidator(Calendar.WEEKLY)


def _monthly_consolidator():
    from AlgorithmImports import Calendar, TradeBarConsolidator

    return TradeBarConsolidator(Calendar.MONTHLY)


@dataclass(frozen=True)
class TimeframeSpec:
    """Una entrada del registro: añadir un timeframe = añadir una instancia, no editar fórmulas."""

    code: str                # "D" | "W" | "M" (futuros: "5T", "15T", "30T")
    source_resolution: str   # "daily" | "minute" — el mapeo a Resolution de LEAN vive en symbol_data
    bars_per_period: int     # barras fuente por barra consolidada: D=1, W=5, M=21
    buffer_bars: int         # colchón por barra parcial inicial + feriados: D=5, W=10, M=21
    consolidator_factory: Callable[[], object] | None = None

    def warmup_bars(self, period: int) -> int:
        """Barras fuente necesarias para calentar un indicador de `period` periodos."""
        return period * self.bars_per_period + self.buffer_bars

    def make_consolidator(self):
        """Construye el consolidator de LEAN (import perezoso: aquí sí se toca el CLR)."""
        if self.consolidator_factory is None:
            raise ValueError(f"Timeframe '{self.code}' has no consolidator factory")
        return self.consolidator_factory()


TIMEFRAMES: dict[str, TimeframeSpec] = {
    "D": TimeframeSpec("D", "daily", 1, 5, _daily_consolidator),
    "W": TimeframeSpec("W", "daily", 5, 10, _weekly_consolidator),
    "M": TimeframeSpec("M", "daily", 21, 21, _monthly_consolidator),
}


@dataclass(frozen=True)
class PlannedSeries:
    tf: str
    period: int
    warmup_bars: int


@dataclass(frozen=True)
class WarmupPlan:
    depth_by_resolution: dict[str, int]   # max de warmup_bars de las series incluidas, por resolución fuente
    included: list[PlannedSeries]
    excluded: list[PlannedSeries]         # series cuyo warmup_bars excede el presupuesto


def plan_warmup(
    requirements: dict[str, set[int]],
    budget: dict[str, int] | None = None,
    registry: dict[str, TimeframeSpec] | None = None,
) -> WarmupPlan:
    """Resuelve profundidades de warmup contra un presupuesto por resolución fuente.

    requirements: unión por símbolo, ej. {"D": {8, 20, 200}, "W": {8, 20, 200}}.
    budget: ej. {"daily": 1200}; None = sin límite. Series sobre presupuesto van
    a `excluded` — el llamador decide loguear y no crear esas SMAs.
    registry: registro de timeframes (default TIMEFRAMES; inyectable en tests).
    """
    registry = TIMEFRAMES if registry is None else registry
    included: list[PlannedSeries] = []
    excluded: list[PlannedSeries] = []

    for tf_code, periods in requirements.items():
        if tf_code not in registry:
            raise KeyError(
                f"Unknown timeframe '{tf_code}' in requirements "
                f"(registered: {sorted(registry)})"
            )
        spec = registry[tf_code]
        limit = None if budget is None else budget.get(spec.source_resolution)
        for period in sorted(periods):
            series = PlannedSeries(tf_code, period, spec.warmup_bars(period))
            if limit is not None and series.warmup_bars > limit:
                excluded.append(series)
            else:
                included.append(series)

    depth_by_resolution: dict[str, int] = {}
    for series in included:
        resolution = registry[series.tf].source_resolution
        depth_by_resolution[resolution] = max(
            depth_by_resolution.get(resolution, 0), series.warmup_bars
        )

    return WarmupPlan(depth_by_resolution, included, excluded)
