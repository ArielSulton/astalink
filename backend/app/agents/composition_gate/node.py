"""N1b — Composition Gate (allocate_capital only).

Pauses the graph right after Layer 0 decides the cash/stocks/business split,
so the user can approve or reject that composition before the (costlier)
Layer 1 stock analysis + optimizer + legal check run at all. Mirrors
app/agents/hitl/node.py's interrupt() pattern exactly — that node just
sits at a different point in the pipeline (after the plan is fully built,
gating execution) whereas this one gates entry into building the plan."""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from app.agents.state import AgentState, UserApproval
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)


@track_node_duration("n1b_composition_gate")
def composition_gate_node(state: AgentState) -> AgentState:
    try:
        get_admin_client().table("audit_log").update({
            "status": "awaiting_composition_approval",
        }).eq("audit_id", state["audit_id"]).execute()
    except Exception as exc:
        log.error("composition_gate_node: audit_log update failed: %s", exc)

    resume = interrupt({
        "audit_id": state["audit_id"],
        "layer0_result": state.get("layer0_result"),
    })

    approval = resume.get("approval", "rejected")
    return {
        "composition_approval": UserApproval.APPROVED if approval == "approved"
                                else UserApproval.REJECTED,
    }


def composition_rejected_handler(state: AgentState) -> AgentState:
    """User declined the Layer 0 composition — stop here. No Layer 1 stock
    analysis, no optimizer, no legal check ever runs for this turn."""
    msg = (
        "Oke, alokasi ini dibatalkan — tidak ada analisis lanjutan yang dijalankan. "
        "Anda bisa minta analisis baru kapan saja dengan nominal atau kombinasi "
        "saham/bisnis yang berbeda."
    )
    return {"messages": [*state.get("messages", []), AIMessage(content=msg)]}
