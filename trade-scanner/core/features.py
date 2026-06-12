"""Features (L3): cómputos puros de lectura sobre SymbolData.

Negocio puro, importable sin CLR (patrón universe): cero AlgorithmImports.
L3 solo lee estado ya calculado por SymbolData (L2) — nunca pide datos ni
calcula indicadores.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PositionResult:
    """Posición del cierre respecto a una SMA: valor usado, distancia relativa y bucket.

    `side` se deriva del signo de `distance_pct` en construcción (`>= 0` → "above"):
    la invariante vive en el dataclass y no puede divergir de la distancia.
    """

    value: float
    distance_pct: float
    side: str = field(init=False)
    bucket: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "side", "above" if self.distance_pct >= 0 else "below")
