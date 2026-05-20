import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.pin import hash_pin
from app.core.supabase_admin import get_admin_client

router = APIRouter()


class SetPinRequest(BaseModel):
    pin: str = Field(..., min_length=6, max_length=8, pattern=r"^\d+$")


@router.post("/me/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_pin(body: SetPinRequest, user: dict = Depends(get_current_user)) -> None:
    salt = secrets.token_hex(16)
    hashed = hash_pin(body.pin)
    try:
        get_admin_client().table("pin_codes").upsert({
            "user_id": user["sub"],
            "hashed_pin": hashed,
            "salt": salt,  # not used by Argon2 (it salts internally) but the column exists
            "attempts": 0,
            "locked_until": None,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to persist PIN: {exc}")
