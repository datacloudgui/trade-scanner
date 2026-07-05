"""UniverseSpec: lee un CSV desde ObjectStore y devuelve la lista filtrada de tickers.

Sin imports de AlgorithmImports — testeable con cualquier mock que tenga .read(key) -> str.
"""
import io
import re

import pandas as pd

# DECISIÓN (#10 triaje E1–E8, reconcilia con PLAN §5): el alias map se acota A PROPÓSITO
# a las columnas que el screener usa (etapa-04.md:77,93) — el resto de las 11 columnas del
# export Barchart se ignora sin mapear. Si una etapa futura (E9+) filtra por columnas
# nuevas, ampliar este map y _REQUIRED_COLUMNS a la vez.
COLUMN_ALIASES: dict[str, str] = {
    "Symbol": "ticker",
    "5D Avg Vol": "avg_vol_5d",
    "Latest": "price",
    "5D %Chg": "pct_chg_5d",
    "%Change": "pct_chg_1d",
}

_TICKER_RE = r"^[A-Z]{1,5}$"
_PCT_COLUMNS = {"pct_chg_5d", "pct_chg_1d"}
_REQUIRED_COLUMNS = {"avg_vol_5d", "price"}

# Tope duro de producto (CLAUDE.md / PLAN §5): ≤200 tickers post-filtro. Se aplica en
# código (#11 triaje E1–E8): un max_universe mal configurado (>200) solo puede BAJAR
# el límite, nunca superarlo.
_HARD_CAP = 200


def _parse_pct(val: str) -> float:
    return float(str(val).strip().lstrip("+").rstrip("%")) / 100.0


class UniverseSpec:
    def __init__(
        self,
        universe_key: str,
        filter_expr: str,
        max_tickers: int = 200,
    ) -> None:
        self.universe_key = universe_key
        self.filter_expr = filter_expr
        if max_tickers > _HARD_CAP:
            print(
                f"[UniverseSpec] WARNING: max_tickers={max_tickers} excede el tope duro "
                f"{_HARD_CAP} (CLAUDE.md/PLAN §5); se usa {_HARD_CAP}"
            )
        self.max_tickers = min(max_tickers, _HARD_CAP)

    def load(self, object_store) -> list[str]:
        """Lee, parsea, filtra y devuelve lista de tickers (≤ max_tickers).

        object_store: cualquier objeto con .read(key: str) -> str
        """
        raw_csv = object_store.read(self.universe_key)
        df = pd.read_csv(io.StringIO(raw_csv))

        # Footer strip: descartar filas cuyo Symbol no sea un ticker válido
        df = df[df["Symbol"].astype(str).str.match(_TICKER_RE)].copy()

        # Alias rename: Symbol→ticker, 5D Avg Vol→avg_vol_5d, etc.
        df = df.rename(columns=COLUMN_ALIASES)

        # Verificar columnas requeridas por el filtro declarativo
        for col in _REQUIRED_COLUMNS:
            if col not in df.columns:
                raise KeyError(
                    f"Required column missing after rename: '{col}' "
                    f"(check COLUMN_ALIASES and source CSV headers)"
                )

        # Parsear porcentajes: "+14.32%" → 0.1432
        for col in _PCT_COLUMNS:
            if col in df.columns:
                df[col] = df[col].apply(_parse_pct)

        # Convertir numéricas
        df["avg_vol_5d"] = pd.to_numeric(df["avg_vol_5d"], errors="raise")
        df["price"] = pd.to_numeric(df["price"], errors="raise")

        # Filtro declarativo sobre alias normalizados. Nota (#13 triaje E1–E8):
        # _REQUIRED_COLUMNS no se deriva de filter_expr — un filtro sobre una columna sin
        # alias mapeado recién falla aquí; se envuelve con contexto para diagnóstico.
        try:
            df = df.query(self.filter_expr)
        except Exception as exc:
            raise ValueError(
                f"filter_expr inválido para '{self.universe_key}': {self.filter_expr!r} "
                f"(columnas disponibles: {df.columns.tolist()}): {exc}"
            ) from exc

        # Orden alfabético: garantiza reproducibilidad entre runs con el mismo CSV
        df = df.sort_values("ticker")

        # Tope duro de seguridad
        if len(df) > self.max_tickers:
            print(
                f"[UniverseSpec] WARNING: truncating {self.universe_key} "
                f"from {len(df)} to {self.max_tickers} tickers"
            )
            df = df.iloc[: self.max_tickers]

        return list(df["ticker"].values)

    def refresh_universe(self) -> None:
        """No-op en V1. Sobrescribir en Fase 2 para refresh intradiario."""
