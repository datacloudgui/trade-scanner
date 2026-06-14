"""Rules (L4): filtros componibles sobre el snapshot precalculado, con evidencia.

Negocio puro, importable sin CLR (patrón features): cero AlgorithmImports. L4 no
calcula indicadores ni pide datos ni mide posiciones — solo LEE buckets ya asignados
en el snapshot único (Etapa 6B) y arma el veredicto pasa/no-pasa + la evidencia anidada.
"""
from dataclasses import dataclass

from core.features import BUCKETS, mirror_buckets, snapshot_evidence


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


class SMAPositionRule:
    """Filtro puro: pasa si el bucket de CADA tf en `tfs` (para `period`) ∈ buckets permitidos.

    Lee SOLO el snapshot precalculado (`snapshot[tf][period].bucket`): no mide ni
    re-bucketiza — la pureza es invariante de tipo (D6B.3), no convención. `buckets_allowed`
    se autora en vocabulario canónico "above", se valida ⊆ `BUCKETS` (fail-fast) y se espeja
    al `side` UNA vez en construcción (D6B.4): el `evaluate` resultante es idéntico para ambos
    lados, solo cambia el set permitido. AND estricto sobre todos los tf, sin short-circuit:
    la evidencia queda completa aun cuando la rule no pasa.
    """

    def __init__(
        self,
        period: int,
        tfs: list[str],
        buckets_allowed,
        side: str,
        required: bool = True,
        label: str = "SMA",
    ) -> None:
        unknown = set(buckets_allowed) - set(BUCKETS)
        if unknown:
            raise ValueError(
                f"buckets_allowed con buckets desconocidos: {sorted(unknown)}; "
                f"válidos: {list(BUCKETS)}"
            )
        self.period = period
        self.tfs = list(tfs)
        self.side = side
        self.label = label
        self.required = required
        # Espejo aplicado una sola vez (mirror_buckets valida `side`, fail-fast).
        self.buckets_allowed = mirror_buckets(buckets_allowed, side)

    @property
    def name(self) -> str:
        tfs = "+".join(self.tfs)
        if self.label == "SMA":
            prefix = "AboveSMA" if self.side == "above" else "BelowSMA"
            return f"{prefix}({self.period},{tfs})"
        return f"{self.label}({self.period},{tfs})"

    def evaluate(self, snapshot: dict) -> RuleResult:
        """Filtra sobre el snapshot ya construido (símbolo caliente). Evalúa TODOS los tf
        (sin short-circuit) para evidencia completa; NO maneja fríos: `FeatureNotReady`
        aflora en el builder (Etapa 6B/T1), no aquí."""
        passed = True
        for tf in self.tfs:
            if snapshot[tf][self.period].bucket not in self.buckets_allowed:
                passed = False
        evidence = snapshot_evidence(snapshot, [(tf, self.period) for tf in self.tfs])
        return RuleResult(
            passed=passed,
            evidence=evidence,
            name=self.name,
            required=self.required,
        )
