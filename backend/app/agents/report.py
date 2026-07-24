"""Markdown allocation report for the chat surface.

`/chat` used to answer a successful allocation run with a single "lolos
validasi legal, setujui di Approvals" sentence even though the final
AgentState already carries everything the user asked the AI to do:
the Layer 0 split + vetoes + scores, the per-ticker Layer 1 verdicts,
the optimizer weights + narration, and the legal outcome. This module
formats that state into one GFM-markdown report — deterministically, with
no extra LLM call (it only reuses narrations already produced upstream).

Every section is read via .get() and silently skipped when its data is
absent, so partial runs (0%-stocks terminal, stock-engine failure, no
citations) still produce a coherent report. INSUFFICIENT_DATA returns
None: the staged intake questions appended by allocation/node.py are the
better reply there. WhatsApp keeps the plain style — this report is only
requested by the web chat endpoint (build_chat_reply(style="report"))."""
from __future__ import annotations

from typing import Any

from app.agents.state import AgentState, LegalStatus, UserApproval

_BAND_LABELS = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "watchlist": "Watchlist",
    "avoid": "Hindari",
    "reject": "Tolak",
    "no_verdict": "Data Kurang",
}

_LEGAL_LABELS = {
    LegalStatus.APPROVED.value: "Lolos",
    LegalStatus.PARTIAL.value: "Lolos sebagian",
    LegalStatus.REJECTED.value: "Ditolak",
    LegalStatus.REJECTED_AFTER_MAX_REVISIONS.value: "Ditolak (setelah 3 revisi)",
}

_MAX_DEVILS_ADVOCATE = 3
_MAX_DETAIL_LINES = 3


def _fmt_rp(value: float) -> str:
    return f"Rp {value:,.0f}".replace(",", ".")


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "-"


def _fmt_score(value: Any) -> str:
    try:
        return f"{float(value):.0f}"
    except (TypeError, ValueError):
        return "-"


def _status_line(state: AgentState, layer0: dict[str, Any]) -> str:
    legal_status = state.get("legal_status")
    if state.get("user_approval") == UserApproval.APPROVED and state.get("transactions"):
        return "**Status:** transaksi sudah dieksekusi."
    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        return "**Status:** rencana ditolak pada validasi legal."
    if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return "**Status:** menunggu persetujuan Anda di halaman Approvals."
    allocation = layer0.get("allocation") or {}
    if allocation.get("stocks") == 0:
        return "**Status:** analisis selesai — tanpa alokasi saham, tidak ada yang perlu disetujui."
    return "**Status:** analisis selesai."


def _layer0_section(layer0: dict[str, Any]) -> str:
    lines = ["### Layer 0 — Alokasi Modal", ""]

    allocation = layer0.get("allocation") or {}
    if allocation:
        lines += [
            "| Kas | Saham | Bisnis |",
            "| --- | --- | --- |",
            f"| {_fmt_pct(allocation.get('cash'))} "
            f"| {_fmt_pct(allocation.get('stocks'))} "
            f"| {_fmt_pct(allocation.get('business'))} |",
            "",
        ]

    confidence = layer0.get("confidence")
    if confidence is not None:
        lines.append(
            f"Keyakinan: **{layer0.get('confidence_label', '-')}** ({confidence}/100)")

    scores = [
        (label, layer0.get(key))
        for label, key in (("bisnis", "business_score"),
                           ("saham", "stock_score"),
                           ("baseline", "baseline_score"))
        if layer0.get(key) is not None
    ]
    if scores:
        lines.append(
            "Skor: " + " · ".join(f"{label} {_fmt_score(v)}" for label, v in scores))

    veto_flags = layer0.get("veto_flags") or []
    if veto_flags:
        lines += ["", "**Catatan veto:**"]
        for flag in veto_flags:
            marker = "⛔" if flag.get("hard", True) else "⚠"
            lines.append(f"- {marker} `{flag.get('code', '?')}` — {flag.get('reason', '')}")

    rejected = layer0.get("rejected_reasons") or []
    if rejected:
        lines += ["", "**Leg bisnis ditolak karena:**"]
        lines += [f"- {reason}" for reason in rejected]

    for heading, key in (("Kenapa tidak 100% saham", "why_not_all_stocks"),
                         ("Kenapa tidak 100% bisnis", "why_not_all_business")):
        text = (layer0.get(key) or "").strip()
        if text:
            lines += ["", f"**{heading}:** {text}"]

    devils = layer0.get("devils_advocate") or []
    if devils:
        lines += ["", "**Devil's advocate:**"]
        for item in devils[:_MAX_DEVILS_ADVOCATE]:
            finding = item.get("finding") or item.get("title") or ""
            lines.append(f"- `{item.get('code', '?')}` {finding}")

    narration = (layer0.get("narration") or "").strip()
    if narration:
        lines += ["", narration]

    return "\n".join(lines)


def _layer1_section(state: AgentState) -> str | None:
    engine = (state.get("entities") or {}).get("stock_engine") or {}
    verdicts: dict[str, dict[str, Any]] = engine.get("verdicts") or {}
    if not verdicts:
        return None

    lines = [
        "### Layer 1 — Verdik per Saham",
        "",
        "| Ticker | Band | Skor | Gate |",
        "| --- | --- | --- | --- |",
    ]
    for ticker, v in verdicts.items():
        band = _BAND_LABELS.get(str(v.get("band", "")), str(v.get("band", "-")))
        lines.append(
            f"| {ticker} | {band} | {_fmt_score(v.get('score'))} "
            f"| {str(v.get('gate_status', '-')).upper()} |")

    for ticker, v in verdicts.items():
        bullet_lines = []
        for detail in (v.get("detail") or [])[:_MAX_DETAIL_LINES]:
            bullet_lines.append(f"- {detail}")
        invalidation = (v.get("invalidation_condition") or "").strip()
        if invalidation:
            bullet_lines.append(f"- Batalkan tesis jika: {invalidation}")
        risk = str(v.get("manipulation_risk") or "").lower()
        if risk and risk != "low":
            bullet_lines.append(f"- ⚠ Risiko manipulasi: {risk.upper()}")
        gaps = v.get("evidence_gaps") or []
        if gaps:
            bullet_lines.append(f"- Data tidak tersedia: {'; '.join(gaps)}")
        if bullet_lines:
            lines += ["", f"**{ticker}**"] + bullet_lines

    return "\n".join(lines)


def _plan_section(state: AgentState) -> str | None:
    plan = state.get("allocation_plan") or {}
    weights = plan.get("weights") or []
    if not weights:
        return None

    lines = [
        "### Rencana Alokasi (Optimizer)",
        "",
        "| Ticker | Bobot |",
        "| --- | --- |",
    ]
    lines += [
        f"| {w.get('ticker', '?')} | {_fmt_pct(w.get('weight'))} |" for w in weights
    ]

    extras = []
    if plan.get("cash") is not None:
        extras.append(f"- Dana slice saham: {_fmt_rp(float(plan['cash']))}")
    if plan.get("cash_buffer") is not None:
        extras.append(f"- Buffer kas minimum: {_fmt_pct(plan['cash_buffer'])}")
    for relaxation in plan.get("relaxations_applied") or []:
        extras.append(f"- Relaksasi constraint: {relaxation}")
    if extras:
        lines += [""] + extras

    narration = (plan.get("narration") or "").strip()
    if narration:
        lines += ["", narration]

    return "\n".join(lines)


def _legal_section(state: AgentState) -> str | None:
    legal_status = state.get("legal_status")
    if legal_status is None:
        return None

    status_value = getattr(legal_status, "value", str(legal_status))
    label = _LEGAL_LABELS.get(status_value, status_value)
    lines = ["### Validasi Legal", "", f"Status: **{label}**"]

    citations = state.get("legal_citations") or []
    if citations:
        lines.append("")
        for c in citations:
            ref = str(c.get("source", "?"))
            if c.get("pasal"):
                ref += f" Pasal {c['pasal']}"
            if c.get("ayat"):
                ref += f" ayat ({c['ayat']})"
            span = (c.get("span") or "").strip()
            lines.append(f"- {ref}" + (f" — {span}" if span else ""))

    return "\n".join(lines)


def _next_steps_section(state: AgentState, layer0: dict[str, Any]) -> str:
    audit_id = state.get("audit_id")
    legal_status = state.get("legal_status")
    lines = ["### Langkah Berikutnya", ""]

    transactions = state.get("transactions") or []
    if state.get("user_approval") == UserApproval.APPROVED and transactions:
        lines += ["| Ticker | Status |", "| --- | --- |"]
        for t in transactions:
            status = ("Berhasil dieksekusi" if t.get("status") == "filled"
                      else "Ditolak — saldo tidak mencukupi"
                      if t.get("status") == "rejected_insufficient_balance"
                      else str(t.get("status", "-")))
            lines.append(f"| {t.get('ticker', '?')} | {status} |")
        lines += ["", f"Detail lengkap ada di halaman Audit (Audit ID: {audit_id})."]
        return "\n".join(lines)

    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        lines.append(
            "Rencana ini ditolak validasi legal dan tidak dapat dilanjutkan. "
            "Coba revisi permintaannya — misalnya ganti saham atau turunkan "
            f"nominalnya. Audit ID: {audit_id}.")
        return "\n".join(lines)

    if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL) \
            and state.get("user_approval") is None:
        lines.append(
            "Rencana lolos validasi legal. Tinjau dan setujui dengan PIN di "
            f"halaman Approvals (Audit ID: {audit_id}).")
        return "\n".join(lines)

    allocation = layer0.get("allocation") or {}
    if allocation.get("stocks") == 0:
        lines.append(
            "Mesin analisis saham tidak dijalankan karena alokasi saham 0%. "
            "Perbarui profil investor Anda bila kondisinya sudah berubah, lalu "
            "minta analisis ulang.")
        return "\n".join(lines)

    lines.append(f"Analisis selesai. Audit ID: {audit_id}.")
    return "\n".join(lines)


def build_allocation_report(state: AgentState) -> str | None:
    """Format a finished allocation run into one markdown report.

    Returns None when no allocation run happened (no layer0_result) or when
    Layer 0 stopped at INSUFFICIENT_DATA — in both cases the message already
    sitting in state is the right reply."""
    layer0 = state.get("layer0_result")
    if not layer0 or layer0.get("status") == "insufficient_data":
        return None

    header = "\n".join([
        "## Laporan Analisis Alokasi",
        "",
        f"Audit ID: `{state.get('audit_id')}`",
        _status_line(state, layer0),
    ])

    sections = [
        header,
        _layer0_section(layer0),
        _layer1_section(state),
        _plan_section(state),
        _legal_section(state),
        _next_steps_section(state, layer0),
    ]
    return "\n\n".join(s for s in sections if s)
