"""Renderer del correo compartido (L4): un solo cuerpo, dos transportes (Etapa 8, D8.1).

Función **pura y SDK-free** — **sin `AlgorithmImports` ni SDK de Gmail** a nivel de módulo
(precedente `universe.py`, D-E4): la importan *ambos* planos, el algoritmo (transporte `qc_notify`
vía `self.notify.email`) y el script host (transporte Gmail). Flipar de cloud a local NO recompone
el cuerpo: el render es el mismo objeto; el entorno solo elige quién lo despacha (D8.4).

Robustez cross-plano: el envelope llega como dict construido por `build_envelope` (algoritmo —
`as_of` `datetime`, claves `period` int) **o** como `json.loads(latest.json)` (script host — `as_of`
string ISO, claves `period` string). Los helpers de formato (`_format_as_of`, `_evidence_str`)
toleran ambos para que el render sea **idéntico** en los dos planos (requisito de T6).

Template V1 (D8.6), revisable: el render es puro, iterar el HTML no toca lógica.
"""
import html
import re
from dataclasses import dataclass
from datetime import datetime

# Orden de display de las secciones: LONG antes que SHORT (D8.6). El envelope ya trae los candidatos
# ordenados dentro de cada sección (D8.2); aquí solo se decide el orden ENTRE secciones.
SECTION_ORDER = ("long", "short")

# Prefijo del subject (D8.6). Constante de presentación, no del envelope (que es la unidad de datos
# D8.2); un prefijo configurable por entorno es V2 (fuera de scope). El `email.subject_prefix` de
# `notifications.json` documenta el valor de referencia.
SUBJECT_PREFIX = "[trade-scanner]"

# Columnas de la tabla de detalle (D8.6.2). La barra parcial NO es columna: es uniforme por scan
# (deriva del horario, D7.4) y se anota una sola vez en el header del cuerpo.
_DETAIL_HEADERS = ("Ticker", "Reglas OK", "Qué cumple", "Distancia a las medias")

_PARTIAL_NOTE = "barra parcial: resultado provisional intradía"

# Humanización del correo (solo presentación; el CSV/JSON de output.py conservan los valores crudos).
# Timeframe → sustantivo legible. Desconocido → su propia letra (fallback).
_TF_NOUN = {"D": "días", "W": "semanas", "M": "meses"}

# Nombre de regla `Label(period,tf1+tf2+...)` (ver core/rules.py `SMAPositionRule.name`).
_RULE_RE = re.compile(r"^(\w+)\((\d+),([\w+]+)\)$")


@dataclass
class EmailDoc:
    """El correo renderizado, agnóstico del transporte: el mismo objeto va a `self.notify.email`
    (cloud, usa `html_body`) y al envío Gmail del script host. `text_body` es el fallback en texto
    plano; `subject` la línea de asunto. Construido solo por `render_email`.
    """

    subject: str
    text_body: str
    html_body: str


def render_email(envelope: dict) -> EmailDoc:
    """Envelope (D8.2) → `EmailDoc`. Render puro: lee el envelope, no toca estado ni datos.

    Itera las secciones en orden LONG → SHORT consumiendo el orden ya fijado por el envelope
    (reproducibilidad D7.6 — NO reordena). Una sección ausente se omite; una presente pero vacía
    renderiza "(sin candidatos)" sin reventar (D8.2/D8.6).
    """
    sections = envelope.get("sections", {})

    text_blocks: list[str] = []
    html_blocks: list[str] = []
    for side in SECTION_ORDER:
        section = sections.get(side)
        if section is None:
            continue
        text_blocks.append(_section_text(side, section))
        html_blocks.append(_section_html(side, section))

    text_body = _header_text(envelope) + "\n\n".join(text_blocks) + "\n"
    html_body = _header_html(envelope) + "\n".join(html_blocks)
    return EmailDoc(
        subject=_subject(envelope),
        text_body=text_body,
        html_body=html_body,
    )


# --- Subject + header (T2.4) ---------------------------------------------------------------------


def _subject(envelope: dict) -> str:
    """`[trade-scanner] {strategy} — {all} candidatos ({long} LONG · {short} SHORT) · {as_of}Z` (D8.6)."""
    totals = envelope.get("totals", {})
    return (
        f"{SUBJECT_PREFIX} {envelope.get('strategy', '')} — "
        f"{totals.get('all', 0)} candidatos "
        f"({totals.get('long', 0)} LONG · {totals.get('short', 0)} SHORT) · "
        f"{_format_as_of(envelope.get('as_of'))}Z"
    )


def _header_text(envelope: dict) -> str:
    """Header del cuerpo en texto: `estrategia · entorno · as_of`, + nota si `partial_bar` (D8.6)."""
    line = (
        f"{envelope.get('strategy', '')} · {envelope.get('env', '')} · "
        f"{_format_as_of(envelope.get('as_of'))}Z"
    )
    if envelope.get("partial_bar"):
        line += f"\n({_PARTIAL_NOTE})"
    return line + "\n\n"


def _header_html(envelope: dict) -> str:
    """Header del cuerpo en HTML, mismo contenido que `_header_text`."""
    line = (
        f"<p><strong>{html.escape(str(envelope.get('strategy', '')))}</strong> · "
        f"{html.escape(str(envelope.get('env', '')))} · "
        f"{html.escape(_format_as_of(envelope.get('as_of')))}Z</p>"
    )
    if envelope.get("partial_bar"):
        line += f"\n<p><em>{html.escape(_PARTIAL_NOTE)}</em></p>"
    return line + "\n"


# --- Secciones: lista de tickers (T2.2) + tabla de detalle (T2.3) --------------------------------


def _section_text(side: str, section: dict) -> str:
    """Bloque de una sección en texto: rótulo + lista de tickers uno-por-línea (sin viñetas) + tabla."""
    label = side.upper()
    candidates = section.get("candidates", [])
    if not candidates:
        return f"{label}\n(sin candidatos)"
    tickers = "\n".join(str(c.get("ticker", "")) for c in candidates)
    return f"{label}\n{tickers}\n\n{_detail_table_text(candidates)}"


def _section_html(side: str, section: dict) -> str:
    """Bloque de una sección en HTML: `<h2>` + `<pre>` de tickers (copia-pega) + `<table>` de detalle."""
    label = side.upper()
    candidates = section.get("candidates", [])
    if not candidates:
        return f"<h2>{label}</h2>\n<p>(sin candidatos)</p>"
    tickers = "\n".join(html.escape(str(c.get("ticker", ""))) for c in candidates)
    return f"<h2>{label}</h2>\n<pre>{tickers}</pre>\n{_detail_table_html(candidates)}"


def _detail_row(candidate: dict) -> tuple[list[str], list[str]]:
    """Las dos celdas multi-línea de la fila de detalle (D8.6.2): reglas y evidencias, una por línea."""
    return (
        [_humanize_rule(r) for r in candidate.get("passed_rules", [])],
        _evidence_lines(candidate),
    )


def _detail_table_text(candidates: list[dict]) -> str:
    """Tabla de detalle en texto plano. Reglas y evidencias van **una por línea** (columnas
    paralelas): cada candidato ocupa tantas líneas como su lado más largo; `Ticker`/`Reglas OK` solo
    en la primera. Mantiene la alineación a ancho fijo sin meter saltos dentro de una celda."""
    matrix: list[tuple[str, ...]] = [_DETAIL_HEADERS]
    for candidate in candidates:
        rules, evidence = _detail_row(candidate)
        rules, evidence = rules or [""], evidence or [""]
        for i in range(max(len(rules), len(evidence))):
            matrix.append((
                str(candidate.get("ticker", "")) if i == 0 else "",
                str(candidate.get("rules_passed_count", 0)) if i == 0 else "",
                rules[i] if i < len(rules) else "",
                evidence[i] if i < len(evidence) else "",
            ))
    widths = [max(len(row[j]) for row in matrix) for j in range(len(_DETAIL_HEADERS))]
    fmt = lambda row: "  ".join(c.ljust(widths[j]) for j, c in enumerate(row)).rstrip()
    return "\n".join(fmt(row) for row in matrix)


def _detail_table_html(candidates: list[dict]) -> str:
    """Tabla de detalle en HTML (`<table>`), una fila `<tr>` por candidato; reglas y evidencias
    apiladas con `<br>` dentro de su celda."""
    head = "".join(f"<th>{html.escape(h)}</th>" for h in _DETAIL_HEADERS)
    body = ""
    for candidate in candidates:
        rules, evidence = _detail_row(candidate)
        cells = (
            html.escape(str(candidate.get("ticker", ""))),
            html.escape(str(candidate.get("rules_passed_count", 0))),
            "<br>".join(html.escape(r) for r in rules),
            "<br>".join(html.escape(e) for e in evidence),
        )
        body += "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"
    return f'<table border="1"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


# --- Formato robusto cross-plano -----------------------------------------------------------------


def _format_as_of(value: object) -> str:
    """`as_of` → `YYYY-MM-DD HH:MM` (D8.6). Tolera `datetime` (algoritmo) y string ISO (script host)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(value)


def _humanize_rule(name: str) -> str:
    """Nombre técnico de regla → frase legible (solo presentación). Etiqueta/forma desconocida → cruda.

    `AboveSMA(20,W+M)` → "sobre las medias de semanas, meses"; `BelowSMA(...)` → "bajo ...";
    `NotExtended(8,D)` → "sin sobreextensión en días". El periodo de la SMA vive en la evidencia.
    """
    match = _RULE_RE.match(name)
    if not match:
        return name
    label, _period, tfs_raw = match.group(1), match.group(2), match.group(3)
    nouns = [_TF_NOUN.get(tf, tf) for tf in tfs_raw.split("+")]
    joined = ", ".join(nouns)
    medias = "la media" if len(nouns) == 1 else "las medias"
    if label == "AboveSMA":
        return f"sobre {medias} de {joined}"
    if label == "BelowSMA":
        return f"bajo {medias} de {joined}"
    if label == "NotExtended":
        return f"sin sobreextensión en {joined}"
    return name


def _evidence_lines(candidate: dict) -> list[str]:
    """Evidencia legible (D8.6.2), **una línea por `(tf, period)`** en orden de `time_frames_evaluated`.

    `distance_pct` es fracción (0.0231 → `2.31%`; negativo conserva el signo). Claves `period` int
    (algoritmo) o str (host JSON): se ordenan por valor numérico. Ej.: `["20SMA en días: 2.31%",
    "20SMA en semanas: 3.46%"]`.
    """
    evidence = candidate.get("sma_evidence", {})
    lines: list[str] = []
    for tf in candidate.get("time_frames_evaluated", []):
        tf_evidence = evidence.get(tf)
        if not tf_evidence:
            continue
        noun = _TF_NOUN.get(tf, tf)
        for period in sorted(tf_evidence, key=lambda p: int(p)):
            distance = tf_evidence[period].get("distance_pct", 0.0)
            lines.append(f"{period}SMA en {noun}: {distance:.2%}")
    return lines
