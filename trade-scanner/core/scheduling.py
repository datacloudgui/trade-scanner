"""Scheduling: mapeo declarativo del string de schedule (config) → time-rule de LEAN.

Extraído de main.py para poder testearlo sin engine (#6 triaje E1–E8): recibe `time_rules`
y `anchor` por parámetro (duck-typed) — cero AlgorithmImports, patrón core. Un cambio en el
string de config o en el mapeo rompía el schedule en silencio (grupo omitido con log).
"""


def time_rule_for(schedule: str, time_rules, anchor):
    """Traduce el string de schedule a una time-rule de LEAN anclada a `anchor`.

    `after_close` lleva +1 min para asegurar que la barra de cierre ya consolidó (D5).
    Desconocido → None (el caller loguea y omite el grupo). Punto de extensión: por ahora
    cubre los strings presentes en `strategies.json`.
    """
    if schedule == "after_close":
        return time_rules.after_market_close(anchor, 1)
    if schedule == "before_close_30m":
        return time_rules.before_market_close(anchor, 30)
    return None
