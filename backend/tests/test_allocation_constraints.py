"""L0-2 personal-constraint hard vetoes."""
from __future__ import annotations

from app.agents.allocation.constraints import evaluate_constraints
from app.agents.allocation.schemas import (
    BusinessProfile,
    EvidenceTag,
    InvestorProfile,
    Tagged,
)


def _healthy_investor() -> InvestorProfile:
    return InvestorProfile(
        monthly_expenses=10_000_000,
        emergency_fund=100_000_000,      # 10 months
        capital_is_borrowed=False,
        horizon_months=60,
        net_worth=1_000_000_000,
        consumer_debt_interest_pct=0.0,
        available_hours_per_week=40,
    )


def test_healthy_profile_no_vetoes():
    res = evaluate_constraints(_healthy_investor())
    assert res.veto_flags == []
    assert res.max_allocation_business == 1.0
    assert not res.force_cash


def test_emergency_fund_forces_cash_and_blocks_both():
    inv = _healthy_investor()
    inv.emergency_fund = 30_000_000  # 3 months < 6
    res = evaluate_constraints(inv)
    assert res.force_cash
    assert res.max_allocation_business == 0.0
    assert any(f.code == "EMERGENCY_FUND" and f.target == "both"
               for f in res.veto_flags)


def test_borrowed_capital_vetoes_business():
    inv = _healthy_investor()
    inv.capital_is_borrowed = True
    res = evaluate_constraints(inv)
    assert res.max_allocation_business == 0.0
    assert any(f.code == "BORROWED_CAPITAL" for f in res.veto_flags)
    assert not res.force_cash  # stocks still allowed


def test_short_horizon_vetoes_business():
    inv = _healthy_investor()
    inv.horizon_months = 12
    res = evaluate_constraints(inv)
    assert res.max_allocation_business == 0.0
    assert any(f.code == "SHORT_HORIZON" for f in res.veto_flags)


def test_concentration_veto_uses_business_capital_need():
    inv = _healthy_investor()
    biz = BusinessProfile()
    biz.capital_need.amount = Tagged(value=600_000_000,
                                     evidence=EvidenceTag.CLAIMED)
    res = evaluate_constraints(inv, biz)  # 60% of 1B net worth
    assert res.max_allocation_business == 0.0
    assert any(f.code == "CONCENTRATION" for f in res.veto_flags)


def test_high_interest_debt_is_advisory_not_hard():
    inv = _healthy_investor()
    inv.consumer_debt_interest_pct = 0.20
    res = evaluate_constraints(inv)
    flag = next(f for f in res.veto_flags if f.code == "HIGH_INTEREST_DEBT")
    assert flag.hard is False
    assert res.max_allocation_business == 1.0  # advisory, not a ceiling cut


def test_capacity_mismatch_flagged_when_operator_business_and_no_hours():
    inv = _healthy_investor()
    inv.available_hours_per_week = 5
    biz = BusinessProfile()
    biz.user_role.operator_or_passive = Tagged(value="operator",
                                               evidence=EvidenceTag.CLAIMED)
    res = evaluate_constraints(inv, biz)
    flag = next(f for f in res.veto_flags if f.code == "CAPACITY_MISMATCH")
    assert flag.hard is False


def test_missing_answers_surface_as_notes_not_silent_pass():
    res = evaluate_constraints(InvestorProfile())
    assert res.veto_flags == []          # unknown never auto-vetoes...
    assert len(res.notes) >= 3           # ...but is loudly surfaced
