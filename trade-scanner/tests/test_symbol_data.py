"""T3.4–T3.8 (Etapa 5A): consolidators de calendario y SymbolData con TradeBars sintéticos.

Corren DENTRO de la imagen LEAN (scripts/run_tests.sh). Gotchas aplicados:
- Emisión perezosa (hallazgo T2): la barra queda en working hasta una barra posterior
  o scan(time); el lag se encadena a W/M. Cada test flushea con trailing bar o scan.
- Symbol.create(EQUITY) exige map file provider (solo existe dentro del engine):
  se construye el Symbol vía SecurityIdentifier.generate_equity(..., mapSymbol=False).
Calendario 2024 usado: 1-ene lunes → 8-ene lunes, 10-ene miércoles, 5-feb lunes (bisiesto).
"""
from datetime import datetime, timedelta

import pytest
from AlgorithmImports import Market, SecurityIdentifier, Symbol, TradeBar

from core.symbol_data import SymbolData
from core.timeframes import TIMEFRAMES

SPY = Symbol(SecurityIdentifier.generate_equity("SPY", Market.USA, False), "SPY")


def daily_bar(y, m, d, o, h, lo, c, v=100):
    # barra diaria LEAN: time 00:00 → end_time 00:00 del día siguiente
    return TradeBar(datetime(y, m, d), SPY, o, h, lo, c, v, timedelta(days=1))


def flat_day(y, m, d, px, v=100):
    return daily_bar(y, m, d, px, px, px, px, v)


def collect(consolidator) -> list:
    emitted = []
    consolidator.data_consolidated += lambda _s, bar: emitted.append(bar)
    return emitted


def push_week(sink, year, month, first_monday, close, v=100):
    """Empuja lun–vie planos con el close dado (sink = consolidator o SymbolData)."""
    push = sink.update
    for day in range(first_monday, first_monday + 5):
        push(flat_day(year, month, day, close, v))


# --- T3.4 — semana cierra viernes: 2 semanas lun–vie → exactamente 2 barras W ---

def test_t3_4_weekly_bars_group_monday_to_sunday():
    cons = TIMEFRAMES["W"].make_consolidator()
    emitted = collect(cons)
    # semana 1 (8–12 ene): O=10 (lunes), H=15 (martes), L=8 (miércoles), C=11 (viernes), V=5×100
    cons.update(daily_bar(2024, 1, 8, 10, 12, 9, 11))
    cons.update(daily_bar(2024, 1, 9, 11, 15, 10, 14))
    cons.update(daily_bar(2024, 1, 10, 14, 14, 8, 9))
    cons.update(daily_bar(2024, 1, 11, 9, 10, 9, 10))
    cons.update(daily_bar(2024, 1, 12, 10, 11, 10, 11))
    # semana 2 (15–19 ene): O=20, H=22 (viernes), L=19, C=22, V=5×100
    for day in (15, 16, 17, 18):
        cons.update(daily_bar(2024, 1, day, 20, 20, 20, 20))
    cons.update(daily_bar(2024, 1, 19, 20, 22, 19, 22))
    assert len(emitted) == 1  # solo W1 emitida (emisión perezosa)
    # scan sobre consolidator de CALENDARIO: debe emitir W2 (condiciona frescura W/M en 5B)
    cons.scan(datetime(2024, 1, 22))
    assert len(emitted) == 2
    w1, w2 = emitted
    assert (float(w1.open), float(w1.high), float(w1.low), float(w1.close)) == (10, 15, 8, 11)
    assert float(w1.volume) == 500
    # Calendar.WEEKLY agrupa lunes→domingo: time = lunes, end_time = lunes siguiente
    assert w1.time == datetime(2024, 1, 8) and w1.end_time == datetime(2024, 1, 15)
    assert (float(w2.open), float(w2.high), float(w2.low), float(w2.close)) == (20, 22, 19, 22)
    assert w2.time == datetime(2024, 1, 15) and w2.end_time == datetime(2024, 1, 22)


# --- T3.5 — mes calendario: 2 meses de barras diarias → 2 barras M ---

def test_t3_5_monthly_bars_group_calendar_month():
    cons = TIMEFRAMES["M"].make_consolidator()
    emitted = collect(cons)
    # enero: O=10 (día 2), H=13 (día 31), L=9 (día 16), C=12 (día 31), V=3×100
    cons.update(daily_bar(2024, 1, 2, 10, 10, 10, 10))
    cons.update(daily_bar(2024, 1, 16, 11, 12, 9, 11))
    cons.update(daily_bar(2024, 1, 31, 11, 13, 10, 12))
    # febrero (bisiesto, 29 días): O=20 (día 1), H=22, L=18, C=21 (día 29), V=2×100
    cons.update(daily_bar(2024, 2, 1, 20, 21, 19, 20))
    cons.update(daily_bar(2024, 2, 29, 20, 22, 18, 21))
    # flush por trailing bar (mecanismo alternativo a scan): marzo cruza el límite
    cons.update(flat_day(2024, 3, 1, 30))
    assert len(emitted) == 2
    m1, m2 = emitted
    assert (float(m1.open), float(m1.high), float(m1.low), float(m1.close)) == (10, 13, 9, 12)
    assert float(m1.volume) == 300
    # Calendar.MONTHLY: time = día 1 del mes (aunque la primera barra sea del día 2)
    assert m1.time == datetime(2024, 1, 1) and m1.end_time == datetime(2024, 2, 1)
    assert (float(m2.open), float(m2.high), float(m2.low), float(m2.close)) == (20, 22, 18, 21)
    assert m2.time == datetime(2024, 2, 1) and m2.end_time == datetime(2024, 3, 1)


# --- T3.6 — SMA a mano vía la cadena completa: semanas que cierran 10, 20, 30 → SMA(3) = 20.0 ---

def test_t3_6_weekly_sma_hand_checked_through_chain():
    sd = SymbolData(SPY, {"W": {3}})
    push_week(sd, 2024, 1, 8, 10)    # semana 1 cierra 10
    push_week(sd, 2024, 1, 15, 20)   # semana 2 cierra 20
    push_week(sd, 2024, 1, 22, 30)   # semana 3 cierra 30
    assert sd.is_ready("W", 3) is False  # lag encadenado: W3 aún sin emitir
    # trailing bar (lun sem.4) + scan: el lunes debe ser EMITIDO como barra diaria
    # para llegar al consolidator W y cruzar el límite (hallazgo T2)
    sd.update(flat_day(2024, 1, 29, 40))
    sd.scan(datetime(2024, 1, 30))
    assert sd.is_ready("W", 3) is True
    # SMA(3) = (10+20+30)/3 = 20.0; la semana 4 en curso NO contamina (sin emitir)
    assert float(sd.sma("W", 3).current.value) == pytest.approx(20.0)
    assert int(sd.sma("W", 3).samples) == 3


# --- T3.7 — primera barra parcial: el buffer expulsa la semana incompleta de la ventana ---

def test_t3_7_buffer_pushes_partial_first_week_out_of_sma_window():
    sd = SymbolData(SPY, {"W": {2}})
    w_bars = collect(sd._chained["W"])  # introspección de test (como T3.8)
    bars_pushed = 0
    # historia arranca un MIÉRCOLES (10-ene): semana 1 parcial (mié–vie), close 100 (valor veneno)
    for day in (10, 11, 12):
        sd.update(flat_day(2024, 1, day, 100))
        bars_pushed += 1
    # 3 semanas completas: cierran 10, 20, 30 (la del 29-ene cruza a febrero)
    for monday, close in ((15, 10), (22, 20)):
        push_week(sd, 2024, 1, monday, close)
        bars_pushed += 5
    for m, d in ((1, 29), (1, 30), (1, 31), (2, 1), (2, 2)):
        sd.update(flat_day(2024, m, d, 30))
        bars_pushed += 1
    # trailing (lun 5-feb) + scan para flushear la semana 4
    sd.update(flat_day(2024, 2, 5, 40))
    bars_pushed += 1
    sd.scan(datetime(2024, 2, 6))
    # el buffer de D1 (n×5+10) cubre la historia usada: 19 ≤ warmup_bars(2) = 20
    assert bars_pushed <= TIMEFRAMES["W"].warmup_bars(2)
    # la primera barra W emitida ES parcial: solo mié–vie, pero time = lunes de su semana
    assert len(w_bars) == 4
    first = w_bars[0]
    assert float(first.close) == 100 and float(first.volume) == 300  # 3 días × 100
    assert first.time == datetime(2024, 1, 8) and first.end_time == datetime(2024, 1, 15)
    # SMA(2) = (20+30)/2 = 25.0 — la ventana rodante ya expulsó la semana parcial (close 100)
    assert float(sd.sma("W", 2).current.value) == pytest.approx(25.0)
    assert int(sd.sma("W", 2).samples) == 4


# --- T3.8 — unión exacta: solo se construye lo declarado, nada de más ---

def test_t3_8_exact_union_builds_nothing_extra():
    sd = SymbolData(SPY, {"D": {8, 20}, "W": {20}})
    assert sd.timeframes == {"D", "W"}          # no existe consolidator M
    assert sd.declared == {("D", 8), ("D", 20), ("W", 20)}
    with pytest.raises(KeyError, match="W:8"):  # SMA W:8 no fue declarada
        sd.sma("W", 8)
    with pytest.raises(KeyError, match="M:20"):
        sd.sma("M", 20)


def test_t3_8_empty_period_set_builds_nothing():
    sd = SymbolData(SPY, {"D": {8}, "M": set()})
    assert sd.timeframes == {"D"}
    assert sd.declared == {("D", 8)}


def test_t3_8_unknown_timeframe_raises_keyerror_naming_it():
    with pytest.raises(KeyError, match="X"):
        SymbolData(SPY, {"X": {8}})
