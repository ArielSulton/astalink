from unittest.mock import MagicMock, patch

from app.agents.intents import Intent
from app.agents.summary import summary_node
from app.agents.state import new_state


def test_summary_node_portfolio_status_reports_real_cash_balance() -> None:
    """"berapa saldo saya" used to always get the hardcoded "belum tersedia"
    message, even though workspaces.cash_balance has held a real number
    since the sandbox-wallet feature shipped. The reply must include it."""
    state = new_state()
    state["intent"] = Intent.PORTFOLIO_STATUS.value
    state["_workspace_id"] = "ws-1"
    state["messages"] = []

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 987_654_321}])

    with patch("app.agents.summary.get_admin_client", return_value=fake_admin):
        update = summary_node(state)

    reply = update["messages"][-1].content
    assert "987.654.321" in reply
    assert "Asset View" in reply


def test_summary_node_portfolio_status_falls_back_when_workspace_missing() -> None:
    """No _workspace_id (shouldn't normally happen, but defensively) or a
    workspace row that doesn't exist — keep the honest fallback message
    instead of crashing or reporting a bogus balance."""
    state = new_state()
    state["intent"] = Intent.PORTFOLIO_STATUS.value
    state["_workspace_id"] = "ws-missing"
    state["messages"] = []

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])

    with patch("app.agents.summary.get_admin_client", return_value=fake_admin):
        update = summary_node(state)

    reply = update["messages"][-1].content
    assert "belum tersedia" in reply
