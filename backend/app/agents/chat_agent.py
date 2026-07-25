"""Builds a natural-language chat reply from the main pipeline's final state.

Advisory mode: the pipeline produces analysis and recommendations only.
No automatic execution — the user retains full control. This module
formats the pipeline's final AgentState into one conversational reply;
it holds no graph of its own."""
from __future__ import annotations

from app.agents.intents import Intent
from app.agents.report import build_allocation_report, build_composition_summary
from app.agents.state import AgentState, LegalStatus, UserApproval


def _last_text(messages: list) -> str:
    last = messages[-1]
    return getattr(last, "content", "") or ""


def _plain_composition_prompt(state: AgentState) -> str:
    """Short, table-free composition-gate prompt for plain-style channels
    (WhatsApp) — the full markdown table in build_composition_summary
    renders as literal pipe characters there. WhatsApp also gets an image of
    the same split alongside this text, so the numbers don't need repeating
    in full detail here."""
    layer0 = state.get("layer0_result") or {}
    alloc = layer0.get("allocation") or {}
    business_name = layer0.get("business_name")
    line = (f"Rekomendasi awal: Kas {alloc.get('cash', 0):.0%}, "
            f"Saham {alloc.get('stocks', 0):.0%}")
    if business_name:
        line += f", Bisnis {alloc.get('business', 0):.0%} ({business_name})"
    return (
        f"{line}.\n\nBalas *ya* untuk lanjut ke analisis saham, atau *tidak* "
        "untuk berhenti di sini."
    )


def build_chat_reply(state: AgentState, *, style: str = "plain") -> str:
    """Turn a finished pipeline run into one chat message.

    style="report" (web chat) formats allocation runs into the full markdown
    advisory report from app.agents.report; the default "plain" keeps the
    short single-sentence replies (WhatsApp renders no markdown).

    Priority mirrors what the user needs to see first:
    0. Paused at the composition gate (allocate_capital) — show Layer 0's
       split and ask for ya/tidak, before anything else runs.
    0b. User just said "tidak" to that gate — relay the cancellation
        message, not a regenerated (and now misleading) allocation report.
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

    if state.get("__interrupt__"):
        if style == "report":
            summary = build_composition_summary(state)
            if summary:
                return summary
        return _plain_composition_prompt(state)

    if state.get("composition_approval") == UserApproval.REJECTED and messages:
        return _last_text(messages)

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

