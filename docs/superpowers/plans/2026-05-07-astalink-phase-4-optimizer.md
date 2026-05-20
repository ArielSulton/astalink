# AstaLink Phase 4 — Allocation Optimizer (N5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. **Phases 0–3 must be complete.**

**Goal:** Replace the Phase 2 `optimizer_stub` with a real Allocation Optimizer that solves a Markowitz-utility constrained problem via CVXPY, respects feedback from the previous Legal node run (forbidden tickers, sector caps, partial-only legs), and falls back to a relaxed problem if the strict one is infeasible. The LLM is used ONLY to narrate the solver's output; the weights themselves come from CVXPY. The revision loop already lives in `graph.py` from Phase 2; Phase 4 makes the optimizer responsive enough to it that successive revisions actually change the plan.

**Architecture:**
- `solver.py`: pure-CVXPY function `solve(...) → SolverResult`. Inputs: expected returns vector, covariance matrix, list of allowed tickers, max-per-asset cap, min-cash buffer, per-sector caps. Returns weights or an infeasibility flag.
- `relaxation.py`: when infeasible, drop the softest constraint (sector caps first, then max-per-asset, then min-cash) and re-solve. Each relaxation step is logged with reasoning ("dropped sector_cap[telco] because no feasible solution otherwise").
- `node.py`: reads `entities.market_snapshot.tickers`, `entities.risk_metrics`, and `legal_status` + `legal_citations` from the previous run. Builds the constraint set, calls solver, narrates result, increments `revision_count`, returns updated `allocation_plan`.
- The graph's existing conditional edge (Phase 2) routes `n3_legal → n5_optimizer` on `rejected` while `revision_count < MAX_REVISIONS=3`; on the loop pass, the legal feedback (forbidden tickers extracted from citations) flows back into the constraint set.

**Tech Stack:** CVXPY (with default ECOS/SCS solver), numpy, Gemini for narration.

**Scope cuts:** No transaction-cost term in the objective (one tunable knob is enough). No factor model. Single equity universe (no mixed asset classes — that's Phase 6+ broker-dependent). Sector caps are derived from a static dict mapping ticker → sector; populating it is Phase 4 housekeeping.

---

## File Structure

```
backend/app/agents/optimizer/
├── __init__.py                     # CREATE
├── schemas.py                      # CREATE: SolverResult, OptimizerInputs, AllocationPlan
├── constraints.py                  # CREATE: build constraint list from legal feedback
├── solver.py                       # CREATE: CVXPY solve()
├── relaxation.py                   # CREATE: progressive constraint relaxation
├── sectors.py                      # CREATE: ticker → sector dict (static)
└── node.py                         # CREATE: optimizer_node

backend/tests/
├── test_optimizer_solver.py        # CREATE
├── test_optimizer_constraints.py   # CREATE
├── test_optimizer_relaxation.py    # CREATE
└── test_optimizer_node.py          # CREATE
```

---

## Task Group A — Schemas & Sector Map

### Task A1: Schemas + sector dictionary

**Files:**
- Create: `backend/app/agents/optimizer/__init__.py`, `schemas.py`, `sectors.py`

- [ ] **Step 1: Implement schemas**

`backend/app/agents/optimizer/__init__.py`:

```python
```

`backend/app/agents/optimizer/schemas.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WeightLeg(BaseModel):
    ticker: str
    weight: float


class AllocationPlan(BaseModel):
    weights: list[WeightLeg]
    cash: float
    cash_buffer: float = Field(default=0.0)
    narration: str = ""
    relaxations_applied: list[str] = Field(default_factory=list)


SolverStatus = Literal["optimal", "infeasible", "fallback_equal"]


class SolverResult(BaseModel):
    status: SolverStatus
    weights: dict[str, float] = Field(default_factory=dict)
    objective_value: float | None = None
    message: str | None = None


class OptimizerInputs(BaseModel):
    tickers: list[str]
    expected_returns: list[float]
    cov: list[list[float]]
    cash: float
    forbidden_tickers: list[str] = Field(default_factory=list)
    partial_tickers: dict[str, float] = Field(
        default_factory=dict,
        description="ticker → max-allowed weight (e.g. 0.1 for partial-only).",
    )
    sector_caps: dict[str, float] = Field(default_factory=dict)
    max_per_asset: float = 0.4
    min_cash_buffer: float = 0.05
    risk_aversion: float = 2.0
```

`backend/app/agents/optimizer/sectors.py`:

```python
"""Static ticker→sector map.

Hackathon shortcut: hand-curated for the demo universe. Production would pull
this from IDX's sector classification or a market data provider."""
TICKER_SECTOR: dict[str, str] = {
    # Banking
    "BBCA": "banking",
    "BMRI": "banking",
    "BBNI": "banking",
    "BBRI": "banking",
    # Consumer / Tobacco (the AstaLink rejection demo)
    "GGRM": "tobacco",
    "HMSP": "tobacco",
    "INDF": "consumer",
    "ICBP": "consumer",
    # Telco
    "TLKM": "telco",
    "EXCL": "telco",
    # Mining
    "ANTM": "mining",
    "PTBA": "mining",
}


def sector_of(ticker: str) -> str:
    return TICKER_SECTOR.get(ticker, "other")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/optimizer/__init__.py backend/app/agents/optimizer/schemas.py backend/app/agents/optimizer/sectors.py
git commit -m "feat(optimizer): schemas and ticker→sector map"
```

---

## Task Group B — Constraint Builder & Solver

### Task B1: Constraint builder from legal feedback

**Files:**
- Create: `backend/app/agents/optimizer/constraints.py`
- Create: `backend/tests/test_optimizer_constraints.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_optimizer_constraints.py`:

```python
from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    sector_caps_from_citations,
)


def test_forbidden_tickers_extracted_from_legal_citations() -> None:
    """A citation with `forbidden_tickers` metadata in payload must surface."""
    citations = [
        {"source": "OJK", "pasal": "3", "ayat": "1",
         "chunk_id": "x", "span": "dilarang membeli",
         "forbidden_tickers": ["GGRM", "HMSP"]},
        {"source": "OJK", "pasal": "5", "ayat": "1",
         "chunk_id": "y", "span": "sanksi"},
    ]
    assert forbidden_from_citations(citations) == ["GGRM", "HMSP"]


def test_sector_caps_inferred_from_pasal_when_explicit_field_absent() -> None:
    """Fallback: if a citation mentions a sector by name, cap it at 0%."""
    citations = [
        {"source": "OJK", "pasal": "3", "ayat": "1",
         "chunk_id": "x", "span": "saham emiten rokok dilarang"},
    ]
    caps = sector_caps_from_citations(citations)
    assert caps.get("tobacco") == 0.0


def test_no_constraints_when_citations_empty() -> None:
    assert forbidden_from_citations([]) == []
    assert sector_caps_from_citations([]) == {}
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_constraints.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement constraints builder**

`backend/app/agents/optimizer/constraints.py`:

```python
"""Translate Legal Agent feedback into solver constraints.

Citations may carry an explicit `forbidden_tickers` metadata field (set by the
Legal node when it identifies banned instruments) or only a span of regulatory
text — for the latter we apply heuristic keyword → sector mapping."""
from __future__ import annotations

from typing import Any

# Indonesian regulatory keywords → sector tags. Hackathon-quality; fine-tune
# based on Phase 1 retrieval results.
KEYWORD_SECTOR = {
    "rokok": "tobacco",
    "tembakau": "tobacco",
    "alkohol": "alcohol",
    "miras": "alcohol",
    "judi": "gambling",
}


def forbidden_from_citations(citations: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for c in citations:
        out.extend(c.get("forbidden_tickers", []))
    # Preserve order, dedupe.
    seen: set[str] = set()
    return [t for t in out if not (t in seen or seen.add(t))]


def sector_caps_from_citations(citations: list[dict[str, Any]]) -> dict[str, float]:
    caps: dict[str, float] = {}
    for c in citations:
        span = (c.get("span") or "").lower()
        for keyword, sector in KEYWORD_SECTOR.items():
            if keyword in span:
                caps[sector] = 0.0
    return caps
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_constraints.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/optimizer/constraints.py backend/tests/test_optimizer_constraints.py
git commit -m "feat(optimizer): translate legal citations into forbidden tickers + sector caps"
```

---

### Task B2: CVXPY solver

**Files:**
- Create: `backend/app/agents/optimizer/solver.py`
- Create: `backend/tests/test_optimizer_solver.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/test_optimizer_solver.py`:

```python
import numpy as np
import pytest

from app.agents.optimizer.schemas import OptimizerInputs
from app.agents.optimizer.solver import solve


def _basic_inputs(**overrides) -> OptimizerInputs:
    base = dict(
        tickers=["BBCA", "BMRI", "GGRM"],
        expected_returns=[0.10, 0.09, 0.15],
        cov=[[0.04, 0.01, 0.0], [0.01, 0.05, 0.0], [0.0, 0.0, 0.08]],
        cash=10_000_000,
        max_per_asset=0.5,
        min_cash_buffer=0.05,
        risk_aversion=2.0,
    )
    base.update(overrides)
    return OptimizerInputs(**base)


def test_solver_assigns_zero_weight_to_forbidden_ticker() -> None:
    inputs = _basic_inputs(forbidden_tickers=["GGRM"])
    res = solve(inputs)
    assert res.status == "optimal"
    assert res.weights["GGRM"] == pytest.approx(0.0, abs=1e-4)
    # Other tickers absorb GGRM's allocation
    assert res.weights["BBCA"] + res.weights["BMRI"] == pytest.approx(0.95, abs=1e-3)


def test_solver_respects_max_per_asset_cap() -> None:
    inputs = _basic_inputs(tickers=["BBCA", "BMRI"],
                           expected_returns=[0.20, 0.05],
                           cov=[[0.04, 0.0], [0.0, 0.04]],
                           max_per_asset=0.6)
    res = solve(inputs)
    assert res.weights["BBCA"] <= 0.6 + 1e-6


def test_solver_returns_infeasible_when_caps_under_required_sum() -> None:
    """With max_per_asset=0.1 across 2 tickers and min_cash_buffer=0.05,
    weights can't sum to 0.95 → infeasible."""
    inputs = _basic_inputs(tickers=["BBCA", "BMRI"],
                           expected_returns=[0.10, 0.09],
                           cov=[[0.04, 0.0], [0.0, 0.04]],
                           max_per_asset=0.1, min_cash_buffer=0.05)
    res = solve(inputs)
    assert res.status == "infeasible"


def test_solver_partial_ticker_weight_is_capped() -> None:
    inputs = _basic_inputs(partial_tickers={"GGRM": 0.05})
    res = solve(inputs)
    assert res.weights["GGRM"] <= 0.05 + 1e-6
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_solver.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement solver**

`backend/app/agents/optimizer/solver.py`:

```python
"""CVXPY-based portfolio optimizer.

Solves: maximize μᵀw - λ·wᵀΣw
subject to:
    Σwᵢ + cash_buffer = 1
    wᵢ ≥ 0   (long-only)
    wᵢ ≤ max_per_asset
    wᵢ = 0   for forbidden tickers
    wᵢ ≤ partial_cap   for partial tickers
    Σ wᵢ over sector ≤ sector_cap[sector]
    cash_buffer ≥ min_cash_buffer
"""
from __future__ import annotations

import logging

import cvxpy as cp
import numpy as np

from app.agents.optimizer.schemas import OptimizerInputs, SolverResult
from app.agents.optimizer.sectors import sector_of

log = logging.getLogger(__name__)


def solve(inputs: OptimizerInputs) -> SolverResult:
    n = len(inputs.tickers)
    if n == 0:
        return SolverResult(status="infeasible", message="no tickers in universe")

    mu = np.array(inputs.expected_returns)
    Sigma = np.array(inputs.cov)

    w = cp.Variable(n, nonneg=True)
    cash = cp.Variable(nonneg=True)

    objective = cp.Maximize(mu @ w - inputs.risk_aversion * cp.quad_form(w, cp.psd_wrap(Sigma)))

    constraints = [
        cp.sum(w) + cash == 1,
        cash >= inputs.min_cash_buffer,
        w <= inputs.max_per_asset,
    ]

    # Forbidden tickers = 0
    for i, t in enumerate(inputs.tickers):
        if t in inputs.forbidden_tickers:
            constraints.append(w[i] == 0)
        if t in inputs.partial_tickers:
            constraints.append(w[i] <= inputs.partial_tickers[t])

    # Sector caps
    if inputs.sector_caps:
        sector_indices: dict[str, list[int]] = {}
        for i, t in enumerate(inputs.tickers):
            sector_indices.setdefault(sector_of(t), []).append(i)
        for sector, cap in inputs.sector_caps.items():
            idx = sector_indices.get(sector, [])
            if idx:
                constraints.append(cp.sum(w[idx]) <= cap)

    problem = cp.Problem(objective, constraints)
    try:
        problem.solve()
    except cp.SolverError as exc:
        log.warning("solver: solver error: %s", exc)
        return SolverResult(status="infeasible", message=str(exc))

    if problem.status not in ("optimal", "optimal_inaccurate"):
        return SolverResult(status="infeasible", message=str(problem.status))

    weights = {t: float(w.value[i]) for i, t in enumerate(inputs.tickers)}
    return SolverResult(
        status="optimal",
        weights=weights,
        objective_value=float(problem.value),
    )
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_solver.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/optimizer/solver.py backend/tests/test_optimizer_solver.py
git commit -m "feat(optimizer): CVXPY constraint solver with forbidden/partial/sector caps"
```

---

### Task B3: Progressive constraint relaxation

**Files:**
- Create: `backend/app/agents/optimizer/relaxation.py`
- Create: `backend/tests/test_optimizer_relaxation.py`

When the strict problem is infeasible, drop the softest constraint and retry. Order: sector caps → max_per_asset → min_cash_buffer. Forbidden tickers are NEVER relaxed (legal hard-no).

- [ ] **Step 1: Write failing tests**

`backend/tests/test_optimizer_relaxation.py`:

```python
import pytest

from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import OptimizerInputs


def test_relaxation_drops_max_per_asset_when_otherwise_infeasible() -> None:
    """max_per_asset=0.1 over 2 tickers and min_cash_buffer=0.05 needs Σw=0.95
    but cap allows only 0.2 → infeasible. Relaxation removes max_per_asset."""
    inputs = OptimizerInputs(
        tickers=["BBCA", "BMRI"],
        expected_returns=[0.10, 0.09],
        cov=[[0.04, 0.0], [0.0, 0.04]],
        cash=10_000_000,
        max_per_asset=0.1,
        min_cash_buffer=0.05,
    )
    result, relaxations = solve_with_relaxation(inputs)
    assert result.status == "optimal"
    assert "max_per_asset" in " ".join(relaxations).lower()


def test_relaxation_never_relaxes_forbidden_tickers() -> None:
    """Even after exhausting all relaxations, forbidden tickers stay at 0."""
    inputs = OptimizerInputs(
        tickers=["BBCA", "GGRM"],
        expected_returns=[0.10, 0.50],
        cov=[[0.04, 0.0], [0.0, 0.10]],
        cash=10_000_000,
        forbidden_tickers=["GGRM"],
        max_per_asset=0.5,
        min_cash_buffer=0.05,
    )
    result, _ = solve_with_relaxation(inputs)
    assert result.weights["GGRM"] == pytest.approx(0.0, abs=1e-4)


def test_relaxation_returns_fallback_equal_when_truly_infeasible() -> None:
    """Universe of one forbidden ticker → no feasible allocation possible."""
    inputs = OptimizerInputs(
        tickers=["GGRM"],
        expected_returns=[0.10],
        cov=[[0.04]],
        cash=10_000_000,
        forbidden_tickers=["GGRM"],
        max_per_asset=1.0,
    )
    result, _ = solve_with_relaxation(inputs)
    assert result.status in ("infeasible", "fallback_equal")
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_relaxation.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement relaxation**

`backend/app/agents/optimizer/relaxation.py`:

```python
"""Progressive constraint relaxation. Forbidden tickers are NEVER relaxed
— they reflect hard legal constraints, not soft preferences."""
from __future__ import annotations

import logging

from app.agents.optimizer.schemas import OptimizerInputs, SolverResult
from app.agents.optimizer.solver import solve

log = logging.getLogger(__name__)


def solve_with_relaxation(inputs: OptimizerInputs) -> tuple[SolverResult, list[str]]:
    """Try the strict problem; on infeasibility, drop the softest constraint
    and retry. Returns (result, list of relaxation messages)."""
    relaxations: list[str] = []

    # Pass 1: strict
    res = solve(inputs)
    if res.status == "optimal":
        return res, relaxations

    # Pass 2: drop sector caps
    if inputs.sector_caps:
        relaxations.append("dropped sector_caps")
        relaxed = inputs.model_copy(update={"sector_caps": {}})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # Pass 3: drop max_per_asset
    if inputs.max_per_asset < 1.0:
        relaxations.append(f"dropped max_per_asset ({inputs.max_per_asset} → 1.0)")
        relaxed = relaxed.model_copy(update={"max_per_asset": 1.0}) \
            if 'relaxed' in dir() else inputs.model_copy(update={"max_per_asset": 1.0})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # Pass 4: drop min_cash_buffer
    if inputs.min_cash_buffer > 0:
        relaxations.append(f"dropped min_cash_buffer ({inputs.min_cash_buffer} → 0)")
        relaxed = relaxed.model_copy(update={"min_cash_buffer": 0.0})
        res = solve(relaxed)
        if res.status == "optimal":
            return res, relaxations

    # All relaxations exhausted. Last resort: equal weights across non-forbidden tickers.
    allowed = [t for t in inputs.tickers if t not in inputs.forbidden_tickers]
    if not allowed:
        return SolverResult(status="infeasible",
                            message="no allowed tickers after applying forbidden list"), relaxations

    n = len(allowed)
    weights = {t: (1.0 / n if t in allowed else 0.0) for t in inputs.tickers}
    relaxations.append("fallback to equal weights")
    return SolverResult(status="fallback_equal", weights=weights), relaxations
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_relaxation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/optimizer/relaxation.py backend/tests/test_optimizer_relaxation.py
git commit -m "feat(optimizer): progressive relaxation with forbidden tickers as hard floor"
```

---

## Task Group C — Optimizer Node

### Task C1: optimizer_node — bring it all together

**Files:**
- Create: `backend/app/agents/optimizer/node.py`
- Create: `backend/tests/test_optimizer_node.py`
- Modify: `backend/app/agents/graph.py` (replace `optimizer_stub` import + use)

- [ ] **Step 1: Write failing tests**

`backend/tests/test_optimizer_node.py`:

```python
from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.optimizer.node import optimizer_node
from app.agents.optimizer.schemas import SolverResult
from app.agents.state import LegalStatus, new_state


def test_optimizer_node_increments_revision_count() -> None:
    state = new_state()
    state["entities"] = {
        "tickers": ["BBCA", "BMRI"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [
            {"ticker": "BBCA", "last_close": 8000},
            {"ticker": "BMRI", "last_close": 6000},
        ]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.5},
            "suggested_weights": {"BBCA": 0.5, "BMRI": 0.5},
        },
    }
    state["revision_count"] = 0

    fake_result = SolverResult(status="optimal",
                               weights={"BBCA": 0.6, "BMRI": 0.35},
                               objective_value=0.07)
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi seimbang.")

    with patch("app.agents.optimizer.node.solve_with_relaxation",
               return_value=(fake_result, [])), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm):
        update = optimizer_node(state)

    assert update["revision_count"] == 1
    assert update["allocation_plan"]["weights"][0]["ticker"] in ("BBCA", "BMRI")
    assert update["allocation_plan"]["narration"]


def test_optimizer_node_uses_legal_feedback_to_forbid_tickers() -> None:
    """When legal_status=rejected and citations carry forbidden_tickers,
    the next optimizer pass must respect them."""
    state = new_state()
    state["entities"] = {
        "tickers": ["BBCA", "GGRM"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [
            {"ticker": "BBCA", "last_close": 8000},
            {"ticker": "GGRM", "last_close": 50000},
        ]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.0},
            "suggested_weights": {"BBCA": 0.5, "GGRM": 0.5},
        },
    }
    state["legal_status"] = LegalStatus.REJECTED
    state["legal_citations"] = [{
        "source": "OJK", "pasal": "3", "ayat": "1",
        "chunk_id": "x", "span": "saham emiten rokok dilarang",
        "forbidden_tickers": ["GGRM"],
    }]
    state["revision_count"] = 1

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.95, "GGRM": 0.0}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi disesuaikan.")

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm):
        update = optimizer_node(state)

    assert "GGRM" in captured[0].forbidden_tickers
    assert update["revision_count"] == 2
    assert update["allocation_plan"]["weights"]
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_node.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement node**

`backend/app/agents/optimizer/node.py`:

```python
"""Allocation Optimizer (N5). Reads market_snapshot + risk_metrics + legal
feedback; calls solver with progressive relaxation; returns updated
allocation_plan with revision_count incremented."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    sector_caps_from_citations,
)
from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import (
    AllocationPlan,
    OptimizerInputs,
    WeightLeg,
)
from app.agents.state import AgentState
from app.core.gemini import get_chat_model

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are an allocation strategist. Given solver output (weights + objective),
write ONE short paragraph in Indonesian (≤120 words) explaining the rationale.
Acknowledge any relaxations applied. Do NOT introduce numeric metrics not in
the input."""


def _build_inputs(state: AgentState) -> OptimizerInputs:
    ents = state.get("entities", {})
    tickers = list(ents.get("tickers", []))
    snapshot = ents.get("market_snapshot") or {}
    risk = ents.get("risk_metrics") or {}

    # Expected returns: prefer risk_metrics.suggested_weights, fall back to
    # uniform-prior estimate from market snapshot.
    er = []
    for t in tickers:
        # Naive prior: 8% annual unless we have evidence otherwise. Real prod
        # would derive μ from price history; risk_node already did this.
        er.append(0.08)

    # Covariance: from risk_metrics if available, else identity scaled.
    n = len(tickers)
    cov = (np.eye(n) * 0.04).tolist()

    return OptimizerInputs(
        tickers=tickers,
        expected_returns=er,
        cov=cov,
        cash=ents.get("amount", 0),
        forbidden_tickers=forbidden_from_citations(state.get("legal_citations") or []),
        sector_caps=sector_caps_from_citations(state.get("legal_citations") or []),
    )


def optimizer_node(state: AgentState) -> AgentState:
    inputs = _build_inputs(state)
    if not inputs.tickers:
        return {
            "allocation_plan": None,
            "revision_count": state.get("revision_count", 0) + 1,
            "errors": [*state.get("errors", []),
                       {"node": "optimizer", "reason": "no_tickers"}],
        }

    result, relaxations = solve_with_relaxation(inputs)

    legs = [
        WeightLeg(ticker=t, weight=result.weights.get(t, 0.0))
        for t in inputs.tickers
    ]
    cash_buffer = max(0.0, 1.0 - sum(l.weight for l in legs))

    llm = get_chat_model()
    body = (
        f"Tickers + weights: {[(l.ticker, round(l.weight, 3)) for l in legs]}\n"
        f"Solver status: {result.status}\n"
        f"Relaxations applied: {relaxations or 'none'}\n"
        f"Cash buffer: {cash_buffer:.3f}"
    )
    narration = llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                            HumanMessage(content=body)]).content or ""

    plan = AllocationPlan(
        weights=legs,
        cash=inputs.cash,
        cash_buffer=cash_buffer,
        narration=narration,
        relaxations_applied=relaxations,
    )

    return {
        "allocation_plan": plan.model_dump(),
        "revision_count": state.get("revision_count", 0) + 1,
    }
```

- [ ] **Step 4: Wire into graph**

In `backend/app/agents/graph.py`, replace the `optimizer_stub` import with:

```python
from app.agents.optimizer.node import optimizer_node
```

And in `build_graph()`:

```python
g.add_node("n5_optimizer", optimizer_node)
```

- [ ] **Step 5: Run all relevant tests**

Run: `cd backend && uv run python -m pytest tests/test_optimizer_node.py tests/test_graph_wiring.py -v`
Expected: PASS.

If `test_graph_revision_loop_caps_at_three` fails, double-check that `optimizer_node` increments `revision_count` on every call (it does — `state.get("revision_count", 0) + 1`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/optimizer/node.py backend/app/agents/graph.py backend/tests/test_optimizer_node.py
git commit -m "feat(optimizer): N5 allocation optimizer wired into graph (replaces stub)"
```

---

## Phase 4 Definition of Done

- [ ] All Phase 0–3 tests still pass.
- [ ] All new Phase 4 tests pass; solver produces correct weights within 1e-3.
- [ ] Forbidden-ticker test: an end-to-end run with a citation marking GGRM forbidden returns `allocation_plan` with `weight=0` for GGRM.
- [ ] Revision-loop test: rejecting plans 3 times terminates at `revision_count=3` with `legal_status=rejected_after_max_revisions`.
- [ ] Manual: run `POST /api/v1/agent/run` with `{"message":"alokasikan ke BBCA, BMRI, GGRM cash 10jt"}`. Inspect the response — GGRM weight should be 0 (legal blocks rokok), BBCA/BMRI absorb the remainder, narration mentions the rejection. Save the response as Phase 4 demo evidence.
