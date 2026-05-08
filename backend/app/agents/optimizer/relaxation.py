"""Progressive constraint relaxation. Forbidden tickers are NEVER relaxed
— they reflect hard legal constraints, not soft preferences."""
from __future__ import annotations

import logging

from app.agents.optimizer.schemas import OptimizerInputs, SolverResult
from app.agents.optimizer.solver import solve

log = logging.getLogger(__name__)


def solve_with_relaxation(inputs: OptimizerInputs) -> tuple[SolverResult, list[str]]:
    """Try the strict problem; on infeasibility, drop the softest constraint
    and retry. Returns (result, list of relaxation messages)."""
    relaxations: list[str] = []
    relaxed = inputs

    # Pass 1: strict
    res = solve(relaxed)
    if res.status == "optimal":
        return res, relaxations

    # Pass 2: drop sector caps
    if relaxed.sector_caps:
        relaxations.append("dropped sector_caps")
        relaxed = relaxed.model_copy(update={"sector_caps": {}})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # Pass 3: drop max_per_asset
    if relaxed.max_per_asset < 1.0:
        relaxations.append(f"dropped max_per_asset ({relaxed.max_per_asset} → 1.0)")
        relaxed = relaxed.model_copy(update={"max_per_asset": 1.0})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # Pass 4: drop min_cash_buffer
    if relaxed.min_cash_buffer > 0:
        relaxations.append(f"dropped min_cash_buffer ({relaxed.min_cash_buffer} → 0)")
        relaxed = relaxed.model_copy(update={"min_cash_buffer": 0.0})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # All relaxations exhausted. Last resort: equal weights across non-forbidden tickers.
    allowed = [t for t in inputs.tickers if t not in inputs.forbidden_tickers]
    if not allowed:
        return SolverResult(status="infeasible",
                            message="no allowed tickers after applying forbidden list"), relaxations

    n = len(allowed)
    weights = {t: (1.0 / n if t in allowed else 0.0) for t in inputs.tickers}
    relaxations.append("fallback to equal weights")
    return SolverResult(status="fallback_equal", weights=weights), relaxations
