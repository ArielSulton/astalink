"""Sandbox cash-balance helpers for the `workspaces.cash_balance` column.

AstaLink's execution layer only ever talks to SandboxBroker (see
app.integrations.broker) — no real money moves. Each workspace instead
tracks a virtual balance (seeded at Rp 1,000,000,000 by migration 0011)
that the optimizer treats as available cash and execution debits on every
filled order, so the sandbox behaves like a real account with finite funds."""
from __future__ import annotations


def get_workspace_balance(sb, workspace_id: str) -> float | None:
    """Returns the workspace's current cash_balance, or None if the
    workspace row doesn't exist."""
    res = (
        sb.table("workspaces").select("cash_balance")
        .eq("id", workspace_id).limit(1).execute()
    )
    if not res.data:
        return None
    return float(res.data[0]["cash_balance"])


def debit_workspace_balance(sb, workspace_id: str, amount: float) -> float | None:
    """Atomically decrement cash_balance by `amount` if sufficient funds
    exist. Returns the new balance on success, or None if funds were
    insufficient, the workspace doesn't exist, or a concurrent debit
    already changed the balance since we read it (optimistic-concurrency
    lost race).

    Safety comes from `.eq("cash_balance", current)` on the UPDATE's WHERE
    clause: it requires the database's balance to still exactly match what
    we just read. If any other debit committed between our read and this
    write — even one that individually looked "affordable" and wouldn't
    have tripped a bare `.gte(amount)` check — the WHERE clause no longer
    matches, `res.data` comes back empty, and we correctly return None
    instead of silently double-spending. The `.gte("cash_balance", amount)`
    filter is kept alongside it as a redundant defensive check (harmless,
    since Python already verified `current >= amount` above) but the
    `.eq("cash_balance", current)` compare-and-swap is what actually
    prevents double-spend."""
    if amount <= 0:
        raise ValueError("amount must be > 0")

    current = get_workspace_balance(sb, workspace_id)
    if current is None or current < amount:
        return None

    new_balance = current - amount
    res = (
        sb.table("workspaces")
        .update({"cash_balance": new_balance})
        .eq("id", workspace_id)
        .eq("cash_balance", current)
        .gte("cash_balance", amount)
        .execute()
    )
    return new_balance if res.data else None
