import numpy as np
import pytest

from app.agents.risk.var import historical_var, parametric_var


def test_historical_var_at_95_is_5th_percentile_of_losses() -> None:
    """VaR_95 = absolute value of the 5th percentile of returns."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0, 0.01, size=10_000)
    var = historical_var(returns, confidence=0.95)
    expected = -float(np.percentile(returns, 5))
    assert var == pytest.approx(expected, rel=1e-6)


def test_parametric_var_assumes_normal_distribution() -> None:
    """For a normal series with σ ≈ 0.01, VaR_95 ≈ 1.6449 * σ."""
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0, 0.01, size=100_000)
    var = parametric_var(returns, confidence=0.95)
    assert var == pytest.approx(1.6449 * np.std(returns, ddof=1), rel=0.05)


def test_var_raises_on_empty_input() -> None:
    with pytest.raises(ValueError):
        historical_var(np.array([]), confidence=0.95)
