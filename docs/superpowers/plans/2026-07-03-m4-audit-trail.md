# M4 Audit Trail UI & Read API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give users a readable audit trail — a backend read API plus `/audit` list and `/audit/[auditId]` detail pages — so every AI-CIO decision is inspectable by `audit_id`.

**Architecture:** Read-only FastAPI router (`/audit`) that assembles run history and per-run detail from the already-persisted `audit_log` + `allocation_plans` + `transactions` tables (no DB migration, no pipeline change). Frontend mirrors the existing approvals list/detail pages. Plus foundation cleanup: delete dead `stubs.py`, fix misleading `graph.py` docstring, update PRD milestone status.

**Tech Stack:** FastAPI, Pydantic, Supabase (service-role admin client), pytest (`asyncio_mode="auto"`), Next.js 16 App Router, React 19, TypeScript strict, Tailwind v4.

## Global Constraints

- Auth on every audit endpoint via `get_current_user` (Supabase JWT bearer) — copy the approvals pattern exactly.
- Audit reads use `get_admin_client()` and MUST filter by both `workspace_id` and `user_id` (`user["sub"]`) — never leak another user's runs.
- Preserve boots-without-keys: no new required env var, no import that fails when optional keys are absent.
- No backend linter/formatter — match existing style. Frontend: TypeScript strict, verify with `npx tsc --noEmit`.
- Backend tests run: `cd backend && PYTHONPATH="" uv run python -m pytest tests/ -v`.
- UI copy is Indonesian (match existing pages: "Memuat…", "Tidak ada…").
- Frequent commits: one per task.

---

### Task 1: Audit response models

**Files:**
- Create: `backend/app/models/audit.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `AuditSummary(audit_id: str, intent: str | None, status: str, created_at: str, completed_at: str | None)`
  - `AuditListResponse(audits: list[AuditSummary])`
  - `AuditDetail(audit_id: str, status: str, intent: str | None, workspace_id: str, created_at: str, completed_at: str | None, allocation_plan: dict | None, legal_status: str | None, legal_citations: list[dict], transactions: list[dict])`

- [ ] **Step 1: Write the models file**

```python
# backend/app/models/audit.py
from typing import Any

from pydantic import BaseModel, Field


class AuditSummary(BaseModel):
    audit_id: str
    intent: str | None = None
    status: str
    created_at: str
    completed_at: str | None = None


class AuditListResponse(BaseModel):
    audits: list[AuditSummary]


class AuditDetail(BaseModel):
    audit_id: str
    status: str
    intent: str | None = None
    workspace_id: str
    created_at: str
    completed_at: str | None = None
    allocation_plan: dict[str, Any] | None = None
    legal_status: str | None = None
    legal_citations: list[dict[str, Any]] = Field(default_factory=list)
    transactions: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 2: Verify it imports**

Run: `cd backend && PYTHONPATH="" uv run python -c "from app.models.audit import AuditSummary, AuditListResponse, AuditDetail; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/audit.py
git commit -m "feat(audit): add audit response models"
```

---

### Task 2: Audit read API router

**Files:**
- Create: `backend/app/api/v1/audit.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_audit_endpoint.py`

**Interfaces:**
- Consumes: `AuditSummary`, `AuditListResponse`, `AuditDetail` from Task 1; `get_current_user` from `app.api.deps`; `get_admin_client` from `app.core.supabase_admin`.
- Produces: HTTP routes `GET /api/v1/audit?workspace_id=<id>` and `GET /api/v1/audit/{audit_id}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_audit_endpoint.py
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_list_audit_returns_all_statuses_for_user_workspace(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    workspace_id = str(uuid.uuid4())

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .eq.return_value.order.return_value.execute.return_value) = MagicMock(
        data=[
            {"audit_id": "a1", "intent": "allocate_stocks", "status": "approved",
             "created_at": "2026-05-04T00:00:00Z", "completed_at": "2026-05-04T00:01:00Z",
             "workspace_id": workspace_id, "user_id": user["sub"]},
            {"audit_id": "a2", "intent": "allocate_stocks", "status": "rejected",
             "created_at": "2026-05-03T00:00:00Z", "completed_at": None,
             "workspace_id": workspace_id, "user_id": user["sub"]},
        ]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit?workspace_id={workspace_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["audits"]) == 2
    statuses = {a["status"] for a in body["audits"]}
    assert statuses == {"approved", "rejected"}


def test_get_audit_detail_assembles_plan_and_transactions(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = [
        MagicMock(data={"audit_id": audit_id, "status": "approved",
                        "intent": "allocate_stocks", "workspace_id": "w",
                        "created_at": "2026-05-04T00:00:00Z",
                        "completed_at": "2026-05-04T00:01:00Z",
                        "user_id": user["sub"]}),
        MagicMock(data={"plan_json": {"weights": [{"ticker": "BBCA", "weight": 0.5}], "cash": 1000},
                        "legal_status": "approved", "legal_citations": []}),
    ]
    # transactions: .table().select().eq().execute() (no .single)
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(
        data=[{"ticker": "BBCA", "side": "buy", "quantity": 5, "status": "filled",
               "broker_ref": "SBX-1"}]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"] == audit_id
    assert body["allocation_plan"]["cash"] == 1000
    assert body["legal_status"] == "approved"
    assert len(body["transactions"]) == 1
    assert body["transactions"][0]["ticker"] == "BBCA"


def test_get_audit_detail_rejects_other_users_run(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.return_value) = MagicMock(
        data={"audit_id": audit_id, "status": "approved", "intent": "x",
              "workspace_id": "w", "created_at": "2026-05-04T00:00:00Z",
              "completed_at": None, "user_id": "SOMEONE-ELSE"}
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 404


def test_get_audit_detail_tolerates_missing_plan(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = [
        MagicMock(data={"audit_id": audit_id, "status": "rejected",
                        "intent": "allocate_stocks", "workspace_id": "w",
                        "created_at": "2026-05-04T00:00:00Z",
                        "completed_at": None, "user_id": user["sub"]}),
        MagicMock(data=None),  # no allocation_plans row
    ]
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["allocation_plan"] is None
    assert body["transactions"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH="" uv run python -m pytest tests/test_audit_endpoint.py -v`
Expected: FAIL — 404 on all routes (router not registered yet).

- [ ] **Step 3: Write the router**

```python
# backend/app/api/v1/audit.py
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.supabase_admin import get_admin_client
from app.models.audit import AuditDetail, AuditListResponse, AuditSummary

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AuditListResponse)
async def list_audit(
    workspace_id: str, user: dict = Depends(get_current_user)
) -> AuditListResponse:
    res = (
        get_admin_client().table("audit_log")
        .select("audit_id, intent, status, created_at, completed_at, workspace_id, user_id")
        .eq("workspace_id", workspace_id)
        .eq("user_id", user["sub"])
        .order("created_at", desc=True)
        .execute()
    )
    audits = [
        AuditSummary(
            audit_id=row["audit_id"],
            intent=row.get("intent"),
            status=row.get("status", "unknown"),
            created_at=row.get("created_at", ""),
            completed_at=row.get("completed_at"),
        )
        for row in (res.data or [])
    ]
    return AuditListResponse(audits=audits)


def _load_audit(audit_id: str, user_sub: str) -> dict:
    audit = (
        get_admin_client().table("audit_log").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data
    if not audit or audit.get("user_id") != user_sub:
        raise HTTPException(status_code=404, detail="not found")
    return audit


@router.get("/{audit_id}", response_model=AuditDetail)
async def get_audit(
    audit_id: str, user: dict = Depends(get_current_user)
) -> AuditDetail:
    audit = _load_audit(audit_id, user["sub"])

    plan_row = (
        get_admin_client().table("allocation_plans").select("*")
        .eq("audit_id", audit_id).single().execute()
    ).data or {}

    tx_res = (
        get_admin_client().table("transactions").select("*")
        .eq("audit_id", audit_id).execute()
    )

    return AuditDetail(
        audit_id=audit_id,
        status=audit.get("status", "unknown"),
        intent=audit.get("intent"),
        workspace_id=audit["workspace_id"],
        created_at=audit.get("created_at", ""),
        completed_at=audit.get("completed_at"),
        allocation_plan=plan_row.get("plan_json"),
        legal_status=plan_row.get("legal_status"),
        legal_citations=plan_row.get("legal_citations") or [],
        transactions=tx_res.data or [],
    )
```

- [ ] **Step 4: Register the router**

In `backend/app/api/v1/router.py`, add `audit` to the imports and include it. The file becomes:

```python
from fastapi import APIRouter

from app.api.v1 import agent, audit, chat, health, legal, market
from app.api.v1 import approvals as approvals_router
from app.api.v1 import pin as pin_router
from app.api.v1 import whatsapp as wa_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(pin_router.router, prefix="/users", tags=["pin"])
api_router.include_router(approvals_router.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH="" uv run python -m pytest tests/test_audit_endpoint.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/audit.py backend/app/api/v1/router.py backend/tests/test_audit_endpoint.py
git commit -m "feat(audit): add read API for run history and detail"
```

---

### Task 3: Frontend api-client audit methods

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Consumes: `jsonFetch` helper and `api` object already in the file.
- Produces:
  - `AuditSummary` interface, `AuditDetail` interface.
  - `api.listAudit(workspaceId, token) => Promise<{ audits: AuditSummary[] }>`
  - `api.getAudit(auditId, token) => Promise<AuditDetail>`

- [ ] **Step 1: Add interfaces after the existing `ApprovalDetail` interface (after line 25)**

```typescript
export interface AuditSummary {
  audit_id: string;
  intent: string | null;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface AuditDetail {
  audit_id: string;
  status: string;
  intent: string | null;
  workspace_id: string;
  created_at: string;
  completed_at: string | null;
  allocation_plan: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  legal_status: string | null;
  legal_citations: { source: string; pasal: string; ayat: string | null; span: string }[];
  transactions: {
    ticker: string;
    side: string;
    quantity: number;
    status: string;
    broker_ref: string | null;
  }[];
}
```

- [ ] **Step 2: Add methods to the `api` object (after the `reject` method, before `setPin`)**

```typescript
  listAudit: (workspaceId: string, token: string) =>
    jsonFetch<{ audits: AuditSummary[] }>(
      `/api/v1/audit?workspace_id=${workspaceId}`, { method: "GET" }, token,
    ),
  getAudit: (auditId: string, token: string) =>
    jsonFetch<AuditDetail>(`/api/v1/audit/${auditId}`, { method: "GET" }, token),
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat(audit): add audit api-client methods"
```

---

### Task 4: Audit list page

**Files:**
- Create: `frontend/app/(protected)/audit/page.tsx`

**Interfaces:**
- Consumes: `api.listAudit`, `AuditSummary` from Task 3; `createClient` from `@/lib/supabase/client`; `WorkspaceSwitcher` from `@/components/workspace-switcher`.
- Produces: route `/audit`.

- [ ] **Step 1: Write the page** (mirrors `approvals/page.tsx`; no polling — audit is historical)

```tsx
"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type AuditSummary } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { History, ArrowRight } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  approved: "text-emerald-400 bg-emerald-500/10 border-emerald-500/15",
  rejected: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  rejected_after_max_revisions: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/15",
};

export default function AuditTrail() {
  const [items, setItems] = useState<AuditSummary[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    const fetchData = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const res = await api.listAudit(workspaceId, session.access_token);
      setItems(res.audits);
    };
    fetchData();
  }, [workspaceId]);

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground">
      <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Decision Ledger
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Jejak Audit
          </h1>
        </div>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      {!workspaceId && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Pilih workspace untuk melihat jejak keputusan.
        </div>
      )}

      {workspaceId && items.length === 0 && (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
          Belum ada keputusan tercatat untuk workspace ini.
        </div>
      )}

      {workspaceId && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((it) => {
            const formattedDate = new Date(it.created_at).toLocaleDateString("id-ID", {
              day: "numeric", month: "short", year: "numeric",
              hour: "2-digit", minute: "2-digit",
            });
            const badge = STATUS_STYLE[it.status] ?? "text-muted-foreground bg-secondary border-border";
            return (
              <li
                key={it.audit_id}
                className="flex items-center justify-between p-4 bg-card border border-border rounded-2xl hover:border-primary/30 hover:bg-primary/[0.04] transition-all duration-200"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <History className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-foreground text-sm tracking-tight truncate">
                      {it.intent ?? "Keputusan Portofolio"}
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {formattedDate}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge}`}>
                    {it.status}
                  </span>
                  <Link
                    href={`/audit/${it.audit_id}`}
                    className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold transition-all duration-200"
                  >
                    Detail
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/(protected)/audit/page.tsx"
git commit -m "feat(audit): add audit trail list page"
```

---

### Task 5: Audit detail page

**Files:**
- Create: `frontend/app/(protected)/audit/[auditId]/page.tsx`

**Interfaces:**
- Consumes: `api.getAudit`, `AuditDetail` from Task 3; `createClient`; `AllocationChart` from `@/components/allocation-chart` (used by approvals detail — same `weights` prop).
- Produces: route `/audit/[auditId]`. This is the deep-link target from WhatsApp and the post-approve redirect in `approvals/[auditId]/page.tsx`.

- [ ] **Step 1: Write the page** (decision timeline: intent → alokasi → legal → status → transaksi)

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type AuditDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { AllocationChart } from "@/components/allocation-chart";
import { Target, ShieldCheck, Scale, CheckCircle2, Receipt } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  approved: "text-emerald-400 bg-emerald-500/10 border-emerald-500/15",
  partial: "text-amber-400 bg-amber-500/10 border-amber-500/15",
  rejected: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  rejected_after_max_revisions: "text-rose-400 bg-rose-500/10 border-rose-500/15",
  awaiting_approval: "text-amber-400 bg-amber-500/10 border-amber-500/15",
};

function badge(status: string | null): string {
  if (!status) return "text-muted-foreground bg-secondary border-border";
  return STATUS_STYLE[status] ?? "text-muted-foreground bg-secondary border-border";
}

export default function AuditDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [detail, setDetail] = useState<AuditDetail | null>(null);

  useEffect(() => {
    const load = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setDetail(await api.getAudit(auditId, session.access_token));
    };
    load();
  }, [auditId]);

  if (!detail) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-muted-foreground text-xs font-mono tracking-wider">
        <span className="w-2 h-2 rounded-full bg-primary animate-ping mr-2.5" />
        Memuat jejak audit…
      </div>
    );
  }

  const plan = detail.allocation_plan;

  return (
    <main className="p-8 max-w-4xl mx-auto bg-background min-h-screen text-foreground space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
            Decision Trace
          </p>
          <h1 className="text-foreground text-2xl font-bold tracking-tight">
            Audit #{auditId.slice(0, 8)}…
          </h1>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge(detail.status)}`}>
          {detail.status}
        </span>
      </div>

      {/* 1 — Intent */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-2">
          <Target className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Permintaan</h2>
        </div>
        <p className="text-sm text-muted-foreground">{detail.intent ?? "—"}</p>
      </section>

      {/* 2 — Alokasi */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Alokasi</h2>
        </div>
        {plan ? <AllocationChart weights={plan.weights} /> : <p className="text-sm text-muted-foreground">Tidak ada data alokasi.</p>}
        {plan?.narration && (
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-4">
            {plan.narration}
          </p>
        )}
      </section>

      {/* 3 — Legal */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-border pb-4">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <h2 className="text-foreground font-bold text-base tracking-tight">Kepatuhan regulasi</h2>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider border ${badge(detail.legal_status)}`}>
            {detail.legal_status ?? "—"}
          </span>
        </div>
        {detail.legal_citations.length === 0 ? (
          <p className="text-sm text-muted-foreground">Tidak ada catatan hukum terlampir.</p>
        ) : (
          <ul className="space-y-4">
            {detail.legal_citations.map((c, i) => (
              <li key={i} className="bg-secondary border border-border rounded-xl p-4 text-sm leading-relaxed text-muted-foreground">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/15 font-mono text-[9px] font-bold text-primary uppercase tracking-wider">
                    {c.source}
                  </span>
                  <span className="text-[10px] text-foreground font-semibold font-mono">
                    Pasal {c.pasal}{c.ayat ? ` ayat (${c.ayat})` : ""}
                  </span>
                </div>
                <div className="italic font-serif pl-3 border-l border-border mt-2 text-foreground/85">
                  &ldquo;{c.span}&rdquo;
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 4 — Transaksi */}
      <section className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <Receipt className="h-5 w-5 text-primary" />
          <h2 className="text-foreground font-bold text-base tracking-tight">Transaksi</h2>
        </div>
        {detail.transactions.length === 0 ? (
          <p className="text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Tidak ada transaksi tereksekusi.
          </p>
        ) : (
          <ul className="space-y-2">
            {detail.transactions.map((t, i) => (
              <li key={i} className="flex items-center justify-between bg-secondary border border-border rounded-xl p-3 text-sm">
                <div className="flex items-center gap-2 font-mono">
                  <span className="font-bold text-foreground">{t.ticker}</span>
                  <span className="uppercase text-[10px] text-muted-foreground">{t.side}</span>
                  <span className="text-muted-foreground">×{t.quantity}</span>
                </div>
                <div className="flex items-center gap-2">
                  {t.broker_ref && <span className="text-[10px] text-muted-foreground font-mono">{t.broker_ref}</span>}
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold font-mono uppercase border ${badge(t.status)}`}>
                    {t.status}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/(protected)/audit/[auditId]/page.tsx"
git commit -m "feat(audit): add audit detail decision-timeline page"
```

---

### Task 6: Foundation cleanup

**Files:**
- Delete: `backend/app/agents/stubs.py`
- Modify: `backend/app/agents/graph.py:1-5` (docstring)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing (removal + docstring only). `graph.py` must still import and compile.

- [ ] **Step 1: Confirm `stubs.py` is not imported anywhere**

Run: `cd backend && grep -rn "stubs" app/ --include="*.py"`
Expected: matches ONLY inside `app/agents/stubs.py` itself (self-references). If any OTHER file imports it, STOP and do not delete — report instead.

- [ ] **Step 2: Delete the dead module**

```bash
git rm backend/app/agents/stubs.py
```

- [ ] **Step 3: Fix the misleading docstring in `graph.py`**

Replace lines 1–5 (the module docstring) with:

```python
"""AstaLink LangGraph wiring.

All nodes are real: intent, market, business, risk, optimizer, legal,
hitl (real interrupt-based pause), and execution."""
```

- [ ] **Step 4: Verify the graph still compiles**

Run: `cd backend && PYTHONPATH="" uv run python -c "from app.agents.graph import graph; print('graph ok')"`
Expected: prints `graph ok`.

- [ ] **Step 5: Run the full backend suite (nothing broke)**

Run: `cd backend && PYTHONPATH="" uv run python -m pytest tests/ -v`
Expected: PASS (including the new audit tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/graph.py
git commit -m "chore(agents): remove dead stubs.py, fix graph docstring"
```

---

### Task 7: Update PRD milestone status

**Files:**
- Modify: `prd-astalink.md` (§13 Timeline & Milestone table)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing (docs only).

- [ ] **Step 1: Update the milestone table in `prd-astalink.md` §13**

Replace the M1–M5 rows so status reflects reality:

```markdown
| M1 | Pipeline end-to-end dengan node riil (N1–N5) | ✅ Selesai | Backend |
| M2 | Legal RAG + loop revisi + HITL pause (PostgresSaver) | ✅ Selesai | Backend |
| M3 | Integrasi broker N7 (sandbox) + PIN/approval UI | 🟡 Sebagian — sandbox buy-only; broker riil (Phase 8) tertunda | Backend/Frontend |
| M4 | Observability (Grafana) + audit trail read API & UI | ✅ Selesai | DevOps/Frontend |
| M5 | Beta terbatas + hardening keamanan/compliance | ⬜ Belum | Semua |
```

- [ ] **Step 2: Commit**

```bash
git add prd-astalink.md
git commit -m "docs: mark M4 complete, M3 partial in PRD timeline"
```

---

## Verification (end-to-end, after all tasks)

Requires a live Supabase project (see `SUPABASE_SETUP.md`) and a run in `audit_log`.

- [ ] Backend suite green: `cd backend && PYTHONPATH="" uv run python -m pytest tests/ -v`
- [ ] `curl -s "http://localhost:8010/api/v1/audit?workspace_id=<id>" -H "Authorization: Bearer <token>"` returns run list.
- [ ] Visit `http://localhost:3001/audit` → history table renders; click a row → detail timeline shows intent → alokasi → legal → transaksi.
- [ ] After approving a run in `/approvals/[id]`, the redirect to `/audit/[id]` now lands on a real page (previously 404).
- [ ] Stack still boots with optional keys absent.

## Self-Review Notes

- **Spec coverage:** §5A → Tasks 1–2; §5B → Tasks 3–5; §5C → Tasks 6–7. All spec sections mapped.
- **Type consistency:** `AuditSummary`/`AuditDetail` field names identical across backend model (Task 1), API (Task 2), and frontend interface (Task 3). `allocation_plan` (not `plan_json`) used consistently on the audit side — deliberately differs from approvals' `plan_json` because the audit model names it `allocation_plan`; the frontend interface matches.
- **No new required env:** audit router only uses the already-lazy admin client. Boots-without-keys preserved.
