"""CVXPY-based portfolio optimizer.

Solves: maximize μᵀw - λ·wᵀΣw
subject to:
    Σwᵢ + cash_buffer = 1
    wᵢ ≥ 0   (long-only)
    wᵢ ≤ max_per_asset
    wᵢ = 0   for forbidden tickers
    wᵢ ≤ partial_cap   for partial tickers
    Σ wᵢ over sector ≤ sector_cap[sector]
    cash_buffer ≥ min_cash_buffer
"""
from __future__ import annotations

import logging

import cvxpy as cp
import numpy as np

from app.agents.optimizer.schemas import OptimizerInputs, SolverResult
from app.agents.optimizer.sectors import sector_of

log = logging.getLogger(__name__)


def solve(inputs: OptimizerInputs) -> SolverResult:
    n = len(inputs.tickers)
    if n == 0:
        return SolverResult(status="infeasible", message="no tickers in universe")

    mu = np.array(inputs.expected_returns)
    Sigma = np.array(inputs.cov)

    w = cp.Variable(n, nonneg=True)

    # Cash buffer is treated as a fixed reservation: weights must sum to
    # exactly (1 - min_cash_buffer).  This makes the problem fully
    # investable up to the budget and lets the infeasibility test work
    # correctly (if per-asset caps prevent reaching the required sum, the
    # problem is genuinely infeasible).
    invest_budget = 1.0 - inputs.min_cash_buffer

    objective = cp.Maximize(mu @ w - inputs.risk_aversion * cp.quad_form(w, cp.psd_wrap(Sigma)))

    constraints = [
        cp.sum(w) == invest_budget,
        w <= inputs.max_per_asset,
    ]

    # Forbidden tickers = 0
    for i, t in enumerate(inputs.tickers):
        if t in inputs.forbidden_tickers:
            constraints.append(w[i] == 0)
        if t in inputs.partial_tickers:
            constraints.append(w[i] <= inputs.partial_tickers[t])

    # Sector caps
    if inputs.sector_caps:
        sector_indices: dict[str, list[int]] = {}
        for i, t in enumerate(inputs.tickers):
            sector_indices.setdefault(sector_of(t), []).append(i)
        for sector, cap in inputs.sector_caps.items():
            idx = sector_indices.get(sector, [])
            if idx:
                constraints.append(cp.sum(w[idx]) <= cap)

    problem = cp.Problem(objective, constraints)
    try:
        problem.solve()
    except cp.SolverError as exc:
        log.warning("solver: solver error: %s", exc)
        return SolverResult(status="infeasible", message=str(exc))

    if problem.status not in ("optimal", "optimal_inaccurate"):
        return SolverResult(status="infeasible", message=str(problem.status))

    weights = {t: float(w.value[i]) for i, t in enumerate(inputs.tickers)}
    # Clip tiny negative values from numerical noise
    weights = {t: max(v, 0.0) for t, v in weights.items()}
    return SolverResult(
        status="optimal",
        weights=weights,
        objective_value=float(problem.value),
    )
