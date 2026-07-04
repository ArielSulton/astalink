import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from langchain_core.messages import HumanMessage

import app.core.config as _config
from app.agents.graph import graph
from app.agents.state import new_state
from app.core.supabase_admin import get_admin_client
from app.integrations.whatsapp import send_text, verify_signature

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook")
async def verify(request: Request):
    qp = dict(request.query_params)
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge", "")
    if mode == "subscribe" and token == _config.settings.WHATSAPP_VERIFY_TOKEN:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid verify token")


def _already_seen(message_id: str) -> bool:
    try:
        get_admin_client().table("whatsapp_messages_seen").insert({
            "message_id": message_id,
        }).execute()
        return False
    except Exception:
        # Duplicate primary key → message already processed.
        return True


def _resolve_user(phone_e164: str) -> dict[str, str] | None:
    res = (
        get_admin_client().table("whatsapp_bindings")
        .select("user_id, workspace_id").eq("phone_e164", phone_e164).single().execute()
    )
    return res.data


def _onboarding_link(phone_e164: str) -> str:
    """Generate a one-time code and return the dashboard URL the user should
    open after signing up to bind their phone."""
    import secrets
    from datetime import datetime, timedelta, timezone
    code = secrets.token_urlsafe(8)
    get_admin_client().table("whatsapp_pending_codes").insert({
        "code": code,
        "phone_e164": phone_e164,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }).execute()
    return f"{_config.settings.APP_BASE_URL}/settings/whatsapp?code={code}"


@router.post("/webhook")
async def receive(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()
    if not verify_signature(body=body, signature_header=x_hub_signature_256,
                            app_secret=_config.settings.WHATSAPP_APP_SECRET):
        raise HTTPException(status_code=403, detail="bad signature")

    payload: dict[str, Any] = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                _process_message(msg)
    return {"ok": True}


def _process_message(msg: dict[str, Any]) -> None:
    msg_id = msg.get("id")
    if not msg_id or _already_seen(msg_id):
        return

    phone = msg.get("from")
    text = (msg.get("text") or {}).get("body", "")
    if msg.get("type") != "text" or not phone or not text:
        return

    binding = _resolve_user(phone)
    if not binding:
        link = _onboarding_link(phone)
        send_text(to_phone_e164=phone,
                  body=f"Halo! Untuk memulai AstaLink, silakan daftar dan link nomor Anda: {link}")
        return

    initial = new_state()
    initial["messages"] = [HumanMessage(content=text)]
    initial["entities"] = {"workspace_id": binding["workspace_id"]}
    initial["_user_id"] = binding["user_id"]
    initial["_workspace_id"] = binding["workspace_id"]

    thread_id = f"wa-{phone}-{binding['workspace_id']}"
    final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

    audit_id = final.get("audit_id")
    if final.get("__interrupt__") or final.get("user_approval") is None:
        link = f"{_config.settings.APP_BASE_URL}/approvals/{audit_id}"
        send_text(to_phone_e164=phone,
                  body=f"Saya sudah menyiapkan rekomendasi alokasi.\nReview & approve di: {link}")
    elif final.get("transactions"):
        n = len(final["transactions"])
        send_text(to_phone_e164=phone,
                  body=f"Eksekusi selesai: {n} order. Detail: {_config.settings.APP_BASE_URL}/audit/{audit_id}")
    else:
        send_text(to_phone_e164=phone,
                  body="Permintaan tidak dapat diproses. Coba pesan yang lebih spesifik.")
