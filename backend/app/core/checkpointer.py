"""LangGraph checkpointer factory.

Returns a PostgresSaver bound to Supabase Postgres if SUPABASE_DB_URL is set;
falls back to MemorySaver for local dev without DB credentials. The fallback
keeps tests fast and lets contributors run without a Supabase connection,
but Phase 5's interrupt() requires the Postgres saver in production."""
from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    PostgresSaver = None  # type: ignore[assignment,misc]

from app.core.config import settings

log = logging.getLogger(__name__)

_saver: Any = None


def get_checkpointer():
    global _saver
    if _saver is not None:
        return _saver

    if settings.SUPABASE_DB_URL and PostgresSaver is not None:
        log.info("checkpointer: using PostgresSaver against Supabase")
        _saver = PostgresSaver.from_conn_string(settings.SUPABASE_DB_URL)
    else:
        log.warning(
            "checkpointer: SUPABASE_DB_URL unset or langgraph-checkpoint-postgres "
            "missing; falling back to MemorySaver (graph state will not survive restart)"
        )
        _saver = MemorySaver()
    return _saver
