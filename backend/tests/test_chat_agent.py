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
