"""B0 — Business Intake (interrogative, never assumes).

Converts a stored intake profile into a completeness verdict + a staged,
prioritized question list. This module NEVER fills gaps with assumptions:
an UNKNOWN field stays UNKNOWN and simply generates a question.

Interrogation is staged — the three highest-signal questions come first
(priority 1), not a 40-question dump:
  1. Does the business currently have revenue?
  2. What is the money for, specifically — and what happens without it?
  3. What does the user receive in return?
"""
from __future__ import annotations

from app.agents.allocation.schemas import (
    BusinessProfile,
    CompletenessTier,
    IntakeQuestion,
)
from app.core.allocation_config import allocation_config

# Every field that counts toward the completeness denominator.
# (All leaf fields of BusinessProfile are required for a full evaluation.)
REQUIRED_FIELDS: tuple[str, ...] = (
    "identity.sector", "identity.business_model", "identity.b2b_or_b2c",
    "identity.location",
    "current_state.stage", "current_state.age_months", "current_state.headcount",
    "traction.monthly_revenue", "traction.growth_rate", "traction.gross_margin",
    "traction.customer_count", "traction.retention_rate",
    "unit_economics.price", "unit_economics.cogs_per_unit", "unit_economics.cac",
    "unit_economics.ltv", "unit_economics.contribution_margin",
    "unit_economics.payback_months",
    "cash.cash_on_hand", "cash.monthly_burn", "cash.runway_months",
    "cash.is_profitable",
    "capital_need.amount", "capital_need.breakdown",
    "capital_need.consequence_if_unfunded",
    "deal_structure.instrument", "deal_structure.ownership_pct",
    "user_role.operator_or_passive", "user_role.hours_per_week",
    "control.ownership_pct", "control.veto_rights",
    "control.shareholder_agreement_exists",
    "exit.mechanism", "exit.expected_timeline_months",
    "team.operator_identity", "team.track_record",
    "team.founder_capital_contributed",
)

# Question catalog: dotted field → (priority, Indonesian question).
# Priority 1 = the three highest-signal questions (asked first, alone).
_QUESTIONS: dict[str, tuple[int, str]] = {
    # --- Stage 1: the three highest-signal questions ---
    "current_state.stage": (
        1, "Apakah bisnis ini sudah punya pendapatan saat ini? Di tahap apa "
           "(ide / belum ada omzet / omzet awal / sudah untung / scaling)?"),
    "capital_need.breakdown": (
        1, "Uangnya untuk apa, spesifiknya? Mohon rincian per pos (mis. "
           "marketing Rp X, stok Rp Y) — dan apa yang terjadi jika dana ini "
           "tidak masuk?"),
    "deal_structure.instrument": (
        1, "Apa yang Anda terima sebagai imbalan? Saham (berapa %), pinjaman "
           "(bunga berapa), convertible, atau bagi hasil?"),
    # --- Stage 2: viability ---
    "traction.monthly_revenue": (
        2, "Berapa omzet bulanan 12 bulan terakhir? Idealnya didukung mutasi "
           "rekening/bank statement."),
    "cash.monthly_burn": (
        2, "Berapa pengeluaran (burn) bulanan bisnis saat ini?"),
    "cash.runway_months": (
        2, "Dengan kas yang ada sekarang, bisnis bertahan berapa bulan tanpa "
           "suntikan dana (runway)?"),
    "cash.is_profitable": (
        2, "Apakah bisnis sudah profit — setelah menghitung gaji pemilik, "
           "sewa, dan pajak?"),
    "capital_need.amount": (
        2, "Berapa total dana yang dibutuhkan?"),
    "capital_need.consequence_if_unfunded": (
        2, "Apa konsekuensinya jika dana ini tidak diberikan?"),
    "unit_economics.contribution_margin": (
        2, "Berapa margin kontribusi per unit (harga jual dikurangi biaya "
           "variabel)?"),
    "exit.mechanism": (
        2, "Bagaimana mekanisme keluar (exit)? Buyback, dividen, jual ke pihak "
           "lain? Apakah tertulis?"),
    "team.founder_capital_contributed": (
        2, "Berapa modal yang sudah disetor pendiri sendiri (skin in the game)?"),
    # --- Stage 3: depth ---
    "identity.sector": (3, "Bergerak di sektor apa bisnis ini?"),
    "identity.business_model": (3, "Bagaimana model bisnisnya menghasilkan uang?"),
    "identity.b2b_or_b2c": (3, "Pelanggannya bisnis (B2B) atau konsumen (B2C)?"),
    "identity.location": (3, "Di mana bisnis ini beroperasi?"),
    "current_state.age_months": (3, "Sudah berapa lama bisnis ini berjalan (bulan)?"),
    "current_state.headcount": (3, "Berapa jumlah karyawan saat ini?"),
    "traction.growth_rate": (3, "Berapa pertumbuhan omzet bulanan rata-rata?"),
    "traction.gross_margin": (3, "Berapa gross margin-nya?"),
    "traction.customer_count": (3, "Berapa jumlah pelanggan aktif?"),
    "traction.retention_rate": (
        3, "Berapa tingkat retensi pelanggan? Omzetnya berulang (recurring) "
           "atau sekali beli?"),
    "unit_economics.price": (3, "Berapa harga jual per unit?"),
    "unit_economics.cogs_per_unit": (3, "Berapa HPP (COGS) per unit?"),
    "unit_economics.cac": (3, "Berapa biaya akuisisi pelanggan (CAC)?"),
    "unit_economics.ltv": (3, "Berapa nilai seumur hidup pelanggan (LTV)?"),
    "unit_economics.payback_months": (
        3, "Berapa bulan waktu balik modal per pelanggan (payback)?"),
    "cash.cash_on_hand": (3, "Berapa kas yang dipegang bisnis saat ini?"),
    "deal_structure.ownership_pct": (
        3, "Jika saham: berapa persen kepemilikan yang Anda dapat?"),
    "user_role.operator_or_passive": (
        3, "Peran Anda: ikut mengoperasikan atau investor pasif?"),
    "user_role.hours_per_week": (
        3, "Berapa jam per minggu yang bisa Anda dedikasikan?"),
    "control.ownership_pct": (3, "Berapa persen kepemilikan Anda setelah masuk?"),
    "control.veto_rights": (3, "Apakah Anda punya hak veto atas keputusan besar?"),
    "control.shareholder_agreement_exists": (
        3, "Apakah ada perjanjian pemegang saham (shareholder agreement) tertulis?"),
    "exit.expected_timeline_months": (
        3, "Berapa lama perkiraan waktu sampai bisa exit (bulan)?"),
    "team.operator_identity": (3, "Siapa yang menjalankan bisnis sehari-hari?"),
    "team.track_record": (
        3, "Apa rekam jejak operator? Pernah menjalankan bisnis serupa?"),
}


def compute_completeness(profile: BusinessProfile) -> float:
    """count(fields not UNKNOWN) / count(required fields)."""
    known = {name for name, tagged in profile.iter_fields() if tagged.known}
    return len(known & set(REQUIRED_FIELDS)) / len(REQUIRED_FIELDS)


def completeness_tier(completeness: float) -> CompletenessTier:
    cfg = allocation_config.completeness
    if completeness < cfg.insufficient_below:
        return CompletenessTier.INSUFFICIENT
    if completeness <= cfg.partial_below:
        return CompletenessTier.PARTIAL
    return CompletenessTier.OK


def missing_questions(profile: BusinessProfile, *, staged: bool = True) -> list[IntakeQuestion]:
    """Prioritized questions for every UNKNOWN required field.

    staged=True (default): if any priority-1 question is open, return ONLY
    the priority-1 batch — the three highest-signal questions come first,
    never a full-form dump."""
    known = {name for name, tagged in profile.iter_fields() if tagged.known}
    open_qs = [
        IntakeQuestion(field=f, question=q, priority=p)
        for f, (p, q) in _QUESTIONS.items()
        if f not in known
    ]
    open_qs.sort(key=lambda q: (q.priority, q.field))
    if staged:
        first_batch = [q for q in open_qs if q.priority == 1]
        if first_batch:
            return first_batch[: allocation_config.completeness.staged_questions_first_batch]
    return open_qs
