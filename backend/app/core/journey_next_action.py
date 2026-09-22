from dataclasses import dataclass

from app.models.journey import NextAction


@dataclass(frozen=True)
class JourneySignals:
    pending_transaction_id: str | None = None
    pending_approvals_count: int = 0
    decisive_gaps: tuple[str, ...] = ()
    hard_veto_codes: tuple[str, ...] = ()
    allocation_available: bool = False
    allocation_acknowledged: bool = False
    holdings_count: int = 0


def choose_next_action(signals: JourneySignals) -> NextAction:
    if signals.pending_transaction_id:
        return NextAction(
            kind="resolve_transaction",
            title="Konfirmasi transaksi tertunda",
            rationale="Selesaikan pencatatan agar ringkasan keuangan tetap akurat.",
            href="/chatbot",
            rule_id="pending_transaction",
        )
    if signals.pending_approvals_count:
        return NextAction(
            kind="review_approval",
            title="Tinjau persetujuan yang menunggu",
            rationale="Ada keputusan yang membutuhkan tindakanmu.",
            href="/approvals",
            rule_id="pending_approval",
        )
    if signals.decisive_gaps:
        return NextAction(
            kind="complete_readiness",
            title="Lengkapi kesiapan finansial",
            rationale="Beberapa informasi penting masih menentukan arah dana.",
            href="/allocation/investor",
            rule_id="decisive_gap",
        )
    if signals.hard_veto_codes:
        return NextAction(
            kind="address_readiness",
            title="Amankan kondisi dasar terlebih dahulu",
            rationale="Ada batas kesiapan yang perlu diselesaikan sebelum menambah investasi.",
            href="/allocation",
            rule_id="readiness_blocker",
        )
    if signals.allocation_available and not signals.allocation_acknowledged:
        return NextAction(
            kind="review_allocation",
            title="Tinjau rencana dan pembagian dana",
            rationale="Rencana terbaru sudah tersedia untuk diperiksa.",
            href="/allocation",
            rule_id="unreviewed_allocation",
        )
    if signals.allocation_available and signals.holdings_count == 0:
        return NextAction(
            kind="explore_investments",
            title="Eksplorasi pilihan investasi",
            rationale="Kondisimu sudah cukup untuk mulai membandingkan pilihan.",
            href="/recommendations",
            rule_id="ready_empty_portfolio",
        )
    if signals.holdings_count:
        return NextAction(
            kind="review_portfolio",
            title="Tinjau perkembangan portofolio",
            rationale="Lihat perubahan nilai dan kesesuaian bobot investasimu.",
            href="/portfolio",
            rule_id="existing_holdings",
        )
    return NextAction(
        kind="ask_asta",
        title="Mulai dari kondisi keuanganmu",
        rationale="Asta dapat membantu menentukan langkah yang paling relevan.",
        href="/chatbot",
        rule_id="neutral_fallback",
    )
