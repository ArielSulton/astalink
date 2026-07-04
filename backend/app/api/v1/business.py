from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client

router = APIRouter()


class BusinessCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    workspace_id: str


class BusinessOut(BaseModel):
    id: str
    name: str
    industry: str | None
    description: str | None
    created_at: str


class FinancialRecordCreateRequest(BaseModel):
    period_year: int = Field(..., ge=1900, le=2100)
    aset: float = Field(..., ge=0)
    omset: float = Field(..., ge=0)
    profit: float


class FinancialRecordOut(BaseModel):
    id: str
    period_year: int
    aset: float
    omset: float
    profit: float


class BusinessDetailOut(BusinessOut):
    financial_records: list[FinancialRecordOut]


def _get_owned_business(sb, business_id: str, user_id: str) -> dict:
    res = sb.table("businesses").select("*").eq("id", business_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Business not found.")
    business = res.data[0]
    assert_workspace_owned(sb, business["workspace_id"], user_id)
    return business


@router.post("", response_model=BusinessOut)
async def create_business(
    body: BusinessCreateRequest,
    user: dict = Depends(get_current_user),
) -> BusinessOut:
    sb = get_admin_client()
    assert_workspace_owned(sb, body.workspace_id, user["sub"])
    row = (
        sb.table("businesses")
        .insert({
            "workspace_id": body.workspace_id,
            "name": body.name.strip(),
            "industry": (body.industry or "").strip() or None,
            "description": (body.description or "").strip() or None,
        })
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=500, detail="Failed to create business.")
    return BusinessOut(**row.data[0])


@router.get("", response_model=list[BusinessOut])
async def list_businesses(
    workspace_id: str = Query(...),
    user: dict = Depends(get_current_user),
) -> list[BusinessOut]:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    res = (
        sb.table("businesses").select("id,name,industry,description,created_at")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [BusinessOut(**row) for row in (res.data or [])]


@router.get("/{business_id}", response_model=BusinessDetailOut)
async def get_business(
    business_id: str,
    user: dict = Depends(get_current_user),
) -> BusinessDetailOut:
    sb = get_admin_client()
    business = _get_owned_business(sb, business_id, user["sub"])
    records_res = (
        sb.table("business_financial_records")
        .select("id,period_year,aset,omset,profit")
        .eq("business_id", business_id)
        .order("period_year", desc=True)
        .execute()
    )
    return BusinessDetailOut(
        id=business["id"],
        name=business["name"],
        industry=business["industry"],
        description=business["description"],
        created_at=business["created_at"],
        financial_records=[FinancialRecordOut(**r) for r in (records_res.data or [])],
    )


@router.post("/{business_id}/financials", response_model=FinancialRecordOut)
async def add_financial_record(
    business_id: str,
    body: FinancialRecordCreateRequest,
    user: dict = Depends(get_current_user),
) -> FinancialRecordOut:
    sb = get_admin_client()
    _get_owned_business(sb, business_id, user["sub"])
    row = (
        sb.table("business_financial_records")
        .upsert({
            "business_id": business_id,
            "period_year": body.period_year,
            "aset": body.aset,
            "omset": body.omset,
            "profit": body.profit,
        }, on_conflict="business_id,period_year")
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=500, detail="Failed to save financial record.")
    return FinancialRecordOut(**row.data[0])
