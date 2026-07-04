from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.supabase_admin import get_admin_client

router = APIRouter()


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(personal|business)$")


class WorkspaceOut(BaseModel):
    id: str
    name: str
    type: str


@router.post("", response_model=WorkspaceOut)
async def create_workspace(
    body: WorkspaceCreateRequest,
    user: dict = Depends(get_current_user),
) -> WorkspaceOut:
    sb = get_admin_client()
    row = (
        sb.table("workspaces")
        .insert({
            "owner_user_id": user["sub"],
            "name": body.name.strip(),
            "type": body.type,
        })
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=500, detail="Failed to create workspace.")
    return WorkspaceOut(**row.data[0])
