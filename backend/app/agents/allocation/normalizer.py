"""L0-1 — Comparability Normalizer + STEP 4/5 of the Layer 0 decision flow.

Puts business, stocks, and the boring baseline on the same 0-100 scale,
applies the risk & time adjustments, and converts adjusted scores into an
ALLOCATION (cash/stocks/business) — never a binary verdict.

CRITICAL RULE (STEP 4): if the user has no real control AND no information
edge, both premiums collapse to 1.0 — what remains is illiquid, unmeasured,
and un-exitable, so the business must additionally beat stocks by a large
configured hurdle before receiving any allocation at all.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.allocation.schemas import (
    AllocationSplit,
    BusinessProfile,
    ConstraintResult,
    InvestorProfile,
)
from app.core.allocation_config import allocation_config


class AdjustmentDetail(BaseModel):
    illiquidity_discount: float
    time_cost_factor: float
    control_premium: float
    info_edge_premium: float
    has_control: bool
    has_info_edge: bool
    notes: list[str] = Field(default_factory=list)


def adjust_business_score(
    raw_score: float,
    profile: BusinessProfile,
    investor: InvestorProfile,
    capital_amount: float | None,
) -> tuple[float, AdjustmentDetail]:
    """STEP 4: business_adj = raw × illiquidity × time_cost × control × edge."""
    cfg = allocation_config.adjustment
    notes: list[str] = []

    # Illiquidity: a written exit mechanism earns the lighter discount.
    exit_known = profile.exit.mechanism.known
    illiq = cfg.illiquidity_discount_max if exit_known else cfg.illiquidity_discount_min
    if not exit_known:
        notes.append("Tanpa mekanisme exit tertulis → diskon ilikuiditas terberat")

    # Time cost: deduct the value of the user's hours if they operate.
    time_factor = 1.0
    role = profile.user_role.operator_or_passive
    if role.known and str(role.value).lower().startswith("operator") \
            and investor.available_hours_per_week and capital_amount:
        annual_cost = (investor.available_hours_per_week * 52
                       * cfg.operator_hour_value_idr)
        drag = min(0.3, annual_cost / capital_amount)
        time_factor = 1.0 - drag
        notes.append(f"Biaya waktu operator ≈ Rp {annual_cost:,.0f}/tahun "
                     f"→ faktor {time_factor:.2f}")

    # Control: real control only (majority or explicit veto rights).
    own = profile.control.ownership_pct
    veto = profile.control.veto_rights
    has_control = bool(
        (own.known and (own.value or 0) > 0.5)
        or (veto.known and veto.value))

    # Info edge: the user actually knows this sector.
    has_edge = investor.knows_sector is True

    if not has_control and not has_edge:
        control_p = info_p = 1.0
        notes.append(
            "Tanpa kontrol nyata DAN tanpa keunggulan informasi: kedua premium "
            "= 1.0. Bisnis kehilangan satu-satunya keunggulan strukturalnya — "
            "yang tersisa ilikuid, tak terukur, dan tak bisa di-exit. Ia harus "
            "mengalahkan saham dengan selisih sangat besar untuk dipilih.")
    else:
        mid = lambda lo, hi: (lo + hi) / 2  # noqa: E731
        control_p = mid(cfg.control_premium_min, cfg.control_premium_max) \
            if has_control else cfg.control_premium_min
        info_p = mid(cfg.info_edge_premium_min, cfg.info_edge_premium_max) \
            if has_edge else cfg.info_edge_premium_min

    adjusted = raw_score * illiq * time_factor * control_p * info_p
    return min(100.0, adjusted), AdjustmentDetail(
        illiquidity_discount=illiq, time_cost_factor=time_factor,
        control_premium=control_p, info_edge_premium=info_p,
        has_control=has_control, has_info_edge=has_edge, notes=notes)


def compute_split(
    business_adj: float | None,
    stock_score: float | None,
    constraints: ConstraintResult,
    business_hard_rejected: bool,
    no_edge: bool,
) -> AllocationSplit:
    """STEP 5: adjusted scores → cash/stocks/business split.

    Transparent proportional rule: each eligible option earns allocation for
    its score margin above `score_floor`; the baseline's margin goes to cash,
    and cash keeps a configured floor. Vetoes zero an option outright."""
    cfg = allocation_config.split
    baseline = allocation_config.baseline.baseline_score

    if constraints.force_cash:
        return AllocationSplit(cash=1.0, stocks=0.0, business=0.0)

    stocks_vetoed = any(f.hard and f.target in ("stocks", "both")
                        for f in constraints.veto_flags)
    business_vetoed = (business_hard_rejected
                       or constraints.max_allocation_business <= 0
                       or any(f.hard and f.target in ("business", "both")
                              for f in constraints.veto_flags))

    b = business_adj if (business_adj is not None and not business_vetoed) else None
    s = stock_score if (stock_score is not None and not stocks_vetoed) else None

    # No control + no edge: business must beat stocks by a large margin.
    if b is not None and no_edge:
        hurdle = (s if s is not None else baseline) + cfg.no_edge_business_hurdle
        if b < hurdle:
            b = None

    margins = {
        "stocks": max(0.0, (s - cfg.score_floor)) if s is not None else 0.0,
        "business": max(0.0, (b - cfg.score_floor)) if b is not None else 0.0,
        "cash": max(0.0, baseline - cfg.score_floor),
    }
    total = sum(margins.values())
    if total == 0:
        return AllocationSplit(cash=1.0, stocks=0.0, business=0.0)

    split = {k: v / total for k, v in margins.items()}

    # Business ceiling from L0-2 → excess flows to cash.
    ceiling = constraints.max_allocation_business
    if split["business"] > ceiling:
        split["cash"] += split["business"] - ceiling
        split["business"] = ceiling

    # Cash floor → taken proportionally from the others.
    if split["cash"] < cfg.min_cash_floor:
        deficit = cfg.min_cash_floor - split["cash"]
        others = split["stocks"] + split["business"]
        if others > 0:
            split["stocks"] -= deficit * split["stocks"] / others
            split["business"] -= deficit * split["business"] / others
        split["cash"] = cfg.min_cash_floor

    return AllocationSplit(cash=round(split["cash"], 4),
                           stocks=round(split["stocks"], 4),
                           business=round(split["business"], 4))
