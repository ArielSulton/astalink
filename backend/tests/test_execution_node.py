from unittest.mock import MagicMock, patch

from app.agents.execution.node import execution_node
from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.state import UserApproval, new_state


def test_execution_node_places_one_order_per_leg() -> None:
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.6}, {"ticker": "BMRI", "weight": 0.3}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
        {"ticker": "BMRI", "last_close": 6000},
    ]}}
    state["user_approval"] = UserApproval.APPROVED

    fake_broker = MagicMock()
    fake_broker.place_order.side_effect = lambda **kw: BrokerOrder(
        ticker=kw["ticker"], qty=kw["qty"], side=kw["side"],
        broker_ref="x", status="filled",
    )
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # allocation_plans lookup returns one row with id
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": "plan-1"}])

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    assert len(update["transactions"]) == 2
    assert {t["ticker"] for t in update["transactions"]} == {"BBCA", "BMRI"}
    assert fake_broker.place_order.call_count == 2


def _mock_execution_admin(*, balance: float, debit_success: bool):
    """Routes `.table(name)` calls to distinct fluent-query mocks by name —
    same pattern as test_business_node.py's _mock_admin_client — so the
    workspace-balance read/update, the allocation_plans lookup, and the
    transactions insert/select each get their own independent response
    instead of colliding on one shared mock."""
    sb = MagicMock()

    transactions_query = MagicMock()
    transactions_query.select.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=[])  # no existing fills
    transactions_query.insert.return_value.execute.return_value = MagicMock(data=[{}])

    allocation_plans_query = MagicMock()
    allocation_plans_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "plan-1"}])

    workspaces_query = MagicMock()
    workspaces_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": balance}])
    workspaces_query.update.return_value.eq.return_value.gte.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": balance - 1}] if debit_success else [])

    def _table(name: str):
        return {
            "transactions": transactions_query,
            "allocation_plans": allocation_plans_query,
            "workspaces": workspaces_query,
        }[name]

    sb.table.side_effect = _table
    return sb


def test_execution_node_debits_balance_on_successful_order() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
    ]}}
    state["user_approval"] = UserApproval.APPROVED

    fake_broker = MagicMock()
    fake_broker.place_order.side_effect = lambda **kw: BrokerOrder(
        ticker=kw["ticker"], qty=kw["qty"], side=kw["side"],
        broker_ref="x", status="filled",
    )
    # qty = (10_000_000 * 1.0) / 8000 = 1250; cost = 1250 * 8000 = 10_000_000
    fake_admin = _mock_execution_admin(balance=100_000_000, debit_success=True)

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    assert update["transactions"][0]["status"] == "filled"


def test_execution_node_rejects_order_when_balance_insufficient() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
    ]}}
    state["user_approval"] = UserApproval.APPROVED

    fake_broker = MagicMock()
    # balance (100) < cost (10_000_000) — debit_workspace_balance returns
    # None before ever calling .update(), so debit_success is irrelevant here.
    fake_admin = _mock_execution_admin(balance=100, debit_success=False)

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    fake_broker.place_order.assert_not_called()
    assert update["transactions"][0]["status"] == "rejected_insufficient_balance"
    assert any(e["node"] == "execution" and e["reason"] == "insufficient_balance"
               for e in update.get("errors", []))


def test_execution_node_refuses_to_run_without_approval() -> None:
    """Defense-in-depth: the graph router already gates n7 behind
    user_approval == APPROVED, but the node must not trust that alone —
    a future wiring change or direct call must not silently execute."""
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
    ]}}
    state["user_approval"] = None  # not yet approved

    fake_broker = MagicMock()
    fake_admin = MagicMock()

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    fake_broker.place_order.assert_not_called()
    assert update["transactions"] == []
    assert any(e["node"] == "execution" and e["reason"] == "not_approved"
               for e in update.get("errors", []))
