# AstaLink — Master Phasing Plan

> **For agentic workers / human readers:** This is a **phasing document**, not a step-by-step implementation plan. It decomposes AstaLink into 9 ordered phases. Each phase will get its own detailed implementation plan written using `superpowers:writing-plans` once approved (e.g. `2026-05-07-astalink-phase-1-legal-agent.md`). Do not attempt to execute this document directly with `subagent-driven-development` — execute the per-phase sub-plans.

**Goal:** Build AstaLink, an AI Chief Investment Officer (AI-CIO) accessed via WhatsApp + Web Dashboard, that helps retail investors and UMKM allocate idle assets with mandatory regulatory validation and human-in-the-loop approval.

**Architecture (3-layer LangGraph pipeline):**
- **Layer 1 — Input & Intent:** N1 Intent Classifier (LLM with structured output enum, clarification loop on unknown intents).
- **Layer 2 — Analysis & Compliance:** N2a Market Analyzer / N2b Business Evaluator / N2c Risk Agent run in parallel, then converge on N3 Legal & Compliance Agent (RAG bottleneck — every allocation passes through here).
- **Layer 3 — Decision & Execution:** N5 Allocation Optimizer (CVXPY + LLM reasoning, may revise plans) → N6 HITL gate (LangGraph `interrupt()` + PIN approval) → N7 Execution Engine (Broker / Open Finance APIs). Rejection Handler returns alternatives, not bare denials.
- All nodes share a `AgentState` TypedDict carrying `audit_id`, `allocation_plan`, `revision_count`, `legal_status`, `user_approval`.

**Tech Stack (locked):** Next.js 16 + Shadcn UI / FastAPI (async) / Supabase (Auth + Postgres + RLS) / LangGraph + LangChain / Google Gemini / Pinecone (dense) + BM25 (sparse) + RRF / scipy + numpy + CVXPY + TA-Lib / Meta WhatsApp Business API / Yahoo Finance + News API + Open Finance + Broker API / Grafana + Prometheus + DeepEval / Docker Compose (dev no-traefik, prod traefik on Dokploy).

**Non-negotiable design philosophy:**
1. Verify first, allocate second — Legal Agent is a mid-pipeline gate, never end-of-pipeline.
2. Human-in-the-Loop is mandatory for every transaction (PIN-based via dashboard).
3. Anti-hallucination by design — LLM Grader after every RAG call; DeepEval on every numeric/regulatory output.
4. Compliance first — every recommendation cited against OJK / UUPM / perpajakan / banking regulation.
5. End-to-end audit trail — `audit_id` generated at N1, propagated through every node, persisted to Supabase.
6. Zero-friction WhatsApp UX — usable without a tutorial.

---

## Current Repository State (as of 2026-05-07)

**What already exists** (from `2026-05-04-nextjs-fastapi-template.md`):
- Monorepo with `frontend/` (Next.js 16 + Shadcn + Tailwind v4) and `backend/` (FastAPI + LangGraph 0.2 + langchain-openai).
- Supabase auth wired up: middleware refreshes session on every request, `/login` and `/signup` routes, JWT verified by backend in `app/core/security.py`.
- Docker Compose dev (`docker-compose.yml`, hot-reload) and prod (`docker-compose.prod.yml` + nginx).
- A toy LangGraph chat agent (`backend/app/agents/chat_agent.py`) with one node calling GPT-4o-mini.
- Test scaffolding (`backend/tests/`, `.deepeval/`).

**What must change for AstaLink:**
- **Swap LLM provider:** rip out `langchain-openai` + `OPENAI_API_KEY`, swap in `langchain-google-genai` + `GOOGLE_API_KEY` (or Gemini SDK directly). Update env, config, agent code.
- **Replace toy chat agent** with the 3-layer LangGraph pipeline.
- **Database schema** — Supabase currently only has Auth tables. We need Feature tables (workspaces, allocation_plans, audit_log, transactions, pin_codes, regulation_documents) with RLS for Personal/Business workspace isolation.
- **Add quant libraries** to `pyproject.toml`: scipy, numpy, cvxpy, TA-Lib, yfinance, pandas.
- **Add RAG stack:** pinecone-client, rank-bm25, langchain-pinecone.
- **Add WhatsApp + observability:** Meta WhatsApp SDK, prometheus-fastapi-instrumentator, deepeval.
- **Frontend:** workspace switcher, allocation approval inbox, PIN modal, audit trail viewer.
- **Production Compose:** swap nginx config for Traefik labels (Dokploy target).

This audit is non-trivial — Phase 0 absorbs all dependency / schema / config churn so later phases stay focused.

---

## Critical-Path Reasoning

**Why Legal Agent (Phase 1) before everything else?**
The product philosophy says "verify first, allocate second." If the Legal Agent doesn't work — if it hallucinates pasal references or fails to ground citations — every downstream agent (analyzers, optimizer) wastes work. Building Legal first lets us prove the hardest unknown (RAG quality + LLM grader) early, when there's still time to swap retriever / chunking / grader strategies. It's also the single component most likely to fail a hackathon judge demo.

**Why HITL gate (Phase 5) is built mid-project, not at the end?**
The `interrupt()` mechanic shapes the entire backend ↔ frontend contract (resumable graph runs, persistent state, signal endpoints). Building it after analysis layers exposes integration bugs while the graph is still small.

**Why WhatsApp (Phase 7) is late?**
WhatsApp is a *channel*, not the *product*. The product is the graph. Bring up the web dashboard channel first (it's needed for HITL anyway), then layer WhatsApp on top via the same backend endpoints. If hackathon time runs out, demoing on web is acceptable; without a working graph, WhatsApp adds nothing.

**MVP cut-line for hackathon (recommended):**
Phases 0 → 1 → 2 → 5 → 7 are the spine. Phases 3 & 4 can ship with simplified stubs (single-asset allocation, hardcoded risk profile, no DCF) and still demo. Phase 6 can be sandboxed (log to Supabase, simulate broker). Phase 8 can ship with Prometheus only (skip Grafana dashboards if time is short).

---

## Phase Breakdown

Each phase below is owned by a role (fill in team-member names in the per-phase sub-plan). Each phase produces working, demo-able software on its own. Definition of Done (DoD) for every phase requires: code merged, tests passing, manual smoke-test screenshot or log captured, sub-plan checkboxes 100 % complete.

---

### Phase 0 — Foundation: Dependencies, Schema, Config Migration

**Sub-plan file:** `2026-05-07-astalink-phase-0-foundation.md`
**Owner role:** DevOps Lead + Backend Lead
**Estimated size:** Small-Medium (1–2 days for 2 people)
**Depends on:** —
**Blocks:** Every other phase

**Scope:**
- Replace OpenAI dependencies with Google Gemini (`langchain-google-genai`), update `.env.example`, `app/core/config.py`, `app/agents/chat_agent.py`.
- Add Python deps: `scipy`, `numpy`, `cvxpy`, `ta-lib`, `yfinance`, `pandas`, `pinecone-client`, `rank-bm25`, `langchain-pinecone`, `prometheus-fastapi-instrumentator`, `deepeval`. Verify TA-Lib system library is installed in the backend Dockerfile (it requires a C dep).
- Create Supabase migrations (`backend/migrations/` or via Supabase Studio SQL):
  - `workspaces` (id, owner_user_id, type ENUM('personal','business'), name, created_at)
  - `audit_log` (audit_id PK, workspace_id, user_id, intent, created_at, completed_at, status, payload jsonb)
  - `allocation_plans` (id, audit_id FK, plan_json, legal_status, revision_count, created_at)
  - `transactions` (id, allocation_plan_id FK, broker_ref, executed_at, status, payload jsonb)
  - `pin_codes` (user_id PK, hashed_pin, salt, attempts, last_failed_at, locked_until)
  - `regulation_documents` (id, source, title, version, indexed_at, doc_hash) — index metadata for RAG corpus
  - RLS policies: a user can read/write rows only where `workspace_id` belongs to a workspace they own.
- Add singleton clients to `backend/app/core/`: `gemini.py` (Gemini chat + embedding clients), `pinecone.py` (index handle), `supabase_admin.py` (service-role client for writes the user can't make directly).
- Add `AgentState` TypedDict in `backend/app/agents/state.py` — empty stubs for `audit_id`, `allocation_plan`, `revision_count`, `legal_status`, `user_approval`, `messages`. This is shared infra that every later phase imports.
- Update `docker-compose.yml` to add Prometheus container (Grafana deferred to Phase 8).
- Update `.env.example` with all new keys: `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `WHATSAPP_*`, `YAHOO_FINANCE_*`, `BROKER_*`, etc. Mark which are required vs optional.

**Definition of Done:**
- `make dev` boots without errors; `/api/v1/health` returns 200.
- `pytest backend/tests/test_smoke.py` (new) verifies Gemini, Pinecone, Supabase clients initialize.
- Supabase Studio shows all new tables with RLS enabled.
- `AgentState` import works from `backend/app/agents/state.py`.
- `.env.example` is complete; missing keys cause clear startup errors, not silent failures.

---

### Phase 1 — Legal Agent + RAG (Critical Path)

**Sub-plan file:** `2026-05-07-astalink-phase-1-legal-agent.md`
**Owner role:** AI Lead
**Estimated size:** Large (4–6 days)
**Depends on:** Phase 0
**Blocks:** Phase 2 (graph wiring needs a working Legal node), Phase 4 (optimizer reads `legal_status`)

**Scope:**
- **Document ingestion pipeline** (`backend/scripts/ingest_regulations.py`):
  - Input directory of PDFs (OJK regulations, UUPM, peraturan perpajakan, banking rules — at least 3 documents to start).
  - Use `pypdf` or `pdfplumber` to extract text, preserving article (Pasal) markers. Custom chunker that keeps "Pasal X ayat (Y)" boundaries intact — never split mid-pasal.
  - For each chunk: produce dense embedding via Gemini, push to Pinecone with metadata `{source, pasal, ayat, page, doc_hash}`. Push the same chunk text into a local BM25 index serialized to disk (`backend/data/bm25_index.pkl`).
  - Insert `regulation_documents` row in Supabase per ingested PDF.
- **Hybrid retriever** (`backend/app/agents/legal/retriever.py`):
  - `dense_retrieve(query, k=10)` → Pinecone similarity search.
  - `sparse_retrieve(query, k=10)` → BM25 over chunk text (handles "Pasal 5 ayat (2)" exact-match queries that dense retrieval often misses).
  - `hybrid_retrieve(query, k=10)` → Reciprocal Rank Fusion combining both, returns top-k unique chunks with merged scores.
- **LLM Grader** (`backend/app/agents/legal/grader.py`):
  - Takes the retriever's chunks + the LLM's draft answer (with cited pasal references).
  - For each citation in the draft answer, ask Gemini "Does chunk text actually contain pasal X ayat (Y)? Yes/No + evidence span."
  - Drop any citation the grader can't ground; if all citations are dropped, force `legal_status='rejected'` with reason "no grounded basis."
- **Legal Agent node** (`backend/app/agents/legal/node.py`):
  - Input from `AgentState`: `allocation_plan` (proposal), context.
  - Build query from plan (e.g. "Saham X, sektor Y, jumlah Rp Z — apakah ada pembatasan investor ritel?").
  - Run hybrid retrieve → LLM with structured output `LegalDecision { status: 'approved'|'partial'|'rejected', citations: [{source, pasal, ayat, span}], reasoning, alternative_actions: [...] }`.
  - Run grader on output. Persist decision to `audit_log` keyed by `audit_id`.
  - Return updated `AgentState` with `legal_status` set.
- **Standalone API endpoint** `/api/v1/legal/check` for testing without the full graph.
- **DeepEval test suite** (`backend/tests/test_legal_hallucination.py`):
  - Hallucination metric: ≥ 0.95 (no fabricated pasal references).
  - Faithfulness: every citation must appear in retrieved chunks.
  - Run on a curated set of 20 hand-labeled prompts ("invest in tobacco stock", "buy parent-company shares", etc.).

**Definition of Done:**
- Ingest 3+ regulation PDFs end-to-end; Pinecone shows chunks; BM25 index loads.
- `POST /api/v1/legal/check` with sample plan returns `LegalDecision` with grounded citations.
- DeepEval suite passes hallucination ≥ 0.95 on the 20-prompt eval set.
- Manual test: ask "saham A insider trading restriction" — system either returns the relevant pasal or refuses with no fabricated reference.

---

### Phase 2 — LangGraph Orchestration Skeleton + Intent Classifier (N1)

**Sub-plan file:** `2026-05-07-astalink-phase-2-graph-skeleton.md`
**Owner role:** AI Lead + Backend Lead
**Estimated size:** Medium (2–3 days)
**Depends on:** Phases 0, 1
**Blocks:** Phases 3, 4, 5

**Scope:**
- Define `Intent` enum (`backend/app/agents/intents.py`): `ALLOCATE_STOCKS`, `EVALUATE_BUSINESS`, `RISK_REVIEW`, `PORTFOLIO_STATUS`, `EXPLAIN`, `UNKNOWN`.
- **Intent Classifier (N1)** (`backend/app/agents/intent/node.py`):
  - Gemini structured output bound to `IntentDecision { intent: Intent, entities: dict, confidence: float, clarification_question: str | None }`.
  - If `confidence < 0.6` or `intent = UNKNOWN`, set `clarification_question` and route to a clarification edge (graph re-enters N1 after user reply).
- **Graph wiring** (`backend/app/agents/graph.py`):
  - Build `StateGraph(AgentState)` with nodes: `n1_intent`, `n2a_market_stub`, `n2b_business_stub`, `n2c_risk_stub`, `n3_legal` (uses Phase 1 node), `n5_optimizer_stub`, `n6_hitl_stub`, `n7_execute_stub`.
  - Phase 2 ships stubs for N2a/b/c, N5, N6, N7 — they just log and pass-through. Real implementations come in later phases.
  - Conditional edges: from N1 → N2{a,b,c} (parallel) → join → N3. From N3, conditional: `approved` → N5, `rejected` → END (with rejection_handler). From N5 → N6 → N7 → END.
  - `revision_count` increment on N5; if N3 rejects after revision, re-route N5 again, max 3 revisions then END.
  - Generate `audit_id = uuid4()` at N1 entry; persist initial `audit_log` row.
- **Checkpointer** — replace `MemorySaver` with `PostgresSaver` (langgraph's Postgres checkpointer) backed by Supabase, so graph runs survive backend restarts (mandatory for `interrupt()` to be useful in Phase 5).
- **API endpoint** `POST /api/v1/agent/run` accepting `{message, workspace_id, thread_id?}` — invokes graph, returns final state (or interrupt signal in Phase 5).
- **Tests:** unit-test each node in isolation with hand-built `AgentState`. Integration test: end-to-end happy path through the stubbed graph.

**Definition of Done:**
- Calling `POST /api/v1/agent/run` with "alokasikan 10 juta ke saham bank" routes through N1 (intent=ALLOCATE_STOCKS) → stub analyzers → real Legal Agent → stub optimizer/HITL/execution and returns a final state.
- Unknown-intent clarification loop works: ambiguous input gets a clarification question, follow-up message is correctly classified.
- `audit_log` rows visible in Supabase for each run, sharing one `audit_id`.
- Graph state survives backend restart (verify via Postgres checkpointer).

---

### Phase 3 — Analysis Layer: Market, Business, Risk Agents (N2a/b/c)

**Sub-plan file:** `2026-05-07-astalink-phase-3-analysis-layer.md`
**Owner role:** AI Lead + Quant contributor
**Estimated size:** Medium-Large (3–5 days, parallelizable across N2a/b/c)
**Depends on:** Phase 2
**Blocks:** Phase 4

**Scope:**
- **N2a Market Analyzer** (`backend/app/agents/market/`):
  - `yfinance_client.py` — fetch historical prices, fundamentals, dividend history.
  - `news_client.py` — News API integration: pull recent headlines per ticker, sentiment-tag via Gemini (categorical only: positive/neutral/negative — no numeric "sentiment score" from LLM).
  - `indicators.py` — TA-Lib wrappers: SMA/EMA, RSI, MACD, Bollinger Bands. Pure-Python, no LLM.
  - `node.py` — input: `entities.tickers`. Output: `MarketSnapshot` (per-ticker metrics + recent news headlines + LLM-narrated summary). LLM only narrates; numbers come from TA-Lib.
- **N2b Business Evaluator** (`backend/app/agents/business/`):
  - `dcf.py` — Discounted Cash Flow model (numpy). Inputs: revenue projections, growth rate, discount rate, terminal value. Output: enterprise value.
  - `erp_connector.py` — adapter interface. For hackathon, ship a CSV-import stub (user uploads financial statements via dashboard); real ERP connectors deferred.
  - `node.py` — runs DCF, returns `BusinessValuation`. LLM only translates numbers to natural-language summary; calculation is deterministic.
- **N2c Risk Agent** (`backend/app/agents/risk/`):
  - `mvo.py` — scipy.optimize Mean-Variance Optimization on a candidate portfolio. Returns weights that minimize variance for a target return.
  - `var.py` — historical VaR (numpy percentile) and parametric VaR. Output: `RiskMetrics { var_95, var_99, expected_shortfall, sharpe }`.
  - `node.py` — read user's risk profile (from Supabase `users` profile col), run MVO + VaR, return `RiskAssessment`.
  - **Hard constraint:** quantitative outputs (VaR, MVO weights) are computed by scipy/numpy ONLY. The LLM is forbidden from producing numeric risk metrics — it can only narrate them. Lint rule or code review checklist enforces this.
- **Parallel execution:** the graph already has parallel edges from N1 to N2a/b/c (Phase 2). Verify LangGraph fan-out works; converge on N3.
- **Tests:** golden-data tests for TA-Lib indicators (compare to known values), DCF (compare to spreadsheet output), VaR (compare to scipy reference). DeepEval on LLM narration: factuality vs the underlying numbers.

**Definition of Done:**
- Each of N2a/b/c produces structured output that N3 (Legal) consumes successfully.
- Quantitative tests pass with ≤ 0.1 % deviation from reference values.
- DeepEval factuality on narration ≥ 0.9 (LLM doesn't misrepresent the numbers).
- Manual demo: input "RUUF GOTO BBCA, cash 50jt, profile moderate" → graph returns market snapshot, risk metrics, legal decision.

---

### Phase 4 — Allocation Optimizer (N5) + Revision Loop

**Sub-plan file:** `2026-05-07-astalink-phase-4-optimizer.md`
**Owner role:** AI Lead + Quant contributor
**Estimated size:** Medium (2–3 days)
**Depends on:** Phase 3, Phase 1 (reads `legal_status`)
**Blocks:** Phase 5

**Scope:**
- **CVXPY constraint solver** (`backend/app/agents/optimizer/solver.py`):
  - Variables: portfolio weights vector `w`, sum to 1, `0 ≤ w_i ≤ max_per_asset`.
  - Objective: maximize expected return − λ × risk (Markowitz utility).
  - Constraints from N2c (max VaR), N3 (forbidden tickers / sector caps from `legal_status.partial`), user preferences (min-cash buffer).
  - Returns weights or infeasibility status.
- **LLM reasoning wrapper** (`backend/app/agents/optimizer/node.py`):
  - Run CVXPY solver. If feasible, ask Gemini to narrate the rationale ("60 % BBCA because low VaR + dividend yield, 30 % obligasi for capital preservation, 10 % cash buffer per UUPM Pasal X").
  - If infeasible, build a relaxed problem (drop softest constraint), re-solve, narrate trade-offs.
  - Update `allocation_plan` in `AgentState`. **Always increment `revision_count`** when the node runs.
- **Revision loop:**
  - In `graph.py`: from N5, edge back to N3 (Legal re-checks the new plan). If `legal_status = approved`, proceed to N6. If still `rejected` and `revision_count < 3`, loop N5 again. If `revision_count >= 3`, terminate with `legal_status = rejected_after_max_revisions` and a Rejection Handler message offering manual paths.
- **Rejection Handler** (`backend/app/agents/optimizer/rejection.py`):
  - Not just "no" — produces alternative_actions: e.g. "saham X tidak bisa karena insider trading restriction Pasal X; pertimbangkan ETF sektor Y dengan profil serupa." Use the Legal Agent's `alternative_actions` field plus optimizer's relaxed-solution result.

**Definition of Done:**
- Optimizer produces feasible allocations on happy-path inputs.
- Infeasibility triggers relaxation, not crash.
- Revision loop terminates: e.g. forbidden-ticker-only universe yields a clear rejection-with-alternatives within ≤ 3 revisions.
- Tests: golden inputs → expected weights (within tolerance); legal feedback loop verified with mocked legal_status responses.

---

### Phase 5 — HITL Gate (N6) + Web Dashboard Approval

**Sub-plan file:** `2026-05-07-astalink-phase-5-hitl.md`
**Owner role:** Frontend Lead + Backend Lead
**Estimated size:** Large (4–5 days; parallel frontend + backend work)
**Depends on:** Phases 2, 4
**Blocks:** Phase 6, Phase 7

**Scope:**
- **Backend:**
  - **N6 node** (`backend/app/agents/hitl/node.py`): calls `langgraph.types.interrupt({allocation_plan, summary, audit_id})`. Graph pauses; checkpointer persists state.
  - **Endpoints** (`backend/app/api/v1/approvals.py`):
    - `GET /approvals?workspace_id=` — list pending approvals for current user (joins `audit_log` + `allocation_plans` where `legal_status=approved` and not yet executed).
    - `GET /approvals/{audit_id}` — full plan details.
    - `POST /approvals/{audit_id}/approve` body `{pin}` — verify PIN against `pin_codes` (hashed, with attempt counter + lockout); on success, call `graph.invoke(None, config={'configurable':{'thread_id':audit_id}})` to resume the interrupted graph.
    - `POST /approvals/{audit_id}/reject` body `{reason}` — set state user_approval=rejected, resume graph; graph routes to END.
  - **PIN management:** `POST /users/me/pin` to set initial PIN (Argon2 hash). Lockout after 5 failed attempts for 15 minutes.
- **Frontend:**
  - `frontend/app/(protected)/approvals/page.tsx` — inbox listing pending approvals, polling or Supabase Realtime subscription on `audit_log`.
  - `frontend/app/(protected)/approvals/[auditId]/page.tsx` — plan detail view: weights chart, legal citations, risk metrics, optimizer rationale.
  - `frontend/components/pin-modal.tsx` — Shadcn dialog with masked PIN input, calls `/approvals/{audit_id}/approve`. Shows lockout state and remaining attempts.
  - `frontend/components/audit-trail.tsx` — timeline of all nodes that ran for an `audit_id`, queryable by user.
- **Workspace switcher** (deferred from Phase 0 if not done): top-bar selector between Personal / Business workspace; routes data fetches with `workspace_id` for RLS.

**Definition of Done:**
- End-to-end test: invoke graph → graph pauses at N6 → frontend approval page shows the plan → user enters PIN → graph resumes → execution stub logs.
- Wrong PIN 5× locks the user out for 15 min, recorded in DB.
- Refreshing the approval page mid-flow doesn't lose state (Postgres checkpointer working).
- Audit trail page shows N1→N7 timestamps for a completed run.

---

### Phase 6 — Execution Engine (N7)

**Sub-plan file:** `2026-05-07-astalink-phase-6-execution.md`
**Owner role:** Backend Lead
**Estimated size:** Medium (2–3 days for sandbox; longer if real broker creds available)
**Depends on:** Phase 5
**Blocks:** —

**Scope:**
- **Broker adapter** (`backend/app/integrations/broker.py`): interface `place_order(ticker, qty, side, account_id) → BrokerOrder`. Two implementations: `SandboxBroker` (logs, returns fake fill) and `RealBroker` (HTTP client to chosen broker — pick one Indonesian retail broker that exposes API; fall back to sandbox if creds aren't available at hackathon time).
- **Open Finance adapter** (`backend/app/integrations/openfinance.py`): for fund-source verification (does the user actually have the cash?). Sandbox stub for hackathon.
- **N7 node** (`backend/app/agents/execution/node.py`):
  - For each leg in `allocation_plan.weights`, compute order size (cash × weight ÷ price), call broker.
  - Persist each fill to `transactions` table linked to `audit_id` + `allocation_plan_id`.
  - Idempotency: if N7 is re-invoked for the same `audit_id` + leg, skip already-filled orders (key on `(audit_id, ticker, side)` unique).
  - Return updated `AgentState` with `transactions` summary; emit a notification (Phase 7 — WhatsApp; for now, just a row in `notifications` table).
- **Frontend transactions view** (`frontend/app/(protected)/transactions/page.tsx`): list executions filterable by workspace + date range.

**Definition of Done:**
- Sandbox execution end-to-end: approval → orders logged in `transactions` → frontend displays them.
- Idempotency verified by re-invoking N7 on the same plan; no duplicate transactions.
- Audit trail (Phase 5) shows N7 fills as the final timeline event.

---

### Phase 7 — WhatsApp Channel

**Sub-plan file:** `2026-05-07-astalink-phase-7-whatsapp.md`
**Owner role:** Backend Lead + Frontend Lead (deep links)
**Estimated size:** Medium (2–3 days, blocked by Meta API approval lead time)
**Depends on:** Phases 2, 5 (need a working graph + approval URL to link to)
**Blocks:** —

**Scope:**
- **Meta WhatsApp Business API setup:** verify business, register phone number, configure webhook URL, persist tokens. Document the manual setup steps in the sub-plan; this is partly a paperwork phase.
- **Inbound webhook** (`backend/app/api/v1/whatsapp.py`):
  - `POST /whatsapp/webhook` — verify Meta signature, parse incoming message, look up user by phone number, derive `workspace_id`, call `graph.invoke({messages:[HumanMessage(...)]}, config={configurable:{thread_id: new_or_existing}})`.
  - For graph runs that hit N6 (HITL), return a templated WhatsApp message: "Allocation siap. Approve via [deep link to dashboard?audit_id=...]". Approval still happens in dashboard (PIN entry on web) — WhatsApp itself never accepts PIN (security).
  - For terminal runs (N7 done or rejected), send a summary message via `POST /messages`.
- **User onboarding:** first message from an unknown phone number triggers a sign-up link. Link binding handled via a one-time-code message.
- **Idempotency / replay:** Meta retries webhooks; key on `message_id` to avoid double-processing.
- **Conversation memory:** thread_id per phone number per workspace (stored in `whatsapp_threads` table).
- **Tests:** mock Meta webhook payloads; integration test from "WhatsApp inbound" → graph → "WhatsApp outbound notification" using a test-mode Meta number.

**Definition of Done:**
- Real WhatsApp message → backend webhook → graph → reply with approval link.
- Click approval link in WhatsApp → opens dashboard at the right approval, PIN entry approves → WhatsApp gets execution confirmation.
- Replayed webhook does not duplicate processing.

---

### Phase 8 — Monitoring, Quality Gates, Production Deploy

**Sub-plan file:** `2026-05-07-astalink-phase-8-observability.md`
**Owner role:** DevOps Lead + AI Lead (DeepEval)
**Estimated size:** Medium (2–3 days)
**Depends on:** Phases 0, 1 (DeepEval scaffolding from Phase 1 is reused)
**Blocks:** —

**Scope:**
- **Prometheus instrumentation** (`backend/app/core/metrics.py`):
  - `prometheus-fastapi-instrumentator` for HTTP metrics.
  - Custom counters/histograms per LangGraph node: `astalink_node_duration_seconds{node="n3_legal"}`, `astalink_node_errors_total`, `astalink_revision_count_histogram`, `astalink_legal_status_total{status}`.
  - `/metrics` endpoint scraped by Prometheus container.
- **Grafana dashboards** (`grafana/dashboards/*.json`):
  - Pipeline health: per-node latency p50/p95, error rates.
  - Quality: hallucination rate, faithfulness score from DeepEval.
  - Business: approvals/rejections per day, average revision count, time-to-approve.
- **DeepEval CI gate** (`backend/tests/test_quality_gate.py`): nightly job runs DeepEval suite from Phase 1 + Phase 3; CI fails on regression > 5 %.
- **Production deploy (Dokploy + Traefik):**
  - Replace nginx config with Traefik labels in `docker-compose.prod.yml`.
  - Configure Traefik on Dokploy host: HTTPS via Let's Encrypt, `PROD_DOMAIN` routing.
  - Secret management: Dokploy env vars (no `.env` in image).
  - Smoke-test the prod deploy; verify Prometheus scrapes the prod backend.

**Definition of Done:**
- `/metrics` exposes all custom metrics.
- Grafana dashboards load with live data.
- DeepEval CI gate runs on pull request.
- App deployed to a Dokploy-hosted domain with HTTPS, all phases functional in prod.

---

## Cross-cutting concerns (apply to every phase)

- **`audit_id` propagation** — generated at N1, attached to every Supabase write, every log line, every WhatsApp/dashboard notification. Any code path that loses it is a bug.
- **Error handling** — every external call (Gemini, Pinecone, Yahoo, broker, Meta) has timeout + retry + circuit breaker. On final failure, write error to `audit_log` with full context and surface a user-friendly message; never silently swallow.
- **Quantitative discipline** — VaR, MVO weights, DCF outputs come from scipy/numpy/CVXPY only. LLM may *narrate* numbers, never *produce* them. Code review explicitly checks for this.
- **Compliance discipline** — every legal claim cites a pasal; the LLM Grader gates the citation. No grader → no claim.
- **HITL discipline** — no transaction-affecting code path bypasses N6. Adding a new execution side-effect requires routing through the interrupt pattern.
- **Workspace isolation** — every Supabase query filtered by `workspace_id`; RLS is the second line of defense, not the only one. Frontend never trusts client-side workspace selection — backend re-validates.

---

## Hackathon Time-Box Recommendation

Assuming ~3 weeks until the demo and 4-person team:

| Week | Focus | Phases |
|------|-------|--------|
| 1 | Foundation + Critical Path | Phase 0 (days 1–2), Phase 1 (days 3–7) |
| 2 | Pipeline + HITL | Phase 2 (days 8–10), Phase 3 simplified (days 11–13), Phase 4 simplified (days 13–14), Phase 5 starts |
| 3 | Polish + Channels + Deploy | Phase 5 finishes (days 15–16), Phase 6 sandbox (day 17), Phase 7 (days 18–19), Phase 8 (days 20–21) |

**Hard cuts if behind schedule:**
- Phase 3: ship N2c (Risk) only; stub N2a/b with hardcoded data. Risk + Legal alone is enough to demo "verify first."
- Phase 4: skip CVXPY revision loop; ship single-shot allocation. Document as future work.
- Phase 6: sandbox-only execution. Demo broker integration as "configurable adapter."
- Phase 7: optional. If WhatsApp Business API approval is delayed, demo dashboard-only.
- Phase 8: ship Prometheus + DeepEval; defer Grafana dashboards.

**Demo storyline (what judges should see):**
"User asks WhatsApp: alokasikan idle cash 50 juta, profile moderate. AI fetches market data, computes risk, validates against OJK regulation, proposes allocation with citations. User opens dashboard via link, sees plan + cited regulation, enters PIN, approval triggers execution. Audit trail shows every step."

---

## Next Step

Per the `superpowers:writing-plans` workflow, this phasing document should be followed by a per-phase detailed sub-plan with bite-sized TDD tasks. Recommended order:

1. **Phase 0 first** — unblocks everything; small/fast.
2. **Phase 1 next** — critical path, hardest unknown, ship it while there's time to iterate.
3. Phases 2 → 5 in sequence.
4. Phases 3, 4 (analyzers/optimizer) can run partly in parallel with 5 if team capacity allows.
5. Phases 6, 7, 8 in the final week.

**Action required:** confirm which phase to write the detailed sub-plan for first (recommend: Phase 0). The sub-plan will live in this same `docs/superpowers/plans/` directory and will be executable via `superpowers:subagent-driven-development` or `superpowers:executing-plans`.
