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
        try:
            # from_conn_string returns a context manager in langgraph-checkpoint-postgres >= 2.x
            # Enter it to get the actual saver; the connection lives for the app lifetime.
            cm = PostgresSaver.from_conn_string(settings.SUPABASE_DB_URL)
            _saver = cm.__enter__()
        except Exception as exc:
            log.warning("checkpointer: PostgresSaver init failed (%s); falling back to MemorySaver", exc)
            _saver = MemorySaver()
    else:
        log.warning(
            "checkpointer: SUPABASE_DB_URL unset or langgraph-checkpoint-postgres "
            "missing; falling back to MemorySaver (graph state will not survive restart)"
        )
        _saver = MemorySaver()
    return _saver
