"""Layer 0 decision flow (STEP 0-5) + normalizer critical rule."""
from __future__ import annotations

import pytest

from app.agents.allocation.engine import run_layer0
from app.agents.allocation.normalizer import adjust_business_score, compute_split
from app.agents.allocation.schemas import (
    AllocationSplit,
    BusinessProfile,
    CapitalNeedItem,
    ConstraintResult,
    EvidenceTag,
    InvestorProfile,
    Layer0Status,
    Tagged,
    VetoFlag,
)
from app.core.allocation_config import allocation_config


def _v(value):
    return Tagged(value=value, evidence=EvidenceTag.VERIFIED)


def _healthy_investor(**kw) -> InvestorProfile:
    base = dict(monthly_expenses=10_000_000, emergency_fund=100_000_000,
                capital_is_borrowed=False, horizon_months=60,
                net_worth=2_000_000_000, consumer_debt_interest_pct=0.0,
                available_hours_per_week=40, knows_sector=True)
    base.update(kw)
    return InvestorProfile(**base)


def _strong_business() -> BusinessProfile:
    p = BusinessProfile()
    p.identity.sector = _v("F&B")
    p.identity.business_model = _v("katering langganan B2B")
    p.identity.b2b_or_b2c = _v("b2b")
    p.identity.location = _v("Surabaya")
    p.current_state.stage = _v("profitable")
    p.current_state.age_months = _v(48)
    p.current_state.headcount = _v(12)
    p.traction.monthly_revenue = _v([100.0] * 12)
    p.traction.growth_rate = _v(0.05)
    p.traction.gross_margin = _v(0.4)
    p.traction.customer_count = _v(40)
    p.traction.retention_rate = _v(0.85)
    p.unit_economics.price = _v(50_000)
    p.unit_economics.cogs_per_unit = _v(30_000)
    p.unit_economics.cac = _v(100_000)
    p.unit_economics.ltv = _v(2_000_000)
    p.unit_economics.contribution_margin = _v(20_000)
    p.unit_economics.payback_months = _v(3)
    p.cash.cash_on_hand = _v(500_000_000)
    p.cash.monthly_burn = _v(80_000_000)
    p.cash.runway_months = _v(6)
    p.cash.is_profitable = _v(True)
    p.capital_need.amount = _v(200_000_000)
    p.capital_need.breakdown = _v([CapitalNeedItem(purpose="tambah kapasitas dapur",
                                                   amount=150_000_000),
                                   CapitalNeedItem(purpose="marketing",
                                                   amount=50_000_000)])
    p.capital_need.consequence_if_unfunded = _v("pertumbuhan melambat")
    p.deal_structure.instrument = _v("equity")
    p.deal_structure.ownership_pct = _v(0.6)
    p.user_role.operator_or_passive = _v("passive")
    p.user_role.hours_per_week = _v(2)
    p.control.ownership_pct = _v(0.6)
    p.control.veto_rights = _v(True)
    p.control.shareholder_agreement_exists = _v(True)
    p.exit.mechanism = _v("buyback bertahap tahun ke-3")
    p.exit.expected_timeline_months = _v(36)
    p.team.operator_identity = _v("Pemilik saat ini")
    p.team.track_record = _v("10 tahun F&B, 2 outlet profit")
    p.team.founder_capital_contributed = _v(300_000_000)
    return p


# --- STEP 0 ---

def test_empty_profile_returns_insufficient_data_with_questions():
    res = run_layer0(_healthy_investor(), BusinessProfile())
    assert res.status == Layer0Status.INSUFFICIENT_DATA
    assert res.allocation is None            # no allocation produced. STOP.
    assert len(res.questions) == 3           # staged: top-3 first
    assert res.baseline_score is not None    # boring option still shown


def test_no_business_leg_skips_intake_gate():
    res = run_layer0(_healthy_investor(), business=None)
    assert res.status == Layer0Status.ALLOCATED
    assert res.allocation.business == 0.0
    assert res.allocation.stocks > 0


# --- STEP 1 ---

def test_force_cash_produces_full_cash_allocation():
    inv = _healthy_investor(emergency_fund=10_000_000)  # 1 month
    res = run_layer0(inv, _strong_business())
    assert res.status == Layer0Status.ALLOCATED
    assert res.allocation == AllocationSplit(cash=1.0, stocks=0.0, business=0.0)


# --- STEP 2 ---

def test_survival_purpose_zeroes_business_allocation():
    biz = _strong_business()
    biz.capital_need.breakdown = _v([CapitalNeedItem(purpose="bayar gaji",
                                                     amount=200_000_000)])
    res = run_layer0(_healthy_investor(), biz)
    assert res.allocation.business == 0.0
    assert any("SURVIVAL" in r for r in res.rejected_reasons)


def test_claimed_unverified_revenue_defers_business():
    biz = _strong_business()
    biz.traction.monthly_revenue = Tagged(value=[100.0] * 12,
                                          evidence=EvidenceTag.CLAIMED)
    res = run_layer0(_healthy_investor(), biz)
    assert res.allocation.business == 0.0
    assert any("CLAIMED" in r for r in res.rejected_reasons)


# --- STEP 3-5 ---

def test_strong_verified_business_earns_allocation():
    res = run_layer0(_healthy_investor(), _strong_business())
    assert res.status == Layer0Status.ALLOCATED
    assert res.allocation.business > 0
    assert res.allocation.cash >= allocation_config.split.min_cash_floor
    assert abs(res.allocation.cash + res.allocation.stocks
               + res.allocation.business - 1.0) < 1e-6
    assert res.business_score is not None
    assert res.why_not_all_stocks and res.why_not_all_business


def test_partial_completeness_caps_confidence():
    biz = _strong_business()
    # blank out enough fields to land in the PARTIAL band
    biz.identity = type(biz.identity)()
    biz.current_state = type(biz.current_state)()
    biz.team.track_record = Tagged()
    biz.cash.cash_on_hand = Tagged()
    biz.cash.monthly_burn = Tagged()
    res = run_layer0(_healthy_investor(), biz)
    if res.completeness_tier.value == "partial":
        assert res.confidence <= allocation_config.completeness.partial_confidence_cap


# --- normalizer critical rule ---

def test_no_control_no_edge_premiums_collapse_to_one():
    biz = _strong_business()
    biz.control.ownership_pct = _v(0.10)
    biz.control.veto_rights = _v(False)
    inv = _healthy_investor(knows_sector=False)
    _, detail = adjust_business_score(80.0, biz, inv, 200_000_000)
    assert detail.control_premium == 1.0
    assert detail.info_edge_premium == 1.0
    assert not detail.has_control and not detail.has_info_edge


def test_no_edge_business_needs_large_margin_over_stocks():
    cons = ConstraintResult()
    # business barely above stocks → zeroed under no-edge hurdle
    split = compute_split(business_adj=55.0, stock_score=50.0,
                          constraints=cons, business_hard_rejected=False,
                          no_edge=True)
    assert split.business == 0.0
    # business massively above stocks → allowed even with no edge
    split2 = compute_split(business_adj=80.0, stock_score=50.0,
                           constraints=cons, business_hard_rejected=False,
                           no_edge=True)
    assert split2.business > 0


def test_business_ceiling_from_constraints_respected():
    cons = ConstraintResult(max_allocation_business=0.2)
    split = compute_split(business_adj=90.0, stock_score=50.0,
                          constraints=cons, business_hard_rejected=False,
                          no_edge=False)
    assert split.business <= 0.2 + 1e-9


def test_stock_veto_zeroes_stocks():
    cons = ConstraintResult(veto_flags=[VetoFlag(code="X", target="stocks",
                                                 reason="test")])
    split = compute_split(business_adj=None, stock_score=80.0,
                          constraints=cons, business_hard_rejected=True,
                          no_edge=True)
    assert split.stocks == 0.0
    assert split.cash == pytest.approx(1.0)
