"""Sandbox portfolio holdings — weighted-average-cost accounting.

Pure math (`merged_avg_cost`, `realized_pnl`) is separated from Supabase I/O
(`get_holding`, `apply_buy`, `apply_sell`) so the accounting is testable
without a database. The `holdings` table (migration 0013) is the source of
truth for accumulated positions; execution (N7) upserts on every filled buy
and the portfolio sell endpoint decrements."""
from __future__ import annotations

from datetime import datetime, timezone

# Positions below this many shares are treated as fully closed (float dust).
_QTY_EPSILON = 1e-9


def merged_avg_cost(old_qty: float, old_avg: float,
                    add_qty: float, add_price: float) -> float:
    """Weighted-average cost after adding `add_qty` shares at `add_price`."""
    total_qty = old_qty + add_qty
    if total_qty <= 0:
        return 0.0
    return (old_qty * old_avg + add_qty * add_price) / total_qty


def realized_pnl(qty_sold: float, sell_price: float, avg_cost: float) -> float:
    """Realized gain/loss from selling `qty_sold` shares held at `avg_cost`."""
    return qty_sold * (sell_price - avg_cost)


def get_holding(sb, workspace_id: str, ticker: str) -> dict | None:
    res = (
        sb.table("holdings").select("*")
        .eq("workspace_id", workspace_id).eq("ticker", ticker)
        .limit(1).execute()
    )
    return (res.data or [None])[0]


def apply_buy(sb, workspace_id: str, ticker: str,
              qty: float, price: float) -> dict:
    """Upsert a holding after a filled buy. Returns the resulting position.

    New ticker → insert at `price` as avg cost. Existing → blend into the
    weighted-average cost. Idempotency for pipeline buys is enforced upstream
    (execution skips tickers already filled for the same audit), so this is
    only ever called once per genuinely new fill."""
    now = datetime.now(timezone.utc).isoformat()
    existing = get_holding(sb, workspace_id, ticker)
    if existing:
        old_qty = float(existing["quantity"])
        new_qty = old_qty + qty
        new_avg = merged_avg_cost(old_qty, float(existing["avg_cost"]), qty, price)
        sb.table("holdings").update({
            "quantity": new_qty, "avg_cost": new_avg, "updated_at": now,
        }).eq("id", existing["id"]).execute()
        return {"ticker": ticker, "quantity": new_qty, "avg_cost": new_avg}

    sb.table("holdings").insert({
        "workspace_id": workspace_id, "ticker": ticker,
        "quantity": qty, "avg_cost": price, "updated_at": now,
    }).execute()
    return {"ticker": ticker, "quantity": qty, "avg_cost": price}


def apply_sell(sb, holding: dict, qty_sold: float) -> float:
    """Decrement (or delete when fully closed) a holding after a sell. The
    caller must have already verified `qty_sold <= holding.quantity`. Avg cost
    is unchanged by a sell. Returns the remaining quantity."""
    remaining = float(holding["quantity"]) - qty_sold
    if remaining <= _QTY_EPSILON:
        sb.table("holdings").delete().eq("id", holding["id"]).execute()
        return 0.0
    sb.table("holdings").update({
        "quantity": remaining,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", holding["id"]).execute()
    return remaining
