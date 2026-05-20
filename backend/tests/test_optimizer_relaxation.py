import pytest

from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import OptimizerInputs


def test_relaxation_drops_max_per_asset_when_otherwise_infeasible() -> None:
    """max_per_asset=0.1 over 2 tickers and min_cash_buffer=0.05 needs Σw=0.95
    but cap allows only 0.2 → infeasible. Relaxation removes max_per_asset."""
    inputs = OptimizerInputs(
        tickers=["BBCA", "BMRI"],
        expected_returns=[0.10, 0.09],
        cov=[[0.04, 0.0], [0.0, 0.04]],
        cash=10_000_000,
        max_per_asset=0.1,
        min_cash_buffer=0.05,
    )
    result, relaxations = solve_with_relaxation(inputs)
    assert result.status == "optimal"
    assert "max_per_asset" in " ".join(relaxations).lower()


def test_relaxation_never_relaxes_forbidden_tickers() -> None:
    """Even after exhausting all relaxations, forbidden tickers stay at 0."""
    inputs = OptimizerInputs(
        tickers=["BBCA", "GGRM"],
        expected_returns=[0.10, 0.50],
        cov=[[0.04, 0.0], [0.0, 0.10]],
        cash=10_000_000,
        forbidden_tickers=["GGRM"],
        max_per_asset=0.5,
        min_cash_buffer=0.05,
    )
    result, _ = solve_with_relaxation(inputs)
    assert result.weights["GGRM"] == pytest.approx(0.0, abs=1e-4)


def test_relaxation_returns_fallback_equal_when_truly_infeasible() -> None:
    """Universe of one forbidden ticker → no feasible allocation possible."""
    inputs = OptimizerInputs(
        tickers=["GGRM"],
        expected_returns=[0.10],
        cov=[[0.04]],
        cash=10_000_000,
        forbidden_tickers=["GGRM"],
        max_per_asset=1.0,
    )
    result, _ = solve_with_relaxation(inputs)
    assert result.status in ("infeasible", "fallback_equal")
