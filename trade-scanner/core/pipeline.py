"""Pipeline (L4): el embudo end-to-end de una estrategia + el contrato de salida `ScanResult`.

Negocio puro, importable sin CLR (patrón features/rules): cero AlgorithmImports. El `ScanPipeline`
recibe TODO resuelto en initialize() (D7.1) — rules ya construidas con su `side`, `series`,
`thresholds`, `top_n`, `partial_bar` — y su `scan` solo LEE estado de `SymbolData`: gate por series
referenciadas (B, D7.7), ranking `top_n` por `day_change_pct`, snapshot único por símbolo (A.1) y
cascada de rules → `ScanResult`. La salida a archivo/notificación es Etapa 8; aquí vive en memoria +
log, este último vía un callable INYECTADO (L4 no habla con `QCAlgorithm`).
"""
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from core.features import (
    FeatureNotReady,
    build_position_snapshot,
    day_change_pct,
    reference_price,
    snapshot_evidence,
)
from core.timeframes import TIMEFRAMES

if TYPE_CHECKING:
    from core.rules import SMAPositionRule
    from core.symbol_data import SymbolData


@dataclass
class ScanResult:
    """Contrato de salida (L4): un candidato de la watchlist. El pipeline lo llena (Etapa 7);
    la serialización CSV/JSON es Etapa 8.

    Campos de §5 de PLAN.md (D7.8). `price` = el `reference_price` único (no per-tf). `sma_evidence`
    = `snapshot_evidence` proyectado sobre la unión de series (proyección del snapshot único, NO un
    recompute — D6B.7). `rules_passed_count` = nº de rules `required` que pasaron (score de ranking).
    Todos los campos traen default → el contrato mínimo de 6B (`ScanResult()`) sigue construible.
    """

    strategy: str = ""
    as_of: datetime | None = None
    ticker: str = ""
    direction: str = ""
    partial_bar: bool = False
    price: float = 0.0
    time_frames_evaluated: list[str] = field(default_factory=list)
    sma_evidence: dict = field(default_factory=dict)
    passed_rules: list[str] = field(default_factory=list)
    rules_passed_count: int = 0


def validate_series_against_plan(
    strategy_name: str,
    series: Iterable[tuple[str, int]],
    available: Iterable[tuple[str, int]],
) -> None:
    """Falla fail-fast si una rule referencia series fuera del plan de warmup (#20 triaje E1–E8).

    `available` = las `(tf, period)` incluidas en `plan_warmup(...).included`. Sin este chequeo en
    initialize(), una serie excluida por presupuesto aflora como `KeyError` de `SymbolData` en
    pleno scan (crash del ScheduledEvent), no como error de config claro.
    """
    missing = set(series) - set(available)
    if missing:
        listed = ", ".join(f"{tf}:{p}" for tf, p in sorted(missing))
        raise ValueError(
            f"[{strategy_name}] rules referencian series fuera del plan de warmup: {listed}. "
            f"Sube warmup_budget o quita esas series de la composición/timeframes."
        )


class ScanPipeline:
    """Una estrategia resuelta (D7.1): el bundle inmutable de su composición + el embudo `scan`.

    Construido en initialize() con el `side` ya resuelto (`direction→side` en un solo punto, D7.3);
    las `rules` llegan ya espejadas. El scan es lectura pura sobre `SymbolData`: cero parsing de
    config, cero resolución de `direction` en el hot path.
    """

    def __init__(
        self,
        strategy_name: str,
        direction: str,
        side: str,
        rules: list["SMAPositionRule"],
        series: Iterable[tuple[str, int]],
        thresholds: dict[str, float],
        top_n: int,
        partial_bar: bool,
    ) -> None:
        self.strategy_name = strategy_name
        self.direction = direction
        self.side = side  # ya horneado en las rules; se guarda como estado resuelto del pipeline
        self.rules = rules
        self.series = set(series)
        self.thresholds = thresholds
        self.top_n = top_n
        self.partial_bar = partial_bar
        # Timeframes evaluados en orden canónico del registro (D, W, M — como §5), no alfabético.
        order = list(TIMEFRAMES)
        self.time_frames_evaluated = sorted(
            {tf for tf, _period in self.series},
            key=lambda tf: order.index(tf) if tf in order else len(order),
        )

    def scan(
        self,
        symbol_data_map: dict,
        as_of: datetime | None,
        log: Callable[[str], None] | None = None,
    ) -> list[ScanResult]:
        """Embudo end-to-end: gate (B) → ranking top_n → snapshot+cascada → ScanResult.

        `symbol_data_map`: `{symbol: SymbolData}` (clave LEAN Symbol; el ticker sale de
        `sd.symbol.value`). `log`: callable opcional que recibe cada línea de exclusión/embudo
        (inyectado por main.py; los tests capturan en una lista). Orden determinista por ticker
        (reproducibilidad, consideración #8).
        """
        emit = log or (lambda _msg: None)
        candidates = sorted(symbol_data_map.values(), key=lambda sd: sd.symbol.value)

        # 1. Gate (B, D7.7): excluir si alguna serie REFERENCIADA está fría. No is_ready() global.
        gated = []
        for sd in candidates:
            cold = next(
                ((tf, p) for tf, p in sorted(self.series) if not sd.is_ready(tf, p)), None
            )
            if cold is not None:
                emit(
                    f"[{self.strategy_name}] excluido {sd.symbol.value}: "
                    f"warmup incompleto, serie {cold[0]}:{cold[1]} fría"
                )
                continue
            gated.append(sd)

        # 2. Ranking por day_change_pct: desc long (gainers) / asc short (decliners); tie-break
        #    ticker alfabético (sort estable: ticker primero, luego day_change con reverse).
        scored: list[tuple[float, "SymbolData"]] = []
        for sd in gated:
            try:
                change = day_change_pct(sd)
            except FeatureNotReady as exc:
                emit(f"[{self.strategy_name}] excluido {sd.symbol.value}: {exc}")
                continue
            scored.append((change, sd))
        scored.sort(key=lambda item: item[1].symbol.value)
        scored.sort(key=lambda item: item[0], reverse=self.direction == "long")
        top = [sd for _change, sd in scored[: self.top_n]]

        # 3. Snapshot único por símbolo + evaluación de TODAS las rules (sin short-circuit →
        #    evidencia completa). Backstop: FeatureNotReady del builder (p. ej. SMA==0) excluye.
        evaluated: list[tuple] = []
        for sd in top:
            try:
                snapshot = build_position_snapshot(sd, self.series, self.thresholds)
            except FeatureNotReady as exc:
                emit(f"[{self.strategy_name}] excluido {sd.symbol.value}: {exc}")
                continue
            results = [rule.evaluate(snapshot) for rule in self.rules]
            evaluated.append((sd, snapshot, results))

        # Embudo (arranca en top_n, tras gate+ranking): cascada por rule. Las `required` narrowan;
        # las `optional` informan sin descartar (en V1 todas son required).
        surviving = evaluated
        for i, rule in enumerate(self.rules):
            passers = [entry for entry in surviving if entry[2][i].passed]
            kind = "required" if rule.required else "optional"
            emit(format_filter_line(self.strategy_name, rule.name, len(surviving), len(passers), kind))
            if rule.required:
                surviving = passers
        emit(format_final_line(self.strategy_name, len(surviving)))

        # 4. ScanResult por superviviente (orden de ranking preservado).
        results_out: list[ScanResult] = []
        for sd, snapshot, rule_results in surviving:
            results_out.append(
                ScanResult(
                    strategy=self.strategy_name,
                    as_of=as_of,
                    ticker=sd.symbol.value,
                    direction=self.direction,
                    partial_bar=self.partial_bar,
                    price=reference_price(sd),
                    time_frames_evaluated=list(self.time_frames_evaluated),
                    sma_evidence=snapshot_evidence(snapshot, self.series),
                    passed_rules=[r.name for r in rule_results if r.passed],
                    rules_passed_count=sum(1 for r in rule_results if r.required and r.passed),
                )
            )
        return results_out


def run_group_scan(
    base: str,
    members: Iterable[str],
    pipelines: dict[str, "ScanPipeline"],
    symbol_data_map: dict,
    as_of: datetime | None,
    env: str,
    emit: Callable,
    log: Callable[[str], None] | None = None,
) -> dict[str, list[ScanResult]]:
    """Scan del grupo de una estrategia base (D8.7/T5.2): corre el pipeline de cada miembro
    activo, agrupa los `ScanResult` por dirección en `sections` y emite EXACTAMENTE una vez.

    Extraído de `main._scan_group` para testearlo sin engine (#24 triaje E1–E8): `emit` es el
    `OutputSink.emit` inyectado (firma `(base, env, as_of, partial_bar, sections)`); `log` el
    callable de log. `sections` se siembra con la dirección de cada miembro ACTIVO (no de sus
    resultados): un lado activo sin candidatos queda como sección vacía (count 0) para que el
    correo muestre "(sin candidatos)" en ese bloque (D8.6). `partial_bar` es uniforme por grupo
    (invariante D8.7, validado en initialize()). Devuelve `sections` (evidencia para tests/logs).
    """
    out = log or (lambda _msg: None)
    sections: dict[str, list[ScanResult]] = {}
    partial_bar = False
    for name in members:
        pipeline = pipelines.get(name)
        if pipeline is None:
            continue
        partial_bar = pipeline.partial_bar  # uniforme por grupo (validado en initialize)
        sections.setdefault(pipeline.direction, [])
        results = pipeline.scan(symbol_data_map, as_of, out)
        # Watchlist visible y reproducible en el log: una línea por candidato con su evidencia.
        for r in results:
            out(
                f"[{name}] candidato {r.ticker} {r.direction} "
                f"price={r.price:.4f} partial_bar={r.partial_bar} "
                f"passed={'|'.join(r.passed_rules)} "
                f"evidence={json.dumps(r.sma_evidence, sort_keys=True)}"
            )
        out(f"[{name}] scan @ {as_of}: {len(results)} candidatos")
        sections[pipeline.direction].extend(results)
    # Un solo emit por estrategia base (D8.2): el switch de canal/entorno vive en OutputSink.
    emit(base, env, as_of, partial_bar, sections)
    counts = ", ".join(f"{side}:{len(rs)}" for side, rs in sorted(sections.items()))
    out(f"[{base}] emit @ {as_of}: sections={{{counts}}}")
    return sections


def format_filter_line(
    strategy: str, rule_name: str, n_in: int, n_out: int, kind: str
) -> str:
    """Una línea del embudo de filtrado: cuántos símbolos sobreviven a una rule.

    `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)`, con
    `dropped = n_in - n_out` y `kind ∈ {"required","optional"}`. Pura: solo da formato a
    contadores ya calculados. Símbolos exactos: flecha U+2192 y signo menos U+2212 (no ASCII).
    """
    dropped = n_in - n_out
    return f"[{strategy}] {rule_name}: {n_in} → {n_out} (−{dropped} {kind})"


def format_final_line(strategy: str, n: int) -> str:
    """Línea de cierre del embudo: total de candidatos tras todas las rules.

    `[<strategy>] final: <n> candidatos`.
    """
    return f"[{strategy}] final: {n} candidatos"
