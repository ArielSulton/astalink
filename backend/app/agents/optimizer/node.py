"""Allocation Optimizer (N5). Reads market_snapshot + risk_metrics + legal
feedback; calls solver with progressive relaxation; returns updated
allocation_plan with revision_count incremented."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    partial_tickers_from_citations,
    sector_caps_from_citations,
)
from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import (
    AllocationPlan,
    OptimizerInputs,
    WeightLeg,
)
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import record_revision_count, track_node_duration
from app.core.supabase_admin import get_admin_client
from app.core.wallet import get_workspace_balance

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are an allocation strategist. Given solver output (weights + objective),
write ONE short paragraph in Indonesian (≤120 words) explaining the rationale.
Acknowledge any relaxations applied. Do NOT introduce numeric metrics not in
the input."""


# Heuristic mapping from the free-text risk_profile Gemini extracts in N1
# (e.g. "konservatif"/"sedang"/"agresif") to solver constraints. Anything
# unrecognized (including no risk_profile at all) keeps OptimizerInputs'
# own defaults — behavior for a run with no stated preference is unchanged.
_CONSERVATIVE_KEYWORDS = ("konservatif", "rendah", "low", "conservative")
_AGGRESSIVE_KEYWORDS = ("agresif", "tinggi", "high", "aggressive")


def _constraints_from_risk_profile(risk_profile: str | None) -> tuple[float, float]:
    """Returns (max_per_asset, min_cash_buffer)."""
    profile = (risk_profile or "").strip().lower()
    if any(k in profile for k in _CONSERVATIVE_KEYWORDS):
        return 0.25, 0.15
    if any(k in profile for k in _AGGRESSIVE_KEYWORDS):
        return 0.6, 0.0
    return 0.4, 0.05  # OptimizerInputs' own defaults — "sedang"/unstated


def _build_inputs(state: AgentState) -> OptimizerInputs:
    ents = state.get("entities", {})
    tickers = list(ents.get("tickers", []))

    # Naive prior: 8% annual return per ticker. Real prod would derive μ from
    # price history (Phase 3's risk_node already does this for the cov side).
    er = [0.08] * len(tickers)

    # Identity-scaled covariance fallback (variance 0.04 = 20% std dev annual).
    n = len(tickers)
    cov = (np.eye(n) * 0.04).tolist()

    citations = state.get("legal_citations") or []
    max_per_asset, min_cash_buffer = _constraints_from_risk_profile(ents.get("risk_profile"))

    # Cap the requested amount at the workspace's real sandbox balance
    # (Task 4) — entities.amount alone is just a number the LLM parsed out
    # of the chat message, never checked against anything. Default to the
    # full balance when no amount was stated at all.
    requested = ents.get("amount") or 0
    workspace_id = state.get("_workspace_id")
    balance = get_workspace_balance(get_admin_client(), workspace_id) if workspace_id else None
    if balance is None:
        cash = requested
    elif requested:
        cash = min(requested, balance)
    else:
        cash = balance

    return OptimizerInputs(
        tickers=tickers,
        expected_returns=er,
        cov=cov,
        cash=cash,
        forbidden_tickers=forbidden_from_citations(citations),
        partial_tickers=partial_tickers_from_citations(citations),
        sector_caps=sector_caps_from_citations(citations),
        max_per_asset=max_per_asset,
        min_cash_buffer=min_cash_buffer,
    )


@track_node_duration("n5_optimizer")
def optimizer_node(state: AgentState) -> AgentState:
    inputs = _build_inputs(state)
    if not inputs.tickers:
        return {
            "allocation_plan": None,
            "revision_count": state.get("revision_count", 0) + 1,
            "errors": [*state.get("errors", []),
                       {"node": "optimizer", "reason": "no_tickers"}],
        }

    result, relaxations = solve_with_relaxation(inputs)

    legs = [
        WeightLeg(ticker=t, weight=result.weights.get(t, 0.0))
        for t in inputs.tickers
    ]
    cash_buffer = max(0.0, 1.0 - sum(l.weight for l in legs))

    llm = get_chat_model()
    body = (
        f"Tickers + weights: {[(l.ticker, round(l.weight, 3)) for l in legs]}\n"
        f"Solver status: {result.status}\n"
        f"Relaxations applied: {relaxations or 'none'}\n"
        f"Cash buffer: {cash_buffer:.3f}"
    )
    narration = extract_text(llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                            HumanMessage(content=body)]).content)

    plan = AllocationPlan(
        weights=legs,
        cash=inputs.cash,
        cash_buffer=cash_buffer,
        narration=narration,
        relaxations_applied=relaxations,
    )

    record_revision_count(state.get("revision_count", 0) + 1)
    return {
        "allocation_plan": plan.model_dump(),
        "revision_count": state.get("revision_count", 0) + 1,
    }
