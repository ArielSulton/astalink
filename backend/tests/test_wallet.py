import pytest
from unittest.mock import MagicMock

from app.core.wallet import debit_workspace_balance, get_workspace_balance


def _mock_admin(select_data: list[dict], update_data: list[dict] | None = None):
    """Fake Supabase admin client: `.table("workspaces").select(...).eq(...)
    .limit(...).execute()` returns `select_data`; `.table("workspaces")
    .update(...).eq(...).gte(...).execute()` returns `update_data`."""
    sb = MagicMock()
    query = MagicMock()
    query.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=select_data)
    query.update.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = \
        MagicMock(data=update_data or [])
    sb.table.return_value = query
    return sb, query


def test_get_workspace_balance_returns_value() -> None:
    sb, _ = _mock_admin(select_data=[{"cash_balance": 500_000_000}])
    assert get_workspace_balance(sb, "ws-1") == 500_000_000.0


def test_get_workspace_balance_returns_none_when_workspace_missing() -> None:
    sb, _ = _mock_admin(select_data=[])
    assert get_workspace_balance(sb, "ws-missing") is None


def test_debit_workspace_balance_succeeds_and_returns_new_balance() -> None:
    sb, query = _mock_admin(
        select_data=[{"cash_balance": 1_000_000_000}],
        update_data=[{"cash_balance": 900_000_000}],
    )
    new_balance = debit_workspace_balance(sb, "ws-1", 100_000_000)
    assert new_balance == 900_000_000.0
    query.update.assert_called_once_with({"cash_balance": 900_000_000.0})


def test_debit_workspace_balance_returns_none_when_insufficient_funds() -> None:
    sb, query = _mock_admin(select_data=[{"cash_balance": 50_000}])
    result = debit_workspace_balance(sb, "ws-1", 100_000)
    assert result is None
    query.update.assert_not_called()


def test_debit_workspace_balance_returns_none_when_concurrent_race_loses() -> None:
    """Balance looked sufficient on read, but the WHERE-guarded UPDATE
    matched zero rows — a concurrent debit spent the funds first."""
    sb, _ = _mock_admin(
        select_data=[{"cash_balance": 1_000_000_000}],
        update_data=[],
    )
    result = debit_workspace_balance(sb, "ws-1", 100_000_000)
    assert result is None


def test_debit_workspace_balance_returns_none_when_workspace_missing() -> None:
    sb, query = _mock_admin(select_data=[])
    result = debit_workspace_balance(sb, "ws-missing", 1)
    assert result is None
    query.update.assert_not_called()


def test_debit_workspace_balance_raises_on_non_positive_amount() -> None:
    sb, _ = _mock_admin(select_data=[{"cash_balance": 1_000_000_000}])
    with pytest.raises(ValueError):
        debit_workspace_balance(sb, "ws-1", 0)


def test_debit_workspace_balance_uses_optimistic_lock_on_current_value() -> None:
    """The UPDATE must be guarded by .eq("cash_balance", current) — not just
    .gte(amount) — so a concurrent debit that already changed the balance
    is detected even if the new balance still individually covers this
    debit's amount."""
    sb, query = _mock_admin(
        select_data=[{"cash_balance": 1_000_000_000}],
        update_data=[{"cash_balance": 900_000_000}],
    )
    debit_workspace_balance(sb, "ws-1", 100_000_000)
    query.update.return_value.eq.return_value.eq.assert_called_once_with(
        "cash_balance", 1_000_000_000,
    )
