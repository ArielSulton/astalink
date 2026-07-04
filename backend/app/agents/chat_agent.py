"""Builds a natural-language chat reply from the main pipeline's final state.

`/chat` delegates every message to the same LangGraph pipeline used by
`/agent/run` (see app.agents.graph) instead of running a separate, stateless
Gemini wrapper — this is what makes /chat satisfy the PRD's "menyalurkan
permintaan ke pipeline" requirement (FR-19). This module only formats that
pipeline's final AgentState into one conversational reply; it holds no graph
of its own."""
from __future__ import annotations

from app.agents.intents import Intent
from app.agents.state import AgentState, LegalStatus, UserApproval


def _last_text(messages: list) -> str:
    last = messages[-1]
    return getattr(last, "content", "") or ""


def build_chat_reply(state: AgentState) -> str:
    """Turn a finished/paused pipeline run into one chat message.

    Priority mirrors what the user needs to see first:
    1. N1 couldn't classify the message — relay its clarification question.
    2. EXPLAIN question — relay the Q&A node's direct answer as-is.
    3. Legal rejected the plan — explain that (pipeline stops here).
    4. Legal approved/partial but no human decision yet — point at Approvals.
    5. Execution already ran — summarize the resulting transactions.
    6. Fallback — relay whatever the last message says, or a generic apology.
    """
    messages = state.get("messages") or []
    legal_status = state.get("legal_status")
    audit_id = state.get("audit_id")

    if state.get("_needs_clarification") and messages:
        return _last_text(messages)

    if state.get("intent") == Intent.EXPLAIN.value and messages:
        return _last_text(messages)

    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        return (
            f"Maaf, rencana alokasi ini ditolak secara legal dan tidak dapat "
            f"dilanjutkan. Audit ID: {audit_id}."
        )

    if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL) \
            and state.get("user_approval") is None:
        return (
            "Rencana alokasi sudah dianalisis dan lolos validasi legal. "
            f"Silakan tinjau dan setujui di halaman Approvals (Audit ID: {audit_id})."
        )

    if state.get("user_approval") == UserApproval.APPROVED and state.get("transactions"):
        filled = [t for t in state["transactions"] if t.get("status") == "filled"]
        rejected = [t for t in state["transactions"]
                    if t.get("status") == "rejected_insufficient_balance"]
        parts = []
        if filled:
            parts.append(f"Transaksi berhasil dieksekusi untuk: {', '.join(t['ticker'] for t in filled)}.")
        if rejected:
            parts.append(
                f"{', '.join(t['ticker'] for t in rejected)} ditolak karena saldo tidak mencukupi."
            )
        if parts:
            return " ".join(parts) + f" Audit ID: {audit_id}."

    if messages:
        return _last_text(messages)

    return "Maaf, saya tidak dapat memproses permintaan ini."
