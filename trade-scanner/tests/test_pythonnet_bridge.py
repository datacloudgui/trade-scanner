"""De-riesga el puente pythonnet dentro de la imagen quantconnect/lean: importa
AlgorithmImports y construye un objeto LEAN real (TradeBar), no un assert trivial.
Es el contrato base de todos los tests del proyecto (deben correr en Docker)."""

from AlgorithmImports import TradeBar


def test_pythonnet_bridge_builds_tradebar():
    """Si esto pasa, el CLR cargó y los assemblies de QuantConnect están accesibles."""
    bar = TradeBar()
    bar.close = 100.0
    bar.high = 101.5
    assert bar.close == 100.0
    assert bar.high == 101.5
