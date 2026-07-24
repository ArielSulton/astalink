from langchain_core.messages import AIMessage, HumanMessage

from app.agents.chat_agent import build_chat_reply
from app.agents.state import LegalStatus, UserApproval, new_state


def test_build_chat_reply_returns_clarification_message_when_ambiguous() -> None:
    state = new_state()
    state["_needs_clarification"] = True
    state["messages"] = [
        HumanMessage(content="halo"),
        AIMessage(content="Bisa dijelaskan lagi tujuan Anda?"),
    ]
    assert build_chat_reply(state) == "Bisa dijelaskan lagi tujuan Anda?"


def test_build_chat_reply_asks_for_tickers_instead_of_misleading_legal_rejection() -> None:
    """Live incident: user asked "rekomendasi investasi untuk dana 20 juta"
    without naming any ticker. optimizer_node correctly bails with
    allocation_plan=None and an optimizer/no_tickers error, but the empty
    plan still flowed through to legal_node, which reasonably rejected an
    EMPTY allocation ("cannot ground a decision") — and the user saw that
    downstream rejection as "ditolak secara legal", with zero indication
    that just naming a stock would fix it. The real, fixable reason
    (optimizer/no_tickers) must take priority over the misleading
    downstream legal rejection it caused."""
    state = new_state()
    state["legal_status"] = LegalStatus.REJECTED
    state["audit_id"] = "audit-no-tickers"
    state["errors"] = [{"node": "optimizer", "reason": "no_tickers"}]
    reply = build_chat_reply(state)
    assert "ditolak secara legal" not in reply.lower()
    assert "saham" in reply.lower() or "ticker" in reply.lower()


def test_build_chat_reply_explains_legal_rejection() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.REJECTED
    state["audit_id"] = "audit-123"
    reply = build_chat_reply(state)
    assert "ditolak" in reply.lower()
    assert "audit-123" in reply


def test_build_chat_reply_points_to_approvals_when_awaiting_hitl() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    state["user_approval"] = None
    state["audit_id"] = "audit-456"
    reply = build_chat_reply(state)
    assert "audit-456" in reply
    assert "approv" in reply.lower() or "setuju" in reply.lower()


def test_build_chat_reply_summarizes_completed_transactions() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    state["user_approval"] = UserApproval.APPROVED
    state["audit_id"] = "audit-789"
    state["transactions"] = [
        {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled", "broker_ref": "r1"},
    ]
    reply = build_chat_reply(state)
    assert "BBCA" in reply
    assert "audit-789" in reply


def test_build_chat_reply_falls_back_to_last_message() -> None:
    state = new_state()
    state["messages"] = [AIMessage(content="Ini penjelasan tentang RSI.")]
    assert build_chat_reply(state) == "Ini penjelasan tentang RSI."


def test_build_chat_reply_has_a_message_when_nothing_else_applies() -> None:
    state = new_state()
    assert build_chat_reply(state)  # non-empty string, no crash


def test_build_chat_reply_reports_balance_rejected_legs_honestly() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    state["user_approval"] = UserApproval.APPROVED
    state["audit_id"] = "audit-999"
    state["transactions"] = [
        {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled", "broker_ref": "r1"},
        {"ticker": "BMRI", "side": "buy", "quantity": 5, "status": "rejected_insufficient_balance", "broker_ref": None},
    ]
    reply = build_chat_reply(state)
    assert "BBCA" in reply
    assert "berhasil dieksekusi" in reply.lower()
    assert "BMRI" in reply
    assert "tidak mencukupi" in reply.lower()
    # BMRI must not be listed among the successfully-executed tickers
    executed_sentence = reply.split(".")[0]
    assert "BMRI" not in executed_sentence


def _report_ready_state() -> dict:
    """Awaiting-HITL allocation state carrying full report data."""
    state = new_state()
    state["audit_id"] = "audit-report"
    state["intent"] = "allocate_stocks"
    state["legal_status"] = LegalStatus.APPROVED
    state["layer0_result"] = {
        "status": "allocated",
        "allocation": {"cash": 0.15, "stocks": 0.85, "business": 0.0},
        "confidence": 62,
        "confidence_label": "MEDIUM",
        "veto_flags": [],
        "narration": "",
    }
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.6},
                    {"ticker": "TLKM", "weight": 0.4}],
        "cash": 10_000_000.0,
        "cash_buffer": 0.1,
        "narration": "Bobot terbesar ke BBCA.",
        "relaxations_applied": [],
    }
    return state


def test_report_style_returns_markdown_report_when_awaiting_hitl() -> None:
    reply = build_chat_reply(_report_ready_state(), style="report")
    assert "| BBCA | 60% |" in reply
    assert "audit-report" in reply
    assert "Laporan" in reply


def test_plain_style_keeps_short_reply_for_same_state() -> None:
    """WhatsApp keeps the terse pointer — the report is opt-in per caller."""
    reply = build_chat_reply(_report_ready_state())
    assert "Laporan" not in reply
    assert "audit-report" in reply


def test_report_style_informational_intent_still_wins_over_stale_state() -> None:
    """Continued thread: checkpointed legal_status/layer0_result from an
    earlier allocation run must not hijack the reply to a follow-up question."""
    state = _report_ready_state()
    state["intent"] = "explain"
    state["messages"] = [
        HumanMessage(content="apa itu RSI?"),
        AIMessage(content="RSI adalah indikator momentum."),
    ]
    reply = build_chat_reply(state, style="report")
    assert reply == "RSI adalah indikator momentum."


def test_report_style_no_tickers_still_wins_over_stale_layer0() -> None:
    state = _report_ready_state()
    state["errors"] = [{"node": "optimizer", "reason": "no_tickers"}]
    reply = build_chat_reply(state, style="report")
    assert "Laporan" not in reply
    assert "ticker" in reply.lower() or "saham" in reply.lower()


def test_build_chat_reply_all_legs_rejected_does_not_claim_success() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    state["user_approval"] = UserApproval.APPROVED
    state["audit_id"] = "audit-1000"
    state["transactions"] = [
        {"ticker": "BMRI", "side": "buy", "quantity": 5, "status": "rejected_insufficient_balance", "broker_ref": None},
    ]
    reply = build_chat_reply(state)
    assert "berhasil dieksekusi" not in reply.lower()
    assert "BMRI" in reply
    assert "tidak mencukupi" in reply.lower()
