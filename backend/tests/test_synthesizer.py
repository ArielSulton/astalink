"""Layer 1 synthesizer: formula, gates, renormalization, invalidation."""
from __future__ import annotations

import pytest

from app.agents.market.flow import FlowScore
from app.agents.market.gate import GateCheck, GateResult, GateStatus, ManipulationRisk
from app.agents.market.macro import MacroScore
from app.agents.market.news_scoring import NewsScore
from app.agents.market.synthesizer import VerdictBand, synthesize
from app.core.allocation_config import allocation_config


def _gate(status=GateStatus.PASS, risk=ManipulationRisk.LOW,
          checks=None) -> GateResult:
    return GateResult(
        ticker="BBCA", status=status, manipulation_risk=risk,
        checks=checks if checks is not None else [
            GateCheck(name="market_cap", status="pass", detail="",
                      threshold="", observed=""),
            GateCheck(name="free_float", status="pass", detail="",
                      threshold="", observed=""),
        ])


def _run(news=70.0, macro=60.0, flow=80.0, gate=None, last_close=10_000.0):
    return synthesize(
        "BBCA",
        NewsScore(score=news, n_items=3),
        MacroScore(score=macro),
        gate or _gate(),
        FlowScore(score=flow),
        last_close=last_close,
    )


def test_formula_matches_config_weights():
    w = allocation_config.stock_weights
    v = _run(news=70, macro=60, flow=80)
    expected = (70 * w.a1_news + 60 * w.a2_macro + 100 * w.a3_quality
                + 80 * w.a4_flow)  # a3_quality = 100 (all checks pass)
    assert v.score == pytest.approx(expected, abs=0.1)
    # no adversarial discount: final == base
    assert "devil" not in str(v.model_dump())


def test_gate_fail_is_reject_regardless_of_scores():
    v = _run(news=95, macro=95, flow=95,
             gate=_gate(status=GateStatus.FAIL, risk=ManipulationRisk.HIGH))
    assert v.band == VerdictBand.REJECT
    assert v.score is None
    assert v.manipulation_risk == "high"


def test_conditional_gate_caps_at_watchlist():
    v = _run(news=95, macro=95, flow=95,
             gate=_gate(status=GateStatus.CONDITIONAL))
    assert v.band == VerdictBand.WATCHLIST


def test_missing_component_renormalizes_and_reports():
    v = synthesize("BBCA", NewsScore(score=None), MacroScore(score=60.0),
                   _gate(), FlowScore(score=80.0), last_close=10_000.0)
    assert v.score is not None
    assert v.components["a1_news"] is None
    assert any("direnormalisasi" in g for g in v.evidence_gaps)


def test_too_few_components_is_no_verdict_not_neutral():
    v = synthesize("BBCA", NewsScore(score=None), MacroScore(score=None),
                   GateResult(ticker="BBCA", status=GateStatus.CONDITIONAL,
                              manipulation_risk=ManipulationRisk.LOW, checks=[]),
                   FlowScore(score=70.0))
    assert v.band == VerdictBand.NO_VERDICT
    assert v.score is None


def test_invalidation_condition_has_concrete_price_level():
    v = _run(last_close=10_000.0)
    stop = 10_000 * (1 - allocation_config.synthesizer.invalidation_stop_pct)
    assert f"{stop:,.0f}" in v.invalidation_condition
    assert v.horizon == allocation_config.synthesizer.default_horizon
