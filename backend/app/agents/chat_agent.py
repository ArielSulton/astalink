"""Builds a natural-language chat reply from the main pipeline's final state.

Advisory mode: the pipeline produces analysis and recommendations only.
No automatic execution — the user retains full control. This module
formats the pipeline's final AgentState into one conversational reply;
it holds no graph of its own."""
from __future__ import annotations

from app.agents.intents import Intent
from app.agents.report import build_allocation_report
from app.agents.state import AgentState, LegalStatus


def _last_text(messages: list) -> str:
    last = messages[-1]
    return getattr(last, "content", "") or ""


def build_chat_reply(state: AgentState, *, style: str = "plain") -> str:
    """Turn a finished pipeline run into one chat message.

    style="report" (web chat) formats allocation runs into the full markdown
    advisory report from app.agents.report; the default "plain" keeps the
    short single-sentence replies (WhatsApp renders no markdown).

    Priority mirrors what the user needs to see first:
    1. N1 couldn't classify the message — relay its clarification question.
    2. optimizer_node had no tickers to work with — ask for one.
    3. Informational intents — relay the QA/summary node's answer as-is.
    4. Report-style advisory report (web chat only).
    5. Legal rejected the plan — explain that.
    6. Legal approved — confirm analysis complete.
    7. Fallback — relay whatever the last message says, or a generic apology.
    """
    messages = state.get("messages") or []
    legal_status = state.get("legal_status")
    audit_id = state.get("audit_id")

    if state.get("_needs_clarification") and messages:
        return _last_text(messages)

    optimizer_errors = {e.get("reason") for e in state.get("errors", []) if e.get("node") == "optimizer"}
    if "no_tickers" in optimizer_errors:
        return (
            "Untuk kasih rekomendasi alokasi, saya perlu tahu saham yang ingin Anda "
            "pertimbangkan. Sebutkan ticker-nya, misalnya: \"alokasikan 20 juta ke BBCA "
            "dan TLKM\". Belum ada ide? Cek halaman Market News di dashboard untuk "
            "referensi saham yang sedang tren."
        )

    informational = (
        Intent.EXPLAIN.value,
        Intent.EVALUATE_BUSINESS.value,
        Intent.RISK_REVIEW.value,
        Intent.PORTFOLIO_STATUS.value,
    )
    if state.get("intent") in informational and messages:
        return _last_text(messages)

    if style == "report":
        report = build_allocation_report(state)
        if report:
            return report

    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        return (
            f"Rekomendasi alokasi ini tidak lolos validasi legal. "
            f"Coba revisi permintaannya — misalnya ganti saham atau turunkan "
            f"nominalnya. Audit ID: {audit_id}."
        )

    if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return (
            "Analisis selesai dan rekomendasi lolos validasi legal. "
            f"Lihat laporan lengkap di atas untuk detail rekomendasi. "
            f"Keputusan akhir ada di tangan Anda. Audit ID: {audit_id}."
        )

    if messages:
        return _last_text(messages)

    return "Maaf, saya tidak dapat memproses permintaan ini."

