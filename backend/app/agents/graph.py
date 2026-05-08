"""AstaLink LangGraph wiring (Phase 3).

Real nodes: intent_node, legal_node, market_node, business_node, risk_node.
Remaining stubs (replaced in later phases): optimizer_stub (Phase 4),
hitl_stub (Phase 5), execution_stub (Phase 6)."""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.intent.node import intent_node
from app.agents.legal.node import legal_node
from app.agents.rejection import rejection_handler
from app.agents.state import AgentState, LegalStatus, UserApproval
from app.agents.business.node import business_node
from app.agents.market.node import market_node
from app.agents.risk.node import risk_node
from app.agents.optimizer.node import optimizer_node
from app.agents.stubs import execution_stub, hitl_stub
from app.core.checkpointer import get_checkpointer

log = logging.getLogger(__name__)

MAX_REVISIONS = 3


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
    g.add_node("n6_hitl", hitl_stub)
    g.add_node("n7_execute", execution_stub)
    g.add_node("rejection_handler", rejection_handler)

    # Linear entry
    g.add_edge(START, "n1_intent")

    # Fan-out to analysis layer
    for analyst in ("n2a_market", "n2b_business", "n2c_risk"):
        g.add_edge("n1_intent", analyst)

    # Join: each analyst → optimizer (LangGraph implicitly waits for all preds)
    for analyst in ("n2a_market", "n2b_business", "n2c_risk"):
        g.add_edge(analyst, "n5_optimizer")

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
