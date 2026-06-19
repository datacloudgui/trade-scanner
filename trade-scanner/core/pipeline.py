"""Pipeline (L4): contrato de salida, observabilidad del filtrado y (futuro) orquestación.

Negocio puro, importable sin CLR (patrón features/rules): cero AlgorithmImports. En Etapa 6B
viven aquí el contrato mínimo `ScanResult` (sin lógica de llenado) y los formateadores del log
de embudo del filtrado (contadores → texto). La cascada real (snapshot por símbolo, ranking
top_n, aplicar las rules y llenar `ScanResult`) es Etapa 7; la serialización CSV/JSON, Etapa 8.
"""
from dataclasses import dataclass, field


@dataclass
class ScanResult:
    """Contrato de salida (L4): un candidato de la watchlist. SOLO el contrato — el pipeline
    (Etapa 7) lo llena y la serialización CSV/JSON es Etapa 8.

    `sma_evidence`: `{tf:{period:{value,distance_pct,bucket}}}` — **proyección** del snapshot
    único (`snapshot_evidence` sobre la unión de series de la estrategia), NO un recompute
    (D6B.7). `rules_passed_count`: nº de reglas que pasaron; score de ranking (§5 de PLAN.md).

    Contrato **mínimo** de 6B/T7 (los dos campos nuevos del rediseño del snapshot). Etapa 7 le
    añade el resto de la fila de §5 (`strategy`, `ticker`, `as_of`, `direction`, `price`,
    `partial_bar`, `time_frames_evaluated`, `passed_rules`) al construirlo de verdad.
    """

    rules_passed_count: int = 0
    sma_evidence: dict = field(default_factory=dict)


def format_filter_line(
    strategy: str, rule_name: str, n_in: int, n_out: int, kind: str
) -> str:
    """Una línea del embudo de filtrado: cuántos símbolos sobreviven a una rule.

    `[<strategy>] <rule_name>: <n_in> → <n_out> (−<dropped> <kind>)`, con
    `dropped = n_in - n_out` y `kind ∈ {"required","optional"}`. Pura: NO filtra (la cascada
    es Etapa 7), solo da formato a contadores ya calculados. Símbolos exactos: flecha U+2192
    y signo menos U+2212 (no el guion ASCII).
    """
    dropped = n_in - n_out
    return f"[{strategy}] {rule_name}: {n_in} → {n_out} (−{dropped} {kind})"


def format_final_line(strategy: str, n: int) -> str:
    """Línea de cierre del embudo: total de candidatos tras todas las rules.

    `[<strategy>] final: <n> candidatos`.
    """
    return f"[{strategy}] final: {n} candidatos"
