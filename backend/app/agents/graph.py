"""AstaLink LangGraph wiring.

Advisory mode: intent, market, business, risk, optimizer, legal — the
pipeline produces a comprehensive report and recommendations. No automatic
execution: the user retains full control over allocation decisions."""
from __future__ import annotations

import logging
from typing import Literal, Sequence

from langgraph.graph import END, START, StateGraph

from app.agents.intent.node import intent_node
from app.agents.intents import Intent
from app.agents.legal.node import legal_node
from app.agents.qa import qa_node
from app.agents.rejection import rejection_handler
from app.agents.summary import summary_node
from app.agents.state import AgentState, LegalStatus, UserApproval
from app.agents.allocation.node import layer0_node
from app.agents.business.node import business_node
from app.agents.composition_gate.node import (
    composition_gate_node,
    composition_rejected_handler,
)
from app.agents.market.node import market_node
from app.agents.risk.node import risk_node
from app.agents.optimizer.node import optimizer_node

from app.core.checkpointer import get_checkpointer

log = logging.getLogger(__name__)

MAX_REVISIONS = 3


def _route_after_intent(
    state: AgentState,
) -> str | Sequence[str]:
    """Skip the whole optimizer/legal pipeline when N1 couldn't confidently
    classify the message — there are no entities to build an allocation
    from, so proceeding always dead-ends in optimizer's no_tickers /
    legal's empty_retrieval after burning a full revision loop.

    EXPLAIN is a pure informational question: route it to the direct Q&A
    node — there is nothing to optimize, legally validate, or approve.

    EVALUATE_BUSINESS / RISK_REVIEW only need their own analyst; they end at
    the summary node instead of falling through the optimizer/legal loop
    (which used to produce a wrong "rejected legally" reply for them).
    PORTFOLIO_STATUS has no pipeline yet — the summary node answers honestly.

    Allocation intents (ALLOCATE_STOCKS / ALLOCATE_CAPITAL) go through Layer 0
    (l0_allocation) FIRST for initial analysis, then fan out to all analysts
    for a complete advisory report."""
    if state.get("_needs_clarification"):
        return END
    intent = state.get("intent")
    if intent == Intent.EXPLAIN.value:
        return "n8_qa"
    if intent == Intent.EVALUATE_BUSINESS.value:
        return ["n2b_business"]
    if intent == Intent.RISK_REVIEW.value:
        return ["n2c_risk"]
    if intent == Intent.PORTFOLIO_STATUS.value:
        return "n9_summary"
    return "l0_allocation"


def _route_after_layer0(state: AgentState) -> str | Sequence[str]:
    """Layer 1 (the stock engine fan-out) runs unless Layer 0 returned
    INSUFFICIENT_DATA — in that case l0_allocation already appended the
    user-facing message asking for more info.

    ALLOCATE_CAPITAL (a real business-vs-stocks comparison) pauses at the
    composition gate first — the user explicitly approves/rejects Layer 0's
    cash/stocks/business split before the costlier stock analysis + optimizer
    run. Plain ALLOCATE_STOCKS requests skip the gate and fan out immediately
    (no business in the picture, nothing extra to confirm).

    When L0 recommends 0% stocks, the fan-out STILL runs so the user
    gets a complete advisory report and can decide for themselves."""
    result = state.get("layer0_result") or {}
    if result.get("status") == "insufficient_data":
        return END
    if state.get("intent") == Intent.ALLOCATE_CAPITAL.value:
        return "n1b_composition_gate"
    return ["n2a_market", "n2b_business", "n2c_risk"]


def _route_after_composition_gate(
    state: AgentState,
) -> Literal["composition_rejected_handler", "n2a_market", "n2b_business", "n2c_risk"] | Sequence[str]:
    if state.get("composition_approval") != UserApproval.APPROVED:
        return "composition_rejected_handler"
    return ["n2a_market", "n2b_business", "n2c_risk"]


def _route_after_business(state: AgentState) -> Literal["n9_summary", "n5_optimizer"]:
    if state.get("intent") == Intent.EVALUATE_BUSINESS.value:
        return "n9_summary"
    return "n5_optimizer"


def _route_after_risk(state: AgentState) -> Literal["n9_summary", "n5_optimizer"]:
    if state.get("intent") == Intent.RISK_REVIEW.value:
        return "n9_summary"
    return "n5_optimizer"


def _route_after_legal(
    state: AgentState,
) -> Literal["__end__", "n5_optimizer", "rejection_handler"]:
    """Advisory mode: after legal validation, the pipeline ends with a
    report. No HITL approval or automatic execution — the user decides."""
    status = state.get("legal_status")
    revisions = state.get("revision_count", 0)

    if status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return END
    # rejected
    if revisions >= MAX_REVISIONS:
        return "rejection_handler"
    return "n5_optimizer"  # try again with the legal feedback baked in


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("n1_intent", intent_node)
    g.add_node("l0_allocation", layer0_node)
    g.add_node("n1b_composition_gate", composition_gate_node)
    g.add_node("composition_rejected_handler", composition_rejected_handler)
    g.add_node("n2a_market", market_node)
    g.add_node("n2b_business", business_node)
    g.add_node("n2c_risk", risk_node)
    g.add_node("n5_optimizer", optimizer_node)
    g.add_node("n3_legal", legal_node)

    g.add_node("n8_qa", qa_node)
    g.add_node("n9_summary", summary_node)
    g.add_node("rejection_handler", rejection_handler)

    # Linear entry
    g.add_edge(START, "n1_intent")

    # Fan-out to analysis layer — unless N1 couldn't classify the message
    # (END with clarification question), the message is a pure question
    # (answer directly via n8_qa), or it's an analysis-only intent that ends
    # at the summary node.
    g.add_conditional_edges(
        "n1_intent",
        _route_after_intent,
        ["l0_allocation", "n2b_business", "n2c_risk", "n8_qa", "n9_summary", END],
    )
    g.add_edge("n8_qa", END)
    g.add_edge("n9_summary", END)

    # Layer 0 gates Layer 1: the stock fan-out only runs when Layer 0
    # allocated >0% to stocks; otherwise the run ends with L0's own message.
    # ALLOCATE_CAPITAL detours through the composition gate first.
    g.add_conditional_edges(
        "l0_allocation",
        _route_after_layer0,
        ["n1b_composition_gate", "n2a_market", "n2b_business", "n2c_risk", END],
    )

    # Composition gate: paused via interrupt() in composition_gate_node.
    # Approved → the same analyst fan-out as a plain ALLOCATE_STOCKS run.
    # Rejected → stop immediately, no Layer 1/optimizer/legal at all.
    g.add_conditional_edges(
        "n1b_composition_gate",
        _route_after_composition_gate,
        ["composition_rejected_handler", "n2a_market", "n2b_business", "n2c_risk"],
    )
    g.add_edge("composition_rejected_handler", END)

    # Join: analysts → optimizer for the allocation flow (LangGraph implicitly
    # waits for all activated preds). Business/risk detour to the summary node
    # when they ARE the requested analysis rather than allocation inputs.
    g.add_edge("n2a_market", "n5_optimizer")
    g.add_conditional_edges(
        "n2b_business",
        _route_after_business,
        {"n9_summary": "n9_summary", "n5_optimizer": "n5_optimizer"},
    )
    g.add_conditional_edges(
        "n2c_risk",
        _route_after_risk,
        {"n9_summary": "n9_summary", "n5_optimizer": "n5_optimizer"},
    )

    # Optimizer → Legal (the bottleneck)
    g.add_edge("n5_optimizer", "n3_legal")

    # Advisory mode: legal validation ends the pipeline with a report.
    # No HITL approval or automatic execution.
    g.add_conditional_edges(
        "n3_legal",
        _route_after_legal,
        {
            END: END,
            "n5_optimizer": "n5_optimizer",
            "rejection_handler": "rejection_handler",
        },
    )
    g.add_edge("rejection_handler", END)

    return g.compile(checkpointer=get_checkpointer())


# Singleton compiled graph (for the API layer)
graph = build_graph()
