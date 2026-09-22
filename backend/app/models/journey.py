from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class SectionState(StrEnum):
    READY = "ready"
    EMPTY = "empty"
    STALE = "stale"
    ERROR = "error"


class FinancialMetric(BaseModel):
    key: Literal["cash_balance", "business_revenue", "portfolio_value"]
    label: str
    value: float | None
    unit: Literal["IDR"] = "IDR"
    state: SectionState
    as_of: datetime | None = None
    source: Literal["workspace", "business_financial_records", "portfolio"]
    change_text: str | None = None


class ReadinessSummary(BaseModel):
    status: Literal["ready", "needs_input", "not_ready", "unavailable"]
    decisive_gaps: list[str] = Field(default_factory=list)
    blocker_codes: list[str] = Field(default_factory=list)
    continuation_href: str = "/allocation"


class AllocationPreview(BaseModel):
    cash: float
    stocks: float
    business: float
    confidence_label: Literal["terbatas", "cukup", "kuat"]
    as_of: datetime
    data_gaps: list[str] = Field(default_factory=list)


class ActivityItem(BaseModel):
    id: str
    kind: Literal["business_transaction", "sandbox_trade", "approval"]
    title: str
    amount: float | None = None
    status: str
    occurred_at: datetime
    href: str


class SectionHealth(BaseModel):
    state: SectionState
    message: str | None = None


class NextAction(BaseModel):
    kind: str
    title: str
    rationale: str
    href: str
    rule_id: str


class JourneyHomeResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    workspace_type: Literal["personal", "business"]
    generated_at: datetime
    financial_snapshot: list[FinancialMetric] = Field(default_factory=list)
    readiness_summary: ReadinessSummary
    next_action: NextAction
    allocation_preview: AllocationPreview | None = None
    recent_activity: list[ActivityItem] = Field(default_factory=list)
    pending_approvals_count: int = 0
    section_health: dict[str, SectionHealth] = Field(default_factory=dict)
