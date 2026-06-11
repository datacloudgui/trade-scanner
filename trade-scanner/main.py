# region imports
from AlgorithmImports import *

import json

import core
import strategies
# endregion


class Tradescanner(QCAlgorithm):
    """Walking skeleton (Etapa 2): ancla de calendario SPY, carga config desde ObjectStore
    y registra un ScheduledEvent por estrategia que SOLO loguea. Sin lógica de negocio:
    features, rules, universos y SymbolData llegan en Etapas 4+."""

    def initialize(self):
        self.set_start_date(2013, 10, 7)
        self.set_end_date(2013, 10, 11)
        self.set_cash(100000)

        # Ancla de calendario: SPY provee data (avanza el reloj del backtest) y market hours
        # (fija las time-rules after/before close). Las reglas reales scanean otro universo (Et. 4+).
        self.spy = self.add_equity("SPY", Resolution.MINUTE).symbol

        # Config de negocio desde ObjectStore (key = ruta relativa bajo storage/). Cero
        # config hardcodeada: nombres, schedule y universo salen del JSON, no del código.
        raw = self.object_store.read("config/strategies.json")
        strategies_config = json.loads(raw)["strategies"]

        # Un ScheduledEvent por estrategia; el callback SOLO loguea (sin reglas/universos/SymbolData).
        for name, cfg in strategies_config.items():
            time_rule = self._time_rule_for(cfg["schedule"])
            if time_rule is None:
                self.log(f"schedule desconocido '{cfg['schedule']}' para '{name}': omitido")
                continue
            self.schedule.on(
                self.date_rules.every_day(self.spy),
                time_rule,
                lambda name=name: self.log(f"scan {name} @ {self.time}"),
            )

    def _time_rule_for(self, schedule: str):
        """Mapea el string de schedule a una time-rule de LEAN anclada a SPY. Punto de
        extensión: por ahora cubre los strings de la config; desconocido -> None (se omite)."""
        if schedule == "after_close":
            # +1 min para asegurar que la barra de cierre ya consolidó (ver decisión D5).
            return self.time_rules.after_market_close(self.spy, 1)
        if schedule == "before_close_30m":
            return self.time_rules.before_market_close(self.spy, 30)
        return None
