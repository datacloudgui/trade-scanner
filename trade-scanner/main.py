# region imports
from AlgorithmImports import *

import json
from collections import deque
from time import perf_counter

import core
from core.features import SIDE_BY_DIRECTION, resolve_bucket_thresholds
from core.output import JsonSubscriberSource, OutputSink
from core.pipeline import ScanPipeline, run_group_scan, validate_series_against_plan
from core.scheduling import time_rule_for
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
        # Ventana 2013-10 (Etapa 7/T5): única con datos minute (SPY sample del repo LEAN).
        # SPY ejercita el working_bar; AAPL/IBM/FB no tienen minute aquí → caen al fallback
        # close("D") (C2). SPY M:200 no calienta del todo (~3970 barras pre-2013 < 4221) pero
        # M:200 no la referencia ninguna rule. FB (IPO 2012) tiene M:20 frío → gate B lo excluye.
        self.set_start_date(2013, 10, 7)
        self.set_end_date(2013, 10, 11)
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
            # MINUTE (T5.1): habilita el working_bar intradía del consolidator diario. El
            # warmup sigue siendo DAILY (set_warm_up más abajo); resolución de suscripción ⟂
            # resolución de warmup (5A T3.9). El consolidator diario se cabla a esta suscripción.
            symbol = self.add_equity(
                ticker,
                Resolution.MINUTE,
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
        # DECISIÓN (#5 triaje E1–E8): el fallback usa Resolution.DAILY a propósito y es
        # seguro — el reloj del backtest avanza por las suscripciones del universo (arriba)
        # y before/after_market_close usa las market-hours de SPY, que son independientes
        # de la resolución del feed. Pendiente verificar vs LEAN el caso límite de un
        # entorno con universo 100% daily (hoy no existe: dev suscribe MINUTE).
        spy = next((s for s in self.symbol_data if s.value == "SPY"), None)
        self.spy = spy or self.add_equity("SPY", Resolution.DAILY).symbol

        # Un ScanPipeline por estrategia/variante (config=datos × strategies/=composición),
        # resuelto en initialize() (D7.1): direction→side en un solo punto (D7.3), thresholds y
        # rules ya construidas. El schedule ya NO es por variante: lo registra el grupo (T5.2).
        self.pipelines: dict[str, ScanPipeline] = {}
        self._probe_done = False  # probe de emisión A.3: solo en el primer scan real
        # #20 (triaje E1–E8): las series que referencian las rules deben estar en el plan de
        # warmup; si el presupuesto excluyó una, fallar AQUÍ con ValueError claro, no con
        # KeyError en pleno scan.
        available_series = {
            (tf, p) for tf, periods in self._requirements.items() for p in periods
        }
        for name, cfg in strategies_config.items():
            composition = strategies.STRATEGIES.get(name)
            if composition is None:
                self.log(f"[{name}] sin StrategyConfig en STRATEGIES: omitida del scan")
                continue
            side = SIDE_BY_DIRECTION[cfg["direction"]]
            series = composition.series(side)
            validate_series_against_plan(name, series, available_series)
            self.pipelines[name] = ScanPipeline(
                strategy_name=name,
                direction=cfg["direction"],
                side=side,
                rules=composition.build_rules(side),
                series=series,
                thresholds=resolve_bucket_thresholds(full_config, name),
                top_n=top_n,
                partial_bar=composition.partial_bar,
            )

        # T5.1 — OutputSink (Etapa 8): L5 es el único que toca object_store/notify/live_mode/
        # schedule, así que aquí se construye el sink y se enchufa la config de notificación. El
        # switch local/cloud vive SOLO en OutputSink (D8.4): main.py no decide canal por entorno.
        self._env = env
        notif_cfg = json.loads(self.object_store.read("config/notifications.json"))
        self.output = OutputSink(
            self.object_store,
            self.notify,
            self.live_mode,
            notif_cfg,
            JsonSubscriberSource(notif_cfg),
            self.log,
        )

        # T5.2 — un ScheduledEvent por estrategia BASE (D8.7), no por variante: el grupo corre sus
        # pipelines miembro (long/short) y emite UNA vez. Invariante D8.7 validado aquí (miembros
        # comparten schedule y partial_bar) → config inconsistente = error explícito en initialize().
        for base, members in notif_cfg["notification_groups"].items():
            active = [m for m in members if m in self.pipelines]
            if not active:
                self.log(f"[{base}] grupo sin pipelines activos: omitido del schedule")
                continue
            schedules = {strategies_config[m]["schedule"] for m in active}
            if len(schedules) > 1:
                raise ValueError(
                    f"grupo '{base}' (D8.7): miembros con schedule distinto {schedules}"
                )
            partial_bars = {self.pipelines[m].partial_bar for m in active}
            if len(partial_bars) > 1:
                raise ValueError(
                    f"grupo '{base}' (D8.7): miembros con partial_bar distinto {partial_bars}"
                )
            time_rule = self._time_rule_for(schedules.pop())
            if time_rule is None:
                self.log(f"[{base}] schedule desconocido: grupo omitido")
                continue
            self.schedule.on(
                self.date_rules.every_day(self.spy),
                time_rule,
                lambda base=base, active=tuple(active): self._scan_group(base, active),
            )
            self.log(f"[{base}] schedule registrado: miembros {list(active)}")

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
        """Evidencia del feed→consolidator. Con suscripción minute (T5.1) la relación es N:1
        (N barras minute → 1 barra diaria), así que el chequeo 1:1 estricto de 5B ya no aplica:
        se reporta el conteo informativo (barras recibidas vs diarias consolidadas + working bar)."""
        for symbol, sd in self.symbol_data.items():
            received = self._daily_received[symbol]
            consolidated = self._daily_consolidated[symbol]
            working = sd.working_bar
            tail = (
                f", working hasta {working.end_time}" if working is not None
                else " (sin working bar)"
            )
            self.log(
                f"[{symbol.value}] feed→consolidator: {received} barras recibidas "
                f"(warmup daily + runtime minute), {consolidated} diarias consolidadas{tail}"
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

    def _scan_group(self, base: str, members: tuple) -> None:
        """Callback del ScheduledEvent por estrategia base (D8.7/T5.2). El scan del grupo vive en
        `core.pipeline.run_group_scan` (testeable sin engine, #24 triaje E1–E8); aquí quedan los
        guards que SÍ necesitan el algoritmo: warmup (los ScheduledEvents también disparan con
        data histórica) y el probe A.3 del primer scan real."""
        if self.is_warming_up:
            return
        if not self._probe_done:
            self._emit_probe()          # A.3: confirmar que "hoy" no está consolidado al scan
            self._probe_done = True
        run_group_scan(
            base,
            members,
            self.pipelines,
            self.symbol_data,
            self.utc_time,
            self._env,
            self.output.emit,
            self.log,
        )

    def _emit_probe(self, ticker: str = "SPY") -> None:
        """Probe de emisión (A.3): loguea working_bar vs close('D') de un símbolo en el primer
        scan real. Esperado (timedelta(days=1)): la barra diaria de hoy NO está consolidada al
        scan → working_bar = hoy y close('D') = ayer. Si coincidieran, LEAN emitiría al cierre y
        habría que activar la contingencia de day_change (D7.6). T6 registra el hallazgo."""
        symbol = next((s for s in self.symbol_data if s.value == ticker), None)
        if symbol is None:
            return
        sd = self.symbol_data[symbol]
        working = sd.working_bar
        wb = f"close={working.close}, end_time={working.end_time}" if working is not None else "None"
        try:
            daily_close = sd.close("D")
        except Exception:
            daily_close = None
        self.log(
            f"[probe A.3] {ticker} @ {self.utc_time}: working_bar=({wb}); close('D')={daily_close} "
            f"→ esperado working_bar=hoy, close('D')=ayer (hoy NO consolidado)"
        )

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
        """Mapea el string de schedule a una time-rule de LEAN anclada a SPY. El mapeo vive en
        `core.scheduling.time_rule_for` (testeable sin engine, #6 triaje E1–E8)."""
        return time_rule_for(schedule, self.time_rules, self.spy)
