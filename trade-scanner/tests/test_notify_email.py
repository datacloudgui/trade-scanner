"""Tests del script host-side `scripts/notify_email.py` (Etapa 8, T6).

El script corre en el `.venv` del host, pero se testea DENTRO de la imagen LEAN (run_tests.sh monta
`scripts/` en `/Scripts` y lo añade al PYTHONPATH). Se verifica: (b) el render del script es el MISMO
que el del algoritmo (mismo `core.email_render.render_email`), y (c) el envío real (`send_gmail`) está
aislado y mockeado — no se llama en dry-run, sí en --send — y el token se lee del entorno.
"""
import json
from argparse import Namespace
from pathlib import Path

import core.email_render as email_render
import notify_email

FIXTURE = Path(__file__).parent / "fixtures" / "envelope_sample.json"


def _args(**kw) -> Namespace:
    base = {"sample": None, "file": None, "base": None, "dry_run": True, "send": False}
    base.update(kw)
    return Namespace(**base)


# ---------------------------------------------------------------------------
# (b) Render idéntico al del algoritmo: mismo email_render, cuerpo esperado.
# ---------------------------------------------------------------------------

def test_script_uses_the_same_render_as_algorithm():
    # El script importa la MISMA función que usa OutputSink (qc_notify): render compartido (D8.1).
    assert notify_email.render_email is email_render.render_email


def test_render_of_sample_matches_expected_body():
    envelope = json.loads(FIXTURE.read_text())
    doc = email_render.render_email(envelope)

    assert doc.subject == (
        "[trade-scanner] swing_eod — 5 candidatos (3 LONG · 2 SHORT) · 2026-06-19 20:01Z"
    )
    # Bloque LONG: tickers uno-por-línea, sin viñetas, en orden rules_passed_count desc.
    assert "LONG\nAAPL\nMSFT\nNVDA" in doc.text_body
    # Bloque SHORT idem.
    assert "SHORT\nXYZ\nABC" in doc.text_body
    for bullet in ("- ", "* ", "•"):
        assert bullet not in doc.text_body
    # HTML trae una <table> por sección (LONG + SHORT).
    assert doc.html_body.count("<table") == 2


# ---------------------------------------------------------------------------
# (c) send_gmail aislado y mockeado: dry-run no envía, --send sí; token desde el entorno.
# ---------------------------------------------------------------------------

def test_dry_run_does_not_call_send_gmail(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(notify_email, "send_gmail", lambda *a, **k: calls.append(a))

    notify_email.run(_args(sample=str(FIXTURE), send=False))

    assert calls == []  # dry-run: nunca envía
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "Subject:" in out


def test_send_calls_send_gmail_once_with_rendered_doc(monkeypatch):
    calls = []
    monkeypatch.setattr(notify_email, "send_gmail", lambda doc, rcpts, creds: calls.append((doc, rcpts, creds)))
    # Aísla de la config local (no presente en Docker): suscriptores y creds inyectados.
    monkeypatch.setattr(notify_email, "resolve_recipients", lambda cfg, base: ["x@example.com"])
    monkeypatch.setattr(notify_email, "load_notif_config", lambda: {})
    monkeypatch.setenv("GMAIL_SENDER", "trade-scanner@example.com")

    notify_email.run(_args(sample=str(FIXTURE), send=True))

    assert len(calls) == 1
    doc, recipients, creds = calls[0]
    assert recipients == ["x@example.com"]
    assert doc.subject.startswith("[trade-scanner] swing_eod")
    # El token/credenciales vienen del entorno, no hardcodeados.
    assert creds.get("GMAIL_SENDER") == "trade-scanner@example.com"


def test_load_credentials_reads_from_environment(monkeypatch):
    monkeypatch.delenv("GMAIL_OAUTH_TOKEN", raising=False)
    monkeypatch.setenv("GMAIL_SENDER", "from@example.com")
    monkeypatch.setenv("GMAIL_OAUTH_TOKEN", "tok-123")

    creds = notify_email.load_credentials()

    assert creds["GMAIL_SENDER"] == "from@example.com"
    assert creds["GMAIL_OAUTH_TOKEN"] == "tok-123"


def test_no_hardcoded_token_in_script():
    src = Path(notify_email.__file__).read_text()
    lowered = src.lower()
    # Ningún literal de token/secreto: solo nombres de variables de entorno.
    assert "oauth_token" not in lowered.replace("gmail_oauth_token", "")
    for forbidden in ("ya29.", "1//0", "-----begin"):
        assert forbidden not in lowered
