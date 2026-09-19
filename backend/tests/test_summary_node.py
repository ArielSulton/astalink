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


def test_summary_node_portfolio_status_reply_is_composed() -> None:
    from app.agents.intents import Intent
    from app.agents.state import new_state
    from app.agents.summary import summary_node

    state = new_state()
    state["intent"] = Intent.PORTFOLIO_STATUS.value
    state["_workspace_id"] = "ws-1"
    state["messages"] = []

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 987_654_321}])

    with patch("app.agents.summary.get_admin_client", return_value=fake_admin), \
         patch("app.agents.summary.load_snapshot"), \
         patch("app.agents.summary.compose_dead_end_reply",
               return_value="Saldo Rp 987.654.321. Buka Asset View?") as compose:
        update = summary_node(state)

    assert update["messages"][-1].content == "Saldo Rp 987.654.321. Buka Asset View?"
    kwargs = compose.call_args.kwargs
    assert kwargs["reason"].value == "portfolio_status_unavailable"
    assert "987.654.321" in str(kwargs["facts"])


def test_summary_node_business_not_found_reply_is_composed() -> None:
    from app.agents.intents import Intent
    from app.agents.state import new_state
    from app.agents.summary import summary_node

    state = new_state()
    state["intent"] = Intent.EVALUATE_BUSINESS.value
    state["_workspace_id"] = "ws-1"
    state["messages"] = []
    state["errors"] = [{"node": "business", "reason": "no_matching_business"}]

    with patch("app.agents.summary.load_snapshot"), \
         patch("app.agents.summary.compose_dead_end_reply",
               return_value="Bisnisnya belum terdaftar. Mau daftarkan?") as compose:
        update = summary_node(state)

    assert update["messages"][-1].content == "Bisnisnya belum terdaftar. Mau daftarkan?"
    assert compose.call_args.kwargs["reason"].value == "business_not_found"
