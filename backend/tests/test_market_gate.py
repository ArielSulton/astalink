"""A3 liquidity gate + manipulation_risk (pure logic, no yfinance)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.market.gate import (
    GateStatus,
    LiquidityData,
    ManipulationRisk,
    evaluate_gate,
)
from app.core.allocation_config import allocation_config


def _healthy(**overrides) -> LiquidityData:
    base = dict(
        ticker="BBCA",
        market_cap=1_200_000_000_000_000,   # Rp 1200 T
        free_float_pct=0.42,
        avg_daily_value_20d=500_000_000_000,
        bid_ask_spread_pct=0.001,
        board="Main",
        daily_returns_20d=[0.001] * 20,
        daily_volumes_20d=[1_000_000.0] * 20,
        has_recent_fundamental_news=True,
        as_of=datetime.now(timezone.utc).isoformat(),
    )
    base.update(overrides)
    return LiquidityData(**base)


def test_healthy_bluechip_passes():
    res = evaluate_gate(_healthy(), planned_position_idr=100_000_000)
    assert res.status == GateStatus.PASS
    assert res.manipulation_risk == ManipulationRisk.LOW


def test_small_cap_fails_conservative_profile():
    res = evaluate_gate(_healthy(market_cap=800_000_000_000),
                        planned_position_idr=100_000_000,
                        thresholds=allocation_config.gate.conservative)
    assert res.status == GateStatus.FAIL


def test_small_cap_passes_aggressive_profile():
    res = evaluate_gate(_healthy(market_cap=800_000_000_000),
                        planned_position_idr=100_000_000,
                        thresholds=allocation_config.gate.aggressive)
    assert res.status == GateStatus.PASS


def test_large_cap_tiny_float_still_fails():
    """Big market cap with tiny free float is MORE dangerous, not less."""
    res = evaluate_gate(_healthy(free_float_pct=0.05),
                        planned_position_idr=100_000_000)
    assert res.status == GateStatus.FAIL


def test_unknown_data_yields_conditional_not_pass():
    res = evaluate_gate(_healthy(bid_ask_spread_pct=None),
                        planned_position_idr=100_000_000)
    assert res.status == GateStatus.CONDITIONAL
    check = next(c for c in res.checks if c.name == "bid_ask_spread")
    assert check.status == "unknown"
    assert check.observed == "UNKNOWN"


def test_board_unknown_is_declared_evidence_gap():
    res = evaluate_gate(_healthy(board=None), planned_position_idr=100_000_000)
    assert res.status == GateStatus.CONDITIONAL
    assert any("Papan pencatatan" in g for g in res.evidence_gaps)


def test_special_monitoring_board_fails():
    res = evaluate_gate(_healthy(board="Special Monitoring"),
                        planned_position_idr=100_000_000)
    assert res.status == GateStatus.FAIL


def test_adv_position_ratio_gate():
    # position Rp 100 B vs ADV Rp 500 B → 5x < 20x required
    res = evaluate_gate(_healthy(), planned_position_idr=100_000_000_000)
    assert res.status == GateStatus.FAIL


def test_pump_setup_is_high_risk_and_rejects():
    """Thin float + volume spike + no fundamental news → HIGH → REJECT."""
    vols = [1_000_000.0] * 19 + [10_000_000.0]
    res = evaluate_gate(
        _healthy(free_float_pct=0.20,  # passes float threshold...
                 daily_volumes_20d=vols,
                 has_recent_fundamental_news=False),
        planned_position_idr=100_000_000)
    # 0.20 float is not "thin" (<0.10) → only MEDIUM
    assert res.manipulation_risk == ManipulationRisk.MEDIUM

    res2 = evaluate_gate(
        _healthy(free_float_pct=0.16, daily_volumes_20d=vols,
                 has_recent_fundamental_news=False),
        planned_position_idr=100_000_000)
    assert res2.manipulation_risk == ManipulationRisk.MEDIUM

    # genuinely thin float (fails gate anyway) + spike + no news → HIGH
    res3 = evaluate_gate(
        _healthy(free_float_pct=0.08, daily_volumes_20d=vols,
                 has_recent_fundamental_news=False),
        planned_position_idr=100_000_000)
    assert res3.manipulation_risk == ManipulationRisk.HIGH
    assert res3.status == GateStatus.FAIL


def test_limit_up_streak_then_volume_collapse_is_high():
    rets = [0.0] * 10 + [0.20, 0.22, 0.21, 0.0] + [0.0] * 6
    vols = [1_000_000.0] * 10 + [5_000_000.0, 6_000_000.0, 5_500_000.0,
                                 1_000_000.0] + [900_000.0] * 6
    res = evaluate_gate(_healthy(daily_returns_20d=rets, daily_volumes_20d=vols),
                        planned_position_idr=100_000_000)
    assert res.manipulation_risk == ManipulationRisk.HIGH
    assert res.status == GateStatus.FAIL


def test_stale_data_downgrades_to_conditional():
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    res = evaluate_gate(_healthy(as_of=old), planned_position_idr=100_000_000)
    assert res.stale
    assert res.status == GateStatus.CONDITIONAL
