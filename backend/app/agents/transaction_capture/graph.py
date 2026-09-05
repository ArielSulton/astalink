"""Standalone LangGraph subgraph for WhatsApp business-transaction capture.
Deliberately separate from app.agents.graph (the main advisory pipeline) —
see docs/superpowers/specs/2026-09-04-business-pos-automation-design.md's
"Architecture" section for why."""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.transaction_capture.node import (
    confirm_node,
    extract_node,
    persist_node,
    rejected_node,
)
from app.agents.transaction_capture.state import TransactionCaptureState
from app.core.checkpointer import get_checkpointer


def _route_after_extract(state: TransactionCaptureState) -> Literal["confirm", "__end__"]:
    return END if state.get("gate_failed") else "confirm"


def _route_after_confirm(state: TransactionCaptureState) -> Literal["persist", "rejected"]:
    return "persist" if state.get("confirmed") else "rejected"


def build_capture_graph():
    g = StateGraph(TransactionCaptureState)
    g.add_node("extract", extract_node)
    g.add_node("confirm", confirm_node)
    g.add_node("persist", persist_node)
    g.add_node("rejected", rejected_node)

    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", _route_after_extract, ["confirm", END])
    g.add_conditional_edges("confirm", _route_after_confirm, ["persist", "rejected"])
    g.add_edge("persist", END)
    g.add_edge("rejected", END)

    return g.compile(checkpointer=get_checkpointer())


capture_graph = build_capture_graph()
