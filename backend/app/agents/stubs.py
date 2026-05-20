"""Placeholder nodes for Phase 2 graph wiring. Each is a deliberate stub that
exists so the graph compiles end-to-end; real implementations land in:
- N2a/b/c → Phase 3
- N5 → Phase 4
- N6 → Phase 5 (replaces auto-approve with real interrupt)
- N7 → Phase 6
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.state import AgentState, UserApproval

log = logging.getLogger(__name__)


def market_stub(state: AgentState) -> AgentState:
    log.info("[stub] market_stub: tickers=%s", state.get("entities", {}).get("tickers"))
    snapshot = {"tickers": state.get("entities", {}).get("tickers", []),
                "note": "stubbed — real Phase 3 N2a not wired yet"}
    return {"entities": {**state.get("entities", {}), "market_snapshot": snapshot}}


def business_stub(state: AgentState) -> AgentState:
    log.info("[stub] business_stub")
    return {"entities": {**state.get("entities", {}),
                         "business_valuation": {"note": "stubbed"}}}


def risk_stub(state: AgentState) -> AgentState:
    log.info("[stub] risk_stub")
    return {"entities": {**state.get("entities", {}),
                         "risk_metrics": {"var_95": None, "note": "stubbed"}}}


def optimizer_stub(state: AgentState) -> AgentState:
    """Builds a trivial uniform-weight plan from entities.tickers and
    increments revision_count. Real CVXPY solver lands in Phase 4."""
    tickers = state.get("entities", {}).get("tickers") or ["BBCA"]
    cash = state.get("entities", {}).get("amount", 0)
    n = len(tickers)
    plan: dict[str, Any] = {
        "weights": [{"ticker": t, "weight": 1.0 / n} for t in tickers],
        "cash": cash,
        "note": "stubbed uniform allocation",
    }
    return {
        "allocation_plan": plan,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def hitl_stub(state: AgentState) -> AgentState:
    """Auto-approves so Phase 2 graphs traverse end-to-end. Phase 5 replaces
    this with langgraph.types.interrupt()."""
    log.warning("[stub] hitl_stub: auto-approving (Phase 5 will gate this)")
    return {"user_approval": UserApproval.APPROVED}


def execution_stub(state: AgentState) -> AgentState:
    """Writes simulated transactions to state. Real broker integration in Phase 6."""
    log.info("[stub] execution_stub: simulating fills")
    plan = state.get("allocation_plan") or {}
    fills = []
    for leg in plan.get("weights", []):
        fills.append({
            "ticker": leg.get("ticker"),
            "weight": leg.get("weight"),
            "status": "simulated",
        })
    return {"transactions": fills}
