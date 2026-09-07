"""Standalone LangGraph subgraph for business-transaction capture (WhatsApp
and web chat). Deliberately separate from app.agents.graph (the main advisory
pipeline) — see docs/superpowers/specs/2026-09-04-business-pos-automation-design.md's
"Architecture" section for why.

Node order matters and is not arbitrary: extraction runs before the business
question so a message we cannot read never costs the user a choice, and the
pending-row INSERT sits in `stage` — a node that COMPLETES before `confirm`
pauses — because LangGraph replays an interrupted task from the top on
resume. See node.py's stage_node docstring."""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.transaction_capture.node import (
    confirm_node,
    extract_node,
    persist_node,
    rejected_node,
    resolve_business_node,
    stage_node,
)
from app.agents.transaction_capture.state import TransactionCaptureState
from app.core.checkpointer import get_checkpointer


def _route_after_extract(state: TransactionCaptureState) -> Literal["resolve_business", "__end__"]:
    return END if state.get("gate_failed") else "resolve_business"


def _route_after_resolve(state: TransactionCaptureState) -> Literal["stage", "__end__"]:
    return END if state.get("business_cancelled") else "stage"


def _route_after_confirm(state: TransactionCaptureState) -> Literal["persist", "rejected"]:
    return "persist" if state.get("confirmed") else "rejected"


def build_capture_graph():
    g = StateGraph(TransactionCaptureState)
    g.add_node("extract", extract_node)
    g.add_node("resolve_business", resolve_business_node)
    g.add_node("stage", stage_node)
    g.add_node("confirm", confirm_node)
    g.add_node("persist", persist_node)
    g.add_node("rejected", rejected_node)

    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", _route_after_extract, ["resolve_business", END])
    g.add_conditional_edges("resolve_business", _route_after_resolve, ["stage", END])
    g.add_edge("stage", "confirm")
    g.add_conditional_edges("confirm", _route_after_confirm, ["persist", "rejected"])
    g.add_edge("persist", END)
    g.add_edge("rejected", END)

    return g.compile(checkpointer=get_checkpointer())


capture_graph = build_capture_graph()
