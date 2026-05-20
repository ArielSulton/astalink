"""Verifies the AgentState TypedDict has the contracted shape.

LangGraph nodes will partial-update this dict; the test ensures all fields
the master plan requires are declared with sensible types and defaults."""
import uuid
from app.agents.state import AgentState, new_state, LegalStatus


def test_agentstate_has_required_keys() -> None:
    keys = AgentState.__annotations__.keys()
    expected = {
        "audit_id",
        "messages",
        "intent",
        "entities",
        "allocation_plan",
        "revision_count",
        "legal_status",
        "legal_citations",
        "user_approval",
        "transactions",
        "errors",
    }
    missing = expected - set(keys)
    assert not missing, f"AgentState missing keys: {missing}"


def test_new_state_generates_audit_id_and_zero_revisions() -> None:
    s = new_state()

    # audit_id must be a valid UUID4 string
    uuid.UUID(s["audit_id"], version=4)

    assert s["revision_count"] == 0
    assert s["messages"] == []
    assert s["legal_status"] is None
    assert s["user_approval"] is None
    assert s["allocation_plan"] is None
    assert s["entities"] == {}
    assert s["transactions"] == []
    assert s["errors"] == []


def test_legal_status_enum_values() -> None:
    assert LegalStatus.APPROVED == "approved"
    assert LegalStatus.PARTIAL == "partial"
    assert LegalStatus.REJECTED == "rejected"
    assert LegalStatus.REJECTED_AFTER_MAX_REVISIONS == "rejected_after_max_revisions"
