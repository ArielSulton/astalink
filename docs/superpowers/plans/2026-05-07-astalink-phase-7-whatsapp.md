# AstaLink Phase 7 — WhatsApp Channel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–6 must be complete.** Note: Meta verification has multi-day lead time; start the manual setup work in parallel with Phase 0–1.

**Goal:** Layer a WhatsApp channel on top of the graph so users can `agent/run` from chat. Inbound messages trigger the same graph as the dashboard chat box. When the graph hits the HITL gate, the bot replies with a deep link to the dashboard's approval page (PINs are entered in the dashboard, never in WhatsApp — security). When the graph terminates (executed or rejected), the bot sends a summary message.

**Architecture:**
- **Inbound:** Meta posts to `POST /api/v1/whatsapp/webhook`. We verify the signature using the App Secret, parse the message, look up the user by phone number, derive `workspace_id` from a stored binding, then call `graph.invoke(...)` with a thread_id keyed on `(phone, workspace_id)`.
- **Outbound:** after the graph returns, if it hit `__interrupt__`, send a templated message with an approval URL. If it terminated, send a summary including the audit_id link.
- **Onboarding:** unknown phone number → reply with a sign-up link including a one-time code; once they sign up via web and link the code, we record a `whatsapp_bindings` row.
- **Idempotency:** Meta retries webhooks on 5xx. We dedupe on Meta's `message_id` (insert into `whatsapp_messages_seen` table; conflict → skip).

**Tech Stack:** httpx for outbound Meta API, hmac/sha256 for signature verification, pydantic for webhook payloads.

**Scope cuts:** No interactive buttons in WhatsApp (just text replies). No media handling (text only). No multi-language detection (Indonesian only). The user manually links their phone via a "settings" page on the dashboard — automatic verification via WhatsApp OTP is post-hackathon.

---

## File Structure

```
backend/
├── app/
│   ├── integrations/
│   │   └── whatsapp.py             # CREATE: signature verify + send_message
│   └── api/
│       └── v1/
│           └── whatsapp.py         # CREATE: webhook endpoint
├── migrations/
│   └── 0009_whatsapp.sql           # CREATE: whatsapp_bindings + whatsapp_messages_seen
└── tests/
    ├── test_whatsapp_signature.py  # CREATE
    └── test_whatsapp_webhook.py    # CREATE

frontend/app/(protected)/settings/whatsapp/
└── page.tsx                        # CREATE: phone-binding UI
```

---

## Task Group A — Database Schema

### Task A1: Migration 0009

**Files:**
- Create: `backend/migrations/0009_whatsapp.sql`
- Modify: `backend/tests/test_migrations.py`

```sql
-- 0009_whatsapp.sql

create table if not exists public.whatsapp_bindings (
    user_id uuid primary key references auth.users (id) on delete cascade,
    phone_e164 text not null unique,
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    bound_at timestamptz not null default now()
);
create index if not exists wa_bindings_phone_idx on public.whatsapp_bindings (phone_e164);

create table if not exists public.whatsapp_messages_seen (
    message_id text primary key,
    received_at timestamptz not null default now()
);

create table if not exists public.whatsapp_pending_codes (
    code text primary key,
    phone_e164 text not null,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    consumed_at timestamptz
);

alter table public.whatsapp_bindings enable row level security;
create policy wa_bindings_select_own on public.whatsapp_bindings
    for select using (user_id = auth.uid());
create policy wa_bindings_insert_own on public.whatsapp_bindings
    for insert with check (user_id = auth.uid());
create policy wa_bindings_delete_own on public.whatsapp_bindings
    for delete using (user_id = auth.uid());

-- messages_seen + pending_codes are service-role only (no client access)
alter table public.whatsapp_messages_seen enable row level security;
alter table public.whatsapp_pending_codes enable row level security;
```

Append to `test_migrations.py`:

```python
def test_migration_0009_whatsapp_exists() -> None:
    sql = _read("0009_whatsapp.sql")
    for table in ("whatsapp_bindings", "whatsapp_messages_seen", "whatsapp_pending_codes"):
        assert table in sql
    assert "phone_e164" in sql
```

- [ ] Apply migration via Supabase Studio.
- [ ] Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0009_whatsapp_exists -v`
- [ ] Commit:

```bash
git add backend/migrations/0009_whatsapp.sql backend/tests/test_migrations.py
git commit -m "feat(db): WhatsApp bindings + idempotency tables"
```

---

## Task Group B — WhatsApp Integration Module

### Task B1: Signature verification + outbound send

**Files:**
- Create: `backend/app/integrations/whatsapp.py`
- Create: `backend/tests/test_whatsapp_signature.py`
- Modify: `backend/app/core/config.py`, `.env.example`, `docker-compose.yml`

Add to Settings:

```python
    # WhatsApp Business API (Meta Cloud API)
    WHATSAPP_VERIFY_TOKEN: str = ""        # used during webhook subscription
    WHATSAPP_APP_SECRET: str = ""          # for signature verification
    WHATSAPP_ACCESS_TOKEN: str = ""        # for outbound messages
    WHATSAPP_PHONE_NUMBER_ID: str = ""     # for outbound messages
    APP_BASE_URL: str = "http://localhost:3000"  # for deep links
```

Append to `.env.example`:

```
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
APP_BASE_URL=http://localhost:3000
```

Pass them all in `docker-compose.yml`.

- [ ] **Step 1: Write failing tests**

`backend/tests/test_whatsapp_signature.py`:

```python
import hashlib
import hmac

import pytest

from app.integrations.whatsapp import verify_signature


def test_verify_signature_accepts_correctly_signed_payload() -> None:
    secret = "test-secret"
    body = b'{"a": 1}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body=body, signature_header=sig, app_secret=secret) is True


def test_verify_signature_rejects_tampered_payload() -> None:
    secret = "test-secret"
    body = b'{"a": 1}'
    sig = "sha256=" + hmac.new(secret.encode(), b'{"a":2}', hashlib.sha256).hexdigest()
    assert verify_signature(body=body, signature_header=sig, app_secret=secret) is False


def test_verify_signature_rejects_missing_or_malformed_header() -> None:
    assert verify_signature(body=b"", signature_header=None, app_secret="x") is False
    assert verify_signature(body=b"", signature_header="not-a-valid-sig", app_secret="x") is False
```

- [ ] **Step 2: Implement**

`backend/app/integrations/whatsapp.py`:

```python
"""Meta WhatsApp Business API integration.

Inbound: signature verification, payload parsing.
Outbound: send_text_message via Meta Cloud API."""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

META_BASE = "https://graph.facebook.com/v20.0"


def verify_signature(*, body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not app_secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def send_text(*, to_phone_e164: str, body: str) -> None:
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        log.warning("whatsapp.send_text: skipping (creds unset)")
        return
    try:
        resp = httpx.post(
            f"{META_BASE}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone_e164,
                "type": "text",
                "text": {"body": body},
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as exc:
        log.error("whatsapp.send_text failed: %s", exc)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_whatsapp_signature.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/integrations/whatsapp.py backend/app/core/config.py .env.example docker-compose.yml backend/tests/test_whatsapp_signature.py
git commit -m "feat(whatsapp): signature verification + outbound text helper"
```

---

## Task Group C — Webhook Endpoint

### Task C1: GET (verification) + POST (inbound)

**Files:**
- Create: `backend/app/api/v1/whatsapp.py`
- Create: `backend/tests/test_whatsapp_webhook.py`
- Modify: `backend/app/api/v1/router.py`

The webhook has two roles:
- `GET /webhook` — Meta calls this once to verify ownership. Echo `hub.challenge` if `hub.verify_token` matches `WHATSAPP_VERIFY_TOKEN`.
- `POST /webhook` — every inbound message lands here.

- [ ] **Step 1: Write failing tests**

`backend/tests/test_whatsapp_webhook.py`:

```python
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_webhook_get_verifies_subscription(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "appsec")
    # Reload settings so the new env is picked up
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "secret123",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_get_rejects_wrong_verify_token(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 403


def test_webhook_post_dedupes_replays(client: TestClient, monkeypatch) -> None:
    """Same Meta message_id arriving twice must invoke the graph at most once."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.MSG-ABC",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "alokasikan ke BBCA"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    # First call: row doesn't exist — insert succeeds.
    # Second call: insert fails on PK conflict — caught and treated as already-seen.
    insert_mock = fake_admin.table.return_value.insert
    insert_mock.return_value.execute.side_effect = [
        MagicMock(data=[{}]),       # first
        Exception("duplicate key"),  # second
    ]
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    invoke_mock = MagicMock(return_value={"messages": [], "transactions": []})

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", invoke_mock), \
         patch("app.api.v1.whatsapp.send_text"):
        # First delivery
        r1 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})
        # Replay
        r2 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})

    assert r1.status_code == 200 and r2.status_code == 200
    assert invoke_mock.call_count == 1, "graph must run exactly once for a replayed message_id"
```

- [ ] **Step 2: Implement endpoint**

`backend/app/api/v1/whatsapp.py`:

```python
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from langchain_core.messages import HumanMessage

from app.agents.graph import graph
from app.agents.state import new_state
from app.core.config import settings
from app.core.supabase_admin import get_admin_client
from app.integrations.whatsapp import send_text, verify_signature

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/webhook")
async def verify(
    hub_mode: str | None = None,
    hub_verify_token: str | None = None,
    hub_challenge: str | None = None,
    request: Request = None,
):
    # FastAPI doesn't bind dotted query params natively; pull from request.
    qp = dict(request.query_params)
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid verify token")


def _already_seen(message_id: str) -> bool:
    try:
        get_admin_client().table("whatsapp_messages_seen").insert({
            "message_id": message_id,
        }).execute()
        return False
    except Exception:
        # Duplicate primary key → message already processed.
        return True


def _resolve_user(phone_e164: str) -> dict[str, str] | None:
    res = (
        get_admin_client().table("whatsapp_bindings")
        .select("user_id, workspace_id").eq("phone_e164", phone_e164).single().execute()
    )
    return res.data


def _onboarding_link(phone_e164: str) -> str:
    """Generate a one-time code and return the dashboard URL the user should
    open after signing up to bind their phone."""
    import secrets
    code = secrets.token_urlsafe(8)
    from datetime import datetime, timedelta, timezone
    get_admin_client().table("whatsapp_pending_codes").insert({
        "code": code,
        "phone_e164": phone_e164,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }).execute()
    return f"{settings.APP_BASE_URL}/settings/whatsapp?code={code}"


@router.post("/webhook")
async def receive(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()
    if not verify_signature(body=body, signature_header=x_hub_signature_256,
                            app_secret=settings.WHATSAPP_APP_SECRET):
        raise HTTPException(status_code=403, detail="bad signature")

    payload: dict[str, Any] = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                _process_message(msg)
    return {"ok": True}


def _process_message(msg: dict[str, Any]) -> None:
    msg_id = msg.get("id")
    if not msg_id or _already_seen(msg_id):
        return

    phone = msg.get("from")
    text = (msg.get("text") or {}).get("body", "")
    if msg.get("type") != "text" or not phone or not text:
        return

    binding = _resolve_user(phone)
    if not binding:
        link = _onboarding_link(phone)
        send_text(to_phone_e164=phone,
                  body=f"Halo! Untuk memulai AstaLink, silakan daftar dan link nomor Anda: {link}")
        return

    initial = new_state()
    initial["messages"] = [HumanMessage(content=text)]
    initial["entities"] = {"workspace_id": binding["workspace_id"]}
    initial["_user_id"] = binding["user_id"]                # type: ignore[misc]
    initial["_workspace_id"] = binding["workspace_id"]      # type: ignore[misc]

    thread_id = f"wa-{phone}-{binding['workspace_id']}"
    final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

    audit_id = final.get("audit_id")
    if final.get("__interrupt__") or final.get("user_approval") is None:
        link = f"{settings.APP_BASE_URL}/approvals/{audit_id}"
        send_text(to_phone_e164=phone,
                  body=f"Saya sudah menyiapkan rekomendasi alokasi.\nReview & approve di: {link}")
    elif final.get("transactions"):
        n = len(final["transactions"])
        send_text(to_phone_e164=phone,
                  body=f"Eksekusi selesai: {n} order. Detail: {settings.APP_BASE_URL}/audit/{audit_id}")
    else:
        send_text(to_phone_e164=phone,
                  body="Permintaan tidak dapat diproses. Coba pesan yang lebih spesifik.")
```

Wire in router:

```python
from app.api.v1 import whatsapp as wa_router
api_router.include_router(wa_router.router, prefix="/whatsapp", tags=["whatsapp"])
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run python -m pytest tests/test_whatsapp_webhook.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/whatsapp.py backend/app/api/v1/router.py backend/tests/test_whatsapp_webhook.py
git commit -m "feat(whatsapp): inbound webhook with signature verify + dedup + graph dispatch"
```

---

## Task Group D — Phone Binding UI

### Task D1: Settings page to claim a one-time code

**Files:**
- Create: `frontend/app/(protected)/settings/whatsapp/page.tsx`
- Create: `backend/app/api/v1/whatsapp_bind.py`

`POST /api/v1/whatsapp/bind` accepts `{code, workspace_id}`, looks up the unconsumed pending_code, inserts a `whatsapp_bindings` row, marks the code consumed.

- [ ] Write the endpoint (similar pattern to approvals: validate user owns workspace, validate code unconsumed and unexpired, atomic update).
- [ ] Frontend page reads `?code=` from URL, shows "Bind this number to workspace X?" with confirmation.
- [ ] Manual test: trigger the onboarding flow by sending a WhatsApp message from an unknown number; receive the link; click; bind; resend the same query; verify it now flows to the graph.
- [ ] Commit.

(Detail-level implementation deferred to in-execution polish — pattern is identical to PIN settings + approvals.)

---

## Phase 7 Definition of Done

- [ ] Meta Business verification complete; phone number provisioned; webhook URL configured in Meta dashboard pointing at `https://<your-domain>/api/v1/whatsapp/webhook`.
- [ ] All Phase 0–6 tests still pass; Phase 7 tests pass.
- [ ] Migration 0009 applied.
- [ ] End-to-end demo: send WhatsApp text "alokasikan 5jt ke BBCA" → bot replies with approval link → click → dashboard approval → enter PIN → bot confirms execution.
- [ ] Replay test: resending the same message (Meta retry simulation) does NOT double-process.
- [ ] Unknown-number flow: a phone with no binding receives the sign-up link instead of an error.
- [ ] PINs are NEVER accepted via WhatsApp text — verified by code review.
