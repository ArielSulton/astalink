"""Shared workspace ownership guard.

Used by multiple API entry points (business, agent, chat) to verify that
the authenticated user owns the workspace they are trying to operate on,
before any data is read or mutated via the service-role admin client."""
from __future__ import annotations

from fastapi import HTTPException


def assert_workspace_owned(sb, workspace_id: str, user_id: str) -> None:
    """Raise HTTP 403 if *workspace_id* does not exist or is not owned by *user_id*.

    *sb* must be the service-role admin client (``get_admin_client()``).
    Callers should invoke this before passing *workspace_id* into any agent
    pipeline or admin-scoped DB query, because the admin client bypasses RLS.
    """
    res = (
        sb.table("workspaces").select("id")
        .eq("id", workspace_id).eq("owner_user_id", user_id)
        .limit(1).execute()
    )
    if not res.data:
        raise HTTPException(status_code=403, detail="Workspace not found or not owned by you.")
