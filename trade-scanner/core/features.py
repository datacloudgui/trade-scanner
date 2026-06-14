"""Features (L3): cómputos puros de lectura sobre SymbolData.

Negocio puro, importable sin CLR (patrón universe): cero AlgorithmImports.
L3 solo lee estado ya calculado por SymbolData (L2) — nunca pide datos ni
calcula indicadores.
"""
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.symbol_data import SymbolData


class FeatureNotReady(Exception):
    """Serie fría o SMA degenerada (== 0): la feature no es evaluable.

    Contrato de fríos: aquí solo se define y lanza; el manejo (exclusión del
    scan + log) es del pipeline en Etapa 7.
    """


# Set cerrado de los 7 buckets (tabla del spec). Orden: de más arriba a más
# abajo de la SMA. T3 valida `buckets_allowed` de las rules contra este set.
BUCKETS: tuple[str, ...] = (
    "extended_above",
    "above_strong",
    "above_mild",
    "near",
    "below_mild",
    "below_strong",
    "extended_below",
)


# Espejo above↔below de los 7 buckets (biyección total, `near` autoespejo). Soporta
# la simetría largo/corto (D6B.4): una rule se autora en vocabulario canónico "above" y
# `mirror_buckets` traduce su set permitido al lado "below" sin duplicar reglas.
_MIRROR: dict[str, str] = {
    "extended_above": "extended_below",
    "above_strong": "below_strong",
    "above_mild": "below_mild",
    "near": "near",
    "below_mild": "above_mild",
    "below_strong": "above_strong",
    "extended_below": "extended_above",
}


# Única fuente de la traducción direction→side (lectura de config, D6B.4). La resolución
# real (leer `direction` del strategies.json) es de Etapa 7; aquí solo el mapa.
SIDE_BY_DIRECTION: dict[str, str] = {"long": "above", "short": "below"}


def mirror_buckets(buckets: Iterable[str], side: str) -> frozenset[str]:
    """Set de buckets canónico ("above") proyectado al `side` pedido.

    `side=="above"` → identidad; `side=="below"` → espejo por `_MIRROR`. Biyección
    involutiva y total sobre los 7 buckets (`near` autoespejo) ⇒ el resultado de un set
    canónico válido siempre ⊆ `BUCKETS`, sin re-validar en caliente. Valida `side`
    (fail-fast); asume `buckets` canónicos (la validación ⊆ `BUCKETS` es de la rule, T3).
    """
    if side not in ("above", "below"):
        raise ValueError(f"side inválido: {side!r}; válidos: 'above', 'below'")
    if side == "above":
        return frozenset(buckets)
    return frozenset(_MIRROR[b] for b in buckets)


# Defaults del código (placeholder D2; calibración real en Etapa 9). Última red
# del merge cuando ni el global ni el override de estrategia traen una clave.
DEFAULT_BUCKET_THRESHOLDS: dict[str, float] = {
    "near": 0.005,
    "mild": 0.03,
    "extended": 0.10,
}


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


def position_vs_sma(
    sd: "SymbolData", tf: str, period: int, thresholds: dict[str, float]
) -> PositionResult:
    """Posición del cierre consolidado de `tf` respecto a su SMA(period).

    Solo lee estado vía la API de SymbolData (`is_ready`/`sma`/`close`, D3);
    float() normaliza el decimal de C# a float de Python en la frontera L2→L3.
    """
    if not sd.is_ready(tf, period):
        raise FeatureNotReady(f"{sd.symbol}: SMA {tf}:{period} fría (is_ready=False)")
    sma = float(sd.sma(tf, period).current.value)
    if sma == 0:
        raise FeatureNotReady(f"{sd.symbol}: SMA {tf}:{period} == 0, distancia indefinida")
    distance_pct = (float(sd.close(tf)) - sma) / sma
    return PositionResult(
        value=sma,
        distance_pct=distance_pct,
        bucket=_bucketize(distance_pct, thresholds),
    )


def _bucketize(distance_pct: float, thresholds: dict[str, float]) -> str:
    """Clasifica la distancia en los 7 buckets con los cortes near < mild < extended.

    Invariante de fronteras: un valor exactamente en un corte cae en el bucket
    más alejado de la SMA — `>=` en el piso de los buckets above y, por espejo,
    `<=` en el techo de los below (la cascada lo expresa con `>` sobre el corte
    negado). La cascada va de arriba hacia abajo: exhaustiva y sin solapes por
    construcción.
    """
    near, mild, extended = (
        thresholds["near"], thresholds["mild"], thresholds["extended"]
    )
    if distance_pct >= extended:
        return "extended_above"
    if distance_pct >= mild:
        return "above_strong"
    if distance_pct >= near:
        return "above_mild"
    if distance_pct > -near:
        return "near"
    if distance_pct > -mild:
        return "below_mild"
    if distance_pct > -extended:
        return "below_strong"
    return "extended_below"


def build_position_snapshot(
    sd: "SymbolData",
    series: Iterable[tuple[str, int]],
    thresholds: dict[str, float],
) -> dict[str, dict[int, PositionResult]]:
    """Posición precio↔SMA de cada `(tf, period)` en `series`, una vez por símbolo·scan.

    Snapshot único (ADR-005 / D6B.1): dict anidado plano `{tf: {period: PositionResult}}`,
    misma forma que la evidencia y sin clase envolvente. Reutiliza `position_vs_sma` como
    primitivo per-serie — hereda su contrato de fríos, la normalización `float()` L2→L3 y
    `_bucketize`.

    `series` = solo lo que referencian las rules de la estrategia (D6B.2), NO toda SMA
    declarada en `sd`: ni computa ni excluye por SMAs que ninguna rule mira. El builder no
    deduplica — el dedup es del call site (Etapa 7 pasa la unión como set).

    Frío (D6B.3): la primera serie que lance `FeatureNotReady` se propaga y detiene la
    construcción (no se silencia); la exclusión del scan + log es de Etapa 7.
    """
    snapshot: dict[str, dict[int, PositionResult]] = {}
    for tf, period in series:
        snapshot.setdefault(tf, {})[period] = position_vs_sma(sd, tf, period, thresholds)
    return snapshot


def snapshot_evidence(
    snapshot: dict[str, dict[int, PositionResult]],
    series: Iterable[tuple[str, int]],
) -> dict:
    """Proyecta el subconjunto `series` del snapshot al esquema de evidencia (D6B.7).

    `{tf:{period:{value,distance_pct,bucket}}}` — descarta `side`. Pura lectura del
    snapshot: sin `SymbolData`, sin recompute. Única fuente de evidencia de aquí en
    adelante (`RuleResult.evidence` sobre las series de la rule; `ScanResult.sma_evidence`
    sobre la unión). Contrato: `series ⊆ snapshot` (un `(tf,period)` ausente → `KeyError`).
    """
    evidence: dict = {}
    for tf, period in series:
        pos = snapshot[tf][period]
        evidence.setdefault(tf, {})[period] = {
            "value": pos.value,
            "distance_pct": pos.distance_pct,
            "bucket": pos.bucket,
        }
    return evidence


def resolve_bucket_thresholds(
    full_config: dict, strategy_name: str
) -> dict[str, float]:
    """Resuelve los cortes near/mild/extended de una estrategia (D2).

    `full_config` es el strategies.json ya parseado completo (el objeto raíz, tal cual
    sale de `json.loads`): el global vive en `full_config["bucket_thresholds"]` y el
    override opcional en `full_config["strategies"][strategy_name]["bucket_thresholds"]`.
    Merge poco profundo por clave — override-de-estrategia > global > defaults del
    código — y el dict resuelto siempre trae las 3 claves.

    Valida `0 < near < mild < extended` sobre el resultado: la resolución de config
    es el único punto de control (un chequeo), no el hot path `_bucketize` (por símbolo×tf).
    """
    global_th = full_config.get("bucket_thresholds") or {}
    strategy_block = full_config.get("strategies", {}).get(strategy_name, {})
    strategy_th = strategy_block.get("bucket_thresholds") or {}
    resolved = {
        key: strategy_th.get(key, global_th.get(key, default))
        for key, default in DEFAULT_BUCKET_THRESHOLDS.items()
    }
    if not 0 < resolved["near"] < resolved["mild"] < resolved["extended"]:
        raise ValueError(
            f"bucket_thresholds para '{strategy_name}' deben cumplir "
            f"0 < near < mild < extended; got {resolved}"
        )
    return resolved
