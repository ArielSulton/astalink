"""Resend email sending + template rendering.

Lazy-configured so the backend boots without RESEND_API_KEY set; sending
only fails when actually invoked, matching the optional-key philosophy
already used for Gemini/Pinecone (app.core.gemini, app.core.pinecone)."""
from __future__ import annotations

from pathlib import Path

import resend

from app.core.config import settings

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"
_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        resend.api_key = settings.RESEND_API_KEY
        _configured = True


def render_template(filename: str, **kwargs: str) -> str:
    """Loads backend/app/templates/email/<filename> and replaces
    {{KEY}} placeholders (uppercased) with the given kwargs' values."""
    html = (_TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key.upper()}}}}}", value)
    return html


def send_email(to: str, subject: str, html: str) -> None:
    _ensure_configured()
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": to,
        "subject": subject,
        "html": html,
    })
