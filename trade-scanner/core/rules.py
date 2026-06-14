"""Rules (L4): predicados componibles sobre features, con evidencia.

Negocio puro, importable sin CLR (patrón features): cero AlgorithmImports salvo
tipos bajo TYPE_CHECKING. L4 no calcula indicadores ni pide datos — evalúa
`position_vs_sma` (L3) y arma el veredicto pasa/no-pasa + la evidencia anidada.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.features import BUCKETS, position_vs_sma

if TYPE_CHECKING:
    from core.symbol_data import SymbolData


@dataclass
class RuleResult:
    """Veredicto de una rule + evidencia.

    `evidence`: `{tf: {period: {"value", "distance_pct", "bucket"}}}` — anidada
    (no plana) para soportar futuras rules multi-period sobre el mismo tf sin
    romper el esquema de `sma_evidence` (T6 / serialización en Etapa 8).
    """

    passed: bool
    evidence: dict
    name: str
    required: bool


class AboveSMA:
    """Pasa si el bucket de CADA tf en `tfs` ∈ `buckets_allowed` (AND estricto).

    `buckets_allowed` se valida contra el set cerrado de 7 buckets en construcción
    (fail-fast): una config con un bucket inexistente revienta al crear la rule, no
    en caliente durante el scan.
    """

    def __init__(
        self,
        period: int,
        tfs: list[str],
        buckets_allowed,
        required: bool = True,
    ) -> None:
        unknown = set(buckets_allowed) - set(BUCKETS)
        if unknown:
            raise ValueError(
                f"buckets_allowed con buckets desconocidos: {sorted(unknown)}; "
                f"válidos: {list(BUCKETS)}"
            )
        self.period = period
        self.tfs = list(tfs)
        self.buckets_allowed = set(buckets_allowed)
        self.required = required

    @property
    def name(self) -> str:
        return f"AboveSMA({self.period},{'+'.join(self.tfs)})"

    def evaluate(self, sd: "SymbolData", thresholds: dict) -> RuleResult:
        """Evalúa TODOS los tf (no corta al primer fallo) para que la evidencia
        quede completa aun cuando la rule no pasa. Fríos: `position_vs_sma` lanza
        `FeatureNotReady` y se propaga — la exclusión del scan es del pipeline (Etapa 7)."""
        evidence: dict = {}
        passed = True
        for tf in self.tfs:
            pos = position_vs_sma(sd, tf, self.period, thresholds)
            evidence[tf] = {
                self.period: {
                    "value": pos.value,
                    "distance_pct": pos.distance_pct,
                    "bucket": pos.bucket,
                }
            }
            if pos.bucket not in self.buckets_allowed:
                passed = False
        return RuleResult(
            passed=passed,
            evidence=evidence,
            name=self.name,
            required=self.required,
        )
