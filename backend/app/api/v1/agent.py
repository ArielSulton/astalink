import uuid
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents.graph import graph
from app.agents.state import new_state
from app.api.deps import get_current_user

router = APIRouter()


class AgentRunRequest(BaseModel):
    message: str
    workspace_id: str
    thread_id: str | None = Field(
        default=None,
        description="Pass to continue an existing conversation; omit for a new run.",
    )


class AgentRunResponse(BaseModel):
    audit_id: str
    thread_id: str
    intent: str | None
    legal_status: str | None
    user_approval: str | None
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


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
) -> AgentRunResponse:
    thread_id = body.thread_id or str(uuid.uuid4())

    initial = new_state()
    initial["messages"] = [HumanMessage(content=body.message)]
    initial["_user_id"] = user["sub"]            # type: ignore[misc]
    initial["_workspace_id"] = body.workspace_id  # type: ignore[misc]
    initial["entities"] = {"workspace_id": body.workspace_id}

    final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

    return AgentRunResponse(
        audit_id=final["audit_id"],
        thread_id=thread_id,
        intent=final.get("intent"),
        legal_status=str(final["legal_status"]) if final.get("legal_status") else None,
        user_approval=str(final["user_approval"]) if final.get("user_approval") else None,
        allocation_plan=final.get("allocation_plan"),
        transactions=final.get("transactions", []),
        revision_count=final.get("revision_count", 0),
        messages=_serialize_messages(final.get("messages", [])),
        errors=final.get("errors", []),
    )
