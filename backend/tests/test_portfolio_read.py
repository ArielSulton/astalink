from unittest.mock import MagicMock

from app.core.portfolio_read import build_portfolio


def _admin() -> MagicMock:
    admin = MagicMock()
    holdings = MagicMock()
    holdings.select.return_value.eq.return_value.execute.return_value.data = [
        {"ticker": "BBCA", "quantity": 100, "avg_cost": 9000},
    ]
    transactions = MagicMock()
    transactions.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    workspaces = MagicMock()
    workspaces.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"cash_balance": 500_000},
    ]
    admin.table.side_effect = lambda name: {
        "holdings": holdings,
        "transactions": transactions,
        "workspaces": workspaces,
    }[name]
    return admin


def test_build_portfolio_marks_holdings_to_market() -> None:
    result = build_portfolio(_admin(), "ws-1", price_loader=lambda _: 10_000)
    assert result.total_market_value == 1_000_000
    assert result.total_equity == 1_500_000


def test_build_portfolio_keeps_unavailable_price_null() -> None:
    result = build_portfolio(_admin(), "ws-1", price_loader=lambda _: None)
    assert result.holdings[0].market_value is None
    assert result.total_market_value is None
    assert result.total_equity is None
