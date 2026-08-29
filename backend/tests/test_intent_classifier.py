import pytest

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
    assert {"TLKM", "EXCL", "ISAT"} & set(tickers), "expected telco tickers"


def test_intent_node_resolves_sector_preference_key_shape() -> None:
    """Live-observed shape, a third variant for the exact same phrasing
    ("bank atau telco gitu") across separate live calls: {"sector_preference":
    ["bank", "telco"]} — neither "sector" nor "sectors". Chasing each new key
    name individually doesn't scale, which is why _resolve_sector_tickers
    scans every entity value instead of specific key names."""
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
        entities={"amount": 50_000_000, "market": "IDX",
                  "sector_preference": ["bank", "telco"],
                  "risk_profile": "konservatif"},
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
    assert {"TLKM", "EXCL", "ISAT"} & set(tickers), "expected telco tickers"
    assert tickers != ["BBCA", "TLKM", "ASII", "BBRI"], \
        "must not silently fall through to the generic blue-chip basket"


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


def test_build_chain_pins_function_calling_for_sumopod(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression coverage, verified against the live SumoPod/DeepSeek route:
    with_structured_output()'s default method ("json_schema") uses OpenAI's
    strict response_format, which SumoPod's proxy rejects outright regardless
    of any other setting ("This response_format type is unavailable now") —
    a proxy-level gap. method="function_calling" (forced tool_choice) is
    rejected by DeepSeek's default "thinking" mode specifically ("Thinking
    mode does not support this tool_choice") — fixed at the client level via
    get_chat_model()'s extra_body={"thinking": {"type": "disabled"}}, not
    here. With thinking disabled, function_calling works and is more
    reliable than method="json_mode" (confirmed live: json_mode returned
    syntactically malformed JSON at least once in the same testing)."""
    import app.agents.intent.node as node

    monkeypatch.setattr(node.settings, "LLM_PROVIDER", "sumopod")
    node._build_chain.cache_clear()
    fake_llm = MagicMock()
    with patch("app.agents.intent.node.get_chat_model", return_value=fake_llm):
        node._build_chain()

    fake_llm.with_structured_output.assert_called_once()
    _, kwargs = fake_llm.with_structured_output.call_args
    assert kwargs.get("method") == "function_calling"
    node._build_chain.cache_clear()


def test_build_chain_pins_json_schema_for_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression coverage, verified live: method="function_calling" breaks
    entities extraction on Gemini specifically. IntentDecision.entities is
    `dict[str, Any]`, and Gemini's function-calling schema translation can't
    represent that openly-typed a field ("Key '$defs' is not supported in
    schema, ignoring") — entities silently comes back {} every time under
    that method. json_schema (the with_structured_output() default) handles
    it correctly, as it always has, so Gemini must keep using it even though
    sumopod needs function_calling."""
    import app.agents.intent.node as node

    monkeypatch.setattr(node.settings, "LLM_PROVIDER", "gemini")
    node._build_chain.cache_clear()
    fake_llm = MagicMock()
    with patch("app.agents.intent.node.get_chat_model", return_value=fake_llm):
        node._build_chain()

    fake_llm.with_structured_output.assert_called_once()
    _, kwargs = fake_llm.with_structured_output.call_args
    assert kwargs.get("method") == "json_schema"
    node._build_chain.cache_clear()


def test_system_prompt_contains_json_keyword_required_by_json_mode() -> None:
    """OpenAI-compatible json_object response_format (which method="json_mode"
    uses) 400s outright if the prompt doesn't literally contain the word
    "json" — confirmed live against SumoPod's DeepSeek route ("Prompt must
    contain the word 'json' in some form..."). This must never silently
    regress if SYSTEM is edited later."""
    from app.agents.intent.node import SYSTEM

    assert "json" in SYSTEM.lower()


def test_intent_node_replies_with_apology_instead_of_echoing_user_on_classification_crash() -> None:
    """Regression: previously, a classifier crash (e.g. the sumopod
    response_format 400) left `messages` untouched, and
    build_chat_reply's "N1 couldn't classify" rule just relays
    messages[-1] — silently echoing the user's own text back at them
    instead of surfacing that something broke."""
    from app.agents.intent.node import intent_node
    from app.agents.state import new_state
    from langchain_core.messages import AIMessage

    state = new_state()
    user_text = "Mau investasi 50 juta ke saham IDX, bank atau telco gitu."
    state["messages"] = [HumanMessage(content=user_text)]

    fake_chain = MagicMock()
    fake_chain.invoke.side_effect = RuntimeError("response_format type is unavailable now")

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain):
        update = intent_node(state)

    assert update["_needs_clarification"] is True
    new_messages = update.get("messages", [])
    assert new_messages, "must append a reply, not leave messages untouched"
    last = new_messages[-1]
    assert isinstance(last, AIMessage)
    assert last.content != user_text, "must not echo the user's own message back"
