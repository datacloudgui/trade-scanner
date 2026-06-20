"""notify_email.py — Transporte host-side del correo del screener (Etapa 8, T6).

POR QUÉ vive aquí y no en el algoritmo (D8.1): el algoritmo "solo habla con la API de QCAlgorithm,
sin SDKs externos". El envío por Gmail es un SDK externo → vive en este script del HOST, que lee la
salida ya persistida por el algoritmo (`storage/results/<base>/latest.json`, opción A) y la despacha.
El cuerpo del correo es el MISMO objeto en cloud y local: ambos llaman `core.email_render.render_email`
(render puro y SDK-free); este script solo aporta el transporte. Flipar cloud↔local no recompone el
cuerpo, solo cambia quién lo envía.

ENTORNO (T6.4): corre con el Python 3.11 del `.venv` del host (no Docker; es auxiliar, como
`explore_universe.py`). La regla "solo API QCAlgorithm" aplica al algoritmo, no a este script.

USO:
    # Dry-run contra un envelope de muestra (no envía, no requiere token):
    python scripts/notify_email.py --dry-run --sample tests/fixtures/envelope_sample.json

    # Dry-run contra el último scan real de una estrategia base (lee storage/results/<base>/latest.json):
    python scripts/notify_email.py --dry-run --base swing_eod

    # Envío real (Etapa 9, requiere credenciales — ver abajo):
    python scripts/notify_email.py --send --base swing_eod

CREDENCIALES (nunca en el repo; D8.5): el token/credenciales de Gmail se leen de variables de
entorno (poblar desde `.env`, gitignoreado, o desde el entorno del host/GCP). NO se hardcodean.
    - GMAIL_SENDER                    remitente (ej. trade-scanner@tu-dominio)
    - GMAIL_OAUTH_TOKEN               token OAuth de la app desktop de GCP (se concreta en E9), o
    - GOOGLE_APPLICATION_CREDENTIALS  ruta al JSON de credenciales de servicio
El envío real (`send_gmail`) se valida end-to-end en la Etapa 9; en V1 el modo por defecto es
`--dry-run` y `send_gmail` queda aislado para poder mockearlo en test.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Bootstrap del path: este script corre desde el host, así que añade el proyecto LEAN (`trade-scanner/`)
# al sys.path para importar `core.*` (render puro, sin CLR). En Docker el proyecto ya está en
# PYTHONPATH=/Project; el insert de un dir inexistente es inocuo (no se usa).
_WORKSPACE = Path(__file__).resolve().parent.parent
_PROJECT_DIR = _WORKSPACE / "trade-scanner"
if _PROJECT_DIR.is_dir():
    sys.path.insert(0, str(_PROJECT_DIR))

from core.email_render import EmailDoc, render_email  # noqa: E402  (tras el bootstrap de path)
from core.output import JsonSubscriberSource  # noqa: E402

# Raíces locales: el ObjectStore local del CLI es `<workspace>/storage/` (CLAUDE.md); la config
# versionada (fuente de verdad de suscriptores) vive en `<workspace>/config/`.
_STORAGE_DIR = _WORKSPACE / "storage"
_CONFIG_PATH = _WORKSPACE / "config" / "notifications.json"


def _resolve_path(raw: str) -> Path:
    """Resuelve una ruta de `--sample`/`--file`: tal cual (relativa al CWD) o, si no existe, relativa
    al proyecto `trade-scanner/` (así el ejemplo `tests/fixtures/...` funciona desde la raíz)."""
    p = Path(raw)
    if p.exists():
        return p
    fallback = _PROJECT_DIR / raw
    if fallback.exists():
        return fallback
    return p  # se reporta el error de existencia aguas abajo


def load_envelope(args: argparse.Namespace) -> dict:
    """Carga el envelope a notificar (T6.1). Precedencia: `--sample` / `--file` (ruta explícita) →
    `--base` (puntero fijo `storage/results/<base>/latest.json`, opción A confirmada)."""
    if args.sample or args.file:
        path = _resolve_path(args.sample or args.file)
    elif args.base:
        path = _STORAGE_DIR / "results" / args.base / "latest.json"
    else:  # argparse ya lo garantiza; defensivo
        raise SystemExit("error: indica --sample, --file o --base")
    if not path.exists():
        raise SystemExit(f"error: envelope no encontrado: {path}")
    return json.loads(path.read_text())


def load_notif_config() -> dict:
    """Lee `config/notifications.json` (suscriptores por estrategia base, D8.5). Si falta, devuelve
    un dict vacío (el dry-run igual renderiza; solo no resolverá destinatarios)."""
    if _CONFIG_PATH.exists():
        return json.loads(_CONFIG_PATH.read_text())
    return {}


def resolve_recipients(notif_config: dict, base: str) -> list[str]:
    """Suscriptores de la estrategia base vía la misma abstracción que el algoritmo (D8.5)."""
    return JsonSubscriberSource(notif_config).for_strategy(base)


def load_credentials() -> dict:
    """Credenciales de Gmail desde el entorno (nunca hardcodeadas, D8.5). Se pueblan desde `.env`
    (gitignoreado) o el entorno del host/GCP. Devuelve solo las que estén presentes."""
    keys = ("GMAIL_SENDER", "GMAIL_OAUTH_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS")
    return {k: os.environ[k] for k in keys if os.environ.get(k)}


def send_gmail(doc: EmailDoc, recipients: list[str], creds: dict) -> None:
    """Transporte real por Gmail (AISLADO para test/mock, T6.2). El SDK se importa LAZY aquí dentro
    para que el dry-run y los tests no dependan de él ni del token. La implementación OAuth/GCP
    end-to-end se valida en la **Etapa 9**; en V1 esto solo verifica que haya credenciales."""
    if not creds:
        raise SystemExit(
            "error: faltan credenciales de Gmail (GMAIL_SENDER / GMAIL_OAUTH_TOKEN o "
            "GOOGLE_APPLICATION_CREDENTIALS). Pobla `.env` o usa --dry-run."
        )
    # import lazy del SDK de Gmail/GCP — pendiente de concretar en E9 (app desktop OAuth).
    raise NotImplementedError(
        "envío real por Gmail pendiente de la Etapa 9 (token/app GCP). "
        "Usa --dry-run para previsualizar el correo."
    )


def _print_dry_run(doc: EmailDoc, recipients: list[str], base: str) -> None:
    """Imprime el correo completo sin enviar (T6.3): subject + destinatarios + texto plano + HTML."""
    print("=" * 78)
    print(f"DRY-RUN — estrategia base: {base}")
    print(f"Destinatarios: {', '.join(recipients) if recipients else '(sin suscriptores)'}")
    print(f"Subject: {doc.subject}")
    print("=" * 78)
    print("\n--- TEXT BODY ---\n")
    print(doc.text_body)
    print("\n--- HTML BODY ---\n")
    print(doc.html_body)


def run(args: argparse.Namespace) -> None:
    """Orquestación host-side: carga envelope → render compartido → resuelve suscriptores →
    dry-run (imprime) o envío real (aislado en `send_gmail`)."""
    envelope = load_envelope(args)
    base = envelope.get("strategy", args.base or "?")
    doc = render_email(envelope)
    recipients = resolve_recipients(load_notif_config(), base)

    if not args.send:  # dry-run es el modo por defecto (T6.3)
        _print_dry_run(doc, recipients, base)
        return

    if not recipients:
        raise SystemExit(f"error: sin suscriptores para '{base}'; nada que enviar")
    send_gmail(doc, recipients, load_credentials())
    print(f"Correo enviado a {len(recipients)} destinatario(s) de '{base}'.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Transporte host-side del correo del screener (T6).")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--sample", help="Ruta a un envelope de muestra (ej. tests/fixtures/...).")
    src.add_argument("--file", help="Ruta a un envelope persistido por el algoritmo.")
    src.add_argument("--base", help="Estrategia base: lee storage/results/<base>/latest.json.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Previsualiza sin enviar (por defecto).")
    mode.add_argument("--send", action="store_true", help="Envío real por Gmail (Etapa 9).")
    run(parser.parse_args(argv))


if __name__ == "__main__":
    main()
