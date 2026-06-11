# region imports
from AlgorithmImports import *

import json

import core
from core.symbol_data import SymbolData
from core.universe import UniverseSpec
import strategies
# endregion


class Tradescanner(QCAlgorithm):
    """Orquestación L5 (Etapa 5B): config desde ObjectStore, universo efectivo por
    entorno, un SymbolData por símbolo suscrito a DAILY con su consolidator cableado
    a la suscripción (T2.1), y un ScheduledEvent por estrategia que SOLO loguea.
    Warmup (T2.2), features y rules (Etapas 6+) llegan después."""

    def initialize(self):
        # Ventana corta ≥2016 (D5): el valor está en la historia previa al start
        # (M:200 ≈ 4221 barras diarias; SPY-zip arranca en 1998), no en la duración.
        self.set_start_date(2016, 1, 4)
        self.set_end_date(2016, 1, 15)
        self.set_cash(100000)

        # Config de negocio desde ObjectStore (key = ruta relativa bajo storage/).
        raw = self.object_store.read("config/strategies.json")
        full_config = json.loads(raw)

        env = self.get_parameter("env", "prod")
        env_cfg = full_config["environments"][env]
        top_n = env_cfg["top_n"]
        max_universe = env_cfg["max_universe"]
        strategies_config = full_config["strategies"]

        # Universo efectivo: el override de environment (harness dev, D2) fuerza el
        # universo de TODAS las estrategias; sin override cada una usa el suyo (prod).
        universe_override = env_cfg.get("universe")
        tickers: set[str] = set()
        for name, cfg in strategies_config.items():
            universe_key = f"universes/{universe_override or cfg['universe']}.csv"
            spec = UniverseSpec(
                universe_key=universe_key,
                filter_expr=cfg["universe_filter"],
                max_tickers=max_universe,
            )
            loaded = spec.load(self.object_store)
            tickers.update(loaded)
            self.log(
                f"[{name}] universe loaded: {len(loaded)} tickers "
                f"(env={env}, max={max_universe}, key={universe_key})"
            )

        requirements = self._build_requirements(env_cfg, strategies_config)

        # T2.1 — suscripción DAILY + SymbolData + wiring consolidator→suscripción.
        # El wiring va SIEMPRE antes de cualquier warmup: set_warm_up (T2.2) reusa
        # este cableado para stremear la historia por la suscripción.
        self.symbol_data: dict[Symbol, SymbolData] = {}
        self._daily_received: dict[Symbol, int] = {}
        self._daily_consolidated: dict[Symbol, int] = {}
        for ticker in sorted(tickers):
            symbol = self.add_equity(
                ticker,
                Resolution.DAILY,
                data_normalization_mode=DataNormalizationMode.SPLIT_ADJUSTED,
            ).symbol
            sd = SymbolData(symbol, requirements)
            self.subscription_manager.add_consolidator(symbol, sd.daily_consolidator)
            # Contadores de evidencia del criterio 1:1 de T2.1 (se loguean al final).
            self._daily_received[symbol] = 0
            self._daily_consolidated[symbol] = 0
            sd.daily_consolidator.data_consolidated += (
                lambda _sender, bar, s=symbol: self._count_consolidated(s)
            )
            self.symbol_data[symbol] = sd
            declared = ", ".join(f"{tf}:{p}" for tf, p in sorted(sd.declared))
            self.log(f"[{ticker}] SymbolData listo (series: {declared})")

        # Ancla de calendario para las time-rules: SPY del universo si está suscrito;
        # si no (prod), suscripción propia. Provee data (avanza el reloj) y market hours.
        spy = next((s for s in self.symbol_data if s.value == "SPY"), None)
        self.spy = spy or self.add_equity("SPY", Resolution.DAILY).symbol

        # Un ScheduledEvent por estrategia; el callback SOLO loguea (reglas en Etapa 7).
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

    def on_data(self, data: Slice):
        """Solo evidencia T2.1: cuenta las barras diarias que entrega la suscripción."""
        for symbol in self.symbol_data:
            if data.bars.contains_key(symbol):
                self._daily_received[symbol] += 1

    def on_end_of_algorithm(self):
        """Evidencia del criterio 1:1 (T2.1): cada barra de la suscripción terminó en el
        consolidator — emitida, o retenida como working bar (emisión perezosa, 5A #1)."""
        for symbol, sd in self.symbol_data.items():
            received = self._daily_received[symbol]
            consolidated = self._daily_consolidated[symbol]
            working = sd.working_bar
            pending = 1 if working is not None else 0
            status = "1:1 OK" if received == consolidated + pending else "1:1 MISMATCH"
            tail = f", working hasta {working.end_time}" if working is not None else ""
            self.log(
                f"[{symbol.value}] feed daily→consolidator {status}: "
                f"{received} recibidas, {consolidated} consolidadas{tail}"
            )

    def _count_consolidated(self, symbol: Symbol) -> None:
        self._daily_consolidated[symbol] += 1

    def _build_requirements(
        self, env_cfg: dict, strategies_config: dict
    ) -> dict[str, set[int]]:
        """Series (tf → periodos) compartidas por todos los símbolos: el override de
        environment (harness dev, D2) reemplaza la unión de timeframes de las
        estrategias; sin override se usa la unión (prod). plan_warmup (T2.2) lo
        consumirá una sola vez, global."""
        override = env_cfg.get("timeframes")
        if override is not None:
            return {tf: set(periods) for tf, periods in override.items()}
        requirements: dict[str, set[int]] = {}
        for cfg in strategies_config.values():
            for tf, periods in cfg["timeframes"].items():
                requirements.setdefault(tf, set()).update(periods)
        return requirements

    def _time_rule_for(self, schedule: str):
        """Mapea el string de schedule a una time-rule de LEAN anclada a SPY. Punto de
        extensión: por ahora cubre los strings de la config; desconocido -> None (se omite)."""
        if schedule == "after_close":
            # +1 min para asegurar que la barra de cierre ya consolidó (ver decisión D5).
            return self.time_rules.after_market_close(self.spy, 1)
        if schedule == "before_close_30m":
            return self.time_rules.before_market_close(self.spy, 30)
        return None
