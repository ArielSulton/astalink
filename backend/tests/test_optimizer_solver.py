import numpy as np
import pytest

from app.agents.optimizer.schemas import OptimizerInputs
from app.agents.optimizer.solver import solve


def _basic_inputs(**overrides) -> OptimizerInputs:
    base = dict(
        tickers=["BBCA", "BMRI", "GGRM"],
        expected_returns=[0.10, 0.09, 0.15],
        cov=[[0.04, 0.01, 0.0], [0.01, 0.05, 0.0], [0.0, 0.0, 0.08]],
        cash=10_000_000,
        max_per_asset=0.5,
        min_cash_buffer=0.05,
        risk_aversion=2.0,
    )
    base.update(overrides)
    return OptimizerInputs(**base)


def test_solver_assigns_zero_weight_to_forbidden_ticker() -> None:
    inputs = _basic_inputs(forbidden_tickers=["GGRM"])
    res = solve(inputs)
    assert res.status == "optimal"
    assert res.weights["GGRM"] == pytest.approx(0.0, abs=1e-4)
    # Other tickers absorb GGRM's allocation
    assert res.weights["BBCA"] + res.weights["BMRI"] == pytest.approx(0.95, abs=1e-3)


def test_solver_respects_max_per_asset_cap() -> None:
    inputs = _basic_inputs(tickers=["BBCA", "BMRI"],
                           expected_returns=[0.20, 0.05],
                           cov=[[0.04, 0.0], [0.0, 0.04]],
                           max_per_asset=0.6)
    res = solve(inputs)
    assert res.weights["BBCA"] <= 0.6 + 1e-6


def test_solver_returns_infeasible_when_caps_under_required_sum() -> None:
    """With max_per_asset=0.1 across 2 tickers and min_cash_buffer=0.05,
    weights can't sum to 0.95 → infeasible."""
    inputs = _basic_inputs(tickers=["BBCA", "BMRI"],
                           expected_returns=[0.10, 0.09],
                           cov=[[0.04, 0.0], [0.0, 0.04]],
                           max_per_asset=0.1, min_cash_buffer=0.05)
    res = solve(inputs)
    assert res.status == "infeasible"


def test_solver_partial_ticker_weight_is_capped() -> None:
    inputs = _basic_inputs(partial_tickers={"GGRM": 0.05})
    res = solve(inputs)
    assert res.weights["GGRM"] <= 0.05 + 1e-6
