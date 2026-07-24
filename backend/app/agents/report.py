"""Advisory allocation report for the chat surface.

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

from app.agents.state import AgentState, LegalStatus

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
    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        return "**Status:** rekomendasi tidak lolos validasi legal — lihat catatan di bawah."
    if legal_status in (LegalStatus.APPROVED, LegalStatus.PARTIAL):
        return "**Status:** analisis selesai — rekomendasi lolos validasi legal."
    allocation = layer0.get("allocation") or {}
    if allocation.get("stocks") == 0:
        return "**Status:** analisis selesai — rekomendasi saat ini: 0% saham."
    return "**Status:** analisis selesai."


def _layer0_section(layer0: dict[str, Any]) -> str:
    lines = ["### Layer 0 — Rekomendasi Alokasi Modal", ""]

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
        "### Rekomendasi Bobot Saham (Optimizer)",
        "",
        "| Ticker | Bobot yang Disarankan |",
        "| --- | --- |",
    ]
    lines += [
        f"| {w.get('ticker', '?')} | {_fmt_pct(w.get('weight'))} |" for w in weights
    ]

    extras = []
    if plan.get("cash") is not None:
        extras.append(f"- Dana yang dianalisis: {_fmt_rp(float(plan['cash']))}")
    if plan.get("cash_buffer") is not None:
        extras.append(f"- Buffer kas minimum disarankan: {_fmt_pct(plan['cash_buffer'])}")
    for relaxation in plan.get("relaxations_applied") or []:
        extras.append(f"- Relaksasi constraint: {relaxation}")
    if extras:
        lines += [""] + extras

    narration = (plan.get("narration") or "").strip()
    if narration:
        lines += ["", narration]

    # Impact estimation
    lines += [
        "",
        "### Perkiraan Dampak",
        "",
        "| Skenario | Estimasi |",
        "| --- | --- |",
    ]
    total_cash = float(plan.get('cash') or 0)
    if total_cash > 0:
        for w in weights:
            ticker = w.get('ticker', '?')
            weight = float(w.get('weight', 0))
            allocated = total_cash * weight
            lines.append(f"| {ticker} | {_fmt_rp(allocated)} ({_fmt_pct(weight)} dari dana saham) |")
        buffer = float(plan.get('cash_buffer') or 0)
        if buffer > 0:
            lines.append(f"| Kas (buffer) | {_fmt_rp(total_cash * buffer)} ({_fmt_pct(buffer)}) |")

    lines += [
        "",
        "> ⚠ Angka di atas adalah **perkiraan** berdasarkan data saat ini. "
        "Keputusan alokasi sepenuhnya ada di tangan Anda.",
    ]

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
    lines = ["### Saran Langkah Berikutnya", ""]

    if legal_status in (LegalStatus.REJECTED, LegalStatus.REJECTED_AFTER_MAX_REVISIONS):
        lines.append(
            "Rekomendasi ini tidak lolos validasi legal. Anda bisa: \n"
            "- Meminta analisis ulang dengan saham atau nominal berbeda\n"
            "- Mengecek regulasi terkait di halaman Legal Docs\n"
            f"- Melihat detail di halaman Audit (Audit ID: {audit_id})")
        return "\n".join(lines)

    allocation = layer0.get("allocation") or {}
    lines.append(
        "Berdasarkan analisis di atas, berikut beberapa opsi yang bisa Anda pertimbangkan:\n")

    if allocation.get("stocks", 0) > 0:
        lines.append(
            f"- **Saham ({_fmt_pct(allocation.get('stocks'))}):** "
            "Tinjau rekomendasi bobot per saham dan sesuaikan dengan preferensi Anda")
    if allocation.get("business", 0) > 0:
        lines.append(
            f"- **Bisnis ({_fmt_pct(allocation.get('business'))}):** "
            "Pertimbangkan investasi ke bisnis yang dianalisis, sesuai profil risiko Anda")
    if allocation.get("cash", 0) > 0:
        lines.append(
            f"- **Kas ({_fmt_pct(allocation.get('cash'))}):** "
            "Pertahankan sebagian dana dalam bentuk kas untuk fleksibilitas dan keamanan")

    lines += [
        "",
        f"Detail lengkap tersedia di halaman Audit (Audit ID: {audit_id}).",
        "",
        "> 💡 **Ingat:** AstaLink memberikan analisis dan rekomendasi. "
        "Keputusan investasi akhir sepenuhnya ada di tangan Anda.",
    ]
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
        "## Laporan Analisis & Rekomendasi",
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
