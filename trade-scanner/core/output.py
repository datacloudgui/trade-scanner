"""Salida (L4): serialización pura del scan + envelope por estrategia base (Etapa 8, T1).

Núcleo determinista del contrato de salida. **Sin `AlgorithmImports` ni SDK externo** a nivel de
módulo (precedente `universe.py`, D-E4): así lo importan el algoritmo (transporte `qc_notify`) y el
script host (transporte Gmail) con Python del `.venv`, y los tests corren con `ScanResult` sintéticos
sin CLR. Los handles de LEAN (`object_store`, `notify`) entran por constructor en T3, no por import.

Aquí vive SOLO la parte determinista (D8.2): construcción del envelope `por estrategia base·scan`
con candidatos partidos en secciones long/short, y la serialización CSV/JSON del contrato de
PLAN §5. El dispatch por canal/entorno (`OutputSink`) y el renderer del correo son T3/T2.
"""
import csv
import dataclasses
import io
import json
from collections.abc import Callable
from datetime import datetime

from core.email_render import render_email
from core.pipeline import ScanResult

# Orden canónico de secciones en envelope, CSV y correo: LONG antes que SHORT (D8.2/D8.6).
SECTION_ORDER = ("long", "short")

# Columnas del CSV en el orden exacto de la tabla de PLAN §5 (contrato de salida `ScanResult`).
CSV_HEADER = [
    "strategy",
    "as_of",
    "ticker",
    "direction",
    "partial_bar",
    "price",
    "time_frames_evaluated",
    "sma_evidence",
    "passed_rules",
    "rules_passed_count",
]


def _order_section(results: list[ScanResult]) -> list[ScanResult]:
    """Orden determinista de una sección: `rules_passed_count` desc, tie-break `ticker` asc (D7.6).

    Mismo orden en envelope, CSV y correo (reproducibilidad). Renderer y CSV NO reordenan: consumen
    el orden que fija esta función.
    """
    return sorted(results, key=lambda r: (-r.rules_passed_count, r.ticker))


def _scanresult_to_dict(result: ScanResult) -> dict:
    """Un `ScanResult` a dict serializable. Conserva `as_of` como `datetime` (lo convierte
    `serialize_json` vía su `default`); `sma_evidence` queda como objeto anidado (no string).

    Copia **superficial** de campos a propósito (no `dataclasses.asdict`): `asdict` deepcopia cada
    valor, y en runtime `as_of` es un `datetime` tz-aware cuyo `tzinfo` es el `GMT` de LEAN
    (pythonnet) que **no es deep-copiable** (`GMT.__init__()` revienta). Aquí solo se serializa,
    nunca se muta, así que la copia superficial es suficiente y segura.
    """
    return {f.name: getattr(result, f.name) for f in dataclasses.fields(result)}


def build_envelope(
    strategy: str,
    env: str,
    as_of: datetime | None,
    partial_bar: bool,
    sections: dict[str, list[ScanResult]],
) -> dict:
    """Envelope `por estrategia base·scan` (D8.2): metadata + candidatos por dirección.

    `sections` = `{"long": [ScanResult], "short": [ScanResult]}` (lados ausentes permitidos). Cada
    sección se ordena (`_order_section`) y se serializa a dicts; `totals` (long/short/all) se calcula
    sobre los conteos. No recomputa nada del `ScanResult`: solo agrupa y envuelve.
    """
    out_sections: dict[str, dict] = {}
    for side in SECTION_ORDER:
        results = sections.get(side)
        if results is None:
            continue
        ordered = _order_section(results)
        out_sections[side] = {
            "direction": side,
            "count": len(ordered),
            "candidates": [_scanresult_to_dict(r) for r in ordered],
        }

    n_long = len(sections.get("long") or [])
    n_short = len(sections.get("short") or [])
    return {
        "strategy": strategy,
        "env": env,
        "as_of": as_of,
        "partial_bar": partial_bar,
        "totals": {"long": n_long, "short": n_short, "all": n_long + n_short},
        "sections": out_sections,
    }


def _json_default(obj: object) -> str:
    """`default` de `json.dumps`: `datetime` → ISO 8601. Cualquier otro tipo es un error explícito."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"no serializable a JSON: {type(obj).__name__}")


def serialize_json(envelope: dict) -> str:
    """Envelope a JSON estable (D8.3): `sort_keys` para reproducibilidad, `datetime`→ISO 8601.

    Round-trip estable: `json.loads(serialize_json(env))` reproduce el envelope (con `as_of` y demás
    `datetime` como string ISO; claves `period` int del `sma_evidence` como string, por contrato JSON).
    """
    return json.dumps(envelope, sort_keys=True, default=_json_default, indent=2)


def _csv_row(result: ScanResult) -> list:
    """Una fila CSV del contrato de PLAN §5: tipos exactos (bool→`True`/`False`, listas y evidencia
    aplanadas a string). El quoting de los campos con comas/comillas lo hace `csv.writer`.
    """
    return [
        result.strategy,
        result.as_of.isoformat() if result.as_of is not None else "",
        result.ticker,
        result.direction,
        str(result.partial_bar),  # `True` / `False` (PLAN §5)
        result.price,
        ",".join(result.time_frames_evaluated),  # `D,W,M`
        json.dumps(result.sma_evidence, sort_keys=True),  # JSON string
        "|".join(result.passed_rules),  # pipe-separated
        result.rules_passed_count,
    ]


def serialize_csv(sections: dict[str, list[ScanResult]]) -> str:
    """Filas `ScanResult` de ambos lados en una sola tabla CSV (contrato PLAN §5).

    `sections` = `{"long": [...], "short": [...]}`. Orden: sección long, luego short; dentro de cada
    una, el orden de `_order_section`. La columna `direction` distingue los lados. `csv.writer`
    maneja el quoting del `sma_evidence` (JSON con comas). `\\n` como terminador (estable cross-OS).
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for side in SECTION_ORDER:
        results = sections.get(side)
        if not results:
            continue
        for result in _order_section(results):
            writer.writerow(_csv_row(result))
    return buf.getvalue()


class JsonSubscriberSource:
    """Fuente de suscriptores V1 (D8.5): lee `notifications.json["subscribers"][base]`.

    La lista de correos difiere **por estrategia base** (no por variante: una sola lista para
    `swing_eod` cubre LONG y SHORT) y es la sección más volátil de la config — candidata a migrar a
    DB. Por eso vive detrás de la interfaz mínima `for_strategy(base) -> list[str]`: un futuro
    `DbSubscriberSource` cumple la misma firma sin tocar `OutputSink` ni el render (solo se cambia el
    loader). **Sin secretos**: el token de Gmail vive en `.env`/GCP, nunca en `notifications.json`.
    """

    def __init__(self, notif_config: dict) -> None:
        self._subscribers: dict = notif_config.get("subscribers", {})

    def for_strategy(self, base: str) -> list[str]:
        """Suscriptores de una estrategia base. Base ausente → `[]` (no revienta): un grupo sin
        destinatarios simplemente no dispara `qc_notify` (lo gestiona `OutputSink._emit_qc_notify`)."""
        return list(self._subscribers.get(base, []))


# Punto de extensión documentado (D8.5, NO implementado en V1): una fuente de suscriptores
# respaldada por DB cumpliría la misma interfaz `for_strategy(base) -> list[str]` y se inyectaría en
# `OutputSink` sin cambios en el sink ni en el render. Ejemplo:
#
#   class DbSubscriberSource:
#       def __init__(self, conn): ...
#       def for_strategy(self, base: str) -> list[str]:
#           return [row.email for row in self._conn.query(base)]


class OutputSink:
    """El **único** punto del proyecto con el switch local/cloud (CLAUDE.md): dispatch de la salida
    del scan por **canales declarados en config**, no por `if env == ...` (D8.4, criterio nº6 SPECS).

    Recibe los handles del algoritmo **por constructor** (no import): así `output.py` sigue sin
    `AlgorithmImports` (precedente D-E4) y es testeable con mocks. T3.1 (esta entrega) deja el
    constructor y la resolución de canales por entorno desde `notif_config`; `emit` y la tabla de
    handlers (`file`/`qc_notify`/`host_email`) son T3.2–T3.4.

    `notif_config` es el dict de `config/notifications.json` (T4): `environments[env].channels` +
    `notify_empty`. `subscribers` es un `SubscriberSource` (duck-typed: `for_strategy(base)`),
    implementado en T4. `log` es el callable de log inyectado (patrón L4: el sink no habla con
    `QCAlgorithm`); por defecto no-op.
    """

    def __init__(
        self,
        object_store,
        notify,
        live_mode: bool,
        notif_config: dict,
        subscribers,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._object_store = object_store
        self._notify = notify
        self._live_mode = live_mode
        self._notif_config = notif_config
        self._subscribers = subscribers
        self._log = log or (lambda _msg: None)
        # Mapa entorno → config de canales (D8.4). El `env` activo llega en `emit` (D8.2), no aquí:
        # un mismo sink sirve cualquier entorno resolviendo contra esta tabla.
        self._environments: dict = notif_config.get("environments", {})

    def _channels_for(self, env: str) -> list[str]:
        """Canales habilitados para `env` (D8.4). Entorno ausente en config → `["file"]`: D8.3 exige
        SIEMPRE archivo, nunca se pierde la auditoría por config incompleta."""
        env_cfg = self._environments.get(env)
        if env_cfg is None:
            self._log(f"[output] entorno '{env}' sin config de canales; usando ['file'] (auditoría)")
            return ["file"]
        return list(env_cfg.get("channels", ["file"]))

    def _notify_empty_for(self, env: str) -> bool:
        """`notify_empty` para `env` (D8.3/D8.4): default `False` (un scan sin candidatos escribe
        archivo pero no notifica)."""
        return bool(self._environments.get(env, {}).get("notify_empty", False))

    def emit(
        self,
        strategy: str,
        env: str,
        as_of: datetime | None,
        partial_bar: bool,
        sections: dict,
    ) -> None:
        """Despacha la salida de un scan por estrategia base (D8.2/D8.4).

        Construye **un** envelope (T1.1). El archivo se persiste SIEMPRE (D8.3), fuera de la lista
        de canales: la auditoría no depende de que la config traiga `"file"` (triaje E1–E8 #21).
        Después, por cada canal de notificación habilitado del entorno, ejecuta su handler de la
        tabla `{qc_notify, host_email}`. Ningún `if env == ...`: el entorno solo aporta su lista de
        canales (criterio nº6 SPECS). `sections = {"long": [ScanResult], "short": [...]}`.
        """
        envelope = build_envelope(strategy, env, as_of, partial_bar, sections)
        self._emit_file(envelope, sections)
        handlers = {
            "qc_notify": self._emit_qc_notify,
            "host_email": self._emit_host_email,
        }
        for channel in self._channels_for(env):
            if channel == "file":
                continue  # ya persistido incondicionalmente arriba
            handler = handlers.get(channel)
            if handler is None:
                self._log(f"[output] {strategy}: canal desconocido '{channel}' ignorado")
                continue
            handler(envelope, sections)

    def _emit_file(self, envelope: dict, sections: dict) -> None:
        """Canal `file` (D8.3): persiste envelope JSON + CSV por timestamp y reescribe `latest.json`
        (puntero fijo del script host, opción A). Siempre presente; es la auditoría durable."""
        base = envelope["strategy"]
        ts = _timestamp(envelope.get("as_of"))
        json_str = serialize_json(envelope)
        self._object_store.save(f"results/{base}/{ts}.json", json_str)
        self._object_store.save(f"results/{base}/{ts}.csv", serialize_csv(sections))
        self._object_store.save(f"results/{base}/latest.json", json_str)
        self._log(f"[output] {base}: archivos results/{base}/{ts}.json|csv + latest.json")

    def _emit_qc_notify(self, envelope: dict, sections: dict) -> None:
        """Canal `qc_notify` (cloud): `notify.email` con el render compartido (T2). Guards, en orden:
        vida (D8.4/T3.3: backtest suprime), `notify_empty` (D8.3/T3.4: scan vacío no notifica salvo
        config), suscriptores (lookup por base, D8.5)."""
        base = envelope["strategy"]
        if not self._live_mode:
            self._log(f"[output] {base}: correo suprimido en backtest (qc_notify)")
            return
        if envelope.get("totals", {}).get("all", 0) == 0 and not self._notify_empty_for(
            envelope.get("env", "")
        ):
            self._log(f"[output] {base}: sin candidatos; qc_notify omitido (notify_empty=false)")
            return
        recipients = self._subscribers.for_strategy(base)
        if not recipients:
            self._log(f"[output] {base}: sin suscriptores; qc_notify omitido")
            return
        doc = render_email(envelope)
        self._notify.email(",".join(recipients), doc.subject, doc.html_body)
        self._log(f"[output] {base}: qc_notify enviado a {len(recipients)} suscriptor(es)")

    def _emit_host_email(self, envelope: dict, sections: dict) -> None:
        """Canal `host_email` (local/VPS): no-op de envío en el algoritmo. La persistencia +
        `latest.json` los garantiza el canal `file`; aquí solo se deja traza de "listo para el script
        host", que es quien envía por Gmail (T6). Mantiene el algoritmo agnóstico de Gmail (D8.1)."""
        self._log(f"[output] {envelope['strategy']}: envelope listo para script host (host_email)")


def _timestamp(as_of: datetime | None) -> str:
    """Clave de archivo `YYYYMMDD-HHMM` desde `as_of` (D8.3). `None` → `unknown` (defensivo; en
    runtime `as_of` siempre viene del scan)."""
    if isinstance(as_of, datetime):
        return as_of.strftime("%Y%m%d-%H%M")
    return "unknown"
