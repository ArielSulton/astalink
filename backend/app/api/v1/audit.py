import logging

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.api.deps import get_current_user
from app.core.supabase_admin import get_admin_client
from app.models.audit import AuditDetail, AuditListResponse, AuditSummary

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AuditListResponse)
async def list_audit(
    workspace_id: str, user: dict = Depends(get_current_user)
) -> AuditListResponse:
    res = (
        get_admin_client().table("audit_log")
        .select("audit_id, intent, status, created_at, completed_at, workspace_id, user_id")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user["sub"])
        .order("created_at", desc=True)
        .execute()
    )
    audits = [
        AuditSummary(
            audit_id=row["audit_id"],
            intent=row.get("intent"),
            status=row.get("status", "unknown"),
            created_at=row.get("created_at", ""),
            completed_at=row.get("completed_at"),
        )
        for row in (res.data or [])
    ]
    return AuditListResponse(audits=audits)


def _load_audit(audit_id: str, user_sub: str) -> dict:
    # .single() raises APIError when no row matches — map that to 404.
    try:
        audit = (
            get_admin_client().table("audit_log").select("*")
            .eq("audit_id", audit_id).single().execute()
        ).data
    except APIError:
        audit = None
    if not audit or audit.get("user_id") != user_sub:
        raise HTTPException(status_code=404, detail="not found")
    return audit


@router.get("/{audit_id}", response_model=AuditDetail)
async def get_audit(
    audit_id: str, user: dict = Depends(get_current_user)
) -> AuditDetail:
    audit = _load_audit(audit_id, user["sub"])

    # Runs that stop before the optimizer have no allocation_plans row;
    # .single() raises in that case and the detail must still render.
    try:
        plan_row = (
            get_admin_client().table("allocation_plans").select("*")
            .eq("audit_id", audit_id).single().execute()
        ).data or {}
    except APIError:
        plan_row = {}

    tx_res = (
        get_admin_client().table("transactions").select("*")
        .eq("audit_id", audit_id).execute()
    )

    return AuditDetail(
        audit_id=audit_id,
        status=audit.get("status", "unknown"),
        intent=audit.get("intent"),
        workspace_id=audit["workspace_id"],
        created_at=audit.get("created_at", ""),
        completed_at=audit.get("completed_at"),
        allocation_plan=plan_row.get("plan_json"),
        legal_status=plan_row.get("legal_status"),
        legal_citations=plan_row.get("legal_citations") or [],
        transactions=tx_res.data or [],
    )
