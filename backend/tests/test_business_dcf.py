import pytest
from app.agents.business.dcf import discounted_cash_flow


def test_dcf_zero_growth_zero_terminal_matches_perpetuity_formula() -> None:
    """5-year FCF of 1M each, discount=10%, terminal_growth=0:
    PV ≈ Σ 1M/(1.1^t) for t=1..5 + (1M/0.10)/(1.1^5)."""
    cashflows = [1_000_000] * 5
    result = discounted_cash_flow(
        cashflows=cashflows, discount_rate=0.10, terminal_growth=0.0,
    )
    expected = sum(1_000_000 / (1.10 ** t) for t in range(1, 6))
    expected += (1_000_000 / 0.10) / (1.10 ** 5)
    assert result == pytest.approx(expected, rel=1e-6)


def test_dcf_with_terminal_growth_uses_gordon_model() -> None:
    """terminal value = FCF_n*(1+g)/(r-g), discounted from year n."""
    cashflows = [1_000_000, 1_100_000, 1_210_000]  # 10% growth
    r, g = 0.10, 0.03
    result = discounted_cash_flow(
        cashflows=cashflows, discount_rate=r, terminal_growth=g,
    )
    # Validate by recomputing inline; this guards against off-by-one in years
    pv = sum(c / (1 + r) ** t for t, c in enumerate(cashflows, start=1))
    tv = cashflows[-1] * (1 + g) / (r - g)
    pv += tv / (1 + r) ** len(cashflows)
    assert result == pytest.approx(pv, rel=1e-6)


def test_dcf_raises_when_discount_le_growth() -> None:
    """Gordon model degenerates when r ≤ g; we must reject not silently swallow."""
    with pytest.raises(ValueError, match="discount_rate must be greater than terminal_growth"):
        discounted_cash_flow(cashflows=[100], discount_rate=0.05, terminal_growth=0.10)
