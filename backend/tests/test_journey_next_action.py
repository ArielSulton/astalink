from app.core.journey_next_action import JourneySignals, choose_next_action


def test_pending_transaction_precedes_every_other_action() -> None:
    action = choose_next_action(JourneySignals(
        pending_transaction_id="txn-1",
        pending_approvals_count=2,
        decisive_gaps=("monthly_expenses",),
        hard_veto_codes=("EMERGENCY_FUND",),
        allocation_available=True,
        allocation_acknowledged=False,
        holdings_count=3,
    ))
    assert action.kind == "resolve_transaction"
    assert action.href == "/chatbot"


def test_decisive_gap_precedes_exploration() -> None:
    action = choose_next_action(JourneySignals(
        decisive_gaps=("horizon_months",), allocation_available=True,
    ))
    assert action.kind == "complete_readiness"
    assert action.href == "/allocation/investor"


def test_empty_sandbox_after_readiness_routes_to_exploration() -> None:
    action = choose_next_action(JourneySignals(
        allocation_available=True, allocation_acknowledged=True, holdings_count=0,
    ))
    assert action.kind == "explore_investments"
    assert action.href == "/recommendations"


def test_neutral_fallback_is_always_available() -> None:
    action = choose_next_action(JourneySignals())
    assert action.kind == "ask_asta"
    assert action.href == "/chatbot"
