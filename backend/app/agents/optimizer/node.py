"""Allocation Optimizer (N5). Reads market_snapshot + risk_metrics + legal
feedback; calls solver with progressive relaxation; returns updated
allocation_plan with revision_count incremented."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    sector_caps_from_citations,
)
from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import (
    AllocationPlan,
    OptimizerInputs,
    WeightLeg,
)
from app.agents.state import AgentState
from app.core.gemini import get_chat_model
from app.core.metrics import record_revision_count, track_node_duration

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are an allocation strategist. Given solver output (weights + objective),
write ONE short paragraph in Indonesian (≤120 words) explaining the rationale.
Acknowledge any relaxations applied. Do NOT introduce numeric metrics not in
the input."""


def _build_inputs(state: AgentState) -> OptimizerInputs:
    ents = state.get("entities", {})
    tickers = list(ents.get("tickers", []))

    # Naive prior: 8% annual return per ticker. Real prod would derive μ from
    # price history (Phase 3's risk_node already does this for the cov side).
    er = [0.08] * len(tickers)

    # Identity-scaled covariance fallback (variance 0.04 = 20% std dev annual).
    n = len(tickers)
    cov = (np.eye(n) * 0.04).tolist()

    return OptimizerInputs(
        tickers=tickers,
        expected_returns=er,
        cov=cov,
        cash=ents.get("amount", 0),
        forbidden_tickers=forbidden_from_citations(state.get("legal_citations") or []),
        sector_caps=sector_caps_from_citations(state.get("legal_citations") or []),
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
    narration = llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                            HumanMessage(content=body)]).content or ""

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
