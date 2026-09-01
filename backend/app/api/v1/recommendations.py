"""GET /api/v1/recommendations — hybrid stock recommendations for a
workspace. Read-only discovery; not part of the LangGraph pipeline (see
docs/superpowers/specs/2026-09-01-stock-recommendations-design.md)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.ownership import assert_workspace_owned
from app.core.recommendations import build_recommendations
from app.core.supabase_admin import get_admin_client
from app.models.recommendations import RecommendationsResponse

router = APIRouter()


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(
    workspace_id: str, user: dict = Depends(get_current_user)
) -> RecommendationsResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    return await asyncio.to_thread(build_recommendations, sb, workspace_id)
