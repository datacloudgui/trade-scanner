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


def minute_bar(y, m, d, hh, mm, o, h, lo, c, v=10):
    return TradeBar(datetime(y, m, d, hh, mm), SPY, o, h, lo, c, v, timedelta(minutes=1))


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


# --- T3.9 — equivalencia de rutas (des-riesga 5B): warmup daily vs runtime minute ---

# 2 semanas completas (8–12 y 15–19 ene) + lunes 22 para que la semana 2 emita
EQUIV_DAYS = [(2024, 1, d) for d in (8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22)]


def assert_bars_identical(a, b):
    assert a.time == b.time and a.end_time == b.end_time
    assert (float(a.open), float(a.high), float(a.low), float(a.close), float(a.volume)) == (
        float(b.open), float(b.high), float(b.low), float(b.close), float(b.volume)
    )


def test_t3_9_daily_and_minute_routes_produce_identical_state():
    requirements = {"D": {3}, "W": {2}}
    sd_daily = SymbolData(SPY, requirements)    # ruta (a): warmup con barras diarias
    sd_minute = SymbolData(SPY, requirements)   # ruta (b): runtime con barras minute
    d_a, d_b = collect(sd_daily.daily_consolidator), collect(sd_minute.daily_consolidator)
    w_a, w_b = collect(sd_daily._chained["W"]), collect(sd_minute._chained["W"])

    for i, (y, m, d) in enumerate(EQUIV_DAYS):
        # OHLCV variado y coherente: H > C > O > L, volumen distinto por día
        o, h, lo, c, v = 100 + i, 105 + i, 97 + i, 102 + i, 100 + 10 * i
        sd_daily.update(daily_bar(y, m, d, o, h, lo, c, v))
        # 3 minutos que agregan exactamente al mismo OHLCV: open=1ª, H/L en la del
        # mediodía, close=última, volúmenes 30+40+(v-70)=v
        sd_minute.update(TradeBar(datetime(y, m, d, 9, 31), SPY, o, o, o, o, 30, timedelta(minutes=1)))
        sd_minute.update(TradeBar(datetime(y, m, d, 12, 0), SPY, o, h, lo, c, 40, timedelta(minutes=1)))
        sd_minute.update(TradeBar(datetime(y, m, d, 15, 59), SPY, c, c, c, c, v - 70, timedelta(minutes=1)))

    flush = datetime(2024, 1, 23)
    sd_daily.scan(flush)
    sd_minute.scan(flush)

    # mismas barras diarias emitidas (la ruta minute las construye, la daily las pasa)
    assert len(d_a) == len(d_b) == len(EQUIV_DAYS)
    for bar_a, bar_b in zip(d_a, d_b):
        assert_bars_identical(bar_a, bar_b)
    # mismas barras W: 2 emitidas; la semana del 22 queda en working (sin emitir) en ambas
    assert len(w_a) == len(w_b) == 2
    for bar_a, bar_b in zip(w_a, w_b):
        assert_bars_identical(bar_a, bar_b)
    assert w_a[0].end_time == datetime(2024, 1, 15) and w_a[1].end_time == datetime(2024, 1, 22)
    # SMAs finales idénticas (igualdad exacta, no aproximada) y calientes en ambas rutas
    assert sd_daily.is_ready() and sd_minute.is_ready()
    for tf, period in (("D", 3), ("W", 2)):
        sma_a, sma_b = sd_daily.sma(tf, period), sd_minute.sma(tf, period)
        assert int(sma_a.samples) == int(sma_b.samples)
        assert float(sma_a.current.value) == float(sma_b.current.value)
        assert sma_a.current.end_time == sma_b.current.end_time


# --- T3.10 — working bar: OHLC parcial del día en curso con barras minute ---

def test_t3_10_working_bar_aggregates_partial_day():
    sd = SymbolData(SPY, {"D": {3}})
    assert sd.working_bar is None  # antes de la primera barra
    # media sesión: open de la 1ª=100, high máx=106 (2ª), low mín=98 (2ª), close de la última=104
    sd.update(minute_bar(2024, 1, 8, 9, 31, 100, 102, 99, 101))
    sd.update(minute_bar(2024, 1, 8, 10, 15, 101, 106, 98, 105))
    sd.update(minute_bar(2024, 1, 8, 12, 0, 105, 105, 103, 104))
    wb = sd.working_bar
    assert wb is not None
    assert (float(wb.open), float(wb.high), float(wb.low), float(wb.close)) == (100, 106, 98, 104)
    assert float(wb.volume) == 30  # 3 barras × 10


# --- T3.11 — readiness: 19 barras W no bastan para SMA(20); el agregado refleja la más lenta ---

def push_weeks(sd, first_monday, n_weeks, close=10):
    """n_weeks completas lun–vie de barras diarias planas a partir de un lunes."""
    for week in range(n_weeks):
        for weekday in range(5):
            day = first_monday + timedelta(weeks=week, days=weekday)
            sd.update(flat_day(day.year, day.month, day.day, close))


def test_t3_11_readiness_per_series_and_aggregate():
    sd = SymbolData(SPY, {"D": {3}, "W": {20}})
    monday1 = datetime(2024, 1, 8)
    push_weeks(sd, monday1, 20)
    # 20 semanas pusheadas → solo 19 barras W emitidas (lag encadenado, hallazgo T2)
    assert int(sd.sma("W", 20).samples) == 19
    assert sd.is_ready("W", 20) is False
    assert sd.is_ready("D", 3) is True   # la serie rápida ya está caliente
    assert sd.is_ready() is False        # el agregado refleja la serie más lenta
    # lunes de la semana 21 + scan → emite la barra W nº 20
    monday21 = monday1 + timedelta(weeks=20)
    sd.update(flat_day(monday21.year, monday21.month, monday21.day, 10))
    sd.scan(monday21 + timedelta(days=1))
    assert sd.is_ready("W", 20) is True
    assert sd.is_ready() is True


# --- T3 (Etapa 5B) — accessor de consolidators para observers de L5 ---

def test_5b_t3_consolidator_accessor_and_observer_order():
    sd = SymbolData(SPY, {"D": {2}, "W": {1}})
    assert sd.consolidator("D") is sd.daily_consolidator
    # Observer añadido DESPUÉS de construir SymbolData: cuando emite, la SMA del mismo
    # consolidator YA está actualizada (orden de handlers .NET = orden de suscripción).
    # El recorder de validación de main.py (T3) depende de esta garantía.
    seen = []
    sd.consolidator("W").data_consolidated += (
        lambda _s, bar: seen.append((bar.end_time, float(sd.sma("W", 1).current.value)))
    )
    push_week(sd, 2024, 1, 8, 11)
    sd.scan(datetime(2024, 1, 15))
    assert seen == [(datetime(2024, 1, 15), pytest.approx(11.0))]
    with pytest.raises(KeyError) as err:
        sd.consolidator("M")
    assert "'M'" in str(err.value) and "'D'" in str(err.value) and "'W'" in str(err.value)
