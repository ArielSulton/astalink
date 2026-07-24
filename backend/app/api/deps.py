from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.pin import (
    LockoutError,
    is_locked,
    register_failed_attempt,
    reset_attempts,
    verify_pin,
)
from app.core.security import verify_token
from app.core.supabase_admin import get_admin_client

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


def is_admin_email(email: str | None) -> bool:
    if not email:
        return False
    admin_emails = {e.lower() for e in settings.ADMIN_EMAILS}
    return email.lower() in admin_emails


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not is_admin_email(user.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


def verify_user_pin(user_sub: str, pin: str) -> None:
    """Verify a user's transaction PIN with lockout accounting. Raises
    HTTPException on every failure mode (no PIN set → 400, locked → 423,
    invalid → 401). Shared by the approvals and portfolio routers so the
    lockout state machine lives in exactly one place."""
    pin_row = (
        get_admin_client().table("pin_codes").select("*")
        .eq("user_id", user_sub).single().execute()
    ).data
    if not pin_row:
        raise HTTPException(status_code=400, detail="PIN not set; register one first")

    state = {
        "attempts": pin_row.get("attempts", 0),
        "locked_until": pin_row.get("locked_until"),
        "last_failed_at": pin_row.get("last_failed_at"),
    }
    if is_locked(state):
        raise HTTPException(status_code=423, detail="account locked")

    if not verify_pin(pin, pin_row["hashed_pin"]):
        try:
            register_failed_attempt(state)
        except LockoutError:
            pass
        get_admin_client().table("pin_codes").update({
            "attempts": state["attempts"],
            "locked_until": state["locked_until"].isoformat() if state["locked_until"] else None,
            "last_failed_at": state["last_failed_at"].isoformat() if state["last_failed_at"] else None,
        }).eq("user_id", user_sub).execute()
        raise HTTPException(status_code=401, detail="invalid PIN")

    reset_attempts(state)
    get_admin_client().table("pin_codes").update({
        "attempts": 0, "locked_until": None, "last_failed_at": None,
    }).eq("user_id", user_sub).execute()
