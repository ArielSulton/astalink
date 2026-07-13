import pytest

# Skip locally if talib isn't installed — graph.py now imports market_node which imports talib.
pytest.importorskip("talib")

from unittest.mock import MagicMock, patch
import numpy as np

from langchain_core.messages import HumanMessage

from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.intents import Intent
from app.agents.state import LegalStatus, UserApproval


@pytest.fixture(autouse=True)
def _patch_externals():
    """For graph-wiring tests we don't care about analyzer internals — mock the
    expensive parts so the test stays fast and offline."""
    fake_closes = np.linspace(100, 110, 60)

    fake_broker = MagicMock()
    fake_broker.place_order.side_effect = lambda **kw: BrokerOrder(
        ticker=kw["ticker"], qty=kw["qty"], side=kw["side"],
        broker_ref="test-ref", status="filled",
    )
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": "x"}])

    # Layer 1 stock engine would hit yfinance/NewsAPI — fake it as
    # "everything eligible" so the optimizer path behaves as before.
    fake_engine = lambda tickers, news_by_ticker, total_amount_idr=None: {
        "verdicts": {}, "eligible_tickers": list(tickers),
        "macro": {}, "as_of": "",
    }

    with patch("app.agents.market.node.fetch_close_prices", return_value=fake_closes), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model"), \
         patch("app.agents.market.stock_engine.run_stock_engine", new=fake_engine), \
         patch("app.agents.risk.node.fetch_close_prices", return_value=np.linspace(100, 110, 252)), \
         patch("app.agents.risk.node.get_chat_model"), \
         patch("app.agents.business.node.get_chat_model"), \
         patch("app.agents.optimizer.node.get_chat_model"), \
         patch("app.agents.hitl.node.interrupt", return_value={"approval": UserApproval.APPROVED.value}), \
         patch("app.agents.hitl.node.get_admin_client"), \
         patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        yield


def test_graph_runs_happy_path_to_execution() -> None:
    """Forced-approved path: n3 returns approved → n6 stub approves → n7 stub fires."""
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.APPROVED, "legal_citations": []}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["BBCA"], "amount": 1_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="alokasikan ke BBCA")],
             "audit_id": "test-audit", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t1"}},
        )

    assert result["legal_status"] == LegalStatus.APPROVED
    assert result["user_approval"] == UserApproval.APPROVED
    assert result["transactions"], "execution stub must produce transactions"


def test_graph_rejection_path_skips_execution() -> None:
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.REJECTED,
                            "legal_citations": [{"source": "OJK", "pasal": "3", "ayat": "1",
                                                 "chunk_id": "x", "span": "dilarang"}]}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["GGRM"], "amount": 5_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="GGRM")],
             "audit_id": "test-2", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t2"}},
        )

    assert result["legal_status"] in (LegalStatus.REJECTED,
                                       LegalStatus.REJECTED_AFTER_MAX_REVISIONS)
    assert not result["transactions"], "rejected plans must not execute"
    assert any("tidak dapat" in m.content.lower() for m in result["messages"]
               if hasattr(m, "content"))


def test_graph_revision_loop_caps_at_three() -> None:
    """Stub legal always rejects. Optimizer increments revision_count. After 3
    revisions, graph must terminate."""
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.REJECTED,
                            "legal_citations": []}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["BBCA"], "amount": 1_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="x")],
             "audit_id": "t3", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t3"}, "recursion_limit": 50},
        )

    assert result["revision_count"] == 3
    assert result["legal_status"] in (
        LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS,
    )
    assert not result["transactions"]


def test_layer0_force_cash_gates_off_stock_engine() -> None:
    """L0-2 veto (no emergency fund) → 0% stocks → graph ends at Layer 0:
    no market/optimizer/legal/execution work at all."""
    from app.agents.allocation.schemas import InvestorProfile
    from app.agents.graph import build_graph

    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["BBCA"], "amount": 1_000_000}}
    broke = InvestorProfile(monthly_expenses=10_000_000, emergency_fund=5_000_000)

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.allocation.node.load_investor_profile", return_value=broke):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="beli BBCA")],
             "audit_id": "t4", "revision_count": 0, "_workspace_id": "ws-1",
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t4"}},
        )

    alloc = result["layer0_result"]["allocation"]
    assert alloc == {"cash": 1.0, "stocks": 0.0, "business": 0.0}
    assert not result["transactions"]
    assert result.get("allocation_plan") is None, "optimizer must never run"
    assert any("Dana darurat" in m.content for m in result["messages"]
               if hasattr(m, "content"))


def test_layer0_insufficient_data_is_terminal_with_questions() -> None:
    """ALLOCATE_CAPITAL with an empty intake profile → INSUFFICIENT_DATA is
    the entire output: staged questions, no allocation, no downstream run."""
    from app.agents.allocation.schemas import BusinessProfile, InvestorProfile
    from app.agents.graph import build_graph

    fake_intent = lambda s: {"intent": Intent.ALLOCATE_CAPITAL.value,
                             "entities": {"business_name": "Warung Maju"}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.allocation.node.load_investor_profile",
               return_value=InvestorProfile()), \
         patch("app.agents.allocation.node.load_business_profile",
               return_value=({"id": "b1", "name": "Warung Maju"},
                             BusinessProfile())):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="mending saham atau suntik warung?")],
             "audit_id": "t5", "revision_count": 0, "_workspace_id": "ws-1",
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t5"}},
        )

    l0 = result["layer0_result"]
    assert l0["status"] == "insufficient_data"
    assert l0["allocation"] is None
    assert len(l0["questions"]) == 3
    assert not result["transactions"]
    assert result.get("allocation_plan") is None
