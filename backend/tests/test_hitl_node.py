from unittest.mock import patch

import pytest

from app.agents.hitl.node import hitl_node
from app.agents.state import LegalStatus, UserApproval, new_state


def test_hitl_node_calls_interrupt_with_plan_summary() -> None:
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.6}],
        "cash": 10_000_000,
    }
    state["legal_status"] = LegalStatus.APPROVED

    captured: dict = {}

    def _fake_interrupt(payload):
        captured.update(payload)
        from langgraph.errors import GraphInterrupt
        raise GraphInterrupt(payload)

    with patch("app.agents.hitl.node.interrupt", side_effect=_fake_interrupt), \
         patch("app.agents.hitl.node.get_admin_client"):
        from langgraph.errors import GraphInterrupt
        with pytest.raises(GraphInterrupt):
            hitl_node(state)

    assert captured["audit_id"] == state["audit_id"]
    assert "allocation_plan" in captured
    assert captured["legal_status"] == LegalStatus.APPROVED.value


def test_hitl_node_returns_user_approval_when_resumed() -> None:
    """LangGraph's interrupt() returns the resume value when the graph is
    invoked with a non-None command. We simulate that by patching interrupt
    to return a resume payload."""
    state = new_state()
    state["allocation_plan"] = {"weights": [], "cash": 0}
    state["legal_status"] = LegalStatus.APPROVED

    with patch("app.agents.hitl.node.interrupt",
               return_value={"approval": UserApproval.APPROVED.value}), \
         patch("app.agents.hitl.node.get_admin_client"):
        update = hitl_node(state)

    assert update["user_approval"] == UserApproval.APPROVED
