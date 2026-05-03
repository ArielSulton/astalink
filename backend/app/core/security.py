from jose import jwt, JWTError
from app.core.config import settings


def verify_token(token: str) -> dict | None:
    """Verify a Supabase-issued JWT and return the payload."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        return None
