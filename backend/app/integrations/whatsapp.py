"""Meta WhatsApp Business API integration.

Inbound: signature verification, payload parsing.
Outbound: send_text_message via Meta Cloud API."""
from __future__ import annotations

import hashlib
import hmac
import logging
import re

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


def _normalize_for_whatsapp(body: str) -> str:
    """LLM-authored replies default to standard Markdown often enough that
    prompt instructions alone aren't a reliable guarantee — WhatsApp only
    renders single-asterisk *bold* and has no header syntax, so anything
    else (**bold**, ### heading) shows up as literal punctuation clutter
    instead of formatting. Em dashes get the same treatment: WhatsApp has
    no special rendering for them, so they just read as stray characters."""
    # **bold** / ***bold*** -> *bold* (WhatsApp's own single-asterisk bold)
    body = re.sub(r"\*{2,3}(.+?)\*{2,3}", r"*\1*", body)
    # "### Heading" / "## Heading" -> a plain bold line
    body = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", body, flags=re.MULTILINE)
    body = re.sub(r"\s*—\s*", " - ", body)   # em dash (usually spaced)
    return re.sub(r"\s*–\s*", "-", body)     # en dash (usually unspaced, e.g. ranges)


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
                "text": {"body": _normalize_for_whatsapp(body)},
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_text failed: %s", exc)


def send_buttons(*, to_phone_e164: str, body: str, buttons: list[tuple[str, str]]) -> None:
    """Sends a WhatsApp interactive reply-button message — Meta allows at
    most 3 buttons, each with a title of at most 20 characters.
    buttons: [(id, title), ...] — `id` comes back verbatim in the inbound
    button_reply webhook payload, so callers pick ids the reply-detection
    logic already understands (e.g. "ya"/"tidak")."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        log.warning("whatsapp.send_buttons: skipping (creds unset)")
        return
    try:
        resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone_e164,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": _normalize_for_whatsapp(body)},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": bid, "title": title[:20]}}
                            for bid, title in buttons[:3]
                        ],
                    },
                },
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_buttons failed: %s", exc)


def send_document(*, to_phone_e164: str, doc_bytes: bytes, filename: str, caption: str | None = None) -> None:
    """Uploads doc_bytes (PDF) to Meta's Media API, then sends it as a
    WhatsApp document message — same two-call upload-then-reference flow
    as send_image, just a different media type."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        log.warning("whatsapp.send_document: skipping (creds unset)")
        return
    try:
        upload_resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            data={"messaging_product": "whatsapp", "type": "application/pdf"},
            files={"file": (filename, doc_bytes, "application/pdf")},
            timeout=15.0,
        )
        upload_resp.raise_for_status()
        media_id = upload_resp.json()["id"]

        document_payload: dict = {"id": media_id, "filename": filename}
        if caption:
            document_payload["caption"] = caption

        resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone_e164,
                "type": "document",
                "document": document_payload,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_document failed: %s", exc)


def send_image(*, to_phone_e164: str, image_bytes: bytes, caption: str | None = None) -> None:
    """Uploads image_bytes to Meta's Media API, then sends it as an image
    message. Two calls are required — WhatsApp messages reference media by
    an uploaded media_id, not a raw attachment."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        log.warning("whatsapp.send_image: skipping (creds unset)")
        return
    try:
        upload_resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            data={"messaging_product": "whatsapp", "type": "image/png"},
            files={"file": ("chart.png", image_bytes, "image/png")},
            timeout=15.0,
        )
        upload_resp.raise_for_status()
        media_id = upload_resp.json()["id"]

        image_payload: dict = {"id": media_id}
        if caption:
            image_payload["caption"] = caption

        resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone_e164,
                "type": "image",
                "image": image_payload,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_image failed: %s", exc)


def download_media(media_id: str) -> tuple[bytes, str] | None:
    """Two-step Meta Media API download: GET /{media_id} returns a
    short-lived signed URL + mime_type, then GET that URL (still with the
    bearer token) for the actual bytes. Returns None if credentials are
    unset or either request fails — callers treat that as "couldn't fetch
    this attachment" and reply asking the user to resend."""
    if not settings.WHATSAPP_ACCESS_TOKEN:
        log.warning("whatsapp.download_media: skipping (creds unset)")
        return None
    try:
        meta_resp = httpx.get(
            f"{META_BASE}/{media_id}",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            timeout=10.0,
        )
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        media_resp = httpx.get(
            meta["url"],
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            timeout=15.0,
        )
        media_resp.raise_for_status()
        return media_resp.content, meta.get("mime_type", "application/octet-stream")
    except Exception as exc:
        log.error("whatsapp.download_media failed: %s", exc)
        return None
