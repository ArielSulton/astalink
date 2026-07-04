"""Prometheus metrics: registry + helpers + decorators.

Usage in nodes:
    @track_node_duration("n3_legal")
    def legal_node(state): ...

Or for ad-hoc events:
    record_legal_status("approved")
    record_revision_count(state["revision_count"])
"""
from __future__ import annotations

import time
from functools import wraps

from prometheus_client import Counter, Histogram

NODE_DURATION = Histogram(
    "astalink_node_duration_seconds",
    "Wall-clock duration of a LangGraph node invocation",
    labelnames=["node"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

NODE_ERRORS = Counter(
    "astalink_node_errors_total",
    "Number of node invocations that returned an error in state.errors",
    labelnames=["node"],
)

LEGAL_STATUS = Counter(
    "astalink_legal_status_total",
    "Distribution of Legal Agent decisions",
    labelnames=["status"],
)

REVISION_COUNT = Histogram(
    "astalink_revision_count",
    "Final revision_count per pipeline run",
    buckets=(0, 1, 2, 3, 4, 5),
)

EXECUTIONS = Counter(
    "astalink_executions_total",
    "Number of orders placed by N7",
    labelnames=["status"],
)

CHECKPOINTER_DEGRADED = Counter(
    "astalink_checkpointer_degraded_total",
    "Times the Postgres checkpointer failed to initialize despite "
    "SUPABASE_DB_URL being configured and fell back to MemorySaver",
)


def track_node_duration(node_name: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                NODE_DURATION.labels(node=node_name).observe(time.perf_counter() - t0)
        return wrapper
    return decorator


def record_legal_status(status: str) -> None:
    LEGAL_STATUS.labels(status=status).inc()


def record_revision_count(n: int) -> None:
    REVISION_COUNT.observe(n)


def record_execution(status: str) -> None:
    EXECUTIONS.labels(status=status).inc()


def record_node_error(node_name: str) -> None:
    NODE_ERRORS.labels(node=node_name).inc()


def record_checkpointer_degraded() -> None:
    CHECKPOINTER_DEGRADED.inc()
