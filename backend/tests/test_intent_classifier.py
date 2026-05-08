from app.agents.intents import Intent


def test_intent_enum_has_all_required_values() -> None:
    expected = {
        "ALLOCATE_STOCKS",
        "EVALUATE_BUSINESS",
        "RISK_REVIEW",
        "PORTFOLIO_STATUS",
        "EXPLAIN",
        "UNKNOWN",
    }
    assert {i.name for i in Intent} == expected


def test_intent_string_values_match_names_lowercased() -> None:
    """We store intents as lowercase strings in audit_log.intent."""
    assert Intent.ALLOCATE_STOCKS.value == "allocate_stocks"
    assert Intent.UNKNOWN.value == "unknown"
