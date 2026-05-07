"""Lazy singleton Supabase service-role client.

Use this client ONLY for operations that legitimately need to bypass RLS
(e.g. system writes to audit_log, regulation_documents). For user-scoped
reads/writes, use the anon client + the user's JWT so RLS is enforced."""
from __future__ import annotations

from supabase import Client, create_client

from app.core.config import settings

_client: Client | None = None


def get_admin_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _client
