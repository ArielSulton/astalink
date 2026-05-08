from app.agents.state import LegalStatus, UserApproval, new_state


def test_market_stub_returns_dummy_snapshot() -> None:
    from app.agents.stubs import market_stub
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}
    update = market_stub(state)
    assert "market_snapshot" in update["entities"]


def test_business_stub_returns_dummy_valuation() -> None:
    from app.agents.stubs import business_stub
    update = business_stub(new_state())
    assert "business_valuation" in update["entities"]


def test_risk_stub_returns_dummy_metrics() -> None:
    from app.agents.stubs import risk_stub
    update = risk_stub(new_state())
    assert "risk_metrics" in update["entities"]


def test_optimizer_stub_increments_revision_count() -> None:
    from app.agents.stubs import optimizer_stub
    state = new_state()
    state["entities"] = {"tickers": ["BBCA"], "amount": 10_000_000}
    state["revision_count"] = 0
    update = optimizer_stub(state)
    assert update["revision_count"] == 1
    assert update["allocation_plan"] is not None


def test_hitl_stub_auto_approves() -> None:
    """In Phase 2 the HITL gate auto-approves so the graph runs end-to-end.
    Phase 5 replaces this with a real interrupt()."""
    from app.agents.stubs import hitl_stub
    update = hitl_stub(new_state())
    assert update["user_approval"] == UserApproval.APPROVED


def test_execution_stub_writes_dummy_transaction_record() -> None:
    from app.agents.stubs import execution_stub
    state = new_state()
    state["allocation_plan"] = {"weights": [{"ticker": "BBCA", "weight": 1.0}], "cash": 10_000_000}
    update = execution_stub(state)
    assert update["transactions"]
    assert update["transactions"][0]["status"] == "simulated"


def test_rejection_handler_appends_alternatives_message() -> None:
    from app.agents.rejection import rejection_handler
    state = new_state()
    state["legal_status"] = LegalStatus.REJECTED
    state["legal_citations"] = [{"source": "OJK", "pasal": "3", "ayat": "1",
                                 "chunk_id": "x", "span": "dilarang"}]
    update = rejection_handler(state)
    msgs = update["messages"]
    assert msgs and "tidak dapat" in msgs[-1].content.lower()
