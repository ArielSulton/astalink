"""Execution Engine (N7).

Reads allocation_plan, computes order qty from cash * weight / last_close,
places orders via the broker adapter, persists fills to the transactions
table. Idempotent: re-running for the same audit_id reuses prior fills."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.state import AgentState, UserApproval
from app.core.metrics import record_execution, track_node_duration
from app.core.supabase_admin import get_admin_client
from app.integrations.broker import BrokerAdapter, SandboxBroker

log = logging.getLogger(__name__)


def get_broker() -> BrokerAdapter:
    """Factory hook — Phase 8 swaps in RealBroker via env-flagged config."""
    return SandboxBroker()


def _existing_fills(audit_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Returns map of (ticker, side) → existing transactions row."""
    res = (
        get_admin_client().table("transactions").select("*")
        .eq("audit_id", audit_id).execute()
    )
    return {(row["ticker"], row["side"]): row for row in (res.data or [])}


def _last_close(state: AgentState, ticker: str) -> float | None:
    snapshot = state.get("entities", {}).get("market_snapshot") or {}
    for t in snapshot.get("tickers", []):
        if t.get("ticker") == ticker:
            return t.get("last_close")
    return None


@track_node_duration("n7_execute")
def execution_node(state: AgentState) -> AgentState:
    if state.get("user_approval") != UserApproval.APPROVED:
        log.error(
            "execution_node invoked with user_approval=%r — refusing to place orders",
            state.get("user_approval"),
        )
        return {
            "transactions": [],
            "errors": [*state.get("errors", []),
                       {"node": "execution", "reason": "not_approved"}],
        }

    plan = state.get("allocation_plan") or {}
    weights = plan.get("weights") or []
    cash = float(plan.get("cash") or 0)
    audit_id = state["audit_id"]

    if not weights or cash <= 0:
        return {"transactions": []}

    existing = _existing_fills(audit_id)
    broker = get_broker()
    transactions: list[dict[str, Any]] = []

    for leg in weights:
        ticker = leg["ticker"]
        weight = float(leg["weight"])
        if weight <= 0:
            continue
        side = OrderSide.BUY  # Phase 6 ships buy-only
        key = (ticker, side.value)

        if key in existing:
            log.info("execution: skipping %s (already filled)", key)
            transactions.append(existing[key])
            continue

        last_close = _last_close(state, ticker)
        if not last_close:
            log.error("execution: missing last_close for %s, skipping", ticker)
            continue
        qty = (cash * weight) / last_close
        if qty <= 0:
            continue

        try:
            order: BrokerOrder = broker.place_order(
                ticker=ticker, qty=qty, side=side,
                account_id=state.get("entities", {}).get("workspace_id", "default"),
            )
        except Exception as exc:
            log.error("execution: place_order failed for %s: %s", ticker, exc)
            transactions.append({
                "ticker": ticker, "side": side.value, "quantity": qty,
                "status": "failed", "broker_ref": None,
                "payload": {"error": str(exc)},
            })
            continue

        # Persist (allocation_plan_id resolved via lookup)
        plan_row = (
            get_admin_client().table("allocation_plans").select("id")
            .eq("audit_id", audit_id).limit(1).execute()
        )
        plan_id = (plan_row.data or [{}])[0].get("id")
        try:
            get_admin_client().table("transactions").insert({
                "allocation_plan_id": plan_id,
                "audit_id": audit_id,
                "ticker": ticker,
                "side": side.value,
                "quantity": qty,
                "broker_ref": order.broker_ref,
                "status": order.status,
                "payload": order.payload,
            }).execute()
        except Exception as exc:
            log.warning("execution: transactions insert race: %s", exc)

        transactions.append({
            "ticker": ticker, "side": side.value, "quantity": qty,
            "status": order.status, "broker_ref": order.broker_ref,
        })
        record_execution(order.status)

    return {"transactions": transactions}
