"""Shared helpers for resuming a paused composition-gate run — reused by
chat.py, whatsapp.py (free-text "ya"/"tidak" replies) and agent.py (a
dedicated Setuju/Tidak button, which skips keyword detection and passes the
approval decision directly)."""
from __future__ import annotations

import logging
from typing import Any, Literal

log = logging.getLogger(__name__)

_YES = {"ya", "iya", "yes", "setuju", "oke", "ok", "lanjut", "lanjutkan"}
_NO = {"tidak", "gak", "ga", "nggak", "no", "batal", "stop", "berhenti"}

CompositionReply = Literal["approved", "rejected"]


def detect_composition_reply(text: str) -> CompositionReply | None:
    """Best-effort yes/no classification of a short free-text reply. Returns
    None when the text isn't a clear yes/no — callers should fall back to
    treating the message as a brand new turn rather than guessing."""
    normalized = text.strip().lower().rstrip(".!?")
    if normalized in _YES:
        return "approved"
    if normalized in _NO:
        return "rejected"
    return None


def find_pending_composition_audit(admin_client, thread_id: str) -> str | None:
    """Returns the audit_id of the most recent run on this thread that's
    paused at the composition gate awaiting a reply, if any."""
    try:
        res = (
            admin_client.table("audit_log").select("audit_id")
            .eq("thread_id", thread_id)
            .eq("status", "awaiting_composition_approval")
            .order("created_at", desc=True).limit(1).execute()
        )
    except Exception as exc:
        log.error("find_pending_composition_audit: query failed: %s", exc)
        return None
    rows = res.data or []
    return rows[0]["audit_id"] if rows else None


def resume_composition(thread_id: str, approval: CompositionReply) -> dict[str, Any]:
    from langgraph.types import Command

    from app.agents.graph import graph

    return graph.invoke(
        Command(resume={"approval": approval}),
        config={"configurable": {"thread_id": thread_id}},
    )
