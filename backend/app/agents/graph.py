"""AstaLink LangGraph wiring.

All nodes are real: intent, market, business, risk, optimizer, legal,
hitl (real interrupt-based pause), execution, and a direct Q&A path
for pure informational (EXPLAIN) questions."""
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
from app.agents.business.node import business_node
from app.agents.market.node import market_node
from app.agents.risk.node import risk_node
from app.agents.optimizer.node import optimizer_node
from app.agents.hitl.node import hitl_node
from app.agents.execution.node import execution_node
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
    PORTFOLIO_STATUS has no pipeline yet — the summary node answers honestly."""
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
) -> Literal["n6_hitl", "n5_optimizer", "rejection_handler"]:
    status = state.get("legal_status")
    revisions = state.get("revision_count", 0)

    if status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return "n6_hitl"
    # rejected
    if revisions >= MAX_REVISIONS:
        return "rejection_handler"
    return "n5_optimizer"  # try again with the legal feedback baked in


def _route_after_hitl(state: AgentState) -> Literal["n7_execute", "__end__"]:
    if state.get("user_approval") == UserApproval.APPROVED:
        return "n7_execute"
    return END


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("n1_intent", intent_node)
    g.add_node("n2a_market", market_node)
    g.add_node("n2b_business", business_node)
    g.add_node("n2c_risk", risk_node)
    g.add_node("n5_optimizer", optimizer_node)
    g.add_node("n3_legal", legal_node)
    g.add_node("n6_hitl", hitl_node)
    g.add_node("n7_execute", execution_node)
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
        ["n2a_market", "n2b_business", "n2c_risk", "n8_qa", "n9_summary", END],
    )
    g.add_edge("n8_qa", END)
    g.add_edge("n9_summary", END)

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

    # Conditional after Legal: approve → HITL, reject under cap → loop, reject at cap → terminate
    g.add_conditional_edges(
        "n3_legal",
        _route_after_legal,
        {
            "n6_hitl": "n6_hitl",
            "n5_optimizer": "n5_optimizer",
            "rejection_handler": "rejection_handler",
        },
    )
    g.add_edge("rejection_handler", END)

    # HITL → Execute or END
    g.add_conditional_edges(
        "n6_hitl",
        _route_after_hitl,
        {"n7_execute": "n7_execute", END: END},
    )
    g.add_edge("n7_execute", END)

    return g.compile(checkpointer=get_checkpointer())


# Singleton compiled graph (for the API layer)
graph = build_graph()
