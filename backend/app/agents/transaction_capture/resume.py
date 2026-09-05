"""Shared helpers for routing/resuming the transaction-capture subgraph from
the WhatsApp webhook — mirrors app/agents/composition_gate/resume.py's
shape exactly (same reasoning: reply detection + pending lookup +
Command(resume=...) invocation, kept out of the webhook handler itself)."""
from __future__ import annotations

import logging
from typing import Any, Literal

log = logging.getLogger(__name__)

_YES = {"ya", "iya", "yes", "setuju", "oke", "ok", "benar", "betul"}
_NO = {"tidak", "gak", "ga", "nggak", "no", "batal", "salah"}

TransactionReply = Literal["confirmed", "rejected"]


def detect_transaction_reply(text: str) -> TransactionReply | None:
    normalized = text.strip().lower().rstrip(".!?")
    if normalized in _YES:
        return "confirmed"
    if normalized in _NO:
        return "rejected"
    return None


def resolve_single_business(admin_client, workspace_id: str) -> str | None:
    """MVP scope cut (spec Non-goals): capture only activates when the
    workspace owns exactly one business — 0 or 2+ is ambiguous and gets
    redirected to the dashboard by the webhook layer instead of guessed at
    over WhatsApp."""
    try:
        res = admin_client.table("businesses").select("id").eq("workspace_id", workspace_id).execute()
    except Exception as exc:
        log.error("resolve_single_business: query failed: %s", exc)
        return None
    rows = res.data or []
    return rows[0]["id"] if len(rows) == 1 else None


def find_pending_transaction(admin_client, business_id: str) -> str | None:
    try:
        res = (
            admin_client.table("business_transactions").select("id")
            .eq("business_id", business_id)
            .eq("status", "pending_confirmation")
            .order("created_at", desc=True).limit(1).execute()
        )
    except Exception as exc:
        log.error("find_pending_transaction: query failed: %s", exc)
        return None
    rows = res.data or []
    return rows[0]["id"] if rows else None


def resume_transaction(thread_id: str, decision: TransactionReply) -> dict[str, Any]:
    from langgraph.types import Command

    from app.agents.transaction_capture.graph import capture_graph

    return capture_graph.invoke(
        Command(resume={"decision": decision}),
        config={"configurable": {"thread_id": thread_id}},
    )
