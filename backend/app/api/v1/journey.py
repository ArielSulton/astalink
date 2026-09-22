from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.journey_home import SupabaseJourneySource, build_journey_home
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.models.journey import JourneyHomeResponse

router = APIRouter()


@router.get("/home", response_model=JourneyHomeResponse)
async def get_journey_home(
    workspace_id: str,
    user: dict = Depends(get_current_user),
) -> JourneyHomeResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    source = SupabaseJourneySource(sb, workspace_id, user["sub"])
    return build_journey_home(source)
