"""Layer 0 decision flow (STEP 0-5) as a pure function.

    STEP 0  B0 intake completeness gate  (<0.40 → INSUFFICIENT_DATA + stop)
    STEP 1  L0-2 personal hard vetoes
    STEP 2  business hard vetoes (unit economics, Q5, exit, verification, skin)
    STEP 3  independent scores: business / stocks / baseline (always shown)
    STEP 4  risk & time adjustment (normalizer)
    STEP 5  emit an ALLOCATION, never a binary verdict

The graph node and the API endpoint both call this; DB access stays outside.
INSUFFICIENT_DATA is a *valid terminal output* — "I cannot decide yet, here
is what I need" is success, not an exception.

When no business is in play (pure stock allocation request), STEP 0/2/3's
business legs are skipped and the split runs over stocks vs cash only — the
personal vetoes (STEP 1) still apply.
"""
from __future__ import annotations

from app.agents.allocation.constraints import evaluate_constraints
from app.agents.allocation.devils_advocate import run_devils_advocate
from app.agents.allocation.intake import (
    completeness_tier,
    compute_completeness,
    missing_questions,
)
from app.agents.allocation.normalizer import adjust_business_score, compute_split
from app.agents.allocation.quality import evaluate_quality
from app.agents.allocation.schemas import (
    BusinessProfile,
    CompletenessTier,
    EvidenceTag,
    InvestorProfile,
    Layer0Result,
    Layer0Status,
)
from app.core.allocation_config import allocation_config


def _confidence(completeness: float, tier: CompletenessTier) -> tuple[int, str]:
    cfg = allocation_config.completeness
    conf = round(completeness * 100)
    if tier == CompletenessTier.PARTIAL:
        conf = min(conf, cfg.partial_confidence_cap)
    label = "LOW" if conf < 40 else ("MEDIUM" if conf < 70 else "HIGH")
    return conf, label


def run_layer0(
    investor: InvestorProfile,
    business: BusinessProfile | None = None,
    stock_score: float | None = None,
) -> Layer0Result:
    baseline = allocation_config.baseline.baseline_score

    # ---------- STEP 0: intake completeness gate ----------
    if business is not None:
        completeness = compute_completeness(business)
        tier = completeness_tier(completeness)
        if tier == CompletenessTier.INSUFFICIENT:
            return Layer0Result(
                status=Layer0Status.INSUFFICIENT_DATA,
                completeness=completeness,
                completeness_tier=tier,
                questions=missing_questions(business),
                baseline_score=baseline,
                narration=(
                    f"Data bisnis baru {completeness:.0%} lengkap (< 40%). "
                    "Belum ada alokasi yang bisa dibuat secara jujur — jawab "
                    "pertanyaan berikut lebih dulu. Ini keluaran yang valid, "
                    "bukan kegagalan."),
            )
    else:
        completeness, tier = 1.0, CompletenessTier.OK  # no business leg

    # ---------- STEP 1: personal hard vetoes ----------
    constraints = evaluate_constraints(investor, business)

    # ---------- STEP 2 + 3 (business leg) ----------
    rejected_reasons: list[str] = []
    quality_dump = None
    da_findings: list[dict] = []
    business_score = None
    business_adj = None
    adj_detail = None
    no_edge = True

    if business is not None:
        quality = evaluate_quality(business)
        quality_dump = quality.model_dump()
        rejected_reasons.extend(quality.hard_rejects)

        if not business.exit.mechanism.known:
            rejected_reasons.append("Tidak ada mekanisme exit — modal harus "
                                    "dianggap terkunci permanen.")
        rev = business.traction.monthly_revenue
        if rev.known and rev.evidence == EvidenceTag.CLAIMED:
            rejected_reasons.append(
                "Omzet hanya CLAIMED tanpa verifikasi dokumen — ditangguhkan "
                "sampai ada bukti (mutasi rekening / laporan keuangan).")

        da = run_devils_advocate(business, investor)
        da_findings = [f.model_dump() for f in da.findings]

        if quality.aggregate is not None:
            business_score = quality.aggregate * (1 - da.db_penalty) * completeness
            amount = business.capital_need.amount.value \
                if business.capital_need.amount.known else None
            business_adj, adj_detail = adjust_business_score(
                business_score, business, investor, amount)
            no_edge = not adj_detail.has_control and not adj_detail.has_info_edge

    business_hard_rejected = bool(rejected_reasons)

    # ---------- STEP 3 (stocks leg) ----------
    # Until Layer 1 has run, the boring index baseline stands in as the
    # stock proxy — Layer 1 refines it afterwards, never the reverse.
    effective_stock_score = stock_score if stock_score is not None else baseline

    # ---------- STEP 5: allocation ----------
    split = compute_split(
        business_adj=business_adj,
        stock_score=effective_stock_score,
        constraints=constraints,
        business_hard_rejected=business_hard_rejected,
        no_edge=no_edge,
    )

    conf, label = _confidence(completeness, tier)

    # Symmetric reasoning panels — neither side is the default.
    why_not_stocks = []
    if constraints.force_cash:
        why_not_stocks.append("Dana darurat belum aman — semua opsi berisiko "
                              "diblokir.")
    why_not_stocks.append(
        f"Saham bukan 100%: baseline bebas risiko "
        f"{allocation_config.baseline.risk_free_annual_return:.1%} selalu "
        "tersedia, dan kas menjaga opsi tetap terbuka.")
    if business_adj is not None and not business_hard_rejected:
        why_not_stocks.append(
            f"Bisnis punya skor tersesuaikan {business_adj:.0f}/100 yang "
            "layak porsi.")

    why_not_business = []
    if business is None:
        why_not_business.append("Tidak ada bisnis yang dievaluasi dalam "
                                "permintaan ini.")
    else:
        if business_hard_rejected:
            why_not_business.extend(rejected_reasons)
        if tier == CompletenessTier.PARTIAL:
            why_not_business.append(
                f"Kelengkapan data {completeness:.0%} → keyakinan dibatasi "
                f"{allocation_config.completeness.partial_confidence_cap}/100. "
                "Data yang rapi bukan kualitas aset — tapi data yang bolong "
                "tidak bisa diberi bobot penuh.")
        for f in constraints.veto_flags:
            if f.target in ("business", "both"):
                why_not_business.append(f.reason)
        if not why_not_business:
            # symmetric panel must never be empty — even a strong business
            # carries structural costs a listed stock doesn't
            why_not_business.append(
                "Bisnis privat tetap ilikuid dan terkonsentrasi pada satu "
                "aset: diskon ilikuiditas sudah dipotong dari skornya, dan "
                "kas + saham menjaga likuiditas jika tesisnya salah.")

    return Layer0Result(
        status=Layer0Status.ALLOCATED,
        allocation=split,
        confidence=conf,
        confidence_label=label,
        completeness=completeness,
        completeness_tier=tier,
        questions=missing_questions(business, staged=False) if business else [],
        veto_flags=constraints.veto_flags,
        business_score=round(business_adj, 1) if business_adj is not None else None,
        stock_score=round(effective_stock_score, 1),
        baseline_score=baseline,
        quality=quality_dump,
        devils_advocate=da_findings,
        why_not_all_stocks=" ".join(why_not_stocks),
        why_not_all_business=" ".join(why_not_business),
        rejected_reasons=rejected_reasons,
        narration="",
    )
