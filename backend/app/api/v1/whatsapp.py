import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

import app.core.config as _config
from app.agents.chat_agent import build_chat_reply
from app.agents.graph import graph
from app.agents.state import LegalStatus, UserApproval, new_state
from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
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
        .select("user_id, workspace_id").eq("phone_e164", phone_e164).maybe_single().execute()
    )
    return res.data if res else None


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
    try:
        final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

        audit_id = final.get("audit_id")
        reply = build_chat_reply(final)

        # build_chat_reply's text is web-oriented ("buka halaman Approvals") —
        # WhatsApp has no in-app navigation, so append a direct deep link for the
        # same two cases it already detects, using the identical state-shape
        # checks (never a bare "user_approval is None", which used to also catch
        # informational replies, clarification questions, and legal rejections —
        # none of which have anything to approve).
        legal_status = final.get("legal_status")
        if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL) and final.get("user_approval") is None:
            reply += f"\nReview & approve di: {_config.settings.APP_BASE_URL}/approvals/{audit_id}"
        elif final.get("user_approval") == UserApproval.APPROVED and final.get("transactions"):
            reply += f"\nDetail: {_config.settings.APP_BASE_URL}/audit/{audit_id}"
    except Exception:
        # Any unhandled exception anywhere in the pipeline (market data
        # fetch, solver, legal RAG, etc.) used to propagate all the way up
        # through this webhook handler, 500-ing the request — since
        # send_text() below was never reached, the user just saw silence
        # with no indication anything went wrong.
        log.exception("whatsapp: pipeline failed for thread %s", thread_id)
        reply = "Maaf, terjadi kendala saat memproses permintaan Anda. Silakan coba lagi beberapa saat lagi."

    send_text(to_phone_e164=phone, body=reply)


class BindWhatsAppRequest(BaseModel):
    code: str = Field(..., min_length=1)
    workspace_id: str = Field(..., min_length=1)


@router.post("/bind", status_code=status.HTTP_204_NO_CONTENT)
async def bind(
    body: BindWhatsAppRequest,
    user: dict = Depends(get_current_user),
) -> None:
    sb = get_admin_client()

    code_res = (
        sb.table("whatsapp_pending_codes").select("*")
        .eq("code", body.code).execute()
    )
    if not code_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kode tidak ditemukan.")

    pending = code_res.data[0]
    expires_at = datetime.fromisoformat(pending["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if pending.get("consumed_at") is not None or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Link kadaluarsa, kirim pesan lagi ke bot WhatsApp untuk dapat link baru.",
        )

    assert_workspace_owned(sb, body.workspace_id, user["sub"])

    try:
        sb.table("whatsapp_bindings").insert({
            "user_id": user["sub"],
            "phone_e164": pending["phone_e164"],
            "workspace_id": body.workspace_id,
        }).execute()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nomor ini atau akun Anda sudah terhubung sebelumnya.",
        )

    sb.table("whatsapp_pending_codes").update(
        {"consumed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("code", body.code).execute()
