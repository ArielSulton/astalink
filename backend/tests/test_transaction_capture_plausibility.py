from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.plausibility import compute_plausibility_flag


def _mock_admin(amounts: list[float]) -> MagicMock:
    sb = MagicMock()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = MagicMock(data=[{"amount": a} for a in amounts])
    sb.table.return_value = query
    return sb


def test_plausibility_flags_true_when_not_enough_history() -> None:
    """Fewer than 5 confirmed transactions of this type: not enough history
    to trust a z-score, so this is flagged (not silently trusted) —
    spec-mandated conservative default, not a bug."""
    fake_admin = _mock_admin([10_000.0, 12_000.0])
    with patch("app.agents.transaction_capture.plausibility.get_admin_client", return_value=fake_admin):
        assert compute_plausibility_flag(business_id="biz-1", type_="income", amount=11_000.0) is True


def test_plausibility_flags_false_for_a_typical_amount() -> None:
    history = [10_000.0, 11_000.0, 9_500.0, 10_500.0, 10_200.0, 9_800.0]
    fake_admin = _mock_admin(history)
    with patch("app.agents.transaction_capture.plausibility.get_admin_client", return_value=fake_admin):
        assert compute_plausibility_flag(business_id="biz-1", type_="income", amount=10_300.0) is False


def test_plausibility_flags_true_for_a_wild_outlier() -> None:
    history = [10_000.0, 11_000.0, 9_500.0, 10_500.0, 10_200.0, 9_800.0]
    fake_admin = _mock_admin(history)
    with patch("app.agents.transaction_capture.plausibility.get_admin_client", return_value=fake_admin):
        assert compute_plausibility_flag(business_id="biz-1", type_="income", amount=5_000_000.0) is True


def test_plausibility_handles_zero_stdev_history() -> None:
    history = [10_000.0, 10_000.0, 10_000.0, 10_000.0, 10_000.0]
    fake_admin = _mock_admin(history)
    with patch("app.agents.transaction_capture.plausibility.get_admin_client", return_value=fake_admin):
        assert compute_plausibility_flag(business_id="biz-1", type_="income", amount=10_000.0) is False
        assert compute_plausibility_flag(business_id="biz-1", type_="income", amount=50_000.0) is True
