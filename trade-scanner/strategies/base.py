"""StrategyConfig (L4): composición declarativa de una estrategia — qué rules canónicas usa
y si su scan es intradía. Negocio puro, importable sin CLR (patrón core): cero AlgorithmImports.

D7.2: la lista de rules es *código de composición* (referencia a clases de core/rules.py), no
datos de strategies.json. D7.3: las rules se autoran en vocabulario canónico "above" y el `side`
lo inyecta el pipeline una sola vez (direction→side) al llamar build_rules — StrategyConfig nunca
mira `direction`. Por eso guarda *factories* `(side, filters) -> [rule, ...]`, no instancias (que
tendrían un side fijo): la misma composición se proyecta a long/short sin re-declararse.

R2 (Etapa 10): cada factory recibe también `filters` (el `resolve_filters` de core/features.py,
`{(tf, period): buckets_allowed}`) y devuelve una LISTA de rules — permite que una composición
declare una rule distinta por (tf, period) cuando la estrategia divide un concepto multi-tf en
varias rules independientes (p. ej. swing_eod: SMA20 en D/W/M cada una con su propio
`buckets_allowed`). `build_rules` aplana esa lista-de-listas.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.rules import SMAPositionRule


@dataclass(frozen=True)
class StrategyConfig:
    """Composición de una estrategia V1: nombre, flag de barra parcial y sus rules (factories).

    `rules`: lista de factories `(side, filters) -> [SMAPositionRule, ...]` (no instancias). Cada
    una construye sus rules con el `side` que inyecta el pipeline (mirror interno, D6B.4) y el
    `filters` ya resuelto de config (R2); mantener factories deja la simetría long/short resuelta
    en un solo punto sin duplicar la composición.
    `partial_bar`: metadato del horario (market_close mercado-abierto=True / swing_eod
    cerrado=False, D7.4); NO cambia la fuente de precio. Puro: sin estado de mercado, sin CLR.
    """

    name: str
    partial_bar: bool
    rules: list[Callable[[str, dict], list["SMAPositionRule"]]]

    def build_rules(self, side: str, filters: dict | None = None) -> list["SMAPositionRule"]:
        """Materializa las rules para `side` ("above"/"below"); instancias frescas cada llamada.

        El pipeline lo llama una vez en initialize() con el `side` ya resuelto (D7.1/D7.3) y el
        `filters` de `resolve_filters` (R2; `None`/ausente ⇒ `{}`, cada rule usa su default del
        código). Un `side` inválido (p. ej. "long", que es una *direction*) aflora como ValueError
        fail-fast desde mirror_buckets vía el constructor de la rule — no se revalida aquí por
        duplicado. Aplana la lista-de-listas que devuelve cada factory (una por (tf, period)).
        """
        f = filters or {}
        return [rule for make_rules in self.rules for rule in make_rules(side, f)]

    def series(self, side: str, filters: dict | None = None) -> set[tuple[str, int]]:
        """Unión deduplicada de las `(tf, period)` que las rules referencian (D6B.2).

        El gate de exclusión del pipeline (B) la usa para chequear SOLO las series que de verdad
        se evalúan, no toda SMA declarada en `SymbolData`. Se deriva de las rules construidas (no
        se almacena aparte); es side-independiente (`tf`/`period` no cambian con el espejo), pero
        construir las rules es lo que permite introspeccionar sus `.tfs`/`.period`.
        """
        return {(tf, rule.period) for rule in self.build_rules(side, filters) for tf in rule.tfs}
