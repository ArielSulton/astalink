from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.legal.node import legal_node
from app.agents.state import AgentState
from app.api.deps import get_current_user

router = APIRouter()


class LegalCheckRequest(BaseModel):
    audit_id: str
    workspace_id: str
    allocation_plan: dict[str, Any] = Field(..., description="Proposed allocation to validate.")


class LegalCheckResponse(BaseModel):
    legal_status: str
    legal_citations: list[dict[str, Any]]
    errors: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/check", response_model=LegalCheckResponse)
async def check_legal(
    body: LegalCheckRequest,
    user: dict = Depends(get_current_user),
) -> LegalCheckResponse:
    """Run the Legal Agent in isolation. Used for testing and ad-hoc compliance
    queries; the same node is reused inside the graph in Phase 2."""
    state = AgentState(
        audit_id=body.audit_id,
        messages=[],
        intent=None,
        entities={},
        allocation_plan=body.allocation_plan,
        revision_count=0,
        legal_status=None,
        legal_citations=[],
        user_approval=None,
        transactions=[],
        errors=[],
    )
    update = legal_node(state)
    return LegalCheckResponse(
        legal_status=str(update.get("legal_status", "rejected")),
        legal_citations=update.get("legal_citations", []),
        errors=update.get("errors", []),
    )
