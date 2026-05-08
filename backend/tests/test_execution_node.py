from unittest.mock import MagicMock, patch

from app.agents.execution.node import execution_node
from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.state import new_state


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
