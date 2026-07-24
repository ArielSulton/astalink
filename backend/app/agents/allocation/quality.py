"""L0-3 — Business Quality (Q1-Q5).

All checks are rule-based over the tagged intake profile. Two invariants:
- A field's contribution is weighted by its evidence tag (CLAIMED counts
  substantially less than VERIFIED); UNKNOWN contributes nothing and is
  reported, never defaulted.
- Q5 (purpose of capital) is the single most diagnostic field and is
  classified by hard keyword rules, not heuristics: SURVIVAL, DEBT, and
  UNCLEAR are hard rejects.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.allocation.schemas import (
    BusinessProfile,
    CapitalNeedItem,
    CapitalPurpose,
    EvidenceTag,
    Tagged,
)
from app.core.allocation_config import allocation_config

# Q5 keyword rules (Indonesian + English). Worst category wins:
# DEBT > SURVIVAL > GROWTH.
_DEBT_KEYWORDS = ("utang", "hutang", "pinjaman", "cicilan", "kreditur",
                  "refinanc", "debt", "loan repay", "bayar bank")
_SURVIVAL_KEYWORDS = ("gaji", "payroll", "operasional", "sewa", "listrik",
                      "bertahan", "tutup", "menutupi", "survival",
                      "keep the lights", "rent", "salaries")
_GROWTH_KEYWORDS = ("marketing", "iklan", "promosi", "stok", "inventory",
                    "persediaan", "mesin", "kapasitas", "ekspansi", "cabang",
                    "produksi", "alat", "capacity", "expansion", "hiring sales")


class QualityCheck(BaseModel):
    name: str
    passed: bool | None      # None = cannot evaluate (inputs UNKNOWN)
    weight: float            # evidence weight applied (0 when unknown)
    detail: str


class SubScore(BaseModel):
    code: str                # Q1..Q5
    label: str
    score: float | None      # 0-100; None = wholly unknown
    checks: list[QualityCheck] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)


class QualityResult(BaseModel):
    subscores: list[SubScore]
    q5_purpose: CapitalPurpose
    hard_rejects: list[str] = Field(default_factory=list)   # STEP 2 reasons
    aggregate: float | None = None    # evidence-weighted mean of known subscores


def _evidence_weight(tag: EvidenceTag) -> float:
    ev = allocation_config.evidence
    return {EvidenceTag.VERIFIED: ev.verified,
            EvidenceTag.CLAIMED: ev.claimed,
            EvidenceTag.ESTIMATED: ev.estimated,
            EvidenceTag.UNKNOWN: 0.0}[tag]


def _bool_check(name: str, field: Tagged, cond: bool | None, detail: str) -> QualityCheck:
    if not field.known or cond is None:
        return QualityCheck(name=name, passed=None, weight=0.0,
                            detail=f"{name}: data tidak tersedia")
    return QualityCheck(name=name, passed=cond,
                        weight=_evidence_weight(field.evidence), detail=detail)


def _score(checks: list[QualityCheck]) -> float | None:
    """Evidence-weighted pass ratio × 100. None when nothing is evaluable."""
    total = sum(c.weight for c in checks if c.passed is not None)
    if total == 0:
        return None
    passed = sum(c.weight for c in checks if c.passed)
    return 100.0 * passed / total


def classify_purpose(breakdown: Tagged[list[CapitalNeedItem]]) -> CapitalPurpose:
    """Hard rules. No itemized breakdown → UNCLEAR. Worst category wins."""
    if not breakdown.known or not breakdown.value:
        return CapitalPurpose.UNCLEAR
    worst = CapitalPurpose.GROWTH
    matched_any = False
    for item in breakdown.value:
        text = item.purpose.lower()
        if any(k in text for k in _DEBT_KEYWORDS):
            return CapitalPurpose.DEBT
        if any(k in text for k in _SURVIVAL_KEYWORDS):
            worst = CapitalPurpose.SURVIVAL
            matched_any = True
        elif any(k in text for k in _GROWTH_KEYWORDS):
            matched_any = True
    if not matched_any:
        return CapitalPurpose.UNCLEAR
    return worst


def evaluate_quality(profile: BusinessProfile) -> QualityResult:
    cfg = allocation_config.quality
    ue = profile.unit_economics
    tr = profile.traction
    tm = profile.team
    hard_rejects: list[str] = []

    # --- Q1 unit economics ---
    q1_checks = [
        _bool_check("contribution_margin_positive", ue.contribution_margin,
                    None if not ue.contribution_margin.known
                    else ue.contribution_margin.value > 0,
                    "Margin kontribusi > 0"),
        _bool_check("cac_vs_ltv", ue.cac,
                    None if not (ue.cac.known and ue.ltv.known)
                    else ue.cac.value < ue.ltv.value * cfg.max_cac_to_ltv_ratio,
                    "CAC < LTV/3"),
        _bool_check("payback", ue.payback_months,
                    None if not ue.payback_months.known
                    else ue.payback_months.value < cfg.max_payback_months,
                    f"Payback < {cfg.max_payback_months:.0f} bulan"),
    ]
    if ue.contribution_margin.known and ue.contribution_margin.value <= 0:
        hard_rejects.append(
            "Unit economics negatif: margin kontribusi ≤ 0 — setiap unit "
            "terjual menambah kerugian.")

    # --- Q2 traction ---
    q2_checks = [
        _bool_check("retention", tr.retention_rate,
                    None if not tr.retention_rate.known
                    else tr.retention_rate.value >= 0.5,
                    "Retensi pelanggan ≥ 50% (omzet berulang, bukan sekali beli)"),
        _bool_check("revenue_history", tr.monthly_revenue,
                    None if not tr.monthly_revenue.known
                    else len(tr.monthly_revenue.value or []) >= 6
                    and sum(tr.monthly_revenue.value) > 0,
                    "≥6 bulan riwayat omzet nyata"),
        _bool_check("growth_positive", tr.growth_rate,
                    None if not tr.growth_rate.known
                    else tr.growth_rate.value > 0,
                    "Pertumbuhan omzet positif"),
    ]

    # --- Q3 team ---
    skin = tm.founder_capital_contributed
    q3_checks = [
        _bool_check("track_record", tm.track_record,
                    None if not tm.track_record.known
                    else bool(str(tm.track_record.value).strip()),
                    "Operator punya rekam jejak"),
        _bool_check("skin_in_the_game", skin,
                    None if not skin.known else skin.value > 0,
                    "Pendiri menyetor modal sendiri"),
    ]
    if skin.known and (skin.value or 0) <= 0:
        hard_rejects.append(
            "Pendiri tidak punya skin in the game — tidak menyetor modal "
            "sendiri sama sekali.")

    # --- Q4 moat (proxy only — intake has no direct moat evidence) ---
    q4_checks = [
        _bool_check("switching_cost_proxy", tr.retention_rate,
                    None if not tr.retention_rate.known
                    else tr.retention_rate.value >= 0.7,
                    "Retensi tinggi sebagai proxy switching cost"),
        _bool_check("model_stated", profile.identity.business_model,
                    None if not profile.identity.business_model.known
                    else bool(str(profile.identity.business_model.value).strip()),
                    "Model bisnis dinyatakan (untuk ditantang: kenapa tidak "
                    "bisa ditiru kompetitor bulan depan?)"),
    ]

    # --- Q5 purpose of capital — the single most diagnostic field ---
    purpose = classify_purpose(profile.capital_need.breakdown)
    q5_pass = purpose == CapitalPurpose.GROWTH
    q5_checks = [QualityCheck(
        name="purpose_classification",
        passed=q5_pass,
        weight=_evidence_weight(profile.capital_need.breakdown.evidence)
        if profile.capital_need.breakdown.known else 1.0,
        detail=f"Klasifikasi tujuan dana: {purpose.value.upper()}",
    )]
    if purpose == CapitalPurpose.SURVIVAL:
        hard_rejects.append(
            "Tujuan dana = SURVIVAL (gaji/operasional) — ini bailout, bukan "
            "investasi.")
    elif purpose == CapitalPurpose.DEBT:
        hard_rejects.append(
            "Tujuan dana = DEBT — modal hanya lewat untuk membayar kreditur "
            "lama.")
    elif purpose == CapitalPurpose.UNCLEAR:
        hard_rejects.append(
            "Tujuan dana UNCLEAR — tidak ada rincian penggunaan dana yang "
            "teritemisasi.")

    def _sub(code: str, label: str, checks: list[QualityCheck]) -> SubScore:
        return SubScore(
            code=code, label=label, score=_score(checks), checks=checks,
            unknown_fields=[c.name for c in checks if c.passed is None])

    subs = [
        _sub("Q1", "Unit economics", q1_checks),
        _sub("Q2", "Traction", q2_checks),
        _sub("Q3", "Team", q3_checks),
        _sub("Q4", "Moat", q4_checks),
        _sub("Q5", "Purpose of capital", q5_checks),
    ]
    known = [s.score for s in subs if s.score is not None]
    return QualityResult(
        subscores=subs,
        q5_purpose=purpose,
        hard_rejects=hard_rejects,
        aggregate=sum(known) / len(known) if known else None,
    )
