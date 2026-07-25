import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents.composition_gate.resume import resume_composition
from app.agents.graph import graph
from app.agents.state import new_state
from app.api.deps import get_current_user
from app.api.v1.chat import load_thread_history
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client

router = APIRouter()


class AgentRunRequest(BaseModel):
    message: str
    workspace_id: str
    thread_id: str | None = Field(
        default=None,
        description="Pass to continue an existing conversation; omit for a new run.",
    )


class AgentResumeRequest(BaseModel):
    thread_id: str
    workspace_id: str
    approval: Literal["approved", "rejected"]


class AgentRunResponse(BaseModel):
    audit_id: str
    thread_id: str
    intent: str | None
    legal_status: str | None
    user_approval: str | None
    # Layer 0's cash/stocks/business split, business score, and reasoning —
    # without this, the dashboard panel only ever showed the optimizer's
    # stock-only weights and silently dropped the business side of an
    # ALLOCATE_CAPITAL comparison (e.g. "saham BBCA atau modal ke bisnis
    # saya?"), even though layer0_node evaluated it.
    layer0_result: dict[str, Any] | None
    # True while the run is paused at the composition gate (ALLOCATE_CAPITAL
    # only) awaiting a Setuju/Tidak decision — allocation_plan/legal_status
    # are still empty at this point since Layer 1/optimizer/legal haven't
    # run yet. Resume via POST /agent/resume.
    awaiting_composition_approval: bool
    allocation_plan: dict[str, Any] | None
    transactions: list[dict[str, Any]]
    revision_count: int
    messages: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def _serialize_messages(msgs: list) -> list[dict[str, Any]]:
    out = []
    for m in msgs:
        out.append({"type": m.__class__.__name__, "content": getattr(m, "content", "")})
    return out


def _build_response(final: dict[str, Any], thread_id: str) -> AgentRunResponse:
    # graph.invoke() returns normally (no exception) when a node calls
    # interrupt() — the state carries an extra "__interrupt__" key instead of
    # running to a terminal node. Everything computed before the pause
    # (audit_id, intent, layer0_result) is still present in `final`.
    awaiting = bool(final.get("__interrupt__"))
    return AgentRunResponse(
        audit_id=final["audit_id"],
        thread_id=thread_id,
        intent=final.get("intent"),
        legal_status=str(final["legal_status"]) if final.get("legal_status") else None,
        user_approval=str(final["user_approval"]) if final.get("user_approval") else None,
        layer0_result=final.get("layer0_result"),
        awaiting_composition_approval=awaiting,
        allocation_plan=final.get("allocation_plan"),
        transactions=final.get("transactions", []),
        revision_count=final.get("revision_count", 0),
        messages=_serialize_messages(final.get("messages", [])),
        errors=final.get("errors", []),
    )


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
) -> AgentRunResponse:
    # Namespaced by user_sub like chat.py's thread_id, to prevent one user
    # from reading another's checkpointed history via a guessed/shared raw
    # thread_id. The client only ever sees/round-trips the raw part.
    raw_thread = body.thread_id or str(uuid.uuid4())
    thread_id = f"{user['sub']}:{raw_thread}"

    assert_workspace_owned(get_admin_client(), body.workspace_id, user["sub"])

    initial = new_state()
    # Without this, every dashboard message started a brand-new, contextless
    # thread — a follow-up question in the same session got a generic answer
    # with zero awareness of what was just computed/recommended.
    initial["messages"] = [*load_thread_history(thread_id), HumanMessage(content=body.message)]
    initial["_user_id"] = user["sub"]
    initial["_workspace_id"] = body.workspace_id
    initial["_thread_id"] = thread_id
    initial["entities"] = {"workspace_id": body.workspace_id}

    final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

    return _build_response(final, raw_thread)


@router.post("/resume", response_model=AgentRunResponse)
async def resume_agent(
    body: AgentResumeRequest,
    user: dict = Depends(get_current_user),
) -> AgentRunResponse:
    """Resumes a run paused at the composition gate (see
    app.agents.composition_gate.node) — the dashboard's Setuju/Tidak buttons
    call this instead of free-text keyword detection (chat.py/whatsapp.py
    use app.agents.composition_gate.resume.detect_composition_reply for
    that, since those channels are text-only)."""
    assert_workspace_owned(get_admin_client(), body.workspace_id, user["sub"])
    thread_id = f"{user['sub']}:{body.thread_id}"
    final = resume_composition(thread_id, body.approval)
    return _build_response(final, body.thread_id)
