"""Allocation Optimizer (N5). Reads market_snapshot + risk_metrics + legal
feedback; calls solver with progressive relaxation; returns updated
allocation_plan with revision_count incremented."""
from __future__ import annotations

import logging

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    partial_tickers_from_citations,
    sector_caps_from_citations,
)
from app.agents.optimizer.relaxation import solve_with_relaxation
from app.agents.optimizer.schemas import (
    AllocationPlan,
    OptimizerInputs,
    WeightLeg,
)
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import record_revision_count, track_node_duration
from app.core.supabase_admin import get_admin_client
from app.core.wallet import get_workspace_balance

log = logging.getLogger(__name__)

NARRATE_SYSTEM = """\
You are an allocation advisor. Given solver output (weights + objective),
write ONE short paragraph in Indonesian (≤120 words) explaining the
recommended rationale. Frame this as a recommendation, not a decision.
Acknowledge any relaxations applied. Do NOT introduce numeric metrics not
in the input. End with a reminder that the final decision is the user's."""


# Heuristic mapping from the free-text risk_profile Gemini extracts in N1
# (e.g. "konservatif"/"sedang"/"agresif") to solver constraints. Anything
# unrecognized (including no risk_profile at all) keeps OptimizerInputs'
# own defaults — behavior for a run with no stated preference is unchanged.
_CONSERVATIVE_KEYWORDS = ("konservatif", "rendah", "low", "conservative")
_AGGRESSIVE_KEYWORDS = ("agresif", "tinggi", "high", "aggressive")

# Fallbacks used only when real data is unavailable (non-allocation paths,
# tests, or tickers with too little price history). When risk_node did run,
# its historical μ/Σ are used instead — see _expected_returns / _covariance.
_DEFAULT_EXPECTED_RETURN = 0.08
_DEFAULT_VARIANCE = 0.04
# ± annualized-return tilt applied at the verdict-score extremes (0 → −tilt,
# 100 → +tilt), so a strong A1-A4 verdict pulls weight toward that ticker.
_SCORE_TILT = 0.10


def _expected_returns(tickers: list[str], ents: dict) -> list[float]:
    """Historical μ (from risk_node) tilted by the A1-A4 verdict score.

    base μ comes from risk_metrics.expected_returns (annualized, real);
    absent tickers fall back to a flat prior. The verdict score (0-100, 50
    neutral) then shifts μ by up to ±_SCORE_TILT so differentiated market
    signals — not a uniform prior — drive the weights."""
    hist_mu = (ents.get("risk_metrics") or {}).get("expected_returns") or {}
    verdicts = (ents.get("stock_engine") or {}).get("verdicts") or {}
    out: list[float] = []
    for t in tickers:
        mu = float(hist_mu.get(t, _DEFAULT_EXPECTED_RETURN))
        score = (verdicts.get(t) or {}).get("score")
        if score is not None:
            mu += ((float(score) - 50.0) / 50.0) * _SCORE_TILT
        out.append(mu)
    return out


def _covariance(tickers: list[str], ents: dict) -> list[list[float]]:
    """Real annualized covariance from risk_node, subset to `tickers`.

    Tickers risk_node had no data for get a diagonal-variance fallback and
    zero cross-covariance — keeping the matrix block-PSD for the solver."""
    cov_map = (ents.get("risk_metrics") or {}).get("covariance") or {}
    n = len(tickers)
    if not cov_map:
        return (np.eye(n) * _DEFAULT_VARIANCE).tolist()
    matrix: list[list[float]] = []
    for ti in tickers:
        row_src = cov_map.get(ti, {})
        row = [
            float(row_src.get(tj, _DEFAULT_VARIANCE if ti == tj else 0.0))
            for tj in tickers
        ]
        matrix.append(row)
    return matrix


def _constraints_from_risk_profile(risk_profile: str | None) -> tuple[float, float]:
    """Returns (max_per_asset, min_cash_buffer)."""
    profile = (risk_profile or "").strip().lower()
    if any(k in profile for k in _CONSERVATIVE_KEYWORDS):
        return 0.25, 0.15
    if any(k in profile for k in _AGGRESSIVE_KEYWORDS):
        return 0.6, 0.0
    return 0.4, 0.05  # OptimizerInputs' own defaults — "sedang"/unstated


def _build_inputs(state: AgentState) -> OptimizerInputs:
    ents = state.get("entities", {})
    # The Layer 1 stock engine narrows tickers to those that passed the A3
    # gate + verdict bands; fall back to the raw ticker list when the engine
    # didn't run (non-allocation paths, tests, engine failure).
    if ents.get("eligible_tickers") is not None:
        tickers = list(ents["eligible_tickers"])
    else:
        tickers = list(ents.get("tickers", []))

    # Real market signals: μ from price history (risk_node) tilted by the
    # A1-A4 verdict score, and covariance from price history — both fall back
    # to flat priors only when risk_node had no usable data.
    er = _expected_returns(tickers, ents)
    cov = _covariance(tickers, ents)

    citations = state.get("legal_citations") or []
    max_per_asset, min_cash_buffer = _constraints_from_risk_profile(ents.get("risk_profile"))

    # Cap the requested amount at the workspace's real sandbox balance
    # (Task 4) — entities.amount alone is just a number the LLM parsed out
    # of the chat message, never checked against anything. Default to the
    # full balance when no amount was stated at all.
    #
    # entities is dict[str, Any] (N1's structured-output schema has no
    # numeric field for "amount"), and Gemini sometimes hands it back as a
    # numeral string ("20000000") rather than a number — coerce defensively
    # rather than letting `min()` crash comparing str to float.
    try:
        requested = float(ents.get("amount") or 0)
    except (TypeError, ValueError):
        requested = 0
    workspace_id = state.get("_workspace_id")
    balance = get_workspace_balance(get_admin_client(), workspace_id) if workspace_id else None
    if balance is None:
        base_cash = requested
    elif requested:
        base_cash = min(requested, balance)
    else:
        base_cash = balance

    # The optimizer only ever analyzes Layer 0's own stock-portion of the
    # funds — analyzing the full requested/available amount regardless of
    # what Layer 0 decided (a prior "advisory mode" choice) let the plan
    # openly contradict Layer 0's own split, e.g. Layer 0 saying "24.8% to
    # stocks" while the optimizer put 95% of the FULL amount into one ticker.
    # Missing layer0_result (shouldn't happen on this path, but tests/direct
    # calls may omit it) falls back to the full amount, unchanged behavior.
    layer0_alloc = (state.get("layer0_result") or {}).get("allocation") or {}
    stocks_fraction = layer0_alloc.get("stocks")
    cash = base_cash * stocks_fraction if stocks_fraction is not None else base_cash

    return OptimizerInputs(
        tickers=tickers,
        expected_returns=er,
        cov=cov,
        cash=cash,
        forbidden_tickers=forbidden_from_citations(citations),
        partial_tickers=partial_tickers_from_citations(citations),
        sector_caps=sector_caps_from_citations(citations),
        max_per_asset=max_per_asset,
        min_cash_buffer=min_cash_buffer,
        total_funds=balance if balance is not None else base_cash,
    )


@track_node_duration("n5_optimizer")
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
    try:
        narration = extract_text(llm.invoke([SystemMessage(content=NARRATE_SYSTEM),
                                HumanMessage(content=body)]).content)
    except Exception as exc:
        # The solved weights above are the actual financial recommendation —
        # narration is decorative color on top of it. A flaky LLM call here
        # (seen live: malformed JSON/unexpected errors from some providers)
        # must not cost the whole allocation plan the way it would if this
        # were left unguarded like the rest of this function.
        log.error("optimizer_node: LLM narration failed: %s", exc)
        narration = ""

    plan = AllocationPlan(
        weights=legs,
        cash=inputs.cash,
        cash_buffer=cash_buffer,
        total_funds=inputs.total_funds,
        narration=narration,
        relaxations_applied=relaxations,
    )

    record_revision_count(state.get("revision_count", 0) + 1)
    return {
        "allocation_plan": plan.model_dump(),
        "revision_count": state.get("revision_count", 0) + 1,
    }
