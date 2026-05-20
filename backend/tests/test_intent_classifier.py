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


def test_intent_decision_has_clarification_question_field() -> None:
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent

    d = IntentDecision(
        intent=Intent.UNKNOWN,
        entities={},
        confidence=0.3,
        clarification_question="Apa yang ingin Anda lakukan?",
    )
    assert d.intent == Intent.UNKNOWN
    assert d.confidence == 0.3
    assert d.clarification_question is not None


def test_intent_decision_clarification_optional() -> None:
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent

    d = IntentDecision(intent=Intent.ALLOCATE_STOCKS,
                       entities={"amount": 10_000_000}, confidence=0.95)
    assert d.clarification_question is None


from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage


def test_intent_node_returns_state_update_with_intent_and_entities() -> None:
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="Alokasikan 10 juta ke saham bank")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 10_000_000, "sector": "bank"},
        confidence=0.92,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit") as record:
        update = intent_node(state)

    assert update["intent"] == Intent.ALLOCATE_STOCKS.value
    assert update["entities"] == {"amount": 10_000_000, "sector": "bank"}
    record.assert_called_once()


def test_intent_node_sets_clarification_when_low_confidence() -> None:
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state
    from langchain_core.messages import AIMessage

    state = new_state()
    state["messages"] = [HumanMessage(content="hmm")]

    fake_decision = IntentDecision(
        intent=Intent.UNKNOWN,
        entities={},
        confidence=0.2,
        clarification_question="Apa tujuan investasi Anda?",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    assert update["intent"] == Intent.UNKNOWN.value
    # clarification appended as an AI message so the channel layer (WhatsApp /
    # web chat) can surface it
    assert any(isinstance(m, AIMessage) and "tujuan" in m.content for m in update.get("messages", []))
