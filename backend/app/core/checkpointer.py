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
    from psycopg_pool import ConnectionPool
except ImportError:
    PostgresSaver = None  # type: ignore[assignment,misc]
    ConnectionPool = None  # type: ignore[assignment,misc]

from app.core.config import settings

log = logging.getLogger(__name__)

_saver: Any = None
_pool: Any = None

# SUPABASE_DB_URL points at Supabase's Supavisor pooler in transaction mode
# (port 6543), which recycles/closes idle connections aggressively — a single
# long-lived psycopg.Connection eventually dies with "the connection is
# closed". A ConnectionPool borrows a fresh connection per checkpoint
# operation instead, so PostgresSaver never holds one long enough to see it
# get dropped. prepare_threshold=None disables server-side prepared
# statements entirely — transaction-mode pooling reassigns the physical
# backend connection between statements, so a prepared statement from one
# "connection" can collide with one already on the backend it's handed next
# (psycopg's own docs: 0 means "prepare immediately", None means "never").
_CONNECTION_KWARGS = {"autocommit": True, "prepare_threshold": None}


def get_checkpointer():
    global _saver, _pool
    if _saver is not None:
        return _saver

    if settings.SUPABASE_DB_URL and PostgresSaver is not None:
        log.info("checkpointer: using PostgresSaver (pooled) against Supabase")
        try:
            _pool = ConnectionPool(
                conninfo=settings.SUPABASE_DB_URL,
                kwargs=_CONNECTION_KWARGS,
                min_size=1,
                max_size=5,
                open=True,
            )
            saver = PostgresSaver(_pool)
            # Idempotent, version-tracked schema migrations (checkpoint_migrations
            # table) — required because the hand-written migration
            # (0008_langgraph_checkpoints.sql) mirrors an older library schema
            # and drifts as langgraph-checkpoint-postgres adds columns/indexes.
            saver.setup()
            _saver = saver
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
