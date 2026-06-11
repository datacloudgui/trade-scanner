"""UniverseSpec: lee un CSV desde ObjectStore y devuelve la lista filtrada de tickers.

Sin imports de AlgorithmImports — testeable con cualquier mock que tenga .read(key) -> str.
"""
import io
import re

import pandas as pd

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
        self.max_tickers = max_tickers

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

        # Filtro declarativo sobre alias normalizados
        df = df.query(self.filter_expr)

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
