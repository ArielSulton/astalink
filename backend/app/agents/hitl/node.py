"""Human-in-the-Loop gate (N6).

Calls langgraph.types.interrupt(...) which:
1. On first call (no resume value): raises GraphInterrupt — graph pauses,
   checkpointer persists state.
2. On resume call (graph.invoke(Command(resume={...}))): returns the resume
   payload provided by the API layer.

The payload sent on interrupt MUST include audit_id so the dashboard can
deep-link the user to the right approval."""
from __future__ import annotations

import logging

from langgraph.types import interrupt

from app.agents.state import AgentState, LegalStatus, UserApproval
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)


@track_node_duration("n6_hitl")
def hitl_node(state: AgentState) -> AgentState:
    plan = state.get("allocation_plan") or {}
    legal_status = state.get("legal_status")

    try:
        get_admin_client().table("audit_log").update({
            "status": "awaiting_approval",
        }).eq("audit_id", state["audit_id"]).execute()
    except Exception as exc:
        log.error("hitl_node: audit_log update failed: %s", exc)

    resume = interrupt({
        "audit_id": state["audit_id"],
        "allocation_plan": plan,
        "legal_status": (legal_status.value if isinstance(legal_status, LegalStatus)
                         else legal_status),
    })

    approval = resume.get("approval", "rejected")
    return {
        "user_approval": UserApproval.APPROVED if approval == "approved"
                         else UserApproval.REJECTED,
    }
