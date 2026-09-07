"""Shared helpers for routing/resuming the transaction-capture subgraph from
the WhatsApp webhook and the web chat endpoint — mirrors
app/agents/composition_gate/resume.py's shape (reply detection + pending
lookup + Command(resume=...) invocation, kept out of the handlers).

The pending lookup deliberately reads the GRAPH's own state rather than
inferring a pause from database rows. The previous version queried
business_transactions for a pending_confirmation row inside a 24-hour TTL,
which meant one orphaned row (see node.py's stage_node docstring for how
those were produced) deflected every message on the workspace for a full
day. Asking the checkpointer what the graph is actually waiting for cannot
drift from reality, and needs no TTL at all."""
from __future__ import annotations

import logging
import re
from typing import Any, Literal

log = logging.getLogger(__name__)

_YES = {"ya", "iya", "yes", "setuju", "oke", "ok", "benar", "betul", "txn_ya"}
_NO = {"tidak", "gak", "ga", "nggak", "no", "batal", "salah", "txn_tidak"}
_CANCEL = {"batal", "batalkan", "cancel", "tidak", "bizsel_batal"}

# Returned by detect_business_choice when the user declined to pick.
BUSINESS_CANCEL = "__cancel__"

# The web business-choice card sends this marker rather than a bare id, so a
# choice can never be confused with a plain chat message that happens to
# look like a uuid.
_BIZSEL_PREFIX = "bizsel_"

TransactionReply = Literal["confirmed", "rejected"]


def detect_transaction_reply(text: str) -> TransactionReply | None:
    normalized = text.strip().lower().rstrip(".!?")
    if normalized in _YES:
        return "confirmed"
    if normalized in _NO:
        return "rejected"
    return None


def detect_business_choice(text: str, options: list[dict]) -> str | None:
    """Map a reply to one of `options`, to BUSINESS_CANCEL, or to None.

    Accepts the web card's `bizsel_<id>` marker and WhatsApp's 1-based index
    ("1", "2"). The index is resolved against the very list the interrupt
    payload carried, so the numbering the user saw and the numbering we
    resolve against cannot drift apart. None means "unparseable" — the
    caller re-shows the question rather than guessing."""
    normalized = text.strip().lower().rstrip(".!?")
    if not normalized:
        return None
    if normalized in _CANCEL:
        return BUSINESS_CANCEL

    if normalized.startswith(_BIZSEL_PREFIX):
        picked = text.strip()[len(_BIZSEL_PREFIX):]
        return picked if any(o["id"] == picked for o in options) else None

    if re.fullmatch(r"\d+", normalized):
        idx = int(normalized) - 1
        return options[idx]["id"] if 0 <= idx < len(options) else None

    # Exact business name, case-insensitive — a WhatsApp user typing the name
    # instead of the number is unambiguous when it matches exactly.
    for o in options:
        if o["name"].strip().lower() == normalized:
            return o["id"]
    return None


def list_businesses(admin_client, workspace_id: str) -> list[dict]:
    """Every business in the workspace, oldest first — the order the user is
    shown and the order WhatsApp's numbering indexes into."""
    try:
        res = (
            admin_client.table("businesses").select("id,name")
            .eq("workspace_id", workspace_id)
            .order("created_at").execute()
        )
    except Exception as exc:
        log.error("list_businesses: query failed: %s", exc)
        return []
    return [{"id": r["id"], "name": r["name"]} for r in (res.data or [])]


def pending_interrupt(thread_id: str) -> dict[str, Any] | None:
    """The interrupt payload this capture thread is paused at, or None.

    Carries a "kind" field ("business_selection" | "confirmation") so callers
    know which reply they are waiting for. A thread that was never started
    returns None cleanly."""
    from app.agents.transaction_capture.graph import capture_graph

    try:
        snapshot = capture_graph.get_state({"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        log.error("pending_interrupt: get_state failed for %s: %s", thread_id, exc)
        return None
    for task in snapshot.tasks:
        for itr in task.interrupts:
            return itr.value
    return None


def thread_values(thread_id: str) -> dict[str, Any]:
    """This capture thread's checkpointed state, or {} if it has none."""
    from app.agents.transaction_capture.graph import capture_graph

    try:
        snapshot = capture_graph.get_state({"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        log.error("thread_values: get_state failed for %s: %s", thread_id, exc)
        return {}
    return dict(snapshot.values or {})


def set_thread_values(thread_id: str, values: dict[str, Any]) -> None:
    """Write directly into a capture thread's state without running a node.

    Used by WhatsApp's "ganti bisnis", which has to change what the thread
    remembers between two messages, outside any graph run."""
    from app.agents.transaction_capture.graph import capture_graph

    try:
        capture_graph.update_state({"configurable": {"thread_id": thread_id}}, values)
    except Exception as exc:
        log.error("set_thread_values: update_state failed for %s: %s", thread_id, exc)


def remembered_business_id(thread_id: str) -> str | None:
    """The business this conversation last recorded against.

    This is the whole "remember the last choice per conversation" mechanism:
    txn_thread_id is stable per chat room and per WhatsApp number, and the
    resolved business_id survives in that thread's checkpoint. A new room is
    a new thread, so it forgets — which is how the user switches business on
    the web."""
    return thread_values(thread_id).get("business_id")


def fresh_capture_input(
    *,
    workspace_id: str,
    candidate_businesses: list[dict],
    source: str,
    text_body: str | None = None,
    media_bytes: bytes | None = None,
    media_mime_type: str | None = None,
    phone_e164: str | None = None,
    remembered: str | None = None,
    force_business_choice: bool = False,
) -> dict[str, Any]:
    """Input for a NEW capture on a thread that may already hold state.

    Invoking a graph on an existing thread merges the input into the previous
    checkpoint's values, so every per-run field must be reset explicitly or
    the last capture's extraction, decision and transaction id leak into this
    one. business_id is the deliberate exception — it is what carries the
    remembered business forward."""
    return {
        "workspace_id": workspace_id,
        "candidate_businesses": candidate_businesses,
        "source": source,
        "text_body": text_body,
        "media_bytes": media_bytes,
        "media_mime_type": media_mime_type,
        "phone_e164": phone_e164,
        "business_id": remembered,
        "force_business_choice": force_business_choice,
        # Explicit resets — see docstring.
        "business_name": None,
        "business_cancelled": False,
        "extraction": None,
        "gate_failed": False,
        "transaction_id": None,
        "plausibility_flag": False,
        "confirmed": None,
    }


def resume_transaction(thread_id: str, decision: TransactionReply) -> dict[str, Any]:
    from langgraph.types import Command

    from app.agents.transaction_capture.graph import capture_graph

    return capture_graph.invoke(
        Command(resume={"decision": decision}),
        config={"configurable": {"thread_id": thread_id}},
    )


def resume_business_choice(thread_id: str, business_id: str | None) -> dict[str, Any]:
    """Answer the business question. `None` cancels the capture — the run
    ends before any row is written."""
    from langgraph.types import Command

    from app.agents.transaction_capture.graph import capture_graph

    return capture_graph.invoke(
        Command(resume={"business_id": business_id}),
        config={"configurable": {"thread_id": thread_id}},
    )
