# AstaLink Phase 5 — HITL Gate + Web Dashboard Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–4 must be complete.**

**Goal:** Replace the Phase 2 `hitl_stub` (auto-approve) with a real Human-in-the-Loop gate using LangGraph's `interrupt()`, build the web dashboard pages users approve from, add PIN management with Argon2 hashing + lockout, and wire workspace-scoped audit trail viewing. After Phase 5, no transaction can execute without an explicit user approval — the non-negotiable AstaLink rule.

**Architecture:**
- **Backend N6:** the node calls `langgraph.types.interrupt({allocation_plan, summary, audit_id})`. The graph pauses; the Postgres checkpointer (Phase 2) persists state. The graph run returns to the caller with an `__interrupt__` marker. The API layer detects it and returns a "pending approval" response. Approval endpoint resumes the graph by calling `graph.invoke(None, config={"configurable": {"thread_id": audit_id}})` — LangGraph picks up where it left off.
- **PIN flow:** `pin_codes` table (Phase 0) stores Argon2 hash. `POST /users/me/pin` sets it once. `POST /approvals/{audit_id}/approve` requires a `{pin}` body — verified server-side; lockout after 5 failed attempts for 15 min. Wrong PIN never reveals whether the PIN is unset (timing-safe).
- **Frontend:** Next.js App Router pages under `(protected)/approvals/`. Inbox polls or uses Supabase Realtime on `audit_log`. Plan detail shows weights chart, legal citations, risk metrics, optimizer narration. PIN modal is a Shadcn dialog with masked input + lockout countdown.
- **Workspace switcher:** top-bar selector; chosen workspace_id flows to every API call. Backend re-validates ownership on every request (frontend can't be trusted).
- **Audit trail viewer:** timeline of every node that ran for an `audit_id`, queryable by user.

**Tech Stack:** `langgraph.types.interrupt`, `argon2-cffi`, Supabase Realtime (optional polling fallback), Shadcn UI dialogs, Next.js Server Actions for backend calls.

**Scope cuts:** No multi-approver workflow (one user, one PIN). No biometric auth (Phase 7+). No expiring approvals (an unapproved request stays pending until explicitly rejected or 24h reaper job — only "explicit" lands in this phase; the reaper is a Phase 8 follow-up).

---

## File Structure

```
backend/
├── app/
│   ├── agents/
│   │   └── hitl/
│   │       ├── __init__.py             # CREATE
│   │       └── node.py                 # CREATE: real N6 with interrupt()
│   ├── api/
│   │   └── v1/
│   │       ├── approvals.py            # CREATE: list/get/approve/reject
│   │       ├── pin.py                  # CREATE: set/verify PIN
│   │       └── router.py               # MODIFY: register approvals + pin
│   ├── core/
│   │   └── pin.py                      # CREATE: Argon2 hash + verify + lockout
│   └── models/
│       └── approvals.py                # CREATE: response shapes
└── tests/
    ├── test_pin.py                     # CREATE
    ├── test_hitl_node.py               # CREATE
    ├── test_approvals_endpoint.py      # CREATE
    └── test_pin_endpoint.py            # CREATE

frontend/
├── app/
│   ├── (protected)/
│   │   ├── approvals/
│   │   │   ├── page.tsx                # CREATE: inbox
│   │   │   └── [auditId]/page.tsx      # CREATE: plan detail
│   │   ├── audit/
│   │   │   └── [auditId]/page.tsx      # CREATE: audit trail timeline
│   │   ├── settings/
│   │   │   └── pin/page.tsx            # CREATE: set/change PIN
│   │   └── layout.tsx                  # MODIFY: add workspace switcher to top bar
│   └── api/
│       └── approvals/
│           └── [auditId]/
│               ├── approve/route.ts    # CREATE: server route → backend
│               └── reject/route.ts     # CREATE
├── components/
│   ├── pin-modal.tsx                   # CREATE
│   ├── workspace-switcher.tsx          # CREATE
│   ├── allocation-chart.tsx            # CREATE
│   └── audit-timeline.tsx              # CREATE
└── lib/
    └── api-client.ts                   # CREATE: typed helper around backend
```

---

## Task Group A — PIN Management (backend)

### Task A1: Argon2 PIN hashing + lockout logic

**Files:**
- Modify: `backend/pyproject.toml` (add `argon2-cffi`)
- Create: `backend/app/core/pin.py`
- Create: `backend/tests/test_pin.py`

- [ ] **Step 1: Add dependency**

In `backend/pyproject.toml`, append `"argon2-cffi>=23.0.0"` to `dependencies`. Run `uv sync --extra dev`.

- [ ] **Step 2: Write failing tests**

`backend/tests/test_pin.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.core.pin import (
    LOCKOUT_DURATION,
    LockoutError,
    MAX_ATTEMPTS,
    hash_pin,
    register_failed_attempt,
    reset_attempts,
    verify_pin,
)


def test_hash_pin_returns_argon2_string() -> None:
    h = hash_pin("123456")
    assert h.startswith("$argon2"), "must use argon2 format"
    assert h != "123456"


def test_verify_pin_succeeds_with_correct_pin() -> None:
    h = hash_pin("123456")
    assert verify_pin("123456", h) is True


def test_verify_pin_fails_with_wrong_pin() -> None:
    h = hash_pin("123456")
    assert verify_pin("000000", h) is False


def test_register_failed_attempt_locks_after_max() -> None:
    """Returns the lockout-until timestamp once attempts hit MAX_ATTEMPTS."""
    state = {"attempts": MAX_ATTEMPTS - 1, "last_failed_at": None, "locked_until": None}
    register_failed_attempt(state)
    assert state["attempts"] == MAX_ATTEMPTS
    assert state["locked_until"] is not None
    assert state["locked_until"] > datetime.now(timezone.utc)


def test_locked_account_raises_until_lockout_expires() -> None:
    state = {"attempts": MAX_ATTEMPTS,
             "locked_until": datetime.now(timezone.utc) + LOCKOUT_DURATION}
    with pytest.raises(LockoutError):
        register_failed_attempt(state)


def test_reset_attempts_clears_state() -> None:
    state = {"attempts": 3, "last_failed_at": datetime.now(timezone.utc),
             "locked_until": None}
    reset_attempts(state)
    assert state["attempts"] == 0
    assert state["last_failed_at"] is None
```

- [ ] **Step 3: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_pin.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement PIN core**

`backend/app/core/pin.py`:

```python
"""PIN hashing + verification + lockout state machine.

State is a plain dict so the API layer can persist it to Supabase via the
service-role client; this module is pure logic, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

MAX_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

_ph = PasswordHasher()


class LockoutError(Exception):
    """Raised when an action is attempted on a locked account."""


def hash_pin(pin: str) -> str:
    return _ph.hash(pin)


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pin)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def is_locked(state: dict[str, Any]) -> bool:
    until = state.get("locked_until")
    if until is None:
        return False
    if isinstance(until, str):
        until = datetime.fromisoformat(until)
    return until > datetime.now(timezone.utc)


def register_failed_attempt(state: dict[str, Any]) -> None:
    """Mutates state in place. Raises LockoutError if already locked."""
    if is_locked(state):
        raise LockoutError("Account is locked")
    state["attempts"] = int(state.get("attempts", 0)) + 1
    state["last_failed_at"] = datetime.now(timezone.utc)
    if state["attempts"] >= MAX_ATTEMPTS:
        state["locked_until"] = datetime.now(timezone.utc) + LOCKOUT_DURATION


def reset_attempts(state: dict[str, Any]) -> None:
    state["attempts"] = 0
    state["last_failed_at"] = None
    state["locked_until"] = None
```

- [ ] **Step 5: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_pin.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/core/pin.py backend/tests/test_pin.py
git commit -m "feat(pin): Argon2 hashing + lockout state machine"
```

---

### Task A2: PIN endpoint — set/verify/reset

**Files:**
- Create: `backend/app/api/v1/pin.py`
- Create: `backend/tests/test_pin_endpoint.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_pin_endpoint.py`:

```python
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_set_pin_creates_row(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{}])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.pin.get_admin_client", return_value=fake_admin):
        resp = client.post("/api/v1/users/me/pin", json={"pin": "123456"},
                           headers={"Authorization": "Bearer x"})

    assert resp.status_code == 204
    fake_admin.table.assert_called_with("pin_codes")


def test_set_pin_rejects_short_pin(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    with patch("app.api.deps.verify_token", return_value=user):
        resp = client.post("/api/v1/users/me/pin", json={"pin": "12"},
                           headers={"Authorization": "Bearer x"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_pin_endpoint.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement endpoint**

`backend/app/api/v1/pin.py`:

```python
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.pin import hash_pin
from app.core.supabase_admin import get_admin_client

router = APIRouter()


class SetPinRequest(BaseModel):
    pin: str = Field(..., min_length=6, max_length=8, pattern=r"^\d+$")


@router.post("/me/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_pin(body: SetPinRequest, user: dict = Depends(get_current_user)) -> None:
    salt = secrets.token_hex(16)
    hashed = hash_pin(body.pin)
    try:
        get_admin_client().table("pin_codes").upsert({
            "user_id": user["sub"],
            "hashed_pin": hashed,
            "salt": salt,  # not used by Argon2 (it salts internally) but the column exists
            "attempts": 0,
            "locked_until": None,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to persist PIN: {exc}")
```

Wire into `backend/app/api/v1/router.py`:

```python
from app.api.v1 import pin as pin_router
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_pin_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/pin.py backend/app/api/v1/router.py backend/tests/test_pin_endpoint.py
git commit -m "feat(api): POST /users/me/pin to register PIN"
```

---

## Task Group B — HITL Node with interrupt()

### Task B1: Real N6 node

**Files:**
- Create: `backend/app/agents/hitl/__init__.py`, `node.py`
- Create: `backend/tests/test_hitl_node.py`
- Modify: `backend/app/agents/graph.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_hitl_node.py`:

```python
from unittest.mock import patch

import pytest

from app.agents.hitl.node import hitl_node
from app.agents.state import LegalStatus, UserApproval, new_state


def test_hitl_node_calls_interrupt_with_plan_summary() -> None:
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.6}],
        "cash": 10_000_000,
    }
    state["legal_status"] = LegalStatus.APPROVED

    captured: dict = {}

    def _fake_interrupt(payload):
        captured.update(payload)
        # First call from the graph: pretend the user hasn't responded yet,
        # so interrupt() raises GraphInterrupt
        from langgraph.errors import GraphInterrupt
        raise GraphInterrupt(payload)

    with patch("app.agents.hitl.node.interrupt", side_effect=_fake_interrupt):
        from langgraph.errors import GraphInterrupt
        with pytest.raises(GraphInterrupt):
            hitl_node(state)

    assert captured["audit_id"] == state["audit_id"]
    assert "allocation_plan" in captured
    assert captured["legal_status"] == LegalStatus.APPROVED.value


def test_hitl_node_returns_user_approval_when_resumed() -> None:
    """LangGraph's interrupt() returns the resume value when the graph is
    invoked with a non-None command. We simulate that by patching interrupt
    to return a resume payload."""
    state = new_state()
    state["allocation_plan"] = {"weights": [], "cash": 0}
    state["legal_status"] = LegalStatus.APPROVED

    with patch("app.agents.hitl.node.interrupt",
               return_value={"approval": UserApproval.APPROVED.value}):
        update = hitl_node(state)

    assert update["user_approval"] == UserApproval.APPROVED
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_hitl_node.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement N6**

`backend/app/agents/hitl/__init__.py`:

```python
```

`backend/app/agents/hitl/node.py`:

```python
"""Human-in-the-Loop gate (N6).

Calls langgraph.types.interrupt(...) which:
1. On first call (no resume value): raises GraphInterrupt — graph pauses,
   checkpointer persists state.
2. On resume call (graph.invoke(Command(resume={...}))): returns the resume
   payload provided by the API layer.

The payload sent on interrupt MUST include audit_id so the dashboard can
deep-link the user to the right approval."""
from __future__ import annotations

import logging

from langgraph.types import interrupt

from app.agents.state import AgentState, LegalStatus, UserApproval
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)


def hitl_node(state: AgentState) -> AgentState:
    plan = state.get("allocation_plan") or {}
    legal_status = state.get("legal_status")

    # Mark audit_log as awaiting approval (so the inbox query can find it)
    try:
        get_admin_client().table("audit_log").update({
            "status": "awaiting_approval",
        }).eq("audit_id", state["audit_id"]).execute()
    except Exception as exc:
        log.error("hitl_node: audit_log update failed: %s", exc)

    # interrupt() either raises GraphInterrupt (paused) or returns resume payload
    resume = interrupt({
        "audit_id": state["audit_id"],
        "allocation_plan": plan,
        "legal_status": (legal_status.value if isinstance(legal_status, LegalStatus)
                         else legal_status),
    })

    # Resume payload from the approval endpoint:
    # {"approval": "approved" | "rejected", "reason": "..."}
    approval = resume.get("approval", "rejected")
    return {
        "user_approval": UserApproval.APPROVED if approval == "approved"
                         else UserApproval.REJECTED,
    }
```

- [ ] **Step 4: Wire into graph**

In `backend/app/agents/graph.py`, replace `hitl_stub` import:

```python
from app.agents.hitl.node import hitl_node
from app.agents.stubs import execution_stub  # keep until Phase 6
```

And in `build_graph()`:

```python
g.add_node("n6_hitl", hitl_node)
```

Phase 2's `test_graph_wiring.py` patched the stub; update it to patch `hitl_node` instead, returning a synthetic resume so happy-path tests still terminate.

- [ ] **Step 5: Update existing graph wiring tests**

In `backend/tests/test_graph_wiring.py`, in the happy-path test, replace mocking of the hitl stub with a mock for `interrupt`:

```python
from unittest.mock import patch
from app.agents.state import UserApproval

with patch("app.agents.hitl.node.interrupt",
           return_value={"approval": UserApproval.APPROVED.value}), \
     patch("app.agents.graph.intent_node", new=fake_intent), \
     patch("app.agents.graph.legal_node", new=fake_legal):
    ...
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_hitl_node.py tests/test_graph_wiring.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/hitl/ backend/app/agents/graph.py backend/tests/test_hitl_node.py backend/tests/test_graph_wiring.py
git commit -m "feat(hitl): N6 gate with langgraph interrupt() and audit_log status update"
```

---

## Task Group C — Approval Endpoints

### Task C1: List + get pending approvals

**Files:**
- Create: `backend/app/api/v1/approvals.py`
- Create: `backend/app/models/approvals.py`
- Create: `backend/tests/test_approvals_endpoint.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_approvals_endpoint.py`:

```python
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_list_approvals_returns_pending_for_user_workspace(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    workspace_id = str(uuid.uuid4())

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {"audit_id": "a1", "intent": "allocate_stocks", "status": "awaiting_approval",
             "payload": {}, "created_at": "2026-05-04T00:00:00Z", "workspace_id": workspace_id},
        ]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/approvals?workspace_id={workspace_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["approvals"]) == 1
    assert body["approvals"][0]["audit_id"] == "a1"


def test_get_approval_returns_full_plan(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    # audit_log row
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
        MagicMock(data={"audit_id": audit_id, "status": "awaiting_approval",
                        "payload": {}, "intent": "allocate_stocks",
                        "workspace_id": "w", "user_id": user["sub"]}),
        MagicMock(data={"plan_json": {"weights": [], "cash": 0},
                        "legal_status": "approved", "legal_citations": []}),
    ]

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/approvals/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"] == audit_id
    assert body["plan_json"] is not None
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_approvals_endpoint.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement list/get endpoints**

`backend/app/models/approvals.py`:

```python
from typing import Any
from pydantic import BaseModel


class ApprovalSummary(BaseModel):
    audit_id: str
    intent: str | None
    status: str
    created_at: str
    workspace_id: str


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalSummary]


class ApprovalDetail(BaseModel):
    audit_id: str
    status: str
    intent: str | None
    workspace_id: str
    plan_json: dict[str, Any] | None
    legal_status: str | None
    legal_citations: list[dict[str, Any]]


class ApprovalAction(BaseModel):
    pin: str | None = None
    reason: str | None = None
```

`backend/app/api/v1/approvals.py`:

```python
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.graph import graph
from app.api.deps import get_current_user
from app.core.pin import (
    LockoutError,
    is_locked,
    register_failed_attempt,
    reset_attempts,
    verify_pin,
)
from app.core.supabase_admin import get_admin_client
from app.models.approvals import (
    ApprovalAction,
    ApprovalDetail,
    ApprovalListResponse,
    ApprovalSummary,
)

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(workspace_id: str, user: dict = Depends(get_current_user)) -> ApprovalListResponse:
    res = (
        get_admin_client().table("audit_log")
        .select("audit_id, intent, status, created_at, workspace_id, user_id")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user["sub"])  # second-level check (RLS is the safety net)
        .execute()
    )
    items = [
        ApprovalSummary(**{k: v for k, v in row.items() if k != "user_id"})
        for row in (res.data or [])
        if row.get("status") == "awaiting_approval"
    ]
    return ApprovalListResponse(approvals=items)


def _load_audit(audit_id: str, user_sub: str) -> dict:
    audit = (
        get_admin_client().table("audit_log").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data
    if not audit or audit.get("user_id") != user_sub:
        raise HTTPException(status_code=404, detail="not found")
    return audit


@router.get("/{audit_id}", response_model=ApprovalDetail)
async def get_approval(audit_id: str, user: dict = Depends(get_current_user)) -> ApprovalDetail:
    audit = _load_audit(audit_id, user["sub"])
    plan_row = (
        get_admin_client().table("allocation_plans").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data or {}
    return ApprovalDetail(
        audit_id=audit_id,
        status=audit.get("status", "unknown"),
        intent=audit.get("intent"),
        workspace_id=audit["workspace_id"],
        plan_json=plan_row.get("plan_json"),
        legal_status=plan_row.get("legal_status"),
        legal_citations=plan_row.get("legal_citations") or [],
    )


def _check_pin(user_sub: str, pin: str) -> None:
    """Verify PIN with lockout. Raises HTTPException on any failure mode."""
    pin_row = (
        get_admin_client().table("pin_codes").select("*")
        .eq("user_id", user_sub).single().execute()
    ).data
    if not pin_row:
        raise HTTPException(status_code=400, detail="PIN not set; register one first")

    state = {
        "attempts": pin_row.get("attempts", 0),
        "locked_until": pin_row.get("locked_until"),
        "last_failed_at": pin_row.get("last_failed_at"),
    }
    if is_locked(state):
        raise HTTPException(status_code=423, detail="account locked")

    if not verify_pin(pin, pin_row["hashed_pin"]):
        try:
            register_failed_attempt(state)
        except LockoutError:
            pass
        get_admin_client().table("pin_codes").update({
            "attempts": state["attempts"],
            "locked_until": state["locked_until"].isoformat() if state["locked_until"] else None,
            "last_failed_at": state["last_failed_at"].isoformat() if state["last_failed_at"] else None,
        }).eq("user_id", user_sub).execute()
        raise HTTPException(status_code=401, detail="invalid PIN")

    reset_attempts(state)
    get_admin_client().table("pin_codes").update({
        "attempts": 0, "locked_until": None, "last_failed_at": None,
    }).eq("user_id", user_sub).execute()


@router.post("/{audit_id}/approve", status_code=200)
async def approve(audit_id: str, body: ApprovalAction, user: dict = Depends(get_current_user)):
    if not body.pin:
        raise HTTPException(status_code=400, detail="pin required")
    _load_audit(audit_id, user["sub"])
    _check_pin(user["sub"], body.pin)

    # Resume the paused graph
    from langgraph.types import Command
    final = graph.invoke(
        Command(resume={"approval": "approved"}),
        config={"configurable": {"thread_id": audit_id}},
    )
    get_admin_client().table("audit_log").update({
        "status": "approved",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("audit_id", audit_id).execute()
    return {"audit_id": audit_id, "transactions": final.get("transactions", [])}


@router.post("/{audit_id}/reject", status_code=200)
async def reject(audit_id: str, body: ApprovalAction, user: dict = Depends(get_current_user)):
    _load_audit(audit_id, user["sub"])
    from langgraph.types import Command
    graph.invoke(
        Command(resume={"approval": "rejected", "reason": body.reason or ""}),
        config={"configurable": {"thread_id": audit_id}},
    )
    get_admin_client().table("audit_log").update({
        "status": "rejected",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("audit_id", audit_id).execute()
    return {"audit_id": audit_id}
```

Wire into `backend/app/api/v1/router.py`:

```python
from app.api.v1 import approvals as approvals_router
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_approvals_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/approvals.py backend/app/api/v1/router.py backend/app/models/approvals.py backend/tests/test_approvals_endpoint.py
git commit -m "feat(api): list/get/approve/reject approvals with PIN lockout"
```

---

## Task Group D — Frontend Approval UI

### Task D1: API client helper

**Files:**
- Create: `frontend/lib/api-client.ts`

- [ ] **Step 1: Implement client**

```typescript
// frontend/lib/api-client.ts
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export interface ApprovalSummary {
  audit_id: string;
  intent: string | null;
  status: string;
  created_at: string;
  workspace_id: string;
}

export interface ApprovalDetail {
  audit_id: string;
  status: string;
  intent: string | null;
  workspace_id: string;
  plan_json: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  legal_status: string | null;
  legal_citations: { source: string; pasal: string; ayat: string | null; span: string }[];
}

async function jsonFetch<T>(path: string, init?: RequestInit, accessToken?: string): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  listApprovals: (workspaceId: string, token: string) =>
    jsonFetch<{ approvals: ApprovalSummary[] }>(
      `/api/v1/approvals?workspace_id=${workspaceId}`, { method: "GET" }, token,
    ),
  getApproval: (auditId: string, token: string) =>
    jsonFetch<ApprovalDetail>(`/api/v1/approvals/${auditId}`, { method: "GET" }, token),
  approve: (auditId: string, pin: string, token: string) =>
    jsonFetch<{ audit_id: string; transactions: unknown[] }>(
      `/api/v1/approvals/${auditId}/approve`,
      { method: "POST", body: JSON.stringify({ pin }) },
      token,
    ),
  reject: (auditId: string, reason: string, token: string) =>
    jsonFetch<{ audit_id: string }>(
      `/api/v1/approvals/${auditId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) },
      token,
    ),
  setPin: (pin: string, token: string) =>
    jsonFetch<void>(`/api/v1/users/me/pin`,
      { method: "POST", body: JSON.stringify({ pin }) }, token),
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat(frontend): typed API client for approvals + PIN"
```

---

### Task D2: Approvals inbox page

**Files:**
- Create: `frontend/app/(protected)/approvals/page.tsx`
- Create: `frontend/components/workspace-switcher.tsx`

- [ ] **Step 1: Implement workspace switcher**

`frontend/components/workspace-switcher.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { createBrowserClient } from "@/lib/supabase/client";

interface Workspace { id: string; name: string; type: "personal" | "business"; }

export function WorkspaceSwitcher({
  current,
  onChange,
}: { current: string | null; onChange: (id: string) => void }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  useEffect(() => {
    const sb = createBrowserClient();
    sb.from("workspaces").select("id,name,type").then(({ data }) => {
      setWorkspaces((data as Workspace[]) || []);
    });
  }, []);
  return (
    <select
      className="border rounded px-2 py-1"
      value={current ?? ""}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="" disabled>Select workspace…</option>
      {workspaces.map((w) => (
        <option key={w.id} value={w.id}>{w.name} ({w.type})</option>
      ))}
    </select>
  );
}
```

- [ ] **Step 2: Implement inbox page**

`frontend/app/(protected)/approvals/page.tsx`:

```tsx
"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ApprovalSummary } from "@/lib/api-client";
import { createBrowserClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";

export default function ApprovalsInbox() {
  const [items, setItems] = useState<ApprovalSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    const fetchData = async () => {
      const sb = createBrowserClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.listApprovals(workspaceId, session.access_token);
      setItems(res.approvals);
    };
    fetchData();
    const t = setInterval(fetchData, 5_000);  // simple polling; Realtime is a bonus
    return () => clearInterval(t);
  }, [workspaceId]);

  return (
    <main className="p-6 max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Pending Approvals</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>
      {!workspaceId && <p className="text-muted-foreground">Pilih workspace untuk melihat approval.</p>}
      {workspaceId && items.length === 0 && (
        <p className="text-muted-foreground">Tidak ada approval yang tertunda.</p>
      )}
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.audit_id} className="border rounded p-3 flex justify-between">
            <div>
              <div className="font-medium">{it.intent ?? "—"}</div>
              <div className="text-xs text-muted-foreground">{it.created_at}</div>
            </div>
            <Link className="text-blue-600 underline" href={`/approvals/${it.audit_id}`}>
              Review
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

- [ ] **Step 3: Smoke-test in browser**

Run `make dev`, log in, visit `/approvals`. Should render the inbox shell. Without pending approvals, should show the empty state.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(protected\)/approvals/page.tsx frontend/components/workspace-switcher.tsx
git commit -m "feat(frontend): approvals inbox page with workspace switcher and polling"
```

---

### Task D3: Approval detail page + PIN modal

**Files:**
- Create: `frontend/components/pin-modal.tsx`
- Create: `frontend/components/allocation-chart.tsx`
- Create: `frontend/app/(protected)/approvals/[auditId]/page.tsx`

- [ ] **Step 1: PIN modal**

`frontend/components/pin-modal.tsx`:

```tsx
"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@base-ui/react/dialog";

export function PinModal({
  open, onSubmit, onClose, error,
}: {
  open: boolean;
  onSubmit: (pin: string) => Promise<void>;
  onClose: () => void;
  error?: string | null;
}) {
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    setLoading(true);
    try { await onSubmit(pin); } finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Konfirmasi PIN</DialogTitle>
        </DialogHeader>
        <input
          type="password"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={8}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className="border rounded px-2 py-1 w-full"
          placeholder="6-8 digit PIN"
        />
        {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
        <button
          disabled={loading || pin.length < 6}
          onClick={handle}
          className="mt-3 bg-blue-600 text-white rounded px-4 py-1 disabled:opacity-50"
        >
          {loading ? "Verifying..." : "Approve"}
        </button>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Allocation chart (simple bar list — no chart lib for hackathon)**

`frontend/components/allocation-chart.tsx`:

```tsx
export function AllocationChart({ weights }: { weights: { ticker: string; weight: number }[] }) {
  return (
    <ul className="space-y-1">
      {weights.map((w) => (
        <li key={w.ticker} className="flex items-center gap-2">
          <span className="w-16 font-mono">{w.ticker}</span>
          <div className="flex-1 bg-gray-200 h-3 rounded overflow-hidden">
            <div className="bg-blue-500 h-full" style={{ width: `${w.weight * 100}%` }} />
          </div>
          <span className="w-16 text-right tabular-nums">{(w.weight * 100).toFixed(1)}%</span>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: Approval detail page**

`frontend/app/(protected)/approvals/[auditId]/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type ApprovalDetail } from "@/lib/api-client";
import { createBrowserClient } from "@/lib/supabase/client";
import { PinModal } from "@/components/pin-modal";
import { AllocationChart } from "@/components/allocation-chart";

export default function ApprovalDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const sb = createBrowserClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setDetail(await api.getApproval(auditId, session.access_token));
    };
    load();
  }, [auditId]);

  const submitPin = async (pin: string) => {
    setPinError(null);
    const sb = createBrowserClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    try {
      await api.approve(auditId, pin, session.access_token);
      router.push(`/audit/${auditId}`);
    } catch (err) {
      setPinError(err instanceof Error ? err.message : "Gagal");
    }
  };

  const reject = async () => {
    const sb = createBrowserClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    await api.reject(auditId, "User rejected", session.access_token);
    router.push("/approvals");
  };

  if (!detail) return <p className="p-6">Loading…</p>;
  const plan = detail.plan_json;

  return (
    <main className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Approval {auditId.slice(0, 8)}…</h1>

      <section>
        <h2 className="text-lg font-medium mb-2">Alokasi yang diusulkan</h2>
        {plan ? <AllocationChart weights={plan.weights} /> : <p>Tidak ada plan.</p>}
        {plan?.narration && <p className="mt-2 text-sm">{plan.narration}</p>}
      </section>

      <section>
        <h2 className="text-lg font-medium mb-2">Kepatuhan regulasi</h2>
        <p>Status: <span className="font-medium">{detail.legal_status}</span></p>
        <ul className="list-disc pl-5 text-sm">
          {detail.legal_citations.map((c, i) => (
            <li key={i}>
              {c.source} Pasal {c.pasal}{c.ayat ? ` ayat (${c.ayat})` : ""}: <em>{c.span}</em>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex gap-3">
        <button
          onClick={() => setPinOpen(true)}
          className="bg-blue-600 text-white rounded px-4 py-2"
          disabled={detail.legal_status === "rejected" || detail.legal_status === "rejected_after_max_revisions"}
        >
          Approve dengan PIN
        </button>
        <button
          onClick={reject}
          className="border border-gray-400 rounded px-4 py-2"
        >
          Reject
        </button>
      </div>

      <PinModal
        open={pinOpen}
        onSubmit={submitPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />
    </main>
  );
}
```

- [ ] **Step 4: Smoke-test in browser**

End-to-end: log in → trigger an `agent/run` (will pause at HITL) → visit `/approvals/<auditId>` → enter wrong PIN 5× (account locks) → unset lockout in Supabase Studio (or wait 15 min) → enter correct PIN → graph resumes → redirect to audit page.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/pin-modal.tsx frontend/components/allocation-chart.tsx frontend/app/\(protected\)/approvals/\[auditId\]/page.tsx
git commit -m "feat(frontend): approval detail page with PIN modal and allocation chart"
```

---

### Task D4: Audit trail + PIN settings page

**Files:**
- Create: `frontend/components/audit-timeline.tsx`
- Create: `frontend/app/(protected)/audit/[auditId]/page.tsx`
- Create: `frontend/app/(protected)/settings/pin/page.tsx`

These are simpler than the approval flow. Audit page reads `audit_log` rows for the given audit_id and renders a timeline. PIN settings page calls `api.setPin`.

- [ ] **Step 1: Audit timeline**

`frontend/components/audit-timeline.tsx`:

```tsx
export function AuditTimeline({ events }: { events: { ts: string; node: string; status: string }[] }) {
  return (
    <ol className="border-l-2 border-gray-200 pl-4 space-y-3">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[9px] top-1 w-3 h-3 bg-blue-500 rounded-full" />
          <div className="text-xs text-muted-foreground">{e.ts}</div>
          <div className="font-medium">{e.node}</div>
          <div className="text-sm">{e.status}</div>
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 2: Audit page**

`frontend/app/(protected)/audit/[auditId]/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createBrowserClient } from "@/lib/supabase/client";
import { AuditTimeline } from "@/components/audit-timeline";

interface AuditRow { audit_id: string; status: string; created_at: string; completed_at: string | null; payload: Record<string, unknown>; }

export default function AuditPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [row, setRow] = useState<AuditRow | null>(null);

  useEffect(() => {
    const sb = createBrowserClient();
    sb.from("audit_log").select("*").eq("audit_id", auditId).single()
      .then(({ data }) => setRow(data as AuditRow | null));
  }, [auditId]);

  if (!row) return <p className="p-6">Loading…</p>;

  // Best-effort timeline reconstruction from audit_log payload + dates.
  const events = [
    { ts: row.created_at, node: "n1_intent", status: "intent classified" },
    ...(row.payload && (row.payload as { legal?: unknown }).legal
      ? [{ ts: row.created_at, node: "n3_legal", status: "legal decision recorded" }]
      : []),
    ...(row.completed_at
      ? [{ ts: row.completed_at, node: "completed", status: row.status }]
      : []),
  ];

  return (
    <main className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">Audit Trail</h1>
      <p className="text-xs text-muted-foreground mb-4">audit_id: {auditId}</p>
      <AuditTimeline events={events} />
    </main>
  );
}
```

- [ ] **Step 3: PIN settings**

`frontend/app/(protected)/settings/pin/page.tsx`:

```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { createBrowserClient } from "@/lib/supabase/client";

export default function PinSettings() {
  const [pin, setPin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async () => {
    setMsg(null);
    if (pin !== confirm) { setMsg("PIN dan konfirmasi tidak cocok."); return; }
    const sb = createBrowserClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    try {
      await api.setPin(pin, session.access_token);
      setMsg("PIN berhasil disimpan.");
      setPin(""); setConfirm("");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Gagal");
    }
  };

  return (
    <main className="p-6 max-w-md mx-auto">
      <h1 className="text-2xl font-semibold mb-4">PIN Persetujuan</h1>
      <input type="password" inputMode="numeric" maxLength={8} value={pin}
             onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
             placeholder="6-8 digit PIN" className="border rounded px-2 py-1 w-full mb-2" />
      <input type="password" inputMode="numeric" maxLength={8} value={confirm}
             onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ""))}
             placeholder="Konfirmasi PIN" className="border rounded px-2 py-1 w-full mb-2" />
      <button onClick={submit} className="bg-blue-600 text-white rounded px-4 py-2">Simpan</button>
      {msg && <p className="mt-2 text-sm">{msg}</p>}
    </main>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/audit-timeline.tsx frontend/app/\(protected\)/audit frontend/app/\(protected\)/settings
git commit -m "feat(frontend): audit timeline page + PIN settings page"
```

---

## Phase 5 Definition of Done

- [ ] All Phase 0–4 tests still pass; new Phase 5 tests pass.
- [ ] End-to-end manual flow: trigger an `agent/run` → graph pauses at N6 → `/approvals` inbox shows it → click into detail → PIN modal → wrong PIN 5× locks the account (verify in `pin_codes`) → wait/reset → correct PIN resumes graph → audit page shows N1–N7 events.
- [ ] Restart-mid-flow: kill backend after graph pauses; restart; confirm checkpoint persists and approval still works (verifies Postgres checkpointer is wired correctly).
- [ ] Workspace isolation: log in as a second user; their `/approvals` does NOT show the first user's pending approvals.
- [ ] No transaction-affecting code path bypasses N6 (grep + manual review).
