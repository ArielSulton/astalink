# Migration Note — Two-Layer Capital Allocation Engine

Refactor of the stock/business allocation agent system onto the existing
N1–N9 LangGraph pipeline. This note lists what was removed, what was moved,
and where everything went.

## What was removed

**Nothing — with one important clarification.** The refactor spec called for
deleting a standalone "A5 Devil's Advocate" stock agent (sub-agents D1–D6,
`devil_discount`, `epistemic_confidence`). **No such agent ever existed in
this repo**; the codebase had no per-stock scoring formula at all before this
work. The deliverable is therefore satisfied by construction: the stock
synthesizer was built from day one **without** an adversarial discount layer
(`final_score = base_score`), and A5's three hard gates were implemented
directly inside A1 and A3 (see below) — no new agents, no extra model calls.

The business-side Devil's Advocate (**L0-4, DB1–DB7**) was deliberately
**built and retained** — business data arrives self-reported and unaudited;
the asymmetry with the stock side is intentional.

## What was moved / folded in

| Former A5 concern | Now lives in | Form |
|---|---|---|
| Source credibility | A1 — `market/news_scoring.py` | `NewsItem.credibility` (`primary`/`secondary`/`rumor`), weighted 6:2:1 in the news score |
| News already priced in | A1 — `market/news_scoring.py` | `NewsItem.already_priced_in` (price moved >10% in the 5 days before publication → contributes nothing) |
| Coordinated amplification | A1 — `market/news_scoring.py` | `NewsItem.coordinated_amplification` (≥3 near-duplicate positive stories in low-quality outlets within 24h → echoes ignored) |
| Manipulation detection | A3 — `market/gate.py` | `manipulation_risk` (`low`/`medium`/`high`); **HIGH → automatic REJECT** (a gate, not a score input) |

## New architecture (mapped onto the existing graph)

```
N1 intent ──(allocation intents)──> l0_allocation (LAYER 0)
                                        │
              INSUFFICIENT_DATA / 0% ───┴──> END (message + question list)
              stocks > 0
                │
                ▼
   [n2a_market + n2b_business + n2c_risk]  (existing fan-out)
        │  n2a now also runs the LAYER 1 stock engine:
        │  A1 news · A2 macro · A3 gate · A4 flow (parallel) → synthesizer
        ▼
   n5_optimizer (only distributes Layer 0's stock slice; only eligible tickers)
        ▼
   n3_legal → n6_hitl (PIN) → n7_execute        ← unchanged
```

## New modules

Backend (`backend/app/`):

- `core/allocation_config.py` — **every** weight and threshold (uncalibrated
  placeholders for backtest tuning; no magic numbers in logic)
- `agents/allocation/schemas.py` — B0 intake schema; every field carries an
  evidence tag (`VERIFIED`/`CLAIMED`/`ESTIMATED`/`UNKNOWN`; UNKNOWN is never
  defaulted)
- `agents/allocation/intake.py` — B0 completeness gate (<40% →
  `INSUFFICIENT_DATA`, a valid terminal output) + staged 3-question
  interrogation
- `agents/allocation/constraints.py` — L0-2 personal hard vetoes (absolute)
- `agents/allocation/quality.py` — L0-3 Q1–Q5; Q5 purpose classified by hard
  rules (`SURVIVAL`/`DEBT`/`UNCLEAR` → reject)
- `agents/allocation/devils_advocate.py` — L0-4 DB1–DB7 (retained)
- `agents/allocation/normalizer.py` — L0-1 comparability + STEP 4/5
  (illiquidity discount, time cost, control/info-edge premiums with the
  no-control-no-edge collapse rule, allocation split)
- `agents/allocation/engine.py` — the STEP 0–5 decision flow (pure function)
- `agents/allocation/node.py` — the `l0_allocation` graph node (DB loading)
- `agents/market/gate.py` — A3 liquidity gate + manipulation_risk
- `agents/market/news_scoring.py` — A1 scoring + folded gates
- `agents/market/macro.py` — A2 (IHSG/USDIDR regimes)
- `agents/market/flow.py` — A4 (OBV/AD/volume proxies; foreign-flow
  unavailability declared as an evidence gap)
- `agents/market/synthesizer.py` — verdict bands + invalidation condition
- `agents/market/stock_engine.py` — A1–A4 parallel runner per ticker
- `api/v1/allocation.py` — intake/investor profile CRUD + `POST /analyze`
- `migrations/0012_allocation_layer0.sql` — `business_intake_profiles`,
  `investor_profiles` (RLS, workspace-ownership pattern)

Frontend (`frontend/`):

- `app/(protected)/allocation/page.tsx` — Views 1 (allocation hero bar,
  symmetric why-not panels, blocker to-do, bias strip), 3 (gated stock
  detail) and 4 (insufficient-data checklist)
- `app/(protected)/allocation/intake/[businessId]/page.tsx` — View 2 data
  entry, evidence tag per field
- `app/(protected)/allocation/investor/page.tsx` — L0-2 inputs
- `components/allocation/` — `allocation-bar`, `evidence-badge`,
  `stock-verdict-card`, `business-panel`
- `lib/api-client.ts` — typed endpoints; `middleware.ts` — `/allocation` and
  `/business` added to protected prefixes; sidebar link "Alokasi Modal"

## Behavior changes to pre-existing code

- `Intent.ALLOCATE_CAPITAL` added (N1 prompt extended); the default blue-chip
  basket fallback now also applies to it.
- `_route_after_intent` sends allocation intents to `l0_allocation` instead
  of straight to the analyst fan-out.
- `market_node` (N2a) additionally runs the Layer 1 stock engine when a
  `layer0_result` is in state, and emits `entities.eligible_tickers`.
- `optimizer_node` (N5) prefers `eligible_tickers` and multiplies its budget
  by Layer 0's stock fraction — it distributes the stock *slice*, never the
  full amount.
- `AgentState` gained `layer0_result`.
- `tests/test_intent_classifier.py` expected-enum set updated.
- Out of scope, untouched: legal RAG (N3), HITL/PIN (N6), execution (N7),
  audit threading, WhatsApp, checkpointer, position sizing (a signal is not
  a size).

## Guardrails implemented as code, not docs

1. Market data timestamps (`as_of`) + staleness flag (gate → CONDITIONAL).
2. Claims carry sources (news credibility ladder; gate checks show
   threshold vs observed).
3. `UNKNOWN` is first-class: never interpolated, weights renormalized,
   missing components reported.
4. `INSUFFICIENT_DATA` is a success path (own UI view, staged questions).
5. Position sizing intentionally absent from verdicts.
6. Research-tool disclaimer rendered on the allocation page.
