"""Meta WhatsApp Business API integration.

Inbound: signature verification, payload parsing.
Outbound: send_text_message via Meta Cloud API."""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

META_BASE = "https://graph.facebook.com/v20.0"


def verify_signature(*, body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def send_text(*, to_phone_e164: str, body: str) -> None:
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        log.warning("whatsapp.send_text: skipping (creds unset)")
        return
    try:
        resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone_e164,
                "type": "text",
                "text": {"body": body},
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_text failed: %s", exc)
