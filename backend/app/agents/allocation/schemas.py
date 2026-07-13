"""Layer 0 (capital allocation) schemas.

Core idea: every business-profile field carries an evidence tag. UNKNOWN is
a first-class value — it is never coerced to a default, never interpolated,
and never silently scored. Downstream scoring weights CLAIMED substantially
below VERIFIED (see core/allocation_config.py EvidenceWeights).
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class EvidenceTag(StrEnum):
    VERIFIED = "verified"     # backed by a document (bank statement, contract)
    CLAIMED = "claimed"       # stated by the business owner only
    ESTIMATED = "estimated"   # derived/inferred
    UNKNOWN = "unknown"       # missing


class Tagged(BaseModel, Generic[T]):
    """A value + its evidence tag. `value is None` ⟺ tag is UNKNOWN."""
    value: T | None = None
    evidence: EvidenceTag = EvidenceTag.UNKNOWN

    @property
    def known(self) -> bool:
        return self.evidence != EvidenceTag.UNKNOWN and self.value is not None


class BusinessStage(StrEnum):
    IDEA = "idea"
    PRE_REVENUE = "pre_revenue"
    EARLY_REVENUE = "early_revenue"
    PROFITABLE = "profitable"
    SCALING = "scaling"


class DealInstrument(StrEnum):
    EQUITY = "equity"
    LOAN = "loan"
    CONVERTIBLE = "convertible"
    PROFIT_SHARE = "profit_share"


class CapitalPurpose(StrEnum):
    """Q5 classification — hard rules, not heuristics."""
    GROWTH = "growth"       # marketing, inventory, capacity → may be legitimate
    SURVIVAL = "survival"   # payroll, keeping lights on → bailout → REJECT
    DEBT = "debt"           # repaying creditors → pass-through → REJECT
    UNCLEAR = "unclear"     # no itemized breakdown → REJECT


# --------------------------------------------------------------------------
# B0 intake profile — one block per spec table
# --------------------------------------------------------------------------

class IdentityBlock(BaseModel):
    sector: Tagged[str] = Field(default_factory=Tagged)
    business_model: Tagged[str] = Field(default_factory=Tagged)
    b2b_or_b2c: Tagged[str] = Field(default_factory=Tagged)
    location: Tagged[str] = Field(default_factory=Tagged)


class CurrentStateBlock(BaseModel):
    stage: Tagged[BusinessStage] = Field(default_factory=Tagged)
    age_months: Tagged[int] = Field(default_factory=Tagged)
    headcount: Tagged[int] = Field(default_factory=Tagged)


class TractionBlock(BaseModel):
    monthly_revenue: Tagged[list[float]] = Field(default_factory=Tagged)  # last 12
    growth_rate: Tagged[float] = Field(default_factory=Tagged)
    gross_margin: Tagged[float] = Field(default_factory=Tagged)
    customer_count: Tagged[int] = Field(default_factory=Tagged)
    retention_rate: Tagged[float] = Field(default_factory=Tagged)


class UnitEconomicsBlock(BaseModel):
    price: Tagged[float] = Field(default_factory=Tagged)
    cogs_per_unit: Tagged[float] = Field(default_factory=Tagged)
    cac: Tagged[float] = Field(default_factory=Tagged)
    ltv: Tagged[float] = Field(default_factory=Tagged)
    contribution_margin: Tagged[float] = Field(default_factory=Tagged)
    payback_months: Tagged[float] = Field(default_factory=Tagged)


class CashBlock(BaseModel):
    cash_on_hand: Tagged[float] = Field(default_factory=Tagged)
    monthly_burn: Tagged[float] = Field(default_factory=Tagged)
    runway_months: Tagged[float] = Field(default_factory=Tagged)
    is_profitable: Tagged[bool] = Field(default_factory=Tagged)


class CapitalNeedItem(BaseModel):
    purpose: str
    amount: float


class CapitalNeedBlock(BaseModel):
    amount: Tagged[float] = Field(default_factory=Tagged)
    breakdown: Tagged[list[CapitalNeedItem]] = Field(default_factory=Tagged)
    consequence_if_unfunded: Tagged[str] = Field(default_factory=Tagged)


class DealStructureBlock(BaseModel):
    instrument: Tagged[DealInstrument] = Field(default_factory=Tagged)
    ownership_pct: Tagged[float] = Field(default_factory=Tagged)
    interest_rate: Tagged[float] = Field(default_factory=Tagged)


class UserRoleBlock(BaseModel):
    operator_or_passive: Tagged[str] = Field(default_factory=Tagged)
    hours_per_week: Tagged[float] = Field(default_factory=Tagged)


class ControlBlock(BaseModel):
    ownership_pct: Tagged[float] = Field(default_factory=Tagged)
    veto_rights: Tagged[bool] = Field(default_factory=Tagged)
    shareholder_agreement_exists: Tagged[bool] = Field(default_factory=Tagged)


class ExitBlock(BaseModel):
    mechanism: Tagged[str] = Field(default_factory=Tagged)
    expected_timeline_months: Tagged[int] = Field(default_factory=Tagged)


class TeamBlock(BaseModel):
    operator_identity: Tagged[str] = Field(default_factory=Tagged)
    track_record: Tagged[str] = Field(default_factory=Tagged)
    founder_capital_contributed: Tagged[float] = Field(default_factory=Tagged)


class BusinessProfile(BaseModel):
    """The full B0 intake schema. All fields default to UNKNOWN."""
    identity: IdentityBlock = Field(default_factory=IdentityBlock)
    current_state: CurrentStateBlock = Field(default_factory=CurrentStateBlock)
    traction: TractionBlock = Field(default_factory=TractionBlock)
    unit_economics: UnitEconomicsBlock = Field(default_factory=UnitEconomicsBlock)
    cash: CashBlock = Field(default_factory=CashBlock)
    capital_need: CapitalNeedBlock = Field(default_factory=CapitalNeedBlock)
    deal_structure: DealStructureBlock = Field(default_factory=DealStructureBlock)
    user_role: UserRoleBlock = Field(default_factory=UserRoleBlock)
    control: ControlBlock = Field(default_factory=ControlBlock)
    exit: ExitBlock = Field(default_factory=ExitBlock)
    team: TeamBlock = Field(default_factory=TeamBlock)

    def iter_fields(self) -> list[tuple[str, Tagged[Any]]]:
        """Flat (dotted_name, Tagged) list over every leaf field."""
        out: list[tuple[str, Tagged[Any]]] = []
        for block_name in type(self).model_fields:
            block = getattr(self, block_name)
            for field_name in type(block).model_fields:
                out.append((f"{block_name}.{field_name}",
                            getattr(block, field_name)))
        return out


# --------------------------------------------------------------------------
# L0-2 investor constraints (per workspace, user-entered)
# --------------------------------------------------------------------------

class InvestorProfile(BaseModel):
    """Personal financial-constraint inputs for L0-2. None = not provided —
    a missing answer blocks the related check from passing silently."""
    monthly_expenses: float | None = None
    emergency_fund: float | None = None
    capital_is_borrowed: bool | None = None
    horizon_months: float | None = None       # when is this money needed?
    net_worth: float | None = None
    consumer_debt_interest_pct: float | None = None  # highest-rate debt
    available_hours_per_week: float | None = None
    knows_sector: bool | None = None   # info edge for STEP 4 premiums


class VetoFlag(BaseModel):
    code: str            # e.g. "EMERGENCY_FUND", "BORROWED_CAPITAL"
    target: str          # "business" | "stocks" | "both"
    reason: str
    hard: bool = True    # hard veto vs advisory flag (CAPACITY_MISMATCH)


class ConstraintResult(BaseModel):
    """L0-2 output. Vetoes are absolute — not overridden by any score."""
    veto_flags: list[VetoFlag] = Field(default_factory=list)
    max_allocation_business: float = 1.0   # ceiling %, 0.0..1.0
    force_cash: bool = False
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Layer 0 result
# --------------------------------------------------------------------------

class IntakeQuestion(BaseModel):
    field: str        # dotted field name in BusinessProfile
    question: str     # Indonesian, user-facing
    priority: int     # 1 = highest signal


class CompletenessTier(StrEnum):
    INSUFFICIENT = "insufficient"   # < 0.40 → stop
    PARTIAL = "partial"             # 0.40..0.70 → confidence capped
    OK = "ok"                       # > 0.70


class Layer0Status(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"  # valid terminal output, not an error
    ALLOCATED = "allocated"


class AllocationSplit(BaseModel):
    """The answer is an allocation, never a binary verdict. Sums to 1.0."""
    cash: float
    stocks: float
    business: float


class Layer0Result(BaseModel):
    status: Layer0Status
    allocation: AllocationSplit | None = None
    confidence: int = 0                        # 0-100, capped by completeness
    confidence_label: str = "LOW"              # LOW / MEDIUM / HIGH
    completeness: float = 0.0
    completeness_tier: CompletenessTier = CompletenessTier.INSUFFICIENT
    questions: list[IntakeQuestion] = Field(default_factory=list)  # blockers
    veto_flags: list[VetoFlag] = Field(default_factory=list)
    business_score: float | None = None        # 0-100 after adjustments
    stock_score: float | None = None           # Layer 1 output, if it ran
    baseline_score: float | None = None        # boring alternative, always shown
    quality: dict[str, Any] | None = None      # Q1-Q5 detail
    devils_advocate: list[dict[str, Any]] = Field(default_factory=list)  # DB1-DB7
    why_not_all_stocks: str = ""
    why_not_all_business: str = ""
    rejected_reasons: list[str] = Field(default_factory=list)  # STEP 2 hard rejects
    narration: str = ""
