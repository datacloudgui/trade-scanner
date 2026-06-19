"""Tests de core/pipeline.py — ScanResult (T7) + formateadores del log de filtrado (T6), Etapa 6B.

L4 negocio puro: pipeline.py no importa AlgorithmImports. T6: los formateadores solo dan formato a
contadores (NO ejecutan filtrado — eso es Etapa 7); el test reproduce LITERALMENTE las 4 líneas del
ejemplo de la spec, incluidos la flecha U+2192 y el signo menos U+2212 (no el guion ASCII). T7:
contrato mínimo de ScanResult — construible sin args, campos nuevos con sus defaults, sin lógica de
llenado (eso es Etapa 7).
"""
from core.pipeline import ScanResult, format_filter_line, format_final_line


# (criterio T6) las 4 líneas del ejemplo, reproducidas literalmente desde contadores
def test_filter_log_reproduces_example_lines_literally():
    lines = [
        format_filter_line("swing_eod", "AboveSMA(20,W+M)", 50, 38, "required"),
        format_filter_line("swing_eod", "AboveSMA(20,D)", 38, 29, "required"),
        format_filter_line("swing_eod", "NotExtended(8,D)", 29, 22, "required"),
        format_final_line("swing_eod", 22),
    ]
    assert lines == [
        "[swing_eod] AboveSMA(20,W+M): 50 → 38 (−12 required)",
        "[swing_eod] AboveSMA(20,D): 38 → 29 (−9 required)",
        "[swing_eod] NotExtended(8,D): 29 → 22 (−7 required)",
        "[swing_eod] final: 22 candidatos",
    ]


# dropped = n_in - n_out (incluso 0); kind="optional" se renderiza tal cual
def test_filter_line_computes_dropped_and_renders_optional():
    assert (
        format_filter_line("market_close", "NotExtended(8,D)", 29, 29, "optional")
        == "[market_close] NotExtended(8,D): 29 → 29 (−0 optional)"
    )


# símbolos exactos: flecha U+2192 y signo menos U+2212 (no '->' ni guion ASCII '-')
def test_filter_line_uses_exact_unicode_symbols():
    line = format_filter_line("s", "R", 10, 3, "required")  # dropped = 7
    assert "→" in line                 # → flecha
    assert "(−7 required)" in line     # − signo menos
    assert "->" not in line                 # no la flecha ASCII
    assert "-7" not in line                 # no el guion ASCII en el dropped


# ---------------------------------------------------------------------------
# T7 (Etapa 6B) — ScanResult: contrato mínimo (sin lógica de llenado, eso es Etapa 7).
# Campos nuevos del rediseño del snapshot: rules_passed_count + sma_evidence (proyección).
# ---------------------------------------------------------------------------

# (T7) contrato mínimo: construible sin args; los campos nuevos traen sus defaults
def test_scanresult_minimal_contract_defaults():
    result = ScanResult()
    assert result.rules_passed_count == 0
    assert result.sma_evidence == {}


# (T7) sma_evidence admite la proyección del snapshot {tf:{period:{value,distance_pct,bucket}}}
def test_scanresult_accepts_snapshot_projection_shape():
    evidence = {"D": {20: {"value": 150.20, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    result = ScanResult(rules_passed_count=2, sma_evidence=evidence)
    assert result.rules_passed_count == 2
    assert result.sma_evidence == evidence


# (T7) default_factory: cada instancia tiene su PROPIO dict (no el clásico bug de default mutable)
def test_scanresult_evidence_default_is_per_instance():
    a = ScanResult()
    a.sma_evidence["D"] = {20: {}}
    assert ScanResult().sma_evidence == {}  # una instancia nueva no ve la mutación de `a`
