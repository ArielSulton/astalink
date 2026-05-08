import pytest

# Skip locally if talib isn't installed — graph.py now imports market_node which imports talib.
pytest.importorskip("talib")

from unittest.mock import patch
import numpy as np

from langchain_core.messages import HumanMessage

from app.agents.intents import Intent
from app.agents.state import LegalStatus, UserApproval


@pytest.fixture(autouse=True)
def _patch_externals():
    """For graph-wiring tests we don't care about analyzer internals — mock the
    expensive parts so the test stays fast and offline."""
    fake_closes = np.linspace(100, 110, 60)
    with patch("app.agents.market.node.fetch_close_prices", return_value=fake_closes), \
         patch("app.agents.market.node.fetch_news", return_value=[]), \
         patch("app.agents.market.node.get_chat_model"), \
         patch("app.agents.risk.node.fetch_close_prices", return_value=np.linspace(100, 110, 252)), \
         patch("app.agents.risk.node.get_chat_model"), \
         patch("app.agents.business.node.get_chat_model"), \
         patch("app.agents.optimizer.node.get_chat_model"), \
         patch("app.agents.hitl.node.interrupt", return_value={"approval": UserApproval.APPROVED.value}), \
         patch("app.agents.hitl.node.get_admin_client"):
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
