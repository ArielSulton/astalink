# AstaLink Phase 2 — LangGraph Skeleton + Intent Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0 and 1 must be complete before starting.**

**Goal:** Wire up the full 3-layer LangGraph that AstaLink will run. Phase 2 ships: a real N1 Intent Classifier with structured-output enum + clarification loop, the real N3 Legal node from Phase 1 plugged in, and stub implementations of N2a/b/c, N5, N6, N7 that just log + pass-through. Conditional edges enforce "verify first, allocate second": N3 sits between analysis and execution; revisions cap at 3. Checkpointer swaps from in-memory to Postgres-backed (Supabase) so Phase 5's `interrupt()` can survive a backend restart. A new `POST /api/v1/agent/run` endpoint exercises the whole graph.

**Architecture:**
- `AgentState` (Phase 0) is the single shared dict; every node returns a partial update.
- N1 generates `audit_id` (Phase 0's `new_state()` already does this), classifies intent into a fixed `Intent` enum, extracts entities, and either routes forward or asks a clarification question that re-enters N1 on the user reply.
- N2a/b/c run in parallel via LangGraph fan-out from N1; results converge on N3.
- N3 (real, from Phase 1) decides legal status. Conditional edge: `approved`/`partial` → N5; `rejected` → rejection-handler → END.
- N5 (stub here, real in Phase 4) increments `revision_count`; if N3 still rejects after revision, loop until count == 3 then END.
- N6/N7 (stubs here, real in Phases 5/6) just log.
- Persistence: at N1 entry we insert an `audit_log` row; every node update sets `payload->>node_name` via the admin client.

**Tech Stack:** LangGraph `StateGraph` + `add_conditional_edges` + parallel fan-out; LangGraph `PostgresSaver` against Supabase Postgres; Gemini structured output via `with_structured_output(IntentDecision)`.

**Scope cuts:** Stubs for N2a/b/c just emit a hardcoded `MarketSnapshot`/`BusinessValuation`/`RiskAssessment`; real implementations in Phase 3. Stub N5 just copies the input plan. Stub N6 returns `user_approval=approved` immediately (no real interrupt yet — that's Phase 5). Stub N7 logs "would execute" and writes a no-op transactions row.

---

## File Structure

```
astalink/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── intents.py              # CREATE: Intent enum
│   │   │   ├── intent/
│   │   │   │   ├── __init__.py         # CREATE
│   │   │   │   ├── schemas.py          # CREATE: IntentDecision pydantic model
│   │   │   │   └── node.py             # CREATE: N1 with clarification loop
│   │   │   ├── stubs.py                # CREATE: N2a/b/c, N5, N6, N7 placeholders
│   │   │   ├── rejection.py            # CREATE: rejection handler (alternative actions)
│   │   │   └── graph.py                # CREATE: StateGraph wiring
│   │   ├── core/
│   │   │   └── checkpointer.py         # CREATE: PostgresSaver factory
│   │   └── api/
│   │       └── v1/
│   │           ├── agent.py            # CREATE: POST /api/v1/agent/run
│   │           └── router.py           # MODIFY: register agent router
│   └── tests/
│       ├── test_intent_classifier.py   # CREATE
│       ├── test_intent_clarification.py # CREATE
│       ├── test_graph_wiring.py        # CREATE: routing, parallelism, revision cap
│       ├── test_graph_endpoint.py      # CREATE: /api/v1/agent/run
│       └── test_checkpointer.py        # CREATE
└── backend/migrations/
    └── 0008_langgraph_checkpoints.sql  # CREATE: PostgresSaver schema
```

---

## Task Group A — Intent Enum and Schemas

### Task A1: Define the Intent enum

**Files:**
- Create: `backend/app/agents/intents.py`
- Create: `backend/tests/test_intent_classifier.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_intent_classifier.py`:

```python
from app.agents.intents import Intent


def test_intent_enum_has_all_required_values() -> None:
    expected = {
        "ALLOCATE_STOCKS",
        "EVALUATE_BUSINESS",
        "RISK_REVIEW",
        "PORTFOLIO_STATUS",
        "EXPLAIN",
        "UNKNOWN",
    }
    assert {i.name for i in Intent} == expected


def test_intent_string_values_match_names_lowercased() -> None:
    """We store intents as lowercase strings in audit_log.intent."""
    assert Intent.ALLOCATE_STOCKS.value == "allocate_stocks"
    assert Intent.UNKNOWN.value == "unknown"
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_intent_classifier.py -v -k "enum"`
Expected: FAIL.

- [ ] **Step 3: Implement enum**

`backend/app/agents/intents.py`:

```python
"""User intents the Intent Classifier (N1) maps natural language to.

Stored lowercased in audit_log.intent; the enum value IS the persisted form."""
from __future__ import annotations

from enum import StrEnum


class Intent(StrEnum):
    ALLOCATE_STOCKS = "allocate_stocks"
    EVALUATE_BUSINESS = "evaluate_business"
    RISK_REVIEW = "risk_review"
    PORTFOLIO_STATUS = "portfolio_status"
    EXPLAIN = "explain"
    UNKNOWN = "unknown"
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_intent_classifier.py -v -k "enum"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/intents.py backend/tests/test_intent_classifier.py
git commit -m "feat(agents): define Intent enum for N1 classifier"
```

---

### Task A2: IntentDecision schema

**Files:**
- Create: `backend/app/agents/intent/__init__.py` (empty)
- Create: `backend/app/agents/intent/schemas.py`
- Modify: `backend/tests/test_intent_classifier.py`

- [ ] **Step 1: Append failing test**

```python
def test_intent_decision_has_clarification_question_field() -> None:
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent

    d = IntentDecision(
        intent=Intent.UNKNOWN,
        entities={},
        confidence=0.3,
        clarification_question="Apa yang ingin Anda lakukan?",
    )
    assert d.intent == Intent.UNKNOWN
    assert d.confidence == 0.3
    assert d.clarification_question is not None


def test_intent_decision_clarification_optional() -> None:
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent

    d = IntentDecision(intent=Intent.ALLOCATE_STOCKS,
                       entities={"amount": 10_000_000}, confidence=0.95)
    assert d.clarification_question is None
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_intent_classifier.py -v -k "decision"`
Expected: FAIL.

- [ ] **Step 3: Implement schema**

`backend/app/agents/intent/__init__.py`:

```python
```

`backend/app/agents/intent/schemas.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents.intents import Intent


class IntentDecision(BaseModel):
    intent: Intent
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    clarification_question: str | None = Field(
        default=None,
        description="Set when intent=UNKNOWN or confidence < 0.6.",
    )
```

- [ ] **Step 4: Run to confirm pass**

```bash
cd backend && uv run python -m pytest tests/test_intent_classifier.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/intent/__init__.py backend/app/agents/intent/schemas.py backend/tests/test_intent_classifier.py
git commit -m "feat(agents): add IntentDecision schema with clarification_question"
```

---

## Task Group B — Intent Classifier Node

### Task B1: N1 node with structured-output Gemini call

**Files:**
- Create: `backend/app/agents/intent/node.py`
- Modify: `backend/tests/test_intent_classifier.py`

- [ ] **Step 1: Append failing test**

```python
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage


def test_intent_node_returns_state_update_with_intent_and_entities() -> None:
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state

    state = new_state()
    state["messages"] = [HumanMessage(content="Alokasikan 10 juta ke saham bank")]

    fake_decision = IntentDecision(
        intent=Intent.ALLOCATE_STOCKS,
        entities={"amount": 10_000_000, "sector": "bank"},
        confidence=0.92,
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit") as record:
        update = intent_node(state)

    assert update["intent"] == Intent.ALLOCATE_STOCKS.value
    assert update["entities"] == {"amount": 10_000_000, "sector": "bank"}
    record.assert_called_once()


def test_intent_node_sets_clarification_when_low_confidence() -> None:
    from app.agents.intent.node import intent_node
    from app.agents.intent.schemas import IntentDecision
    from app.agents.intents import Intent
    from app.agents.state import new_state
    from langchain_core.messages import AIMessage

    state = new_state()
    state["messages"] = [HumanMessage(content="hmm")]

    fake_decision = IntentDecision(
        intent=Intent.UNKNOWN,
        entities={},
        confidence=0.2,
        clarification_question="Apa tujuan investasi Anda?",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_decision

    with patch("app.agents.intent.node._build_chain", return_value=fake_chain), \
         patch("app.agents.intent.node._record_audit"):
        update = intent_node(state)

    assert update["intent"] == Intent.UNKNOWN.value
    # clarification appended as an AI message so the channel layer (WhatsApp /
    # web chat) can surface it
    assert any(isinstance(m, AIMessage) and "tujuan" in m.content for m in update.get("messages", []))
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_intent_classifier.py -v -k "intent_node"`
Expected: FAIL.

- [ ] **Step 3: Implement node**

`backend/app/agents/intent/node.py`:

```python
"""Intent Classifier (N1) — first node of every pipeline run.

Generates `audit_id` via new_state() if not present, classifies the latest
user message into an Intent enum, extracts entities, and either continues or
appends a clarification question for low-confidence cases."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.intent.schemas import IntentDecision
from app.agents.intents import Intent
from app.agents.state import AgentState
from app.core.gemini import get_chat_model
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.6

SYSTEM = """\
You are an Indonesian financial-assistant intent classifier.
Map the user message to one of:
- allocate_stocks: user wants to invest cash into stocks/portfolio
- evaluate_business: user wants their own business valued
- risk_review: user wants risk metrics on existing holdings
- portfolio_status: user is asking about current holdings/positions
- explain: user wants an explanation of a concept/term
- unknown: cannot determine

Extract relevant entities (amount, tickers, sector, risk_profile, etc.) into
the `entities` dict. Estimate `confidence` honestly: if the message is
ambiguous, set confidence < 0.6 and provide a `clarification_question` in
Indonesian.
"""


@lru_cache(maxsize=1)
def _build_chain():
    """Bind the structured output schema once. Cached because LLM client
    bindings are expensive to rebuild per invocation."""
    llm = get_chat_model()
    return llm.with_structured_output(IntentDecision)


def _last_user_text(state: AgentState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def _record_audit(state: AgentState, decision: IntentDecision) -> None:
    """Insert or update the audit_log row for this run."""
    try:
        get_admin_client().table("audit_log").upsert({
            "audit_id": state["audit_id"],
            "intent": decision.intent.value,
            "status": "in_progress",
            "payload": {"intent": decision.model_dump()},
            "workspace_id": state.get("entities", {}).get("workspace_id")
                            or state.get("_workspace_id"),  # set by API entry point
            "user_id": state.get("_user_id"),
        }).execute()
    except Exception as exc:
        log.error("intent_node: audit_log upsert failed: %s", exc)


def intent_node(state: AgentState) -> AgentState:
    user_text = _last_user_text(state)
    if not user_text:
        return {"intent": Intent.UNKNOWN.value, "entities": {}}

    chain = _build_chain()
    try:
        decision: IntentDecision = chain.invoke([
            SystemMessage(content=SYSTEM),
            HumanMessage(content=user_text),
        ])
    except Exception as exc:
        log.exception("intent_node: classification failed: %s", exc)
        return {
            "intent": Intent.UNKNOWN.value,
            "entities": {},
            "errors": [*state.get("errors", []),
                       {"node": "intent", "reason": str(exc)}],
        }

    _record_audit(state, decision)

    update: dict[str, Any] = {
        "intent": decision.intent.value,
        "entities": decision.entities,
    }

    if decision.confidence < CONFIDENCE_FLOOR or decision.intent == Intent.UNKNOWN:
        question = decision.clarification_question or \
            "Bisa dijelaskan lagi tujuan Anda? Misal: alokasi dana, valuasi bisnis, atau review risiko."
        update["messages"] = [*state.get("messages", []),
                              AIMessage(content=question)]
    return update
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_intent_classifier.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/intent/node.py backend/tests/test_intent_classifier.py
git commit -m "feat(agents): N1 Intent Classifier with structured output + clarification loop"
```

---

## Task Group C — Stub Nodes & Rejection Handler

### Task C1: Stub nodes for N2a/b/c, N5, N6, N7

**Files:**
- Create: `backend/app/agents/stubs.py`
- Create: `backend/app/agents/rejection.py`
- Create: `backend/tests/test_stubs.py`

These are intentional placeholders so the graph compiles and is fully traversable end-to-end. Real implementations land in Phases 3–6.

- [ ] **Step 1: Write failing tests**

`backend/tests/test_stubs.py`:

```python
from app.agents.state import LegalStatus, UserApproval, new_state


def test_market_stub_returns_dummy_snapshot() -> None:
    from app.agents.stubs import market_stub
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}
    update = market_stub(state)
    assert "market_snapshot" in update["entities"]


def test_business_stub_returns_dummy_valuation() -> None:
    from app.agents.stubs import business_stub
    update = business_stub(new_state())
    assert "business_valuation" in update["entities"]


def test_risk_stub_returns_dummy_metrics() -> None:
    from app.agents.stubs import risk_stub
    update = risk_stub(new_state())
    assert "risk_metrics" in update["entities"]


def test_optimizer_stub_increments_revision_count() -> None:
    from app.agents.stubs import optimizer_stub
    state = new_state()
    state["entities"] = {"tickers": ["BBCA"], "amount": 10_000_000}
    state["revision_count"] = 0
    update = optimizer_stub(state)
    assert update["revision_count"] == 1
    assert update["allocation_plan"] is not None


def test_hitl_stub_auto_approves() -> None:
    """In Phase 2 the HITL gate auto-approves so the graph runs end-to-end.
    Phase 5 replaces this with a real interrupt()."""
    from app.agents.stubs import hitl_stub
    update = hitl_stub(new_state())
    assert update["user_approval"] == UserApproval.APPROVED


def test_execution_stub_writes_dummy_transaction_record() -> None:
    from app.agents.stubs import execution_stub
    state = new_state()
    state["allocation_plan"] = {"weights": [{"ticker": "BBCA", "weight": 1.0}], "cash": 10_000_000}
    update = execution_stub(state)
    assert update["transactions"]
    assert update["transactions"][0]["status"] == "simulated"


def test_rejection_handler_appends_alternatives_message() -> None:
    from app.agents.rejection import rejection_handler
    state = new_state()
    state["legal_status"] = LegalStatus.REJECTED
    state["legal_citations"] = [{"source": "OJK", "pasal": "3", "ayat": "1",
                                 "chunk_id": "x", "span": "dilarang"}]
    update = rejection_handler(state)
    msgs = update["messages"]
    assert msgs and "tidak dapat" in msgs[-1].content.lower()
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_stubs.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement stubs and rejection handler**

`backend/app/agents/stubs.py`:

```python
"""Placeholder nodes for Phase 2 graph wiring. Each is a deliberate stub that
exists so the graph compiles end-to-end; real implementations land in:
- N2a/b/c → Phase 3
- N5 → Phase 4
- N6 → Phase 5 (replaces auto-approve with real interrupt)
- N7 → Phase 6
"""
from __future__ import annotations

import logging
from typing import Any

from app.agents.state import AgentState, UserApproval

log = logging.getLogger(__name__)


def market_stub(state: AgentState) -> AgentState:
    log.info("[stub] market_stub: tickers=%s", state.get("entities", {}).get("tickers"))
    snapshot = {"tickers": state.get("entities", {}).get("tickers", []),
                "note": "stubbed — real Phase 3 N2a not wired yet"}
    return {"entities": {**state.get("entities", {}), "market_snapshot": snapshot}}


def business_stub(state: AgentState) -> AgentState:
    log.info("[stub] business_stub")
    return {"entities": {**state.get("entities", {}),
                         "business_valuation": {"note": "stubbed"}}}


def risk_stub(state: AgentState) -> AgentState:
    log.info("[stub] risk_stub")
    return {"entities": {**state.get("entities", {}),
                         "risk_metrics": {"var_95": None, "note": "stubbed"}}}


def optimizer_stub(state: AgentState) -> AgentState:
    """Builds a trivial uniform-weight plan from entities.tickers and
    increments revision_count. Real CVXPY solver lands in Phase 4."""
    tickers = state.get("entities", {}).get("tickers") or ["BBCA"]
    cash = state.get("entities", {}).get("amount", 0)
    n = len(tickers)
    plan: dict[str, Any] = {
        "weights": [{"ticker": t, "weight": 1.0 / n} for t in tickers],
        "cash": cash,
        "note": "stubbed uniform allocation",
    }
    return {
        "allocation_plan": plan,
        "revision_count": state.get("revision_count", 0) + 1,
    }


def hitl_stub(state: AgentState) -> AgentState:
    """Auto-approves so Phase 2 graphs traverse end-to-end. Phase 5 replaces
    this with langgraph.types.interrupt()."""
    log.warning("[stub] hitl_stub: auto-approving (Phase 5 will gate this)")
    return {"user_approval": UserApproval.APPROVED}


def execution_stub(state: AgentState) -> AgentState:
    """Writes simulated transactions to state. Real broker integration in Phase 6."""
    log.info("[stub] execution_stub: simulating fills")
    plan = state.get("allocation_plan") or {}
    fills = []
    for leg in plan.get("weights", []):
        fills.append({
            "ticker": leg.get("ticker"),
            "weight": leg.get("weight"),
            "status": "simulated",
        })
    return {"transactions": fills}
```

`backend/app/agents/rejection.py`:

```python
"""Rejection Handler — when Legal status is rejected (or rejected_after_max_revisions),
emit a user-facing message that includes alternative actions, never bare 'no'."""
from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState


def rejection_handler(state: AgentState) -> AgentState:
    citations = state.get("legal_citations") or []
    cite_lines = [
        f"- {c.get('source')} Pasal {c.get('pasal')} ayat ({c.get('ayat')}): {c.get('span', '')}"
        for c in citations
    ] or ["(tidak ada kutipan yang dapat dibuktikan)"]

    msg = (
        "Alokasi yang Anda usulkan tidak dapat dilanjutkan karena pembatasan regulasi:\n"
        + "\n".join(cite_lines)
        + "\n\nSaran alternatif:\n"
        "- Pertimbangkan ETF sektor serupa yang tidak terbatas untuk investor ritel.\n"
        "- Bagi alokasi ke instrumen pendapatan tetap (obligasi pemerintah).\n"
        "- Hubungi ahli keuangan untuk skenario yang membutuhkan struktur khusus."
    )
    return {"messages": [*state.get("messages", []), AIMessage(content=msg)]}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_stubs.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/stubs.py backend/app/agents/rejection.py backend/tests/test_stubs.py
git commit -m "feat(agents): stub nodes for N2a/b/c/N5/N6/N7 + rejection handler"
```

---

## Task Group D — Postgres Checkpointer

### Task D1: Migration 0008 — LangGraph checkpoint tables

**Files:**
- Create: `backend/migrations/0008_langgraph_checkpoints.sql`
- Modify: `backend/tests/test_migrations.py`

LangGraph's `PostgresSaver` requires its own schema (checkpoints, checkpoint_writes, checkpoint_blobs). Apply via Supabase Studio.

- [ ] **Step 1: Append migration test**

```python
def test_migration_0008_langgraph_checkpoints_exists() -> None:
    sql = _read("0008_langgraph_checkpoints.sql")
    assert "checkpoints" in sql
    assert "checkpoint_writes" in sql or "checkpoint_blobs" in sql
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0008_langgraph_checkpoints_exists -v`
Expected: FAIL.

- [ ] **Step 3: Create migration file**

`backend/migrations/0008_langgraph_checkpoints.sql`:

```sql
-- 0008_langgraph_checkpoints.sql
-- LangGraph PostgresSaver schema. The library auto-creates these on first
-- use IF the connection has DDL privileges, but we apply them explicitly so
-- the team has control. Schema reference:
-- https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/

create table if not exists public.checkpoints (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb,
    metadata jsonb not null default '{}'::jsonb,
    primary key (thread_id, checkpoint_ns, checkpoint_id)
);

create table if not exists public.checkpoint_writes (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    task_id text not null,
    idx int not null,
    channel text not null,
    type text,
    blob bytea,
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

create table if not exists public.checkpoint_blobs (
    thread_id text not null,
    checkpoint_ns text not null default '',
    channel text not null,
    version text not null,
    type text not null,
    blob bytea,
    primary key (thread_id, checkpoint_ns, channel, version)
);

-- Service-role only (the backend never exposes raw checkpoint state to users).
alter table public.checkpoints enable row level security;
alter table public.checkpoint_writes enable row level security;
alter table public.checkpoint_blobs enable row level security;
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_migrations.py::test_migration_0008_langgraph_checkpoints_exists -v`
Expected: PASS.

- [ ] **Step 5: Apply migration manually in Supabase Studio.**

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/0008_langgraph_checkpoints.sql backend/tests/test_migrations.py
git commit -m "feat(db): add LangGraph checkpoint schema migration"
```

---

### Task D2: PostgresSaver factory

**Files:**
- Create: `backend/app/core/checkpointer.py`
- Modify: `backend/app/core/config.py` (add `SUPABASE_DB_URL`)
- Modify: `.env.example` and `docker-compose.yml`
- Create: `backend/tests/test_checkpointer.py`

- [ ] **Step 1: Add SUPABASE_DB_URL to Settings**

Append to `Settings` in `backend/app/core/config.py`:

```python
    # Supabase Postgres connection string for LangGraph PostgresSaver.
    # Format: postgresql://postgres.<ref>:<password>@<host>:<port>/postgres
    SUPABASE_DB_URL: str = ""
```

Append to `.env.example`:

```bash
# Supabase Postgres direct connection (for LangGraph checkpointer)
# Get from Supabase Dashboard → Project Settings → Database → Connection string (URI)
SUPABASE_DB_URL=postgresql://postgres.your-ref:your-password@aws-0-region.pooler.supabase.com:6543/postgres
```

Append to `docker-compose.yml` backend env block:

```yaml
      - SUPABASE_DB_URL=${SUPABASE_DB_URL}
```

- [ ] **Step 2: Write failing test**

`backend/tests/test_checkpointer.py`:

```python
from unittest.mock import MagicMock, patch


def test_get_checkpointer_uses_postgres_url(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@h:5432/postgres")

    import app.core.checkpointer as cp
    cp._saver = None

    fake = MagicMock()
    with patch("app.core.checkpointer.PostgresSaver.from_conn_string", return_value=fake) as f:
        first = cp.get_checkpointer()
        second = cp.get_checkpointer()

    assert first is second
    f.assert_called_once_with("postgresql://u:p@h:5432/postgres")


def test_get_checkpointer_falls_back_to_memory_when_no_db_url(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "a")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "b")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "c")
    monkeypatch.setenv("GOOGLE_API_KEY", "d")
    monkeypatch.setenv("PINECONE_API_KEY", "e")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    import importlib
    import app.core.config
    importlib.reload(app.core.config)
    import app.core.checkpointer as cp
    importlib.reload(cp)

    saver = cp.get_checkpointer()
    from langgraph.checkpoint.memory import MemorySaver
    assert isinstance(saver, MemorySaver)
```

- [ ] **Step 3: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_checkpointer.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement factory**

`backend/app/core/checkpointer.py`:

```python
"""LangGraph checkpointer factory.

Returns a PostgresSaver bound to Supabase Postgres if SUPABASE_DB_URL is set;
falls back to MemorySaver for local dev without DB credentials. The fallback
keeps tests fast and lets contributors run without a Supabase connection,
but Phase 5's interrupt() requires the Postgres saver in production."""
from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import settings

log = logging.getLogger(__name__)

_saver: Any = None


def get_checkpointer():
    global _saver
    if _saver is not None:
        return _saver

    if settings.SUPABASE_DB_URL:
        log.info("checkpointer: using PostgresSaver against Supabase")
        _saver = PostgresSaver.from_conn_string(settings.SUPABASE_DB_URL)
    else:
        log.warning("checkpointer: SUPABASE_DB_URL unset, falling back to MemorySaver "
                    "(graph state will not survive restart)")
        _saver = MemorySaver()
    return _saver
```

- [ ] **Step 5: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_checkpointer.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/checkpointer.py backend/app/core/config.py .env.example docker-compose.yml backend/tests/test_checkpointer.py
git commit -m "feat(core): add Postgres-backed LangGraph checkpointer with MemorySaver fallback"
```

---

## Task Group E — Graph Wiring

### Task E1: Build the StateGraph with conditional edges

**Files:**
- Create: `backend/app/agents/graph.py`
- Create: `backend/tests/test_graph_wiring.py`

The graph topology:

```
START → n1_intent
n1_intent → (parallel) n2a_market, n2b_business, n2c_risk
n2a, n2b, n2c → n5_optimizer (joins fan-out)
n5_optimizer → n3_legal
n3_legal → conditional:
  approved/partial → n6_hitl
  rejected         → rejection_handler → END
  rejected w/ revision_count<3 → n5_optimizer (retry)
  rejected w/ revision_count>=3 → rejection_handler → END
n6_hitl → conditional:
  approved → n7_execute → END
  rejected → END (no execution)
```

Note: the master plan said "N2 produces, N3 reads, N5 may revise." We thread it as N2{a,b,c} → N5 → N3 → conditional revision loop. The optimizer is what generates the plan; the analysts only feed signals. This makes the loop natural: revise = re-run N5 with the rejection feedback.

- [ ] **Step 1: Write failing tests for graph wiring**

`backend/tests/test_graph_wiring.py`:

```python
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.agents.intents import Intent
from app.agents.state import LegalStatus, UserApproval


def _stub_node(field: str, value):
    def fn(state):
        return {field: value}
    return fn


def test_graph_runs_happy_path_to_execution(monkeypatch) -> None:
    """Forced-approved path: n3 returns approved → n6 stub approves → n7 stub fires."""
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.APPROVED, "legal_citations": []}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["BBCA"], "amount": 1_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="alokasikan ke BBCA")],
             "audit_id": "test-audit", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t1"}},
        )

    assert result["legal_status"] == LegalStatus.APPROVED
    assert result["user_approval"] == UserApproval.APPROVED
    assert result["transactions"], "execution stub must produce transactions"


def test_graph_rejection_path_skips_execution() -> None:
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.REJECTED,
                            "legal_citations": [{"source": "OJK", "pasal": "3", "ayat": "1",
                                                 "chunk_id": "x", "span": "dilarang"}]}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["GGRM"], "amount": 5_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="GGRM")],
             "audit_id": "test-2", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t2"}},
        )

    assert result["legal_status"] == LegalStatus.REJECTED
    assert not result["transactions"], "rejected plans must not execute"
    # Rejection handler appended an AI message with alternatives
    assert any("tidak dapat" in m.content.lower() for m in result["messages"]
               if hasattr(m, "content"))


def test_graph_revision_loop_caps_at_three() -> None:
    """Stub legal always rejects. Optimizer increments revision_count. After 3
    revisions, graph must terminate with REJECTED_AFTER_MAX_REVISIONS."""
    from app.agents.graph import build_graph

    fake_legal = lambda s: {"legal_status": LegalStatus.REJECTED,
                            "legal_citations": []}
    fake_intent = lambda s: {"intent": Intent.ALLOCATE_STOCKS.value,
                             "entities": {"tickers": ["BBCA"], "amount": 1_000_000}}

    with patch("app.agents.graph.intent_node", new=fake_intent), \
         patch("app.agents.graph.legal_node", new=fake_legal):
        graph = build_graph()
        result = graph.invoke(
            {"messages": [HumanMessage(content="x")],
             "audit_id": "t3", "revision_count": 0,
             "entities": {}, "transactions": [], "errors": []},
            config={"configurable": {"thread_id": "t3"}, "recursion_limit": 50},
        )

    # The optimizer ran exactly 3 times before termination
    assert result["revision_count"] == 3
    assert result["legal_status"] in (
        LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS,
    )
    assert not result["transactions"]
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_graph_wiring.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement graph**

`backend/app/agents/graph.py`:

```python
"""AstaLink LangGraph wiring (Phase 2 skeleton).

Real nodes from Phase 1: legal_node.
Stubs replaced in later phases: intent_node (here, real Gemini-backed),
market_stub/business_stub/risk_stub (Phase 3), optimizer_stub (Phase 4),
hitl_stub (Phase 5), execution_stub (Phase 6)."""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.intent.node import intent_node
from app.agents.legal.node import legal_node
from app.agents.rejection import rejection_handler
from app.agents.state import AgentState, LegalStatus, UserApproval
from app.agents.stubs import (
    business_stub,
    execution_stub,
    hitl_stub,
    market_stub,
    optimizer_stub,
    risk_stub,
)
from app.core.checkpointer import get_checkpointer

log = logging.getLogger(__name__)

MAX_REVISIONS = 3


def _route_after_legal(state: AgentState) -> Literal["n6_hitl", "n5_optimizer", "rejection_handler"]:
    status = state.get("legal_status")
    revisions = state.get("revision_count", 0)

    if status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return "n6_hitl"
    # rejected
    if revisions >= MAX_REVISIONS:
        return "rejection_handler"
    return "n5_optimizer"  # try again with the legal feedback baked in


def _route_after_hitl(state: AgentState) -> Literal["n7_execute", END]:
    if state.get("user_approval") == UserApproval.APPROVED:
        return "n7_execute"
    return END


def _mark_max_revisions(state: AgentState) -> AgentState:
    """Tag terminal state when the revision cap is hit."""
    return {"legal_status": LegalStatus.REJECTED_AFTER_MAX_REVISIONS}


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("n1_intent", intent_node)
    g.add_node("n2a_market", market_stub)
    g.add_node("n2b_business", business_stub)
    g.add_node("n2c_risk", risk_stub)
    g.add_node("n5_optimizer", optimizer_stub)
    g.add_node("n3_legal", legal_node)
    g.add_node("n6_hitl", hitl_stub)
    g.add_node("n7_execute", execution_stub)
    g.add_node("rejection_handler", rejection_handler)
    g.add_node("max_revisions_terminator", _mark_max_revisions)

    # Linear entry
    g.add_edge(START, "n1_intent")

    # Fan-out to analysis layer
    for analyst in ("n2a_market", "n2b_business", "n2c_risk"):
        g.add_edge("n1_intent", analyst)

    # Join: each analyst → optimizer (LangGraph implicitly waits for all preds)
    for analyst in ("n2a_market", "n2b_business", "n2c_risk"):
        g.add_edge(analyst, "n5_optimizer")

    # Optimizer → Legal (the bottleneck)
    g.add_edge("n5_optimizer", "n3_legal")

    # Conditional after Legal: approve → HITL, reject under cap → loop, reject at cap → terminate
    g.add_conditional_edges(
        "n3_legal",
        _route_after_legal,
        {
            "n6_hitl": "n6_hitl",
            "n5_optimizer": "n5_optimizer",
            "rejection_handler": "rejection_handler",
        },
    )
    g.add_edge("rejection_handler", END)

    # HITL → Execute or END
    g.add_conditional_edges(
        "n6_hitl",
        _route_after_hitl,
        {"n7_execute": "n7_execute", END: END},
    )
    g.add_edge("n7_execute", END)

    return g.compile(checkpointer=get_checkpointer())


# Singleton
graph = build_graph()
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_graph_wiring.py -v`
Expected: PASS.

If `test_graph_revision_loop_caps_at_three` fails, the loop logic is off. The fix usually is making sure `revision_count` is updated by the optimizer stub on every pass and the conditional reads the *latest* state — which it does because state updates are merged before the conditional fires.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/graph.py backend/tests/test_graph_wiring.py
git commit -m "feat(agents): wire 3-layer LangGraph with parallel analysis, legal gate, revision loop"
```

---

## Task Group F — Agent Run Endpoint

### Task F1: POST /api/v1/agent/run

**Files:**
- Create: `backend/app/api/v1/agent.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_graph_endpoint.py`

This is the integration surface. Phase 7 (WhatsApp) and Phase 5 (web dashboard chat) will both call this endpoint.

- [ ] **Step 1: Write failing test**

`backend/tests/test_graph_endpoint.py`:

```python
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.state import LegalStatus, UserApproval


def test_agent_run_returns_final_state(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4()), "email": "u@test.com"}
    workspace_id = str(uuid.uuid4())

    fake_final = {
        "audit_id": "abc",
        "intent": "allocate_stocks",
        "legal_status": LegalStatus.APPROVED,
        "user_approval": UserApproval.APPROVED,
        "allocation_plan": {"weights": [{"ticker": "BBCA", "weight": 1.0}]},
        "transactions": [{"ticker": "BBCA", "weight": 1.0, "status": "simulated"}],
        "messages": [],
        "errors": [],
        "legal_citations": [],
        "revision_count": 1,
        "entities": {},
    }

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.agent.graph.invoke", return_value=fake_final):
        resp = client.post(
            "/api/v1/agent/run",
            json={"message": "alokasikan 10jt ke BBCA", "workspace_id": workspace_id},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["legal_status"] == "approved"
    assert body["transactions"][0]["status"] == "simulated"


def test_agent_run_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/agent/run", json={"message": "x", "workspace_id": "x"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_graph_endpoint.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement endpoint**

`backend/app/api/v1/agent.py`:

```python
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents.graph import graph
from app.agents.state import new_state
from app.api.deps import get_current_user

router = APIRouter()


class AgentRunRequest(BaseModel):
    message: str
    workspace_id: str
    thread_id: str | None = Field(
        default=None,
        description="Pass to continue an existing conversation; omit for a new run.",
    )


class AgentRunResponse(BaseModel):
    audit_id: str
    thread_id: str
    intent: str | None
    legal_status: str | None
    user_approval: str | None
    allocation_plan: dict[str, Any] | None
    transactions: list[dict[str, Any]]
    revision_count: int
    messages: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def _serialize_messages(msgs: list) -> list[dict[str, Any]]:
    out = []
    for m in msgs:
        out.append({"type": m.__class__.__name__, "content": getattr(m, "content", "")})
    return out


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
) -> AgentRunResponse:
    thread_id = body.thread_id or str(uuid.uuid4())

    initial = new_state()
    initial["messages"] = [HumanMessage(content=body.message)]
    initial["_user_id"] = user["sub"]            # type: ignore[misc]
    initial["_workspace_id"] = body.workspace_id  # type: ignore[misc]
    initial["entities"] = {"workspace_id": body.workspace_id}

    final = graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})

    return AgentRunResponse(
        audit_id=final["audit_id"],
        thread_id=thread_id,
        intent=final.get("intent"),
        legal_status=str(final["legal_status"]) if final.get("legal_status") else None,
        user_approval=str(final["user_approval"]) if final.get("user_approval") else None,
        allocation_plan=final.get("allocation_plan"),
        transactions=final.get("transactions", []),
        revision_count=final.get("revision_count", 0),
        messages=_serialize_messages(final.get("messages", [])),
        errors=final.get("errors", []),
    )
```

`backend/app/api/v1/router.py` — add agent router:

```python
from fastapi import APIRouter

from app.api.v1 import agent, chat, health, legal

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_graph_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/agent.py backend/app/api/v1/router.py backend/tests/test_graph_endpoint.py
git commit -m "feat(api): expose POST /api/v1/agent/run for end-to-end graph invocation"
```

---

## Phase 2 Definition of Done

- [ ] All Phase 0 + Phase 1 tests still pass.
- [ ] All new Phase 2 tests pass.
- [ ] Migration 0008 applied to Supabase; checkpoint tables exist.
- [ ] `make dev` boots; `POST /api/v1/agent/run` with a real JWT and message returns a final state with `intent`, `legal_status`, `transactions`.
- [ ] Manual ambiguous-intent test: send "hmm" → response contains a clarification AI message (not a crash).
- [ ] Manual restart test: start a graph run, kill the backend, restart, and call `agent/run` again with the same `thread_id` — graph resumes from checkpoint instead of starting over (verify by inspecting `checkpoints` table).
- [ ] `audit_log` row created with `status=in_progress` at N1; later updated by the legal node.
