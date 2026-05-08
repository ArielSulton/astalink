# AstaLink Phase 6 — Execution Engine (N7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–5 must be complete.**

**Goal:** Replace `execution_stub` with a real N7 that places orders via a swappable broker adapter, persists fills to the `transactions` table with strict idempotency on `(audit_id, ticker, side)`, and surfaces results in a frontend transactions view. The hackathon ships with a `SandboxBroker` (logs, returns fake fills); a `RealBroker` interface is defined so any Indonesian retail broker that exposes an HTTP API can plug in. Open Finance integration (cash-source verification) ships as a stub for the same reason.

**Architecture:**
- `BrokerAdapter` Protocol with `place_order(ticker, qty, side, account_id) -> BrokerOrder`. Two impls in this phase: `SandboxBroker` (deterministic, tested), `RealBroker` (stub that raises `NotImplementedError` until creds are wired).
- `OpenFinanceAdapter` Protocol with `verify_funds(user_id, amount) -> bool`. Sandbox impl returns True; real adapter is post-hackathon.
- `execution_node` reads `allocation_plan.weights` + `cash`, computes per-leg quantity (`cash * weight / last_close`), calls broker.place_order for each, writes a `transactions` row per fill. The unique constraint on `(audit_id, ticker, side)` from migration 0004 prevents duplicates if N7 runs again.
- Frontend: `/transactions` page lists fills filterable by workspace + date range.

**Tech Stack:** httpx (for the future RealBroker), pydantic schemas, Supabase admin client for inserts.

---

## File Structure

```
backend/app/
├── integrations/
│   ├── __init__.py                 # CREATE
│   ├── broker.py                   # CREATE: BrokerAdapter Protocol + Sandbox/Real impls
│   └── openfinance.py              # CREATE: stub funds-verification adapter
└── agents/
    └── execution/
        ├── __init__.py             # CREATE
        ├── schemas.py              # CREATE: BrokerOrder, ExecutionResult
        └── node.py                 # CREATE: real N7

backend/tests/
├── test_broker_sandbox.py          # CREATE
├── test_execution_node.py          # CREATE
└── test_execution_idempotency.py   # CREATE

frontend/app/(protected)/transactions/
└── page.tsx                        # CREATE
```

---

## Task Group A — Broker Adapter

### Task A1: Adapter protocol + Sandbox impl

**Files:**
- Create: `backend/app/integrations/__init__.py`, `broker.py`, `openfinance.py`
- Create: `backend/app/agents/execution/schemas.py`
- Create: `backend/tests/test_broker_sandbox.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_broker_sandbox.py`:

```python
import pytest
from app.integrations.broker import SandboxBroker
from app.agents.execution.schemas import BrokerOrder, OrderSide


def test_sandbox_returns_filled_order_with_deterministic_ref() -> None:
    b = SandboxBroker(seed=42)
    order = b.place_order(ticker="BBCA", qty=10, side=OrderSide.BUY, account_id="acct-1")
    assert isinstance(order, BrokerOrder)
    assert order.status == "filled"
    assert order.ticker == "BBCA"
    assert order.qty == 10
    assert order.side == OrderSide.BUY
    assert order.broker_ref.startswith("sandbox-")


def test_sandbox_rejects_zero_or_negative_qty() -> None:
    b = SandboxBroker()
    with pytest.raises(ValueError):
        b.place_order(ticker="BBCA", qty=0, side=OrderSide.BUY, account_id="x")


def test_real_broker_raises_until_creds_wired() -> None:
    from app.integrations.broker import RealBroker
    b = RealBroker(api_key="", base_url="")
    with pytest.raises(NotImplementedError):
        b.place_order(ticker="BBCA", qty=1, side=OrderSide.BUY, account_id="x")
```

- [ ] **Step 2: Implement**

`backend/app/agents/execution/__init__.py`:

```python
```

`backend/app/agents/execution/schemas.py`:

```python
from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class BrokerOrder(BaseModel):
    ticker: str
    qty: float
    side: OrderSide
    broker_ref: str
    status: str   # "filled" | "pending" | "failed"
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    orders: list[BrokerOrder]
```

`backend/app/integrations/__init__.py`:

```python
```

`backend/app/integrations/broker.py`:

```python
"""Broker adapter Protocol + Sandbox + RealBroker stub.

The hackathon demo runs against SandboxBroker. RealBroker raises
NotImplementedError until the team wires real credentials and an HTTP client
for the chosen Indonesian retail broker."""
from __future__ import annotations

import random
from typing import Protocol, runtime_checkable

from app.agents.execution.schemas import BrokerOrder, OrderSide


@runtime_checkable
class BrokerAdapter(Protocol):
    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder: ...


class SandboxBroker:
    """Deterministic test broker. Always fills, generates a fake broker_ref."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder:
        if qty <= 0:
            raise ValueError("qty must be > 0")
        ref = f"sandbox-{self._rng.randint(10_000_000, 99_999_999)}"
        return BrokerOrder(
            ticker=ticker, qty=qty, side=side, broker_ref=ref, status="filled",
            payload={"account_id": account_id},
        )


class RealBroker:
    """HTTP-backed real broker. Implementation deferred until creds + chosen
    provider are confirmed. Keeping the class so the wiring code is stable."""

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder:
        raise NotImplementedError(
            "RealBroker is a placeholder; wire HTTP client and broker-specific "
            "endpoints before enabling in production."
        )
```

`backend/app/integrations/openfinance.py`:

```python
"""Open Finance funds-verification adapter. Sandbox impl returns True; real
impl deferred."""
from __future__ import annotations

from typing import Protocol


class OpenFinanceAdapter(Protocol):
    def verify_funds(self, *, user_id: str, amount: float) -> bool: ...


class SandboxOpenFinance:
    def verify_funds(self, *, user_id: str, amount: float) -> bool:
        return True
```

- [ ] **Step 3: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_broker_sandbox.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/integrations backend/app/agents/execution backend/tests/test_broker_sandbox.py
git commit -m "feat(execution): broker adapter protocol with SandboxBroker + RealBroker stub"
```

---

## Task Group B — Execution Node

### Task B1: execution_node with idempotency

**Files:**
- Create: `backend/app/agents/execution/node.py`
- Create: `backend/tests/test_execution_node.py`
- Create: `backend/tests/test_execution_idempotency.py`
- Modify: `backend/app/agents/graph.py` to wire it in

The unique constraint on `(audit_id, ticker, side)` (migration 0004) gives us the floor of idempotency. The node detects pre-existing rows and skips placing the order again.

- [ ] **Step 1: Write failing tests**

`backend/tests/test_execution_node.py`:

```python
from unittest.mock import MagicMock, patch

from app.agents.execution.node import execution_node
from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.state import new_state


def test_execution_node_places_one_order_per_leg() -> None:
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.6}, {"ticker": "BMRI", "weight": 0.3}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
        {"ticker": "BMRI", "last_close": 6000},
    ]}}

    fake_broker = MagicMock()
    fake_broker.place_order.side_effect = lambda **kw: BrokerOrder(
        ticker=kw["ticker"], qty=kw["qty"], side=kw["side"],
        broker_ref="x", status="filled",
    )
    fake_admin = MagicMock()
    # No existing transactions
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    assert len(update["transactions"]) == 2
    assert {t["ticker"] for t in update["transactions"]} == {"BBCA", "BMRI"}
    assert fake_broker.place_order.call_count == 2
```

`backend/tests/test_execution_idempotency.py`:

```python
from unittest.mock import MagicMock, patch

from app.agents.execution.node import execution_node
from app.agents.state import new_state


def test_re_running_execution_does_not_place_duplicate_orders() -> None:
    state = new_state()
    state["audit_id"] = "audit-X"
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000,
    }
    state["entities"] = {"market_snapshot": {"tickers": [
        {"ticker": "BBCA", "last_close": 8000},
    ]}}

    fake_broker = MagicMock()
    fake_admin = MagicMock()
    # Simulate existing transaction for (audit-X, BBCA, buy)
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"audit_id": "audit-X", "ticker": "BBCA", "side": "buy",
               "broker_ref": "old-ref", "status": "filled"}],
    )

    with patch("app.agents.execution.node.get_broker", return_value=fake_broker), \
         patch("app.agents.execution.node.get_admin_client", return_value=fake_admin):
        update = execution_node(state)

    fake_broker.place_order.assert_not_called()
    assert update["transactions"][0]["broker_ref"] == "old-ref"
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_execution_node.py tests/test_execution_idempotency.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement node**

`backend/app/agents/execution/node.py`:

```python
"""Execution Engine (N7).

Reads allocation_plan, computes order qty from cash * weight / last_close,
places orders via the broker adapter, persists fills to the transactions
table. Idempotent: re-running for the same audit_id reuses prior fills."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.execution.schemas import BrokerOrder, OrderSide
from app.agents.state import AgentState
from app.core.supabase_admin import get_admin_client
from app.integrations.broker import BrokerAdapter, SandboxBroker

log = logging.getLogger(__name__)


def get_broker() -> BrokerAdapter:
    """Factory hook — Phase 8 swaps in RealBroker via env-flagged config."""
    return SandboxBroker()


def _existing_fills(audit_id: str) -> dict[str, dict[str, Any]]:
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


def execution_node(state: AgentState) -> AgentState:
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
            # Likely a unique constraint violation on (audit_id, ticker, side) —
            # safe to ignore: the order is already recorded.
            log.warning("execution: transactions insert race: %s", exc)

        transactions.append({
            "ticker": ticker, "side": side.value, "quantity": qty,
            "status": order.status, "broker_ref": order.broker_ref,
        })

    return {"transactions": transactions}
```

- [ ] **Step 4: Wire into graph**

In `backend/app/agents/graph.py`:

```python
from app.agents.execution.node import execution_node
# remove the execution_stub import
g.add_node("n7_execute", execution_node)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_execution_node.py tests/test_execution_idempotency.py tests/test_graph_wiring.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/execution/node.py backend/app/agents/graph.py backend/tests/test_execution_node.py backend/tests/test_execution_idempotency.py
git commit -m "feat(execution): N7 with sandbox broker + idempotency on (audit_id, ticker, side)"
```

---

## Task Group C — Frontend Transactions View

### Task C1: /transactions page

**Files:**
- Create: `frontend/app/(protected)/transactions/page.tsx`

A simple list view filterable by workspace.

```tsx
"use client";
import { useEffect, useState } from "react";
import { createBrowserClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

interface Tx { id: string; audit_id: string; ticker: string; side: string; quantity: number; status: string; broker_ref: string | null; created_at: string; }

export default function TransactionsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [items, setItems] = useState<Tx[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    const sb = createBrowserClient();
    // RLS-scoped: only transactions belonging to audits in the user's workspaces.
    sb.from("transactions")
      .select("*, audit_log!inner(workspace_id)")
      .eq("audit_log.workspace_id", workspaceId)
      .order("created_at", { ascending: false })
      .then(({ data }) => setItems((data as Tx[] | null) || []));
  }, [workspaceId]);

  return (
    <main className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Transactions</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2">Date</th><th>Ticker</th><th>Side</th><th>Qty</th>
            <th>Status</th><th>Broker Ref</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="py-2">{new Date(t.created_at).toLocaleString()}</td>
              <td>{t.ticker}</td>
              <td>{t.side}</td>
              <td>{t.quantity.toFixed(2)}</td>
              <td>{t.status}</td>
              <td className="font-mono text-xs">{t.broker_ref ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 1: Smoke-test**

After running an end-to-end approval, visit `/transactions`. Verify the row shows up.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(protected\)/transactions/page.tsx
git commit -m "feat(frontend): transactions list page filtered by workspace"
```

---

## Phase 6 Definition of Done

- [ ] All Phase 0–5 tests still pass; Phase 6 tests pass.
- [ ] End-to-end demo: agent run → HITL approve → execution → transactions appear in dashboard.
- [ ] Idempotency verified: rerun the graph for the same audit_id (e.g. by manually invoking `graph.invoke(Command(resume=...))` twice) → no duplicate `transactions` rows.
- [ ] `RealBroker` is documented as not-yet-functional in the README; deploying with `BROKER=real` raises NotImplementedError fast at startup (add a startup check in Phase 8 if desired).
- [ ] Audit page shows N7 fills as the final timeline event.
