from typing import Any

from pydantic import BaseModel, Field


class AuditSummary(BaseModel):
    audit_id: str
    intent: str | None = None
    status: str
    created_at: str
    completed_at: str | None = None


class AuditListResponse(BaseModel):
    audits: list[AuditSummary]


class AuditDetail(BaseModel):
    audit_id: str
    status: str
    intent: str | None = None
    workspace_id: str
    created_at: str
    completed_at: str | None = None
    allocation_plan: dict[str, Any] | None = None
    legal_status: str | None = None
    legal_citations: list[dict[str, Any]] = Field(default_factory=list)
    transactions: list[dict[str, Any]] = Field(default_factory=list)
