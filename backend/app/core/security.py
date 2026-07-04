import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_token(token: str) -> dict | None:
    """Verify a Supabase-issued access token by asking Supabase Auth directly.

    This project signs user session tokens with an asymmetric key (not the
    legacy HS256 shared secret), so local jose.jwt.decode() can never
    validate them regardless of SUPABASE_JWT_SECRET. Delegating to
    /auth/v1/user works for either signing scheme and matches what Supabase
    itself considers valid."""
    try:
        resp = httpx.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
            timeout=5.0,
        )
    except httpx.HTTPError as e:
        logger.warning("Supabase auth verification request failed: %s", e)
        return None

    if resp.status_code != 200:
        logger.warning("Token rejected by Supabase auth: %s %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    return {"sub": data["id"], **data}
