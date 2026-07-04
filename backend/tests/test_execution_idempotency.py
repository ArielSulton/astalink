from unittest.mock import MagicMock, patch

from app.agents.execution.node import execution_node
from app.agents.state import UserApproval, new_state


def test_re_running_execution_does_not_place_duplicate_orders() -> None:
    state = new_state()
    state["audit_id"] = "audit-X"
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
    ]}}
    state["user_approval"] = UserApproval.APPROVED

    fake_broker = MagicMock()
    fake_admin = MagicMock()
    # Simulate existing transaction for (audit-X, BBCA, buy)
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"audit_id": "audit-X", "ticker": "BBCA", "side": "buy",
               "broker_ref": "old-ref", "status": "filled"}],
    )

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    fake_broker.place_order.assert_not_called()
    assert update["transactions"][0]["broker_ref"] == "old-ref"
