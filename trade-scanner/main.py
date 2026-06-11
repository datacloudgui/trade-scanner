# region imports
from AlgorithmImports import *

import json
from collections import deque
from time import perf_counter

import core
from core.symbol_data import SymbolData
from core.timeframes import TIMEFRAMES, plan_warmup
from core.universe import UniverseSpec
import strategies
# endregion


class Tradescanner(QCAlgorithm):
    """Orquestación L5 (Etapa 5B): config desde ObjectStore, universo efectivo por
    entorno, un SymbolData por símbolo suscrito a DAILY con su consolidator cableado
    a la suscripción (T2.1), warmup engine-managed con gate opcional contra la ruta
    manual (T2.2, D4; flag validate_warmup). Features y rules (Etapas 6+) llegan después."""

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

        # Plan de warmup global (R4: requirements idénticos entre símbolos → un solo
        # plan). Las series sobre presupuesto NO se construyen: warning por cada una.
        budget = env_cfg.get("warmup_budget")
        plan = plan_warmup(self._build_requirements(env_cfg, strategies_config), budget)
        for series in plan.excluded:
            res = TIMEFRAMES[series.tf].source_resolution
            self.log(
                f"WARNING [warmup] serie {series.tf}:{series.period} excluida del plan: "
                f"necesita {series.warmup_bars} barras ({res}), presupuesto {budget.get(res)}"
            )
        self._requirements: dict[str, set[int]] = {}
        for series in plan.included:
            self._requirements.setdefault(series.tf, set()).add(series.period)

        # T2.1 — suscripción DAILY + SymbolData + wiring consolidator→suscripción.
        # El wiring va SIEMPRE antes del warmup (consideración #8): set_warm_up
        # stremea la historia por la suscripción y los consolidators ya cuelgan de ella.
        self.symbol_data: dict[Symbol, SymbolData] = {}
        self._daily_received: dict[Symbol, int] = {}
        self._daily_consolidated: dict[Symbol, int] = {}
        for ticker in sorted(tickers):
            symbol = self.add_equity(
                ticker,
                Resolution.DAILY,
                data_normalization_mode=DataNormalizationMode.SPLIT_ADJUSTED,
            ).symbol
            sd = SymbolData(symbol, self._requirements)
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

        # T3 — recorder de validación (flag sma_validation, pensado para dev): captura
        # los últimos K=5 puntos (barra consolidada, SMA) por serie; el archivo se
        # escribe al cerrar el warmup (on_warmup_finished, tras el flush).
        self._validation_rows: dict[tuple[Symbol, str, int], deque] = {}
        if env_cfg.get("sma_validation", False):
            for symbol, sd in self.symbol_data.items():
                for tf in sorted(sd.timeframes):
                    periods = tuple(sorted(p for t, p in sd.declared if t == tf))
                    if not periods:
                        continue  # la raíz D existe aunque no declare series
                    for period in periods:
                        self._validation_rows[(symbol, tf, period)] = deque(maxlen=5)
                    sd.consolidator(tf).data_consolidated += (
                        lambda _s, bar, sym=symbol, t=tf, ps=periods:
                            self._record_validation(sym, t, ps, bar)
                    )

        # Ancla de calendario para las time-rules: SPY del universo si está suscrito;
        # si no (prod), suscripción propia. Provee data (avanza el reloj) y market hours.
        spy = next((s for s in self.symbol_data if s.value == "SPY"), None)
        self.spy = spy or self.add_equity("SPY", Resolution.DAILY).symbol

        # Un ScheduledEvent por estrategia; el callback SOLO loguea (reglas en Etapa 7)
        # y va guardado contra warmup dentro de _scan_stub.
        for name, cfg in strategies_config.items():
            time_rule = self._time_rule_for(cfg["schedule"])
            if time_rule is None:
                self.log(f"schedule desconocido '{cfg['schedule']}' para '{name}': omitido")
                continue
            self.schedule.on(
                self.date_rules.every_day(self.spy),
                time_rule,
                lambda name=name: self._scan_stub(name),
            )

        # T2.2 — Estrategia A (D4): warmup engine-managed (adoptada: gate 9/9 series
        # exactas vs ruta manual, 2026-06-11). El gate de cross-check queda detrás del
        # flag validate_warmup del environment — apagado por defecto: duplica el warmup.
        self._gate_enabled = bool(env_cfg.get("validate_warmup", False))
        self._warmup_depth = plan.depth_by_resolution.get("daily", 0)
        driver = max(plan.included, key=lambda s: s.warmup_bars, default=None)
        per_tf_max: dict[str, int] = {}
        for series in plan.included:
            per_tf_max[series.tf] = max(per_tf_max.get(series.tf, 0), series.warmup_bars)
        detail = ", ".join(f"{tf}:{max(self._requirements[tf])}→{bars}"
                           for tf, bars in sorted(per_tf_max.items()))
        if self._warmup_depth:
            self.set_warm_up(self._warmup_depth, Resolution.DAILY)
            self.log(
                f"[warmup] plan(daily): depth={self._warmup_depth} "
                f"(driver {driver.tf}:{driver.period}) | {detail}"
            )
        self._warmup_t0 = perf_counter()

    def on_data(self, data: Slice):
        """Instrumentación 1:1 (cuenta SIEMPRE, warmup incluido) + guard de warmup:
        nada de scans/escritura con data histórica (T2.2)."""
        for symbol in self.symbol_data:
            if data.bars.contains_key(symbol):
                self._daily_received[symbol] += 1
        if self.is_warming_up:
            return
        # Lógica de runtime (Etapas 6+) va debajo de este guard.

    def on_warmup_finished(self):
        """Cierre del warmup (T2.2/T2.3): flush de la emisión perezosa, evidencia de
        duración/ready/estrategia, y gate opcional de cross-check vs ruta manual (D4)."""
        elapsed = perf_counter() - self._warmup_t0
        streamed = sum(self._daily_received.values())

        # Hallazgo #1 de 5A aplica también a la ruta engine EN ESTE INSTANTE: la última
        # barra diaria del warmup sigue retenida (working) hasta la próxima barra o un
        # scan. Sin este flush, las SMAs quedan un periodo frías justo cuando T3 va a
        # escribir el archivo de validación.
        held = sum(1 for sd in self.symbol_data.values() if sd.working_bar is not None)
        for sd in self.symbol_data.values():
            sd.scan(self.time)
        self.log(
            f"[warmup] set_warm_up({self._warmup_depth}, DAILY) completado: {streamed} "
            f"barras stremeadas en {elapsed:.2f}s; flush scan({self.time}) emitió "
            f"{held} working bar(s) retenidas"
        )

        ready = sum(1 for sd in self.symbol_data.values() if sd.is_ready())
        self.log(f"[warmup] ready: {ready}/{len(self.symbol_data)} símbolos")
        for symbol, sd in self.symbol_data.items():
            if not sd.is_ready():
                cold = [f"{tf}:{p}" for tf, p in sorted(sd.declared)
                        if not sd.is_ready(tf, p)]
                self.log(f"WARNING [warmup] {symbol.value} series frías: {', '.join(cold)}")

        gate = "ON" if self._gate_enabled else "OFF (flag validate_warmup)"
        self.log(
            f"[warmup] estrategia: set_warm_up engine-managed (A, adoptada en T2.2 "
            f"con gate 9/9 exactas); gate cross-check {gate}"
        )
        if self._gate_enabled and self._warmup_depth:
            self._run_warmup_gate()

        if self._validation_rows:
            self._write_validation_file()

    def _run_warmup_gate(self) -> None:
        """Gate D4 (bajo flag validate_warmup): la ruta manual de 5A — history[TradeBar] tipado en UNA
        llamada batch + update por barra + scan de cierre — sobre SymbolData sombra
        debe reproducir EXACTAMENTE las SMAs que dejó set_warm_up. Coinciden → A
        adoptado; divergen → WARNING con detalle (causa de rollback)."""
        symbols = list(self.symbol_data)
        shadows = {s: SymbolData(s, self._requirements) for s in symbols}
        history = self.history[TradeBar](symbols, self._warmup_depth, Resolution.DAILY)
        rows = 0
        for trade_bars in history:
            for bar in trade_bars.values():
                shadows[bar.symbol].update(bar)
                rows += 1
        for shadow in shadows.values():
            shadow.scan(self.time)  # mismo instante de flush que la ruta engine

        total = 0
        mismatches: list[str] = []
        for symbol, sd in self.symbol_data.items():
            shadow = shadows[symbol]
            for tf, period in sorted(sd.declared):
                total += 1
                engine_sma = sd.sma(tf, period)
                manual_sma = shadow.sma(tf, period)
                if (engine_sma.current.value != manual_sma.current.value
                        or engine_sma.is_ready != manual_sma.is_ready):
                    mismatches.append(
                        f"{symbol.value} {tf}:{period} "
                        f"engine={engine_sma.current.value} (samples={engine_sma.samples}, "
                        f"ready={engine_sma.is_ready}) vs "
                        f"manual={manual_sma.current.value} (samples={manual_sma.samples}, "
                        f"ready={manual_sma.is_ready})"
                    )
        if not mismatches:
            self.log(
                f"[warmup] gate dev OK: set_warm_up ADOPTADO — {total}/{total} series "
                f"exactas vs ruta manual ({rows} filas vía history[TradeBar], 1 llamada batch)"
            )
        else:
            self.log(
                f"WARNING [warmup] gate dev: {len(mismatches)}/{total} series divergen "
                f"de la ruta manual → ROLLBACK requerido (D4)"
            )
            for mismatch in mismatches:
                self.log(f"WARNING [warmup] gate: {mismatch}")

    def on_end_of_algorithm(self):
        """Evidencia del criterio 1:1 (T2.1): cada barra de la suscripción (warmup +
        runtime) terminó en el consolidator — emitida, o retenida como working bar."""
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

    def _record_validation(
        self, symbol: Symbol, tf: str, periods: tuple, bar: TradeBar
    ) -> None:
        """Punto de validación por barra consolidada. La SMA ya está actualizada cuando
        este handler corre (orden de handlers .NET = orden de suscripción; cubierto
        por test del accessor)."""
        sd = self.symbol_data[symbol]
        for period in periods:
            sma = sd.sma(tf, period)
            self._validation_rows[(symbol, tf, period)].append(
                (bar.end_time, bar.close, sma.current.value, sma.samples)
            )

    def _write_validation_file(self) -> None:
        """T3: últimos K=5 puntos por serie → validation/sma_validation_<fecha>.csv vía
        ObjectStore (storage/validation/ en local). bar_end_time sigue la convención de
        LEAN (C4): cae al inicio del periodo siguiente (W lunes→domingo con cierre
        efectivo viernes; M mes calendario)."""
        lines = ["ticker,timeframe,period,bar_end_time,bar_close,sma_value,bars_consumed"]
        for symbol, tf, period in sorted(
            self._validation_rows, key=lambda k: (k[0].value, k[1], k[2])
        ):
            for end_time, close, sma_value, samples in (
                self._validation_rows[(symbol, tf, period)]
            ):
                lines.append(
                    f"{symbol.value},{tf},{period},{end_time},{close},{sma_value},{samples}"
                )
        key = f"validation/sma_validation_{self.time:%Y%m%d}.csv"
        self.object_store.save(key, "\n".join(lines) + "\n")
        self.log(
            f"[validation] {key}: {len(self._validation_rows)} series, "
            f"{len(lines) - 1} filas (K=5 últimos puntos por serie)"
        )

    def _count_consolidated(self, symbol: Symbol) -> None:
        self._daily_consolidated[symbol] += 1

    def _scan_stub(self, name: str) -> None:
        """Callback placeholder de scan (el pipeline real llega en Etapa 7). Guardado:
        los ScheduledEvents también disparan durante el warmup con data histórica."""
        if self.is_warming_up:
            return
        self.log(f"scan {name} @ {self.time}")

    def _build_requirements(
        self, env_cfg: dict, strategies_config: dict
    ) -> dict[str, set[int]]:
        """Series (tf → periodos) compartidas por todos los símbolos: el override de
        environment (harness dev, D2) reemplaza la unión de timeframes de las
        estrategias; sin override se usa la unión (prod). plan_warmup filtra después
        contra el presupuesto."""
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
