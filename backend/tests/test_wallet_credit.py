import pytest
from unittest.mock import MagicMock

from app.core.wallet import credit_workspace_balance


def _mock_admin(select_data: list[dict], update_data: list[dict] | None = None):
    sb = MagicMock()
    query = MagicMock()
    query.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=select_data)
    query.update.return_value.eq.return_value.eq.return_value.execute.return_value = \
        MagicMock(data=update_data or [])
    sb.table.return_value = query
    return sb, query


def test_credit_increments_balance() -> None:
    sb, query = _mock_admin(
        select_data=[{"cash_balance": 900_000_000}],
        update_data=[{"cash_balance": 950_000_000}],
    )
    new = credit_workspace_balance(sb, "ws-1", 50_000_000)
    assert new == 950_000_000.0
    query.update.assert_called_once_with({"cash_balance": 950_000_000.0})


def test_credit_uses_optimistic_lock_on_current_value() -> None:
    sb, query = _mock_admin(
        select_data=[{"cash_balance": 900_000_000}],
        update_data=[{"cash_balance": 950_000_000}],
    )
    credit_workspace_balance(sb, "ws-1", 50_000_000)
    query.update.return_value.eq.return_value.eq.assert_called_once_with(
        "cash_balance", 900_000_000,
    )


def test_credit_returns_none_when_workspace_missing() -> None:
    sb, query = _mock_admin(select_data=[])
    assert credit_workspace_balance(sb, "ws-missing", 1) is None
    query.update.assert_not_called()


def test_credit_returns_none_on_lost_race() -> None:
    sb, _ = _mock_admin(select_data=[{"cash_balance": 900_000_000}], update_data=[])
    assert credit_workspace_balance(sb, "ws-1", 50_000_000) is None


def test_credit_raises_on_non_positive_amount() -> None:
    sb, _ = _mock_admin(select_data=[{"cash_balance": 1}])
    with pytest.raises(ValueError):
        credit_workspace_balance(sb, "ws-1", 0)
