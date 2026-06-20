"""Tests de core/email_render.py — T2.1 (Etapa 8): orquestación del renderer.

Alcance T2.1: la dataclass `EmailDoc` y `render_email` como esqueleto — forma del doc, iteración de
secciones LONG → SHORT consumiendo el orden del envelope (no reordena), sección ausente sin reventar,
y módulo sin imports LEAN/SDK. El contenido visible (lista de tickers, tabla, subject/header completos)
se testea en T2.2/T2.3/T2.4. Se construye el envelope vía core.output.build_envelope (T1) para no
acoplar el test a la forma interna del dict.
"""
from datetime import datetime

from core.email_render import EmailDoc, render_email
from core.output import build_envelope
from core.pipeline import ScanResult

AS_OF = datetime(2026, 6, 19, 20, 1, 0)


_EVIDENCE = {"D": {20: {"value": 150.2, "distance_pct": 0.0231, "bucket": "above_mild"}}}


def _result(ticker, direction, count, *, passed=None, evidence=None, partial=False):
    return ScanResult(
        strategy="swing_eod", as_of=AS_OF, ticker=ticker, direction=direction,
        rules_passed_count=count, passed_rules=passed or [], sma_evidence=evidence or {},
        partial_bar=partial, time_frames_evaluated=["D", "W", "M"],
    )


def _envelope(long_n=3, short_n=2):
    longs = [_result(t, "long", i) for i, t in enumerate(["AAA", "BBB", "CCC"][:long_n])]
    shorts = [_result(t, "short", i) for i, t in enumerate(["XXX", "YYY"][:short_n])]
    return build_envelope("swing_eod", "prod", AS_OF, False, {"long": longs, "short": shorts})


# (T2.1) render_email devuelve un EmailDoc con los 3 campos string.
def test_render_email_returns_emaildoc_with_three_string_fields():
    doc = render_email(_envelope())
    assert isinstance(doc, EmailDoc)
    assert isinstance(doc.subject, str)
    assert isinstance(doc.text_body, str)
    assert isinstance(doc.html_body, str)


# (T2.1) itera las secciones LONG antes que SHORT, en ambos cuerpos.
def test_render_email_iterates_long_before_short():
    doc = render_email(_envelope())
    assert "LONG" in doc.text_body and "SHORT" in doc.text_body
    assert doc.text_body.index("LONG") < doc.text_body.index("SHORT")
    assert doc.html_body.index("LONG") < doc.html_body.index("SHORT")


# (T2.1) sección ausente se omite sin reventar (D8.2).
def test_render_email_missing_section_does_not_break():
    env = build_envelope("market_close", "dev", AS_OF, False, {"long": [_result("AAA", "long", 1)]})
    doc = render_email(env)
    assert "LONG" in doc.text_body
    assert "SHORT" not in doc.text_body


# (T2.1) envelope sin candidatos en ningún lado: sin crash (defensivo).
def test_render_email_all_empty_does_not_break():
    env = build_envelope("swing_eod", "dev", AS_OF, False, {"long": [], "short": []})
    doc = render_email(env)
    assert isinstance(doc, EmailDoc)


# ---------------------------------------------------------------------------
# T2.2 / T2.3 / T2.4 — contenido del template (criterios a/b/c de T2).
# ---------------------------------------------------------------------------

# (a) 3 long + 2 short: bloque LONG con 3 tickers uno-por-línea, SHORT con 2, sin viñetas, en orden
#     rules_passed_count desc.
def test_text_body_ticker_lists_per_section_without_bullets():
    # counts: CCC=2, BBB=1, AAA=0 (long); YYY=1, XXX=0 (short) → orden desc por count.
    doc = render_email(_envelope())

    long_block = doc.text_body.split("LONG", 1)[1].split("SHORT", 1)[0]
    long_lines = [ln for ln in long_block.splitlines() if ln.strip()]
    assert long_lines[:3] == ["CCC", "BBB", "AAA"]  # tickers uno-por-línea, orden desc por reglas

    short_block = doc.text_body.split("SHORT", 1)[1]
    short_lines = [ln for ln in short_block.splitlines() if ln.strip()]
    assert short_lines[:2] == ["YYY", "XXX"]

    # ninguna línea de la lista de tickers lleva viñeta.
    for ticker in ("AAA", "BBB", "CCC", "XXX", "YYY"):
        assert f"- {ticker}" not in doc.text_body
        assert f"* {ticker}" not in doc.text_body
        assert f"• {ticker}" not in doc.text_body


# (b) html_body trae una <table> por sección, una fila por candidato; subject con strategy y totales.
def test_html_table_per_section_and_subject_totals():
    doc = render_email(_envelope())

    assert doc.html_body.count("<table") == 2  # una por sección (long + short)
    # 5 filas de datos (3 long + 2 short) + 2 filas de header (thead) = 7 <tr>.
    assert doc.html_body.count("<tr>") == 7

    assert "swing_eod" in doc.subject
    assert "(3 LONG · 2 SHORT)" in doc.subject
    assert "5 candidatos" in doc.subject


# (b) tabla de detalle: evidencia y reglas en lenguaje humano.
def test_detail_table_shows_human_evidence_and_rules():
    longs = [_result("AAA", "long", 2, passed=["AboveSMA(20,W+M)", "NotExtended(8,D)"], evidence=_EVIDENCE)]
    env = build_envelope("swing_eod", "prod", AS_OF, False, {"long": longs})
    doc = render_email(env)

    # evidencia: distance_pct (fracción) → "20SMA en días: 2.31%" (sin jerga D20:+...).
    assert "20SMA en días: 2.31%" in doc.text_body
    assert "20SMA en días: 2.31%" in doc.html_body
    assert "D20" not in doc.text_body
    # reglas humanizadas.
    assert "sobre las medias de semanas, meses" in doc.text_body
    assert "sin sobreextensión en días" in doc.text_body
    # reglas/evidencias separadas por salto de línea, NO por "; " ni " · ".
    assert "meses; sobre" not in doc.text_body
    assert "2.31% · " not in doc.text_body
    assert "<br>" in doc.html_body  # apilado en HTML


# evidencia short conserva el signo negativo; plural correcto en regla de 2 tfs.
def test_humanize_short_evidence():
    short_ev = {"D": {20: {"value": 140.0, "distance_pct": -0.018, "bucket": "below_mild"}}}
    shorts = [_result("IBM", "short", 1, passed=["BelowSMA(20,W+M)"], evidence=short_ev)]
    env = build_envelope("market_close", "prod", AS_OF, False, {"short": shorts})
    doc = render_email(env)
    assert "20SMA en días: -1.80%" in doc.text_body
    assert "bajo las medias de semanas, meses" in doc.text_body  # tfs reales W,M → plural


# la barra parcial NO es columna del correo (va en el header del cuerpo).
def test_no_partial_bar_column():
    env = build_envelope("swing_eod", "prod", AS_OF, False, {"long": [_result("AAA", "long", 1)]})
    doc = render_email(env)
    assert "Barra parcial" not in doc.text_body
    assert "Barra parcial" not in doc.html_body


# nombre de regla desconocido → se renderiza crudo (fallback robusto).
def test_unknown_rule_name_falls_back_to_raw():
    from core.email_render import _humanize_rule

    assert _humanize_rule("AboveSMA(20,D)") == "sobre la media de días"  # un solo tf → singular
    assert _humanize_rule("MysteryRule") == "MysteryRule"


# (c) un lado vacío renderiza "(sin candidatos)" sin reventar; el otro lado igual se renderiza.
def test_empty_side_renders_sin_candidatos():
    env = build_envelope("swing_eod", "prod", AS_OF, False,
                         {"long": [_result("AAA", "long", 1)], "short": []})
    doc = render_email(env)
    short_block = doc.text_body.split("SHORT", 1)[1]
    assert "(sin candidatos)" in short_block
    assert "AAA" in doc.text_body  # el lado long sí se renderiza


# (c) totals.all == 0 también renderiza (defensivo).
def test_all_empty_renders_without_crash():
    env = build_envelope("swing_eod", "prod", AS_OF, False, {"long": [], "short": []})
    doc = render_email(env)
    assert "0 candidatos" in doc.subject
    assert doc.text_body.count("(sin candidatos)") == 2


# (T2.4) header del cuerpo: estrategia/entorno/as_of; nota de barra parcial solo si partial_bar.
def test_header_and_partial_bar_note():
    env = build_envelope("market_close", "prod", AS_OF, True, {"long": [_result("AAA", "long", 1)]})
    doc = render_email(env)
    assert "market_close · prod · 2026-06-19 20:01Z" in doc.text_body
    assert "barra parcial: resultado provisional intradía" in doc.text_body

    env_no_partial = build_envelope("market_close", "prod", AS_OF, False, {"long": [_result("AAA", "long", 1)]})
    assert "barra parcial" not in render_email(env_no_partial).text_body


# (T6 precondición) render idéntico con envelope JSON-loaded (as_of string, period str) que con el dict nativo.
def test_render_identical_for_json_loaded_envelope():
    import json

    from core.output import serialize_json

    env = _envelope()
    json_env = json.loads(serialize_json(env))  # as_of → ISO string, period → string
    assert render_email(json_env) == render_email(env)


# (T2.1 / criterio d) email_render.py sin import de AlgorithmImports ni SDK de Gmail.
def test_email_render_module_has_no_external_imports():
    import core.email_render as render_mod

    with open(render_mod.__file__) as fh:
        import_lines = [ln for ln in fh if ln.lstrip().startswith(("import ", "from "))]
    assert not any("AlgorithmImports" in ln for ln in import_lines)
    assert not any(
        sdk in ln.lower() for ln in import_lines for sdk in ("googleapiclient", "smtplib", "google.oauth", "alpaca")
    )
