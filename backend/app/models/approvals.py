from typing import Any
from pydantic import BaseModel


class ApprovalSummary(BaseModel):
    audit_id: str
    intent: str | None
    status: str
    created_at: str
    workspace_id: str


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalSummary]


class ApprovalDetail(BaseModel):
    audit_id: str
    status: str
    intent: str | None
    workspace_id: str
    plan_json: dict[str, Any] | None
    legal_status: str | None
    legal_citations: list[dict[str, Any]]


class ApprovalAction(BaseModel):
    pin: str | None = None
    reason: str | None = None
