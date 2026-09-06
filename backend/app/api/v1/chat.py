import base64
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage
from app.agents.chat_agent import build_chat_reply
from app.agents.composition_gate.resume import (
    detect_composition_reply,
    find_pending_composition_audit,
    resume_composition,
)
from app.agents.graph import graph
from app.agents.state import new_state
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
from app.models.chat import ChatRequest, ChatResponse

log = logging.getLogger(__name__)
router = APIRouter()

# Prior turns re-sent to the graph on a continued thread. The `messages`
# channel has no reducer (nodes overwrite-append), so history must be
# prepended here at the entry point or the QA node never sees it.
MAX_HISTORY = 20


def load_thread_history(thread_id: str) -> list:
    """Best-effort prior messages for a thread; empty list on any failure."""
    try:
        snapshot = graph.get_state(config={"configurable": {"thread_id": thread_id}})
        messages = (snapshot.values or {}).get("messages") or []
        return list(messages)[-MAX_HISTORY:]
    except Exception:  # noqa: BLE001 — history is optional, never fail the turn
        log.warning("chat: could not load history for thread %s", thread_id, exc_info=True)
        return []


def _transaction_ack_text(result: dict) -> str:
    if result.get("confirmed"):
        return "Transaksi tercatat, terima kasih!"
    return "Oke, transaksi dibatalkan."


def _capture_result_response(raw_thread: str, result: dict) -> ChatResponse:
    if result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        warning = "\n⚠️ Nominal ini jauh dari biasanya, mohon dicek ulang." \
            if payload.get("plausibility_flag") else ""
        message = (
            f"Transaksi terdeteksi:\n"
            f"{payload.get('item_description') or '-'} — Rp{payload.get('amount'):,.0f} "
            f"({'pemasukan' if payload.get('type') == 'income' else 'pengeluaran'})"
            f"{warning}\n\nBenar?"
        )
        return ChatResponse(
            message=message,
            thread_id=raw_thread,
            pending_transaction={
                "transaction_id": payload.get("transaction_id"),
                "item_description": payload.get("item_description"),
                "amount": payload.get("amount"),
                "type": payload.get("type"),
                "plausibility_flag": payload.get("plausibility_flag"),
            },
        )
    if result.get("gate_failed"):
        return ChatResponse(
            message="Maaf, saya tidak bisa memahami transaksinya. Bisa dikirim ulang "
                    "lebih jelas? Misalnya: \"jual nasi goreng 15rb\".",
            thread_id=raw_thread,
        )
    return ChatResponse(message="Transaksi tercatat.", thread_id=raw_thread)


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    # Scope thread_id to the authenticated user to prevent cross-user access
    user_sub = current_user["sub"]
    raw_thread = request.thread_id or str(uuid.uuid4())
    thread_id = f"{user_sub}:{raw_thread}"
    txn_thread_id = f"txn-{thread_id}"

    assert_workspace_owned(get_admin_client(), request.workspace_id, user_sub)

    admin = get_admin_client()
    business_id = resolve_single_business(admin, request.workspace_id)
    pending_transaction_id = find_pending_transaction(admin, business_id) if business_id else None
    pending_audit_id = find_pending_composition_audit(admin, thread_id)

    transaction_reply = None
    if pending_transaction_id and request.message:
        if request.message in ("txn_ya", "txn_tidak"):
            # Unambiguous — only the transaction card ever sends these.
            transaction_reply = detect_transaction_reply(request.message)
        else:
            candidate = detect_transaction_reply(request.message)
            if candidate is not None and pending_audit_id:
                # Both flows are simultaneously awaiting a decision and the
                # message is plain "ya"/"tidak" — on the web there's no
                # button-id distinction between the two cards' plain replies,
                # so this is genuinely ambiguous. Do not guess.
                return ChatResponse(
                    message="Anda punya transaksi dan persetujuan alokasi yang "
                            "sama-sama menunggu konfirmasi. Jawab dulu kartu "
                            "konfirmasi transaksi (\"Ya, Benar\"/\"Tidak, Batalkan\"), "
                            "baru balas \"ya\"/\"tidak\" lagi untuk persetujuan alokasi.",
                    thread_id=raw_thread,
                )
            transaction_reply = candidate

    if pending_transaction_id:
        if transaction_reply is not None:
            try:
                result = resume_transaction(txn_thread_id, transaction_reply)
                return ChatResponse(message=_transaction_ack_text(result), thread_id=raw_thread)
            except Exception:
                log.exception("chat: transaction resume failed for thread %s", txn_thread_id)
                return ChatResponse(
                    message="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.",
                    thread_id=raw_thread,
                )
        return ChatResponse(
            message="Anda punya transaksi yang menunggu konfirmasi. "
                    "Balas \"ya\" atau \"tidak\" dulu sebelum mengirim yang baru.",
            thread_id=raw_thread,
        )

    if request.photo_base64:
        if business_id is None:
            return ChatResponse(
                message="Untuk mencatat transaksi lewat chat, daftarkan tepat satu "
                        "bisnis dulu di halaman Bisnis.",
                thread_id=raw_thread,
                requires_business_setup=True,
            )
        try:
            media_bytes = base64.b64decode(request.photo_base64)
            result = capture_graph.invoke(
                {"business_id": business_id, "workspace_id": request.workspace_id,
                 "source": "web_photo", "media_bytes": media_bytes,
                 "media_mime_type": request.photo_mime_type or "image/jpeg"},
                config={"configurable": {"thread_id": txn_thread_id}},
            )
            return _capture_result_response(raw_thread, result)
        except Exception:
            log.exception("chat: capture_graph invoke failed for thread %s", txn_thread_id)
            return ChatResponse(
                message="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.",
                thread_id=raw_thread,
            )

    if business_id is not None and looks_like_transaction(request.message):
        try:
            result = capture_graph.invoke(
                {"business_id": business_id, "workspace_id": request.workspace_id,
                 "source": "web_text", "text_body": request.message},
                config={"configurable": {"thread_id": txn_thread_id}},
            )
            return _capture_result_response(raw_thread, result)
        except Exception:
            log.exception("chat: capture_graph invoke failed for thread %s", txn_thread_id)
            return ChatResponse(
                message="Maaf, terjadi kendala saat memproses transaksi Anda. Silakan coba lagi.",
                thread_id=raw_thread,
            )

    # A message on a thread that's paused at the composition gate is treated
    # as a reply to it ("ya"/"tidak") rather than a brand new turn, as long
    # as it's a clear yes/no — anything else falls through to a fresh turn.
    reply = detect_composition_reply(request.message) if pending_audit_id else None

    if reply is not None:
        final_state = resume_composition(thread_id, reply)
    else:
        initial = new_state()
        initial["messages"] = [*load_thread_history(thread_id),
                               HumanMessage(content=request.message)]
        initial["_user_id"] = user_sub
        initial["_workspace_id"] = request.workspace_id
        initial["_thread_id"] = thread_id
        initial["entities"] = {"workspace_id": request.workspace_id}

        final_state = graph.invoke(
            initial, config={"configurable": {"thread_id": thread_id}},
        )

    if not final_state.get("messages"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent produced no response",
        )

    # Advisory mode: the pipeline produces reports and recommendations only.
    # No HITL approval or automatic execution — the user decides.
    requires_approval = False

    reply_text = build_chat_reply(final_state, style="report")

    # build_chat_reply's output (the report/prompt actually shown to the
    # user) is computed from final_state on every call — it is NEVER itself
    # appended to state["messages"] by any graph node for the allocation
    # path (l0_allocation -> ... -> legal -> END never writes a final
    # AIMessage; only n8_qa's informational path does). Without persisting
    # it here, load_thread_history() on the next turn sees only the user's
    # messages with no record of what AstaLink actually said — so a genuine
    # follow-up ("kenapa alokasi bisnis 0%?") has no report text in its
    # context to refer back to, and gets misclassified as a fresh request
    # instead of the intent_node history fix (see intent/node.py's
    # _history()) ever getting a chance to help. Persist explicitly so every
    # channel's actual reply becomes real conversation history.
    try:
        graph.update_state(
            config={"configurable": {"thread_id": thread_id}},
            values={"messages": [*final_state.get("messages", []),
                                 AIMessage(content=reply_text)]},
        )
    except Exception:
        log.exception("chat: failed to persist reply to thread %s", thread_id)

    return ChatResponse(
        message=reply_text,
        thread_id=raw_thread,
        audit_id=final_state.get("audit_id"),
        requires_approval=requires_approval,
        intent=final_state.get("intent"),
        awaiting_composition_approval=bool(final_state.get("__interrupt__")),
        layer0_result=final_state.get("layer0_result"),
    )
