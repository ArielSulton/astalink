"""L0-4 — Business Devil's Advocate (DB1-DB7). RETAINED by design.

The stock engine has no adversarial agent (its hard gates live inside A1
and A3); the business side keeps one because business data arrives
self-reported and unaudited — the asymmetry is deliberate.

Each finding carries a severity that maps to a score penalty via config:
    business_score = f(Q1..Q5) × (1 − DB_penalty) × completeness_factor
Reflective findings (DB3/DB7 — bias, conflict of interest) are severity
"info": they are surfaced to the user but never move the score, because
they interrogate the USER, not the business.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.agents.allocation.schemas import BusinessProfile, EvidenceTag, InvestorProfile
from app.core.allocation_config import allocation_config


class Severity(StrEnum):
    INFO = "info"          # reflective — shown, no penalty
    WARNING = "warning"
    CRITICAL = "critical"


class Finding(BaseModel):
    code: str              # DB1..DB7
    title: str
    severity: Severity
    finding: str


class DevilsAdvocateResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    db_penalty: float = 0.0    # 0..penalty_cap


def run_devils_advocate(
    profile: BusinessProfile,
    investor: InvestorProfile | None = None,
) -> DevilsAdvocateResult:
    cfg = allocation_config.devils_advocate
    findings: list[Finding] = []

    # --- DB1: fabricated / soft numbers ---
    rev = profile.traction.monthly_revenue
    if rev.known and rev.evidence == EvidenceTag.CLAIMED:
        findings.append(Finding(
            code="DB1", title="Angka tidak terverifikasi", severity=Severity.WARNING,
            finding="Omzet hanya CLAIMED — belum didukung mutasi rekening/"
                    "laporan keuangan. Semua angka turunannya ikut lemah."))
    growth = profile.traction.growth_rate
    if growth.known and growth.evidence != EvidenceTag.VERIFIED \
            and (growth.value or 0) > cfg.hockey_stick_monthly_growth:
        findings.append(Finding(
            code="DB1", title="Proyeksi hockey-stick", severity=Severity.WARNING,
            finding=f"Pertumbuhan {growth.value:.0%}/bulan yang tidak "
                    "terverifikasi adalah pola proyeksi hockey-stick klasik."))
    is_prof = profile.cash.is_profitable
    if is_prof.known and is_prof.value and is_prof.evidence == EvidenceTag.CLAIMED:
        findings.append(Finding(
            code="DB1", title="Profit yang diklaim", severity=Severity.WARNING,
            finding="\"Sudah profit\" hanya klaim — cek apakah profit itu masih "
                    "ada setelah gaji pemilik, sewa, dan pajak dihitung."))

    # --- DB2: base rate / survivorship ---
    sector = profile.identity.sector
    sector_txt = f" di sektor {sector.value}" if sector.known else ""
    findings.append(Finding(
        code="DB2", title="Base rate bertahan hidup", severity=Severity.INFO,
        finding=f"Secara base rate, hanya sekitar "
                f"{cfg.base_rate_5yr_survival:.0%} bisnis kecil{sector_txt} yang "
                "bertahan 5 tahun di Indonesia. Intuisi Anda hampir pasti lebih "
                "optimis dari angka ini."))

    # --- DB3: conflict of interest (reflective) ---
    findings.append(Finding(
        code="DB3", title="Konflik kepentingan", severity=Severity.INFO,
        finding="Siapa yang membawa deal ini — teman/keluarga? Bisakah Anda "
                "menolak dengan jujur? Apakah Anda didekati karena modal Anda, "
                "atau karena kompetensi Anda?"))

    # --- DB4: illiquidity trap ---
    exit_mech = profile.exit.mechanism
    if not exit_mech.known:
        findings.append(Finding(
            code="DB4", title="Jebakan ilikuiditas", severity=Severity.CRITICAL,
            finding="Tidak ada mekanisme exit tertulis. Modelkan modal ini "
                    "sebagai hilang permanen — jika butuh uangnya dalam 2 "
                    "tahun, tidak ada jalan keluar."))
    elif investor and investor.horizon_months is not None \
            and profile.exit.expected_timeline_months.known \
            and profile.exit.expected_timeline_months.value > investor.horizon_months:
        findings.append(Finding(
            code="DB4", title="Jebakan ilikuiditas", severity=Severity.WARNING,
            finding=f"Perkiraan exit "
                    f"{profile.exit.expected_timeline_months.value} bulan lebih "
                    f"lama dari horizon kebutuhan dana Anda "
                    f"({investor.horizon_months:.0f} bulan)."))

    # --- DB5: dilution & minority protection ---
    own = profile.control.ownership_pct
    sha = profile.control.shareholder_agreement_exists
    minority = own.known and (own.value or 0) < 0.5
    no_sha = not sha.known or not sha.value
    if minority and no_sha:
        findings.append(Finding(
            code="DB5", title="Minoritas tanpa perlindungan", severity=Severity.CRITICAL,
            finding="Posisi minoritas tanpa shareholder agreement yang kuat. "
                    "Perlindungan pemegang saham minoritas di PT tertutup "
                    "Indonesia lemah dalam praktik — dalam sengketa, anggap "
                    "ekuitas minoritas nyaris tak bernilai. Ronde berikutnya "
                    "juga bisa mendilusi Anda tanpa bisa dicegah."))
    elif minority:
        findings.append(Finding(
            code="DB5", title="Risiko dilusi", severity=Severity.WARNING,
            finding="Posisi minoritas: pastikan shareholder agreement mengatur "
                    "anti-dilusi, tag-along, dan akses informasi."))

    # --- DB6: honest opportunity cost ---
    base = allocation_config.baseline
    findings.append(Finding(
        code="DB6", title="Opportunity cost yang jujur", severity=Severity.INFO,
        finding=f"Alternatif paling membosankan selalu tersedia: obligasi "
                f"pemerintah ~{base.risk_free_annual_return:.1%} bebas risiko "
                f"atau indeks IHSG ~{base.index_fund_annual_return:.1%}. Jika "
                "bisnis ini tidak jelas-jelas mengalahkannya setelah risiko "
                "dan waktu Anda dihitung, jawabannya bukan salah satu — "
                "melainkan bukan keduanya."))

    # --- DB7: user's own bias (reflective) ---
    findings.append(Finding(
        code="DB7", title="Bias Anda sendiri", severity=Severity.INFO,
        finding="Apakah ketertarikan ini hasil analisis — atau karena bosan "
                "dengan saham, ingin merasa jadi entrepreneur, atau FOMO dari "
                "cerita teman?"))

    penalty_map = {Severity.CRITICAL: cfg.penalty_critical,
                   Severity.WARNING: cfg.penalty_warning,
                   Severity.INFO: cfg.penalty_info}
    penalty = min(cfg.penalty_cap,
                  sum(penalty_map[f.severity] for f in findings))
    return DevilsAdvocateResult(findings=findings, db_penalty=penalty)
