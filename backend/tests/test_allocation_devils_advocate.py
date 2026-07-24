"""L0-4 devil's advocate DB1-DB7."""
from __future__ import annotations

from app.agents.allocation.devils_advocate import Severity, run_devils_advocate
from app.agents.allocation.schemas import (
    BusinessProfile,
    EvidenceTag,
    InvestorProfile,
    Tagged,
)
from app.core.allocation_config import allocation_config


def _codes(res):
    return {f.code for f in res.findings}


def test_reflective_findings_always_present_and_penalty_free():
    res = run_devils_advocate(BusinessProfile())
    assert {"DB2", "DB3", "DB6", "DB7"} <= _codes(res)
    for f in res.findings:
        if f.code in ("DB2", "DB3", "DB6", "DB7"):
            assert f.severity == Severity.INFO


def test_claimed_revenue_triggers_db1_warning():
    p = BusinessProfile()
    p.traction.monthly_revenue = Tagged(value=[10.0] * 12,
                                        evidence=EvidenceTag.CLAIMED)
    res = run_devils_advocate(p)
    db1 = [f for f in res.findings if f.code == "DB1"]
    assert db1 and db1[0].severity == Severity.WARNING


def test_verified_revenue_no_db1():
    p = BusinessProfile()
    p.traction.monthly_revenue = Tagged(value=[10.0] * 12,
                                        evidence=EvidenceTag.VERIFIED)
    res = run_devils_advocate(p)
    assert not any(f.code == "DB1" and "Omzet" in f.finding for f in res.findings)


def test_hockey_stick_growth_flagged():
    p = BusinessProfile()
    p.traction.growth_rate = Tagged(value=0.5, evidence=EvidenceTag.CLAIMED)
    res = run_devils_advocate(p)
    assert any("hockey-stick" in f.finding for f in res.findings)


def test_no_exit_mechanism_is_critical_db4():
    res = run_devils_advocate(BusinessProfile())
    db4 = next(f for f in res.findings if f.code == "DB4")
    assert db4.severity == Severity.CRITICAL


def test_exit_longer_than_horizon_warns():
    p = BusinessProfile()
    p.exit.mechanism = Tagged(value="buyback", evidence=EvidenceTag.CLAIMED)
    p.exit.expected_timeline_months = Tagged(value=60,
                                             evidence=EvidenceTag.CLAIMED)
    inv = InvestorProfile(horizon_months=36)
    res = run_devils_advocate(p, inv)
    db4 = next(f for f in res.findings if f.code == "DB4")
    assert db4.severity == Severity.WARNING


def test_minority_without_sha_is_critical_db5():
    p = BusinessProfile()
    p.control.ownership_pct = Tagged(value=0.20, evidence=EvidenceTag.CLAIMED)
    res = run_devils_advocate(p)
    db5 = next(f for f in res.findings if f.code == "DB5")
    assert db5.severity == Severity.CRITICAL
    assert "PT tertutup" in db5.finding


def test_penalty_sums_and_caps():
    cfg = allocation_config.devils_advocate
    p = BusinessProfile()  # no exit (critical) + minority handled below
    p.control.ownership_pct = Tagged(value=0.10, evidence=EvidenceTag.CLAIMED)
    p.traction.monthly_revenue = Tagged(value=[1.0], evidence=EvidenceTag.CLAIMED)
    res = run_devils_advocate(p)
    expected = 2 * cfg.penalty_critical + cfg.penalty_warning
    assert res.db_penalty == min(cfg.penalty_cap, expected)
    assert res.db_penalty <= cfg.penalty_cap
