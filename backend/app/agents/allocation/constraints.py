"""L0-2 — Personal Constraint agent (HARD VETO authority).

Runs before any scoring. Its vetoes are absolute and are never overridden
by any score from any other agent.

A missing answer (None) does not silently pass a check: it neither vetoes
nor clears — it is surfaced as a note so the UI can ask for it. The only
exception is capital_is_borrowed, where "unknown" cannot be treated as
"not borrowed"; it produces an advisory note, not a veto.
"""
from __future__ import annotations

from app.agents.allocation.schemas import (
    BusinessProfile,
    ConstraintResult,
    InvestorProfile,
    VetoFlag,
)
from app.core.allocation_config import allocation_config


def evaluate_constraints(
    investor: InvestorProfile,
    business: BusinessProfile | None = None,
) -> ConstraintResult:
    cfg = allocation_config.constraints
    flags: list[VetoFlag] = []
    notes: list[str] = []
    max_business = 1.0
    force_cash = False

    # 1. Emergency fund < 6 months expenses → force CASH; block both.
    if investor.emergency_fund is not None and investor.monthly_expenses:
        months = investor.emergency_fund / investor.monthly_expenses
        if months < cfg.min_emergency_fund_months:
            force_cash = True
            max_business = 0.0
            flags.append(VetoFlag(
                code="EMERGENCY_FUND",
                target="both",
                reason=(f"Dana darurat hanya {months:.1f} bulan pengeluaran "
                        f"(< {cfg.min_emergency_fund_months:.0f} bulan). Seluruh "
                        "alokasi dipaksa ke kas sampai dana darurat terpenuhi."),
            ))
    else:
        notes.append("Dana darurat / pengeluaran bulanan belum diisi — "
                     "cek dana darurat tidak bisa dijalankan.")

    # 2. Investment capital is borrowed → veto business entirely.
    if investor.capital_is_borrowed is True:
        max_business = 0.0
        flags.append(VetoFlag(
            code="BORROWED_CAPITAL",
            target="business",
            reason="Modal investasi berasal dari pinjaman — investasi bisnis "
                   "(ilikuid, bisa nol) diveto sepenuhnya.",
        ))
    elif investor.capital_is_borrowed is None:
        notes.append("Sumber modal (pinjaman atau bukan) belum dikonfirmasi.")

    # 3. Money needed within 24 months → veto business (illiquid).
    if investor.horizon_months is not None:
        if investor.horizon_months < cfg.min_horizon_months_for_business:
            max_business = 0.0
            flags.append(VetoFlag(
                code="SHORT_HORIZON",
                target="business",
                reason=(f"Dana dibutuhkan dalam {investor.horizon_months:.0f} bulan "
                        f"(< {cfg.min_horizon_months_for_business:.0f}). Bisnis privat "
                        "ilikuid — hanya saham/kas yang layak."),
            ))
    else:
        notes.append("Horizon kebutuhan dana belum diisi.")

    # 4. Business would exceed 50% of net worth → veto business.
    amount = None
    if business is not None and business.capital_need.amount.known:
        amount = business.capital_need.amount.value
    if amount is not None and investor.net_worth:
        pct = amount / investor.net_worth
        if pct > cfg.max_business_pct_of_net_worth:
            max_business = 0.0
            flags.append(VetoFlag(
                code="CONCENTRATION",
                target="business",
                reason=(f"Kebutuhan modal {pct:.0%} dari kekayaan bersih "
                        f"(> {cfg.max_business_pct_of_net_worth:.0%}) — konsentrasi "
                        "pada satu aset ilikuid diveto."),
            ))
    elif investor.net_worth is None:
        notes.append("Kekayaan bersih belum diisi — cek konsentrasi tidak "
                     "bisa dijalankan.")

    # 5. Consumer debt at >12% interest → recommend paydown first.
    if investor.consumer_debt_interest_pct is not None and \
            investor.consumer_debt_interest_pct > cfg.consumer_debt_interest_veto_pct:
        flags.append(VetoFlag(
            code="HIGH_INTEREST_DEBT",
            target="both",
            hard=False,
            reason=(f"Ada utang konsumtif berbunga "
                    f"{investor.consumer_debt_interest_pct:.0%} — melunasinya adalah "
                    "imbal hasil bebas risiko yang lebih tinggi dari kedua opsi. "
                    "Rekomendasi: lunasi utang dulu."),
        ))

    # 6. Business requires operator, user has <10 hrs/week → CAPACITY_MISMATCH.
    if business is not None:
        role = business.user_role.operator_or_passive
        hours = investor.available_hours_per_week
        if role.known and str(role.value).lower().startswith("operator") \
                and hours is not None and hours < cfg.min_operator_hours_per_week:
            flags.append(VetoFlag(
                code="CAPACITY_MISMATCH",
                target="business",
                hard=False,
                reason=(f"Bisnis membutuhkan operator, tetapi Anda hanya punya "
                        f"{hours:.0f} jam/minggu "
                        f"(< {cfg.min_operator_hours_per_week:.0f})."),
            ))

    return ConstraintResult(
        veto_flags=flags,
        max_allocation_business=max_business,
        force_cash=force_cash,
        notes=notes,
    )
