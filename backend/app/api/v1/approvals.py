import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.agents.graph import graph
from app.api.deps import get_current_user, verify_user_pin
from app.core.supabase_admin import get_admin_client
from app.models.approvals import (
    ApprovalAction,
    ApprovalDetail,
    ApprovalListResponse,
    ApprovalSummary,
)

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(workspace_id: str, user: dict = Depends(get_current_user)) -> ApprovalListResponse:
    res = (
        get_admin_client().table("audit_log")
        .select("audit_id, intent, status, created_at, workspace_id, user_id")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user["sub"])
        .execute()
    )
    items = [
        ApprovalSummary(**{k: v for k, v in row.items() if k != "user_id"})
        for row in (res.data or [])
        if row.get("status") == "awaiting_approval"
    ]
    return ApprovalListResponse(approvals=items)


def _load_audit(audit_id: str, user_sub: str) -> dict:
    audit = (
        get_admin_client().table("audit_log").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data
    if not audit or audit.get("user_id") != user_sub:
        raise HTTPException(status_code=404, detail="not found")
    return audit


@router.get("/{audit_id}", response_model=ApprovalDetail)
async def get_approval(audit_id: str, user: dict = Depends(get_current_user)) -> ApprovalDetail:
    audit = _load_audit(audit_id, user["sub"])
    plan_row = (
        get_admin_client().table("allocation_plans").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data or {}
    return ApprovalDetail(
        audit_id=audit_id,
        status=audit.get("status", "unknown"),
        intent=audit.get("intent"),
        workspace_id=audit["workspace_id"],
        plan_json=plan_row.get("plan_json"),
        legal_status=plan_row.get("legal_status"),
        legal_citations=plan_row.get("legal_citations") or [],
    )


@router.post("/{audit_id}/approve", status_code=200)
async def approve(audit_id: str, body: ApprovalAction, user: dict = Depends(get_current_user)):
    if not body.pin:
        raise HTTPException(status_code=400, detail="pin required")
    _load_audit(audit_id, user["sub"])
    verify_user_pin(user["sub"], body.pin)

    from langgraph.types import Command
    final = graph.invoke(
        Command(resume={"approval": "approved"}),
        config={"configurable": {"thread_id": audit_id}},
    )
    get_admin_client().table("audit_log").update({
        "status": "approved",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("audit_id", audit_id).execute()
    return {"audit_id": audit_id, "transactions": final.get("transactions", [])}


@router.post("/{audit_id}/reject", status_code=200)
async def reject(audit_id: str, body: ApprovalAction, user: dict = Depends(get_current_user)):
    _load_audit(audit_id, user["sub"])
    from langgraph.types import Command
    graph.invoke(
        Command(resume={"approval": "rejected", "reason": body.reason or ""}),
        config={"configurable": {"thread_id": audit_id}},
    )
    get_admin_client().table("audit_log").update({
        "status": "rejected",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("audit_id", audit_id).execute()
    return {"audit_id": audit_id}
