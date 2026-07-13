"""L0-3 quality Q1-Q5 + Q5 hard classification rules."""
from __future__ import annotations

from app.agents.allocation.quality import classify_purpose, evaluate_quality
from app.agents.allocation.schemas import (
    BusinessProfile,
    CapitalNeedItem,
    CapitalPurpose,
    EvidenceTag,
    Tagged,
)


def _tag(value, evidence=EvidenceTag.CLAIMED):
    return Tagged(value=value, evidence=evidence)


def _breakdown(*purposes: str) -> Tagged:
    return _tag([CapitalNeedItem(purpose=p, amount=1_000_000) for p in purposes])


# --- Q5 classification: hard rules ---

def test_no_breakdown_is_unclear():
    assert classify_purpose(Tagged()) == CapitalPurpose.UNCLEAR


def test_growth_keywords():
    assert classify_purpose(_breakdown("iklan digital", "tambah stok")) \
        == CapitalPurpose.GROWTH


def test_survival_keywords_reject():
    assert classify_purpose(_breakdown("bayar gaji karyawan")) \
        == CapitalPurpose.SURVIVAL


def test_debt_dominates_everything():
    assert classify_purpose(_breakdown("marketing", "bayar hutang bank")) \
        == CapitalPurpose.DEBT


def test_unrecognized_purposes_are_unclear():
    assert classify_purpose(_breakdown("lain-lain", "misc")) \
        == CapitalPurpose.UNCLEAR


# --- evaluate_quality ---

def test_survival_purpose_is_hard_reject():
    p = BusinessProfile()
    p.capital_need.breakdown = _breakdown("gaji karyawan")
    res = evaluate_quality(p)
    assert res.q5_purpose == CapitalPurpose.SURVIVAL
    assert any("SURVIVAL" in r for r in res.hard_rejects)


def test_negative_contribution_margin_is_hard_reject():
    p = BusinessProfile()
    p.unit_economics.contribution_margin = _tag(-5.0, EvidenceTag.VERIFIED)
    res = evaluate_quality(p)
    assert any("margin kontribusi" in r.lower() for r in res.hard_rejects)


def test_no_skin_in_game_is_hard_reject():
    p = BusinessProfile()
    p.team.founder_capital_contributed = _tag(0.0, EvidenceTag.VERIFIED)
    res = evaluate_quality(p)
    assert any("skin in the game" in r for r in res.hard_rejects)


def test_unknown_fields_never_scored_and_reported():
    res = evaluate_quality(BusinessProfile())
    q1 = next(s for s in res.subscores if s.code == "Q1")
    assert q1.score is None                      # nothing evaluable
    assert len(q1.unknown_fields) == 3           # all surfaced


def test_claimed_weighs_less_than_verified():
    def profile_with(evidence):
        p = BusinessProfile()
        p.unit_economics.contribution_margin = _tag(10.0, evidence)
        p.unit_economics.cac = _tag(100.0, evidence)
        p.unit_economics.ltv = _tag(150.0, evidence)  # CAC > LTV/3 → fail
        p.unit_economics.payback_months = _tag(6.0, EvidenceTag.VERIFIED)
        return p

    # the failing check (cac_vs_ltv) is CLAIMED in one case, VERIFIED in the
    # other — a verified failure must drag the score down harder
    claimed = evaluate_quality(profile_with(EvidenceTag.CLAIMED))
    verified = evaluate_quality(profile_with(EvidenceTag.VERIFIED))
    q1_claimed = next(s for s in claimed.subscores if s.code == "Q1").score
    q1_verified = next(s for s in verified.subscores if s.code == "Q1").score
    assert q1_claimed > q1_verified


def test_healthy_growth_profile_scores_well_no_rejects():
    p = BusinessProfile()
    v = EvidenceTag.VERIFIED
    p.unit_economics.contribution_margin = _tag(30.0, v)
    p.unit_economics.cac = _tag(50.0, v)
    p.unit_economics.ltv = _tag(600.0, v)
    p.unit_economics.payback_months = _tag(4.0, v)
    p.traction.retention_rate = _tag(0.8, v)
    p.traction.monthly_revenue = _tag([10.0] * 12, v)
    p.traction.growth_rate = _tag(0.05, v)
    p.team.track_record = _tag("10 th di F&B", v)
    p.team.founder_capital_contributed = _tag(200_000_000.0, v)
    p.identity.business_model = _tag("langganan katering B2B", v)
    p.capital_need.breakdown = _breakdown("tambah kapasitas dapur", "marketing")
    res = evaluate_quality(p)
    assert res.hard_rejects == []
    assert res.q5_purpose == CapitalPurpose.GROWTH
    assert res.aggregate is not None and res.aggregate > 80
