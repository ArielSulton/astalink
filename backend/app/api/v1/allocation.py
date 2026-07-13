"""Layer 0 capital-allocation API.

- intake profile CRUD (B0 schema, per business, evidence-tagged jsonb)
- investor profile CRUD (L0-2 personal constraints, per workspace)
- POST /analyze — runs the Layer 0 decision flow (and, when it allocates
  >0% to stocks, the Layer 1 stock engine) synchronously for the UI.
  This is the read/analysis path only: the execution path (optimizer →
  legal → HITL → broker) still runs exclusively through the agent graph.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.allocation.engine import run_layer0
from app.agents.allocation.node import load_business_profile, load_investor_profile
from app.agents.allocation.schemas import BusinessProfile, InvestorProfile
from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TICKERS = ["BBCA", "TLKM", "ASII", "BBRI"]


def _owned_business(sb, business_id: str, user_id: str) -> dict:
    res = sb.table("businesses").select("*").eq("id", business_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Business not found.")
    business = res.data[0]
    assert_workspace_owned(sb, business["workspace_id"], user_id)
    return business


# --------------------------------------------------------------------------
# Intake profile (B0)
# --------------------------------------------------------------------------

@router.get("/intake/{business_id}", response_model=BusinessProfile)
async def get_intake_profile(
    business_id: str,
    user: dict = Depends(get_current_user),
) -> BusinessProfile:
    sb = get_admin_client()
    _owned_business(sb, business_id, user["sub"])
    res = (sb.table("business_intake_profiles").select("profile")
           .eq("business_id", business_id).limit(1).execute())
    raw = (res.data or [{}])[0].get("profile") or {}
    return BusinessProfile.model_validate(raw)


@router.put("/intake/{business_id}", response_model=BusinessProfile)
async def put_intake_profile(
    business_id: str,
    body: BusinessProfile,
    user: dict = Depends(get_current_user),
) -> BusinessProfile:
    sb = get_admin_client()
    _owned_business(sb, business_id, user["sub"])
    sb.table("business_intake_profiles").upsert(
        {"business_id": business_id, "profile": body.model_dump(mode="json")},
        on_conflict="business_id",
    ).execute()
    return body


# --------------------------------------------------------------------------
# Investor profile (L0-2 inputs)
# --------------------------------------------------------------------------

@router.get("/investor/{workspace_id}", response_model=InvestorProfile)
async def get_investor_profile(
    workspace_id: str,
    user: dict = Depends(get_current_user),
) -> InvestorProfile:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    res = (sb.table("investor_profiles").select("profile")
           .eq("workspace_id", workspace_id).limit(1).execute())
    raw = (res.data or [{}])[0].get("profile") or {}
    return InvestorProfile.model_validate(raw)


@router.put("/investor/{workspace_id}", response_model=InvestorProfile)
async def put_investor_profile(
    workspace_id: str,
    body: InvestorProfile,
    user: dict = Depends(get_current_user),
) -> InvestorProfile:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    sb.table("investor_profiles").upsert(
        {"workspace_id": workspace_id, "profile": body.model_dump(mode="json")},
        on_conflict="workspace_id",
    ).execute()
    return body


# --------------------------------------------------------------------------
# Analyze (Layer 0 → Layer 1)
# --------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    workspace_id: str
    business_id: str | None = None
    tickers: list[str] = Field(default_factory=list)
    amount: float | None = Field(default=None, ge=0)


class AnalyzeResponse(BaseModel):
    layer0: dict
    stock_engine: dict | None = None   # None ⟺ Layer 1 was gated off


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    body: AnalyzeRequest,
    user: dict = Depends(get_current_user),
) -> AnalyzeResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, body.workspace_id, user["sub"])

    business_profile = None
    business_row = None
    if body.business_id:
        business_row = _owned_business(sb, body.business_id, user["sub"])
        _, business_profile = load_business_profile(
            body.workspace_id, business_row["name"])
        if business_profile is None:
            business_profile = BusinessProfile()

    investor = load_investor_profile(body.workspace_id)
    result = run_layer0(investor, business_profile)
    layer0 = {
        **result.model_dump(),
        "business_id": (business_row or {}).get("id"),
        "business_name": (business_row or {}).get("name"),
    }

    engine = None
    if result.allocation is not None and result.allocation.stocks > 0:
        from app.agents.market.news_client import fetch_news
        from app.agents.market.stock_engine import run_stock_engine

        tickers = [t.upper() for t in (body.tickers or DEFAULT_TICKERS)]
        try:
            engine = run_stock_engine(
                tickers,
                news_by_ticker={t: fetch_news(t) for t in tickers},
                total_amount_idr=body.amount,
            )
        except Exception as exc:
            log.error("allocation/analyze: stock engine failed: %s", exc)

    return AnalyzeResponse(layer0=layer0, stock_engine=engine)
