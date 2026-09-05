import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

import app.core.config as _config
from app.agents.chat_agent import build_chat_reply
from app.agents.composition_gate.resume import (
    detect_composition_reply,
    find_pending_composition_audit,
    resume_composition,
)
from app.agents.graph import graph
from app.agents.state import LegalStatus, UserApproval, new_state
from app.agents.transaction_capture.classify import looks_like_transaction
from app.agents.transaction_capture.graph import capture_graph
from app.agents.transaction_capture.resume import (
    detect_transaction_reply,
    find_pending_transaction,
    resolve_single_business,
    resume_transaction,
)
from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.integrations.chart import render_allocation_chart, render_composition_chart, render_report_table_chart
from app.integrations.pdf_report import render_allocation_pdf
from app.integrations.whatsapp import (
    download_media,
    send_buttons,
    send_document,
    send_image,
    send_text,
    verify_signature,
)

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


def _reply_for_capture_result(phone: str, result: dict) -> None:
    if result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        warning = "\n⚠️ Nominal ini jauh dari biasanya, mohon dicek ulang." \
            if payload.get("plausibility_flag") else ""
        body = (
            f"Transaksi terdeteksi:\n"
            f"{payload.get('item_description') or '-'} — Rp{payload.get('amount'):,.0f} "
            f"({'pemasukan' if payload.get('type') == 'income' else 'pengeluaran'})"
            f"{warning}\n\nBenar?"
        )
        send_buttons(to_phone_e164=phone, body=body,
                     buttons=[("ya", "Ya, Benar"), ("tidak", "Tidak, Batalkan")])
        return
    if result.get("gate_failed"):
        send_text(to_phone_e164=phone,
                  body="Maaf, saya tidak bisa memahami transaksinya. Bisa dikirim ulang "
                       "lebih jelas? Misalnya: \"jual nasi goreng 15rb\".")
        return
    send_text(to_phone_e164=phone, body="Transaksi tercatat.")


def _build_transaction_ack(result: dict) -> str:
    if result.get("confirmed"):
        return "Transaksi tercatat, terima kasih!"
    return "Oke, transaksi dibatalkan."


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
    msg_type = msg.get("type")
    media_id: str | None = None
    if msg_type == "interactive":
        # Reply to a send_buttons() prompt — the id ("ya"/"tidak") comes back
        # verbatim, so it flows through detect_composition_reply unchanged.
        text = ((msg.get("interactive") or {}).get("button_reply") or {}).get("id", "")
    elif msg_type == "text":
        text = (msg.get("text") or {}).get("body", "")
    elif msg_type in ("image", "audio"):
        text = ""
        media_id = (msg.get(msg_type) or {}).get("id")
    else:
        return
    if not phone or (msg_type not in ("image", "audio") and not text) or \
       (msg_type in ("image", "audio") and not media_id):
        return

    binding = _resolve_user(phone)
    if not binding:
        link = _onboarding_link(phone)
        send_text(to_phone_e164=phone,
                  body=f"Halo! Untuk memulai AstaLink, silakan daftar dan link nomor Anda: {link}")
        return

    workspace_id = binding["workspace_id"]
    thread_id = f"wa-{phone}-{workspace_id}"
    txn_thread_id = f"wa-txn-{phone}-{workspace_id}"

    admin = get_admin_client()
    business_id = resolve_single_business(admin, workspace_id)
    pending_transaction_id = find_pending_transaction(admin, business_id) if business_id else None
    transaction_reply = detect_transaction_reply(text) if pending_transaction_id and text else None

    if pending_transaction_id:
        # A pending confirmation exists on this thread: the bot is waiting
        # on ya/tidak specifically. A plain graph.invoke() on the SAME
        # txn_thread_id (no Command(resume=...)) would silently overwrite
        # the paused checkpoint and orphan the pending row forever instead
        # of ever marking it rejected — so ANY non-reply message here is
        # deflected back to "answer the pending one first" rather than
        # starting a second capture run on top of it.
        if transaction_reply is not None:
            try:
                result = resume_transaction(txn_thread_id, transaction_reply)
                send_text(to_phone_e164=phone, body=_build_transaction_ack(result))
            except Exception:
                # _already_seen() already marked this message id as processed
                # before we got here, so a retry of the SAME webhook delivery
                # will be silently swallowed — same failure mode the advisory
                # path guards against below. Without this, an unhandled
                # exception here (e.g. a Supabase write failure inside
                # persist_node/rejected_node) would 500 the request and leave
                # the user with zero indication their confirmation failed.
                log.exception("whatsapp: transaction resume failed for thread %s", txn_thread_id)
                send_text(to_phone_e164=phone,
                          body="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.")
        else:
            send_text(to_phone_e164=phone,
                      body="Anda punya transaksi yang menunggu konfirmasi. "
                           "Balas \"ya\" atau \"tidak\" dulu sebelum mengirim yang baru.")
        return

    if msg_type in ("image", "audio"):
        if business_id is None:
            send_text(to_phone_e164=phone,
                      body="Untuk mencatat transaksi via WhatsApp, daftarkan tepat satu "
                           "bisnis dulu di dashboard AstaLink.")
            return
        media = download_media(media_id)
        if media is None:
            send_text(to_phone_e164=phone,
                      body="Maaf, gagal mengambil lampiran Anda. Coba kirim ulang.")
            return
        media_bytes, mime_type = media
        source = "whatsapp_photo" if msg_type == "image" else "whatsapp_voice"
        try:
            result = capture_graph.invoke(
                {"business_id": business_id, "workspace_id": workspace_id, "phone_e164": phone,
                 "source": source, "media_bytes": media_bytes, "media_mime_type": mime_type},
                config={"configurable": {"thread_id": txn_thread_id}},
            )
            _reply_for_capture_result(phone, result)
        except Exception:
            # See the comment on the resume_transaction try/except above —
            # same silent-retry-swallow risk via _already_seen(), and the
            # same "the user must always hear something" guarantee the
            # advisory path's try/except (further below) already provides.
            log.exception("whatsapp: capture_graph invoke failed for thread %s", txn_thread_id)
            send_text(to_phone_e164=phone,
                      body="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.")
        return

    if msg_type == "text" and business_id is not None and looks_like_transaction(text):
        try:
            result = capture_graph.invoke(
                {"business_id": business_id, "workspace_id": workspace_id, "phone_e164": phone,
                 "source": "whatsapp_text", "text_body": text},
                config={"configurable": {"thread_id": txn_thread_id}},
            )
            _reply_for_capture_result(phone, result)
        except Exception:
            log.exception("whatsapp: capture_graph invoke failed for thread %s", txn_thread_id)
            send_text(to_phone_e164=phone,
                      body="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.")
        return

    from app.api.v1.chat import load_thread_history

    # A message on a thread paused at the composition gate is treated as a
    # reply to it ("ya"/"tidak") rather than a brand new turn, as long as
    # it's a clear yes/no — anything else falls through to a fresh turn.
    pending_audit = find_pending_composition_audit(admin, thread_id)
    composition_reply = detect_composition_reply(text) if pending_audit else None

    allocation_plan = None
    composition_alloc = None
    final: dict[str, Any] | None = None
    try:
        if composition_reply is not None:
            final = resume_composition(thread_id, composition_reply)
        else:
            initial = new_state()
            initial["messages"] = [*load_thread_history(thread_id),
                                   HumanMessage(content=text)]
            initial["entities"] = {"workspace_id": binding["workspace_id"]}
            initial["_user_id"] = binding["user_id"]
            initial["_workspace_id"] = binding["workspace_id"]
            initial["_thread_id"] = thread_id
            final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

        audit_id = final.get("audit_id")
        reply = build_chat_reply(final)

        if final.get("__interrupt__"):
            # Freshly paused this turn — send the Kas/Saham/Bisnis donut
            # alongside the ya/tidak prompt so the split is visible before
            # deciding, same as the stock chart sent once a plan exists.
            composition_alloc = (final.get("layer0_result") or {}).get("allocation")
        else:
            # build_chat_reply's text is web-oriented ("buka halaman Approvals") —
            # WhatsApp has no in-app navigation, so append a direct deep link for the
            # same two cases it already detects, using the identical state-shape
            # checks (never a bare "user_approval is None", which used to also catch
            # informational replies, clarification questions, and legal rejections —
            # none of which have anything to approve).
            legal_status = final.get("legal_status")
            if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL) and final.get("user_approval") is None:
                reply += f"\nReview & approve di: {_config.settings.APP_BASE_URL}/approvals/{audit_id}"
                allocation_plan = final.get("allocation_plan")
            elif final.get("user_approval") == UserApproval.APPROVED and final.get("transactions"):
                reply += f"\nDetail: {_config.settings.APP_BASE_URL}/audit/{audit_id}"
                allocation_plan = final.get("allocation_plan")
    except Exception:
        # Any unhandled exception anywhere in the pipeline (market data
        # fetch, solver, legal RAG, etc.) used to propagate all the way up
        # through this webhook handler, 500-ing the request — since
        # send_text() below was never reached, the user just saw silence
        # with no indication anything went wrong.
        log.exception("whatsapp: pipeline failed for thread %s", thread_id)
        reply = "Maaf, terjadi kendala saat memproses permintaan Anda. Silakan coba lagi beberapa saat lagi."

    # build_chat_reply's output (what's actually sent to the user) is
    # computed from `final` on every call — it is NEVER itself appended to
    # state["messages"] by any graph node for the allocation path
    # (l0_allocation -> ... -> legal -> END never writes a final AIMessage;
    # only n8_qa's informational path does). Without persisting it here,
    # load_thread_history() on the next turn sees only the user's own
    # messages with no record of what AstaLink actually said — so a genuine
    # follow-up has no report text in its context to refer back to. Skipped
    # when `final` is None (the pipeline itself never completed, so there's
    # no state to attach the reply to).
    if final is not None:
        try:
            graph.update_state(
                config={"configurable": {"thread_id": thread_id}},
                values={"messages": [*final.get("messages", []),
                                     AIMessage(content=reply)]},
            )
        except Exception:
            log.exception("whatsapp: failed to persist reply to thread %s", thread_id)

    if allocation_plan and allocation_plan.get("weights"):
        try:
            png = render_allocation_chart(
                allocation_plan["weights"], allocation_plan.get("cash_buffer", 0.0),
            )
            send_image(to_phone_e164=phone, image_bytes=png, caption="Alokasi Portofolio")
        except Exception:
            # A chart render/upload failure must never block the text reply
            # (which carries the actual approve/detail link) from sending.
            log.exception("whatsapp: chart render/send failed for thread %s", thread_id)
        try:
            engine = ((final or {}).get("entities") or {}).get("stock_engine") or {}
            verdicts = engine.get("verdicts") or {}
            table_png = render_report_table_chart(
                verdicts, allocation_plan["weights"], allocation_plan.get("cash"),
            )
            send_image(to_phone_e164=phone, image_bytes=table_png, caption="Tabel Verdik & Bobot Saham")
        except Exception:
            log.exception("whatsapp: table image render/send failed for thread %s", thread_id)
        try:
            pdf_bytes = render_allocation_pdf(final) if final is not None else None
            if pdf_bytes:
                send_document(
                    to_phone_e164=phone, doc_bytes=pdf_bytes,
                    filename="Laporan-Analisis.pdf",
                    caption="Laporan lengkap analisis & rekomendasi",
                )
        except Exception:
            log.exception("whatsapp: pdf render/send failed for thread %s", thread_id)
    elif composition_alloc:
        try:
            png = render_composition_chart(
                composition_alloc.get("cash", 0.0),
                composition_alloc.get("stocks", 0.0),
                composition_alloc.get("business", 0.0),
            )
            send_image(to_phone_e164=phone, image_bytes=png, caption="Kas vs Saham vs Bisnis")
        except Exception:
            log.exception("whatsapp: composition chart render/send failed for thread %s", thread_id)

    if composition_alloc:
        # Interactive Ya/Tidak buttons instead of plain text — the user taps
        # a reply instead of typing "ya"/"tidak" (still detected as a
        # fallback if they type it anyway, see the type=="text" branch above).
        send_buttons(
            to_phone_e164=phone, body=reply,
            buttons=[("ya", "Ya, Lanjutkan"), ("tidak", "Tidak, Batalkan")],
        )
    else:
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
