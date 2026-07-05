"""#6 (triaje E1–E8): regresión del mapeo schedule-string → time-rule (core/scheduling.py).

Un cambio en los strings de config ("after_close"/"before_close_30m") o en el mapeo rompía
el schedule EN SILENCIO (grupo omitido con log). Sin CLR: `time_rules` es un recorder
duck-typed; se asegura el método invocado, el ancla y el offset en minutos.
"""
from core.scheduling import time_rule_for


class _RecorderTimeRules:
    def __init__(self):
        self.calls = []

    def after_market_close(self, anchor, minutes):
        self.calls.append(("after_market_close", anchor, minutes))
        return "rule-after"

    def before_market_close(self, anchor, minutes):
        self.calls.append(("before_market_close", anchor, minutes))
        return "rule-before"


ANCHOR = object()  # el Symbol de SPY en runtime; opaco para el mapeo


# after_close → after_market_close(SPY, 1): +1 min para que la barra de cierre consolide (D5)
def test_after_close_maps_to_after_market_close_plus_one():
    tr = _RecorderTimeRules()
    assert time_rule_for("after_close", tr, ANCHOR) == "rule-after"
    assert tr.calls == [("after_market_close", ANCHOR, 1)]


def test_before_close_30m_maps_to_before_market_close_thirty():
    tr = _RecorderTimeRules()
    assert time_rule_for("before_close_30m", tr, ANCHOR) == "rule-before"
    assert tr.calls == [("before_market_close", ANCHOR, 30)]


# desconocido → None sin tocar time_rules (el caller loguea y omite el grupo)
def test_unknown_schedule_returns_none_without_calls():
    tr = _RecorderTimeRules()
    assert time_rule_for("at_open", tr, ANCHOR) is None
    assert tr.calls == []
