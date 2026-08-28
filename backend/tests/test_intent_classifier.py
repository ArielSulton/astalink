from app.agents.intents import Intent


def test_intent_enum_has_all_required_values() -> None:
    expected = {
        "ALLOCATE_STOCKS",
        "ALLOCATE_CAPITAL",
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


def test_record_audit_persists_thread_id_for_approvals_resume() -> None:
    """Live incident: approvals.py used to resume graph runs under `audit_id`
    as the thread_id, which never matches the real thread any entry point
    (chat.py/agent.py/whatsapp.py) actually invoked under — silently starting
    a fresh, empty run instead of resuming the paused one. audit_log must
    carry the real thread_id so approvals.py can look it up."""
    from unittest.mock import MagicMock

    from app.agents.intent.node import _record_audit
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["_user_id"] = "user-1"
    state["_thread_id"] = "user-1:thread-abc"

    decision = IntentDecision(intent=Intent.ALLOCATE_STOCKS,
                              entities={"amount": 10_000_000}, confidence=0.9)

    fake_admin = MagicMock()
    with patch("app.agents.intent.node.get_admin_client", return_value=fake_admin):
        _record_audit(state, decision)

    upsert_payload = fake_admin.table.return_value.upsert.call_args[0][0]
    assert upsert_payload["thread_id"] == "user-1:thread-abc"


def test_intent_node_returns_state_update_with_intent_and_entities() -> None:
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="Alokasikan 10 juta ke BBCA")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 10_000_000, "tickers": ["BBCA"]},
        confidence=0.92,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit") as record:
        update = intent_node(state)

    assert update["intent"] == Intent.ALLOCATE_STOCKS.value
    assert update["entities"] == {"amount": 10_000_000, "tickers": ["BBCA"]}
    record.assert_called_once()


def test_intent_node_defaults_to_blue_chip_basket_when_no_ticker_or_sector_named() -> None:
    """"rekomendasi investasi untuk dana 20 juta" names no ticker and no
    sector — a real recommendation request, not something to bounce back
    asking the user to name a stock themselves. Falls back to the same
    blue-chip basket already used as the Market watchlist's default
    (app/api/v1/market.py's DEFAULT_TICKERS)."""
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="rekomendasi investasi untuk dana 20 juta rupiah")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 20_000_000},
        confidence=0.9,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    assert update["entities"]["tickers"] == ["BBCA", "TLKM", "ASII", "BBRI"]
    assert update["entities"]["amount"] == 20_000_000


def test_intent_node_resolves_stated_sector_to_matching_tickers() -> None:
    """A stated sector ("bank atau telco gitu") must resolve to that
    sector's real constituents (BBCA/BMRI/... for "bank"), NOT the generic
    blue-chip basket — ASII/TLKM aren't bank stocks, so that basket would
    quietly ignore what the user actually asked for. Regression coverage:
    previously this case left `entities["tickers"]` empty entirely, which
    made prescreen_stock_score short-circuit to (None, None) and Layer 0
    fall back to the baseline stand-in for the stocks leg — producing an
    uninformative baseline-vs-baseline 50/50 split no matter the request."""
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="alokasikan 10 juta ke saham bank")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 10_000_000, "sector": "bank"},
        confidence=0.92,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    tickers = update["entities"]["tickers"]
    assert tickers, "expected 'bank' to resolve to real bank tickers"
    assert set(tickers) <= {"BBCA", "BMRI", "BBNI", "BBRI", "BBTN", "BRIS"}
    assert "ASII" not in tickers and "TLKM" not in tickers


def test_intent_node_resolves_sectors_list_key_and_merges_across_sectors() -> None:
    """Live-observed shape: the intent LLM extracted {"sectors": ["banking",
    "telecommunications"]} (plural, list) for "bank atau telco gitu", not
    {"sector": "..."} — the entities dict is unconstrained free-form, so both
    shapes must resolve. Multiple stated sectors merge into one ticker list."""
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(
        content="Mau investasi 50 juta ke saham IDX. Saya pemula, mau yang "
                "aman dulu aja — bank atau telco gitu.")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 50_000_000, "risk_profile": "conservative",
                  "sectors": ["banking", "telecommunications"]},
        confidence=0.9,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    tickers = update["entities"]["tickers"]
    assert tickers
    assert {"BBCA", "BMRI", "BBNI", "BBRI"} & set(tickers), "expected banking tickers"
    assert {"TLKM", "EXCL", "ISAT", "FREN"} & set(tickers), "expected telco tickers"


def test_intent_node_leaves_unrecognized_sector_without_tickers() -> None:
    """A sector string we can't map to real constituents must NOT fall back
    to the generic blue-chip basket either — same "don't quietly answer a
    different question" rule, just for the unmapped case. Falls through to
    optimizer_node's existing no-tickers-to-work-with gate instead."""
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="alokasikan 10 juta ke saham perkebunan")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 10_000_000, "sector": "perkebunan"},
        confidence=0.9,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    assert "tickers" not in update["entities"]


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
