"""Tests de core/output.py — T1 (Etapa 8): serialización pura + envelope.

L4 negocio puro: output.py NO importa AlgorithmImports (verificado por test de import + grep en el
criterio (d)). Se testea sobre `ScanResult` sintéticos, sin CLR ni engine: build_envelope (orden,
totals, lado vacío), serialize_csv (contrato PLAN §5, columna direction) y serialize_json (round-trip).
"""
import csv
import io
import json
from datetime import datetime, timedelta, tzinfo

from core.output import (
    CSV_HEADER,
    JsonSubscriberSource,
    OutputSink,
    build_envelope,
    serialize_csv,
    serialize_json,
)
from core.pipeline import ScanResult

AS_OF = datetime(2026, 6, 19, 20, 1, 0)


def _result(ticker, direction, count, *, passed=None, evidence=None, price=100.0):
    return ScanResult(
        strategy="swing_eod",
        as_of=AS_OF,
        ticker=ticker,
        direction=direction,
        partial_bar=False,
        price=price,
        time_frames_evaluated=["D", "W", "M"],
        sma_evidence=evidence or {},
        passed_rules=passed or [],
        rules_passed_count=count,
    )


# ---------------------------------------------------------------------------
# T1.1 / criterio (a) — build_envelope: orden, totals, metadata, lado vacío.
# ---------------------------------------------------------------------------

def test_build_envelope_orders_each_section_and_computes_totals():
    # Desordenado a propósito en ambos lados; tie-break por ticker entre los dos count=2.
    longs = [
        _result("MSFT", "long", 2),
        _result("AAPL", "long", 2),
        _result("NVDA", "long", 3),
    ]
    shorts = [_result("XYZ", "short", 1), _result("ABC", "short", 2)]

    env = build_envelope("swing_eod", "prod", AS_OF, False, {"long": longs, "short": shorts})

    assert env["strategy"] == "swing_eod"
    assert env["env"] == "prod"
    assert env["as_of"] == AS_OF
    assert env["partial_bar"] is False
    assert env["totals"] == {"long": 3, "short": 2, "all": 5}

    # LONG: NVDA(3), luego AAPL(2) antes que MSFT(2) por tie-break alfabético.
    long_tickers = [c["ticker"] for c in env["sections"]["long"]["candidates"]]
    assert long_tickers == ["NVDA", "AAPL", "MSFT"]
    assert env["sections"]["long"]["count"] == 3
    assert env["sections"]["long"]["direction"] == "long"

    # SHORT: ABC(2) antes que XYZ(1).
    short_tickers = [c["ticker"] for c in env["sections"]["short"]["candidates"]]
    assert short_tickers == ["ABC", "XYZ"]
    assert env["sections"]["short"]["count"] == 2


def test_build_envelope_empty_side_does_not_break():
    env = build_envelope("market_close", "dev", AS_OF, False, {"long": [_result("AAPL", "long", 1)]})
    assert env["totals"] == {"long": 1, "short": 0, "all": 1}
    assert "short" not in env["sections"]  # sección ausente, robusto (D8.2)
    assert env["sections"]["long"]["count"] == 1


def test_build_envelope_all_empty():
    env = build_envelope("swing_eod", "dev", AS_OF, False, {"long": [], "short": []})
    assert env["totals"] == {"long": 0, "short": 0, "all": 0}
    assert env["sections"]["long"]["count"] == 0
    assert env["sections"]["short"]["count"] == 0


# ---------------------------------------------------------------------------
# T1.2 / criterio (b) — serialize_csv: header + tipos exactos de PLAN §5.
# ---------------------------------------------------------------------------

def test_serialize_csv_contract_with_both_sides():
    evidence = {"D": {20: {"value": 150.2, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    longs = [_result("AAPL", "long", 2, passed=["AboveSMA20", "NotExtended"], evidence=evidence)]
    shorts = [_result("XYZ", "short", 1, passed=["BelowSMA20"], evidence=evidence)]

    csv_str = serialize_csv({"long": longs, "short": shorts})
    rows = list(csv.reader(io.StringIO(csv_str)))

    # Header exacto.
    assert rows[0] == CSV_HEADER
    assert csv_str.splitlines()[0] == ",".join(CSV_HEADER)

    # Fila long primero, luego short (orden de sección).
    assert rows[1][CSV_HEADER.index("direction")] == "long"
    assert rows[2][CSV_HEADER.index("direction")] == "short"

    long_row = rows[1]
    assert long_row[CSV_HEADER.index("strategy")] == "swing_eod"
    assert long_row[CSV_HEADER.index("as_of")] == "2026-06-19T20:01:00"
    assert long_row[CSV_HEADER.index("ticker")] == "AAPL"
    assert long_row[CSV_HEADER.index("partial_bar")] == "False"
    assert long_row[CSV_HEADER.index("time_frames_evaluated")] == "D,W,M"
    # passed_rules pipe-separated (2 reglas).
    assert long_row[CSV_HEADER.index("passed_rules")] == "AboveSMA20|NotExtended"
    # sma_evidence como JSON string parseable; claves period int → string.
    parsed = json.loads(long_row[CSV_HEADER.index("sma_evidence")])
    assert parsed == {"D": {"20": {"value": 150.2, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    assert long_row[CSV_HEADER.index("rules_passed_count")] == "2"


def test_serialize_csv_orders_within_section():
    longs = [_result("MSFT", "long", 1), _result("AAPL", "long", 3)]
    rows = list(csv.reader(io.StringIO(serialize_csv({"long": longs}))))
    assert [r[CSV_HEADER.index("ticker")] for r in rows[1:]] == ["AAPL", "MSFT"]


def test_serialize_csv_empty_sections_only_header():
    csv_str = serialize_csv({"long": [], "short": []})
    assert csv_str.splitlines() == [",".join(CSV_HEADER)]


# ---------------------------------------------------------------------------
# T1.3 / criterio (c) — serialize_json: round-trip estable, as_of ISO 8601.
# ---------------------------------------------------------------------------

def test_serialize_json_roundtrip():
    evidence = {"D": {20: {"value": 150.2, "distance_pct": 0.0231, "bucket": "above_mild"}}}
    env = build_envelope(
        "swing_eod", "prod", AS_OF, True,
        {"long": [_result("AAPL", "long", 2, passed=["AboveSMA20"], evidence=evidence)]},
    )
    loaded = json.loads(serialize_json(env))

    assert loaded["strategy"] == "swing_eod"
    assert loaded["as_of"] == "2026-06-19T20:01:00"  # datetime → ISO 8601
    assert loaded["partial_bar"] is True
    assert loaded["totals"] == {"long": 1, "short": 0, "all": 1}
    cand = loaded["sections"]["long"]["candidates"][0]
    assert cand["ticker"] == "AAPL"
    assert cand["as_of"] == "2026-06-19T20:01:00"
    # claves period int → string en JSON.
    assert cand["sma_evidence"] == {"D": {"20": {"value": 150.2, "distance_pct": 0.0231, "bucket": "above_mild"}}}


def test_serialize_json_is_stable():
    env = build_envelope("swing_eod", "dev", AS_OF, False, {"long": [_result("AAPL", "long", 1)]})
    assert serialize_json(env) == serialize_json(env)


# ---------------------------------------------------------------------------
# T3.1 — OutputSink: constructor + resolución de canales por entorno (sin emit, eso es T3.2).
# ---------------------------------------------------------------------------

class _StubSubscribers:
    def for_strategy(self, base):
        return []


_NOTIF_CONFIG = {
    "environments": {
        "dev": {"channels": ["file"], "notify_empty": False},
        "prod": {"channels": ["file", "host_email"], "notify_empty": True},
    },
}


def _sink(live_mode=True, log=None):
    return OutputSink(
        object_store=object(), notify=object(), live_mode=live_mode,
        notif_config=_NOTIF_CONFIG, subscribers=_StubSubscribers(), log=log,
    )


# (T3.1) el constructor guarda los handles recibidos (no import).
def test_outputsink_stores_handles():
    store, notify, subs = object(), object(), _StubSubscribers()
    sink = OutputSink(store, notify, False, _NOTIF_CONFIG, subs)
    assert sink._object_store is store
    assert sink._notify is notify
    assert sink._live_mode is False
    assert sink._subscribers is subs


# (T3.1) canales resueltos por entorno desde notif_config (D8.4 — sin if env==).
def test_channels_for_reads_config_per_env():
    sink = _sink()
    assert sink._channels_for("dev") == ["file"]
    assert sink._channels_for("prod") == ["file", "host_email"]


# (T3.1) entorno ausente → ["file"] (D8.3: SIEMPRE archivo) y deja traza en log.
def test_channels_for_unknown_env_defaults_to_file_and_logs():
    logged = []
    sink = _sink(log=logged.append)
    assert sink._channels_for("staging") == ["file"]
    assert any("staging" in line for line in logged)


# (T3.1) notify_empty por entorno: default False, configurable a True.
def test_notify_empty_per_env():
    sink = _sink()
    assert sink._notify_empty_for("dev") is False
    assert sink._notify_empty_for("prod") is True
    assert sink._notify_empty_for("staging") is False  # ausente → default


# ---------------------------------------------------------------------------
# T3.2 — emit + tabla de handlers (file / qc_notify / host_email).
# ---------------------------------------------------------------------------

class _MockStore:
    def __init__(self):
        self.saved = {}

    def save(self, key, value):
        self.saved[key] = value


class _MockNotify:
    def __init__(self):
        self.calls = []

    def email(self, address, subject, message):
        self.calls.append((address, subject, message))


class _Subs:
    def __init__(self, mapping):
        self.mapping = mapping

    def for_strategy(self, base):
        return self.mapping.get(base, [])


def _emit_sink(channels, *, live_mode=True, subs=None, log=None, notify_empty=False):
    cfg = {"environments": {"prod": {"channels": channels, "notify_empty": notify_empty}}}
    store, notify = _MockStore(), _MockNotify()
    sink = OutputSink(store, notify, live_mode, cfg, _Subs(subs or {}), log=log)
    return sink, store, notify


def _sections():
    return {
        "long": [_result("AAPL", "long", 2, passed=["AboveSMA(20,D)"], evidence={"D": {20: {"value": 1.0, "distance_pct": 0.02, "bucket": "above_mild"}}})],
        "short": [_result("IBM", "short", 1, passed=["BelowSMA(20,D)"], evidence={"D": {20: {"value": 1.0, "distance_pct": -0.02, "bucket": "below_mild"}}})],
    }


# (a) file + qc_notify en live: 3 archivos bajo results/<base>/ y notify.email UNA vez.
def test_emit_file_and_qc_notify_live():
    sink, store, notify = _emit_sink(
        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com", "b@x.com"]}
    )
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())

    assert set(store.saved) == {
        "results/swing_eod/20260619-2001.json",
        "results/swing_eod/20260619-2001.csv",
        "results/swing_eod/latest.json",
    }
    # latest.json == el .json del scan (puntero fijo).
    assert store.saved["results/swing_eod/latest.json"] == store.saved["results/swing_eod/20260619-2001.json"]

    assert len(notify.calls) == 1
    address, subject, _message = notify.calls[0]
    assert address == "a@x.com,b@x.com"
    assert "swing_eod" in subject and "(1 LONG · 1 SHORT)" in subject


# (c) file + host_email: archivos escritos, notify.email NUNCA; log marca "listo para host".
def test_emit_file_and_host_email():
    logged = []
    sink, store, notify = _emit_sink(["file", "host_email"], log=logged.append)
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())

    assert "results/swing_eod/latest.json" in store.saved
    assert notify.calls == []
    assert any("listo para script host" in line for line in logged)


# (b/T3.3) backtest: mismos canales pero notify.email NO se llama (gate de vida).
def test_emit_backtest_suppresses_qc_notify():
    logged = []
    sink, store, notify = _emit_sink(
        ["file", "qc_notify"], live_mode=False, subs={"swing_eod": ["a@x.com"]}, log=logged.append
    )
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())

    assert "results/swing_eod/latest.json" in store.saved  # archivo sí
    assert notify.calls == []  # correo no
    assert any("suprimido en backtest" in line for line in logged)


# qc_notify sin suscriptores: no se llama notify.email (lookup por base, D8.5).
def test_emit_qc_notify_without_subscribers():
    sink, store, notify = _emit_sink(["file", "qc_notify"], subs={})  # base sin lista
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())
    assert notify.calls == []


# canal desconocido en config → ignorado (sin reventar), logueado.
def test_emit_unknown_channel_ignored():
    logged = []
    sink, store, notify = _emit_sink(["file", "bogus"], log=logged.append)
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())
    assert "results/swing_eod/latest.json" in store.saved
    assert any("canal desconocido 'bogus'" in line for line in logged)


# ---------------------------------------------------------------------------
# T3.4 — notify_empty: scan sin candidatos escribe archivo pero no notifica (salvo config).
# ---------------------------------------------------------------------------

# (d) totals.all==0 y notify_empty=False: archivo sí, correo no.
def test_emit_empty_scan_writes_file_but_no_notify():
    logged = []
    sink, store, notify = _emit_sink(
        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=False, log=logged.append
    )
    sink.emit("swing_eod", "prod", AS_OF, False, {"long": [], "short": []})

    assert "results/swing_eod/latest.json" in store.saved  # auditoría sí (D8.3)
    assert notify.calls == []  # correo no
    assert any("notify_empty=false" in line for line in logged)


# notify_empty=True: un scan vacío sí dispara qc_notify (override de config).
def test_emit_empty_scan_notifies_when_notify_empty_true():
    sink, store, notify = _emit_sink(
        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=True
    )
    sink.emit("swing_eod", "prod", AS_OF, False, {"long": [], "short": []})
    assert len(notify.calls) == 1


# notify_empty no aplica con candidatos: scan no-vacío notifica normal.
def test_emit_non_empty_notifies_regardless_of_notify_empty():
    sink, store, notify = _emit_sink(
        ["file", "qc_notify"], subs={"swing_eod": ["a@x.com"]}, notify_empty=False
    )
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())
    assert len(notify.calls) == 1


# el CSV escrito conforma el contrato (header PLAN §5 + ambos lados con columna direction).
def test_emit_file_csv_is_plan_contract():
    sink, store, _ = _emit_sink(["file"])
    sink.emit("swing_eod", "prod", AS_OF, False, _sections())
    csv_str = store.saved["results/swing_eod/20260619-2001.csv"]
    rows = list(csv.reader(io.StringIO(csv_str)))
    assert rows[0] == CSV_HEADER
    directions = {r[CSV_HEADER.index("direction")] for r in rows[1:]}
    assert directions == {"long", "short"}


# ---------------------------------------------------------------------------
# Regresión (T5): el `as_of` de runtime es un datetime tz-aware con un tzinfo no-deepcopiable
# (el `GMT` de LEAN/pythonnet). `build_envelope` NO debe deepcopiar (asdict revienta); copia
# superficial + serialización por isoformat.
# ---------------------------------------------------------------------------

class _NoDeepcopyTZ(tzinfo):
    """Simula el `GMT` de LEAN: utcoffset normal, pero revienta si se intenta deep-copiar."""

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "GMT"

    def __deepcopy__(self, memo):
        raise TypeError("GMT.__init__() missing 2 required positional arguments")


def test_build_envelope_does_not_deepcopy_runtime_datetime():
    as_of = datetime(2013, 10, 11, 19, 30, tzinfo=_NoDeepcopyTZ())
    r = ScanResult(
        strategy="market_close_short", as_of=as_of, ticker="IBM", direction="short",
        partial_bar=True, price=184.11, time_frames_evaluated=["D"],
        sma_evidence={"D": {"8": {"distance_pct": -0.002}}}, passed_rules=["BelowSMA(8,D)"],
        rules_passed_count=1,
    )
    env = build_envelope("market_close", "dev", as_of, True, {"short": [r]})
    # Serializa sin reventar y el as_of sale como ISO 8601 con offset.
    out = json.loads(serialize_json(env))
    assert out["as_of"].startswith("2013-10-11T19:30:00")
    assert out["sections"]["short"]["candidates"][0]["ticker"] == "IBM"
    # CSV también serializa el datetime tz-aware sin deepcopy.
    assert "2013-10-11T19:30:00" in serialize_csv({"short": [r]})


# ---------------------------------------------------------------------------
# T4.2 — JsonSubscriberSource: lookup por estrategia base, swappable a DB (D8.5).
# ---------------------------------------------------------------------------

_SUBS_CONFIG = {
    "subscribers": {
        "swing_eod": ["a@example.com", "b@example.com"],
        "market_close": ["c@example.com"],
    },
}


def test_subscriber_source_returns_list_for_base():
    src = JsonSubscriberSource(_SUBS_CONFIG)
    assert src.for_strategy("swing_eod") == ["a@example.com", "b@example.com"]
    assert src.for_strategy("market_close") == ["c@example.com"]


def test_subscriber_source_missing_base_returns_empty():
    src = JsonSubscriberSource(_SUBS_CONFIG)
    # Variante (no es clave de base) y base inexistente → [] sin reventar.
    assert src.for_strategy("swing_eod_short") == []
    assert src.for_strategy("desconocida") == []


def test_subscriber_source_no_subscribers_key():
    # Config sin sección "subscribers" → [] (robusto ante config incompleta).
    assert JsonSubscriberSource({}).for_strategy("swing_eod") == []


# ---------------------------------------------------------------------------
# Criterio (d) — output.py sin AlgorithmImports a nivel de módulo.
# ---------------------------------------------------------------------------

def test_output_module_has_no_algorithm_imports():
    import core.output as output_mod

    src = output_mod.__file__
    with open(src) as fh:
        lines = fh.readlines()
    # No import a nivel de módulo (la palabra puede aparecer en docstrings; lo que importa es que
    # no se importe el SDK de LEAN ni un broker/datos externo).
    import_lines = [ln for ln in lines if ln.lstrip().startswith(("import ", "from "))]
    assert not any("AlgorithmImports" in ln for ln in import_lines)
    assert not any("alpaca" in ln.lower() for ln in import_lines)
