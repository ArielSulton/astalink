import numpy as np
import pytest

from app.agents.risk.mvo import mean_variance_optimize


def test_mvo_two_asset_uncorrelated_equal_means_yields_50_50() -> None:
    """Two assets with identical expected returns and equal variance,
    no correlation → optimal min-variance is 50/50."""
    expected_returns = np.array([0.10, 0.10])
    cov = np.array([[0.04, 0.0], [0.0, 0.04]])
    weights = mean_variance_optimize(
        expected_returns=expected_returns, cov=cov, risk_aversion=1.0,
    )
    assert weights == pytest.approx(np.array([0.5, 0.5]), abs=1e-3)


def test_mvo_returns_sum_to_one_long_only() -> None:
    rng = np.random.default_rng(0)
    er = rng.normal(0.08, 0.03, size=4)
    A = rng.normal(size=(4, 4))
    cov = A @ A.T  # PSD
    w = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=1.0)
    assert pytest.approx(w.sum(), abs=1e-3) == 1.0
    assert (w >= -1e-6).all()


def test_mvo_higher_aversion_increases_diversification() -> None:
    """Higher risk aversion → weights closer to equal."""
    er = np.array([0.20, 0.05])
    cov = np.array([[0.04, 0.0], [0.0, 0.04]])
    w_low = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=0.1)
    w_high = mean_variance_optimize(expected_returns=er, cov=cov, risk_aversion=100.0)
    # Low aversion → tilt to high return; high aversion → near-equal
    assert w_low[0] > w_high[0]
    assert abs(w_high[0] - 0.5) < abs(w_low[0] - 0.5)
