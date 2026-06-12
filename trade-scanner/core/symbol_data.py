"""SymbolData: consolidators + SMAs de la unión de timeframes declarados, por símbolo (L2).

Cadena de datos (D4): update(bar) → consolidator diario → SMAs D + consolidators W/M
encadenados a la barra diaria consolidada. W/M nunca consumen minutos directamente:
warmup (barras diarias históricas) y runtime (barras minute) comparten una sola ruta.

Sin instancia del algorithm (D3): cada SMA se suscribe al evento data_consolidated
de su consolidator — el mismo cableado que register_indicator hace por dentro, con
APIs del engine idénticas en local y QC cloud.

Sin imports de AlgorithmImports a nivel de módulo (patrón universe/timeframes): el
CLR se carga al construir la instancia, así `import core` funciona en el host.
"""
from typing import Any

from core.timeframes import TIMEFRAMES


class SymbolData:
    """Estado de mercado de un símbolo: solo lo declarado, nada de más.

    requirements = unión de (tf → periodos) de todas las estrategias que usan el
    símbolo, ej. {"D": {8, 20}, "W": {20}}. Un timeframe con set vacío no construye
    nada. El consolidator diario existe siempre: es la raíz de la cadena y la
    fuente de working_bar, declare D periodos o no.
    """

    def __init__(self, symbol: Any, requirements: dict[str, set[int]]) -> None:
        from AlgorithmImports import SimpleMovingAverage

        for tf_code in requirements:
            if tf_code not in TIMEFRAMES:
                raise KeyError(
                    f"Unknown timeframe '{tf_code}' in requirements "
                    f"(registered: {sorted(TIMEFRAMES)})"
                )
            spec = TIMEFRAMES[tf_code]
            if spec.source_resolution != "daily":
                raise ValueError(
                    f"Timeframe '{tf_code}' (source_resolution='{spec.source_resolution}') "
                    f"is not supported by SymbolData yet: only the daily-sourced "
                    f"chain (D→W/M) is implemented"
                )

        self.symbol = symbol
        self._smas: dict[tuple[str, int], Any] = {}
        self._chained: dict[str, Any] = {}
        self._daily = TIMEFRAMES["D"].make_consolidator()

        for tf_code, periods in requirements.items():
            if not periods:
                continue
            if tf_code == "D":
                consolidator = self._daily
            else:
                consolidator = TIMEFRAMES[tf_code].make_consolidator()
                self._chained[tf_code] = consolidator
            for period in sorted(periods):
                sma = SimpleMovingAverage(f"{symbol}_{tf_code}_{period}", period)
                # end_time, no time: con time la SMA quedaría desplazada un periodo
                consolidator.data_consolidated += (
                    lambda _sender, bar, _sma=sma: _sma.update(bar.end_time, bar.close)
                )
                self._smas[(tf_code, period)] = sma

        self._daily.data_consolidated += self._feed_chained

    def _feed_chained(self, _sender: Any, daily_bar: Any) -> None:
        for consolidator in self._chained.values():
            consolidator.update(daily_bar)

    def update(self, bar: Any) -> None:
        """Único punto de entrada: barra minute (runtime) o diaria (warmup histórico)."""
        self._daily.update(bar)

    def scan(self, time: Any) -> None:
        """Fuerza la emisión de las barras cuyo periodo ya venció a la hora `time`.

        LEAN emite de forma perezosa incluso con barras diarias que llenan exactamente
        el periodo (verificado 2026-06-11): sin este flush tras el último push del
        warmup, la última barra diaria queda en working y las SMAs un periodo frías.
        """
        self._daily.scan(time)
        for consolidator in self._chained.values():
            consolidator.scan(time)

    @property
    def daily_consolidator(self) -> Any:
        """Consolidator raíz; main.py (5B) lo conecta a la suscripción minute."""
        return self._daily

    @property
    def working_bar(self) -> Any:
        """OHLC parcial del día en curso (working_data), o None antes de la primera barra."""
        return self._daily.working_data

    @property
    def declared(self) -> set[tuple[str, int]]:
        """Series (tf, period) realmente construidas — introspección para tests y logs."""
        return set(self._smas)

    @property
    def timeframes(self) -> set[str]:
        """Timeframes con consolidator construido (la raíz 'D' existe siempre)."""
        return {"D", *self._chained}

    def consolidator(self, tf: str) -> Any:
        """Consolidator del timeframe construido ('D' = raíz, siempre existe); KeyError
        con los construidos si no. Permite a L5 colgar observers (ej. captura de
        evidencia por barra consolidada) sin tocar el wiring interno."""
        if tf == "D":
            return self._daily
        try:
            return self._chained[tf]
        except KeyError:
            raise KeyError(
                f"Timeframe '{tf}' sin consolidator para '{self.symbol}' "
                f"(construidos: {sorted(self.timeframes)})"
            ) from None

    def close(self, tf: str) -> float:
        """Cierre de la última barra consolidada del timeframe (lectura para L3, D3 Etapa 6).

        Sin guard de consolidated=None: el contrato de fríos vive en L3
        (position_vs_sma exige is_ready antes de leer)."""
        return float(self.consolidator(tf).consolidated.close)

    def sma(self, tf: str, period: int) -> Any:
        """SMA declarada para (tf, period); KeyError con las series declaradas si no existe."""
        try:
            return self._smas[(tf, period)]
        except KeyError:
            declared = ", ".join(f"{t}:{p}" for t, p in sorted(self._smas)) or "none"
            raise KeyError(
                f"SMA {tf}:{period} not declared for '{self.symbol}' (declared: {declared})"
            ) from None

    def is_ready(self, tf: str | None = None, period: int | None = None) -> bool:
        """Sin args: todas las SMAs declaradas calientes. Con tf y period: una serie concreta."""
        if (tf is None) != (period is None):
            raise ValueError("Pass both tf and period for one series, or neither for all")
        if tf is None:
            return all(s.is_ready for s in self._smas.values())
        return self.sma(tf, period).is_ready
