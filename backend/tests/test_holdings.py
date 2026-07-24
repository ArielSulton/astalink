from unittest.mock import MagicMock

from app.core.holdings import (
    apply_buy,
    apply_sell,
    merged_avg_cost,
    realized_pnl,
)


def test_merged_avg_cost_blends_weighted() -> None:
    # 100 @ 1000 + 100 @ 2000 → 200 @ 1500
    assert merged_avg_cost(100, 1000, 100, 2000) == 1500


def test_merged_avg_cost_from_empty_position() -> None:
    assert merged_avg_cost(0, 0, 50, 3000) == 3000


def test_realized_pnl_gain_and_loss() -> None:
    assert realized_pnl(10, 1200, 1000) == 2000
    assert realized_pnl(10, 800, 1000) == -2000


def _mock_holdings(select_data: list[dict]):
    sb = MagicMock()
    q = MagicMock()
    (q.select.return_value.eq.return_value.eq.return_value
     .limit.return_value.execute.return_value) = MagicMock(data=select_data)
    sb.table.return_value = q
    return sb, q


def test_apply_buy_inserts_new_holding() -> None:
    sb, q = _mock_holdings(select_data=[])
    result = apply_buy(sb, "ws-1", "BBCA", 100, 9000)
    assert result == {"ticker": "BBCA", "quantity": 100, "avg_cost": 9000}
    q.insert.assert_called_once()
    inserted = q.insert.call_args[0][0]
    assert inserted["quantity"] == 100 and inserted["avg_cost"] == 9000


def test_apply_buy_blends_into_existing() -> None:
    sb, q = _mock_holdings(select_data=[{"id": "h1", "quantity": 100, "avg_cost": 9000}])
    result = apply_buy(sb, "ws-1", "BBCA", 100, 11000)
    assert result["quantity"] == 200
    assert result["avg_cost"] == 10000
    q.update.assert_called_once()


def test_apply_sell_partial_updates_quantity() -> None:
    sb = MagicMock()
    q = MagicMock()
    sb.table.return_value = q
    remaining = apply_sell(sb, {"id": "h1", "quantity": 100}, 40)
    assert remaining == 60
    q.update.assert_called_once()
    q.delete.assert_not_called()


def test_apply_sell_full_deletes_holding() -> None:
    sb = MagicMock()
    q = MagicMock()
    sb.table.return_value = q
    remaining = apply_sell(sb, {"id": "h1", "quantity": 100}, 100)
    assert remaining == 0.0
    q.delete.assert_called_once()
