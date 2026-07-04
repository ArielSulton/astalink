"""Mean-Variance Optimization via scipy.optimize.

Solves: maximize w'μ - λ·w'Σw subject to Σwᵢ = 1, wᵢ ≥ 0.
λ = risk_aversion (higher → more diversification)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def mean_variance_optimize(
    *,
    expected_returns: np.ndarray,
    cov: np.ndarray,
    risk_aversion: float = 1.0,
) -> np.ndarray:
    n = len(expected_returns)
    # np.cov() degenerates to a 0-d scalar (not a 1x1 matrix) when there's
    # only one asset — e.g. risk_node filtering down to a single ticker with
    # sufficient price history. atleast_2d makes w @ cov @ w work for n=1
    # the same way it does for n>1; a no-op when cov is already 2-D.
    cov = np.atleast_2d(cov)

    def neg_utility(w: np.ndarray) -> float:
        return -(w @ expected_returns - risk_aversion * w @ cov @ w)

    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    res = minimize(neg_utility, x0, method="SLSQP", bounds=bounds, constraints=cons)
    if not res.success:
        # Fall back to equal weights with a warning rather than crashing the graph.
        return x0
    return res.x
