"""Renders the same allocation report as report.py's markdown builder into
a PDF, for WhatsApp — Meta's document message type gives users something
they can actually save/print, unlike the plain-text reply WhatsApp already
gets (WA has no markdown table renderer, see report.py's docstring).

Reuses report.py's section data directly rather than re-deriving it, so the
PDF and the web/chatbot markdown report never drift out of sync."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.agents.report import _BAND_LABELS, _LEGAL_LABELS, _fmt_pct, _fmt_rp, _fmt_score
from app.agents.state import AgentState, LegalStatus

_styles = getSampleStyleSheet()
_H1 = ParagraphStyle("H1", parent=_styles["Heading1"], fontSize=16, spaceAfter=10)
_H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6)
_BODY = ParagraphStyle("Body", parent=_styles["BodyText"], fontSize=9.5, leading=13)
_TABLE_HEAD_BG = colors.HexColor("#166534")
_TABLE_ROW_BG = colors.HexColor("#f4f4f5")


def _table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEAD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ROW_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d4d4d8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def render_allocation_pdf(state: AgentState) -> bytes | None:
    """Mirrors report.py::build_allocation_report's guard — None when there
    is no allocation run, or Layer 0 stopped at INSUFFICIENT_DATA."""
    layer0 = state.get("layer0_result")
    if not layer0 or layer0.get("status") == "insufficient_data":
        return None

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    story: list[Any] = [
        Paragraph("Laporan Analisis & Rekomendasi", _H1),
        Paragraph(f"Audit ID: {state.get('audit_id')}", _BODY),
        Spacer(1, 12),
    ]

    allocation = layer0.get("allocation") or {}
    if allocation:
        story.append(Paragraph("Kas vs Saham vs Bisnis", _H2))
        story.append(_table([
            ["Kas", "Saham", "Bisnis"],
            [_fmt_pct(allocation.get("cash")), _fmt_pct(allocation.get("stocks")),
             _fmt_pct(allocation.get("business"))],
        ]))
        confidence = layer0.get("confidence")
        if confidence is not None:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"Keyakinan: <b>{layer0.get('confidence_label', '-')}</b> ({confidence}/100)", _BODY))

    veto_flags = layer0.get("veto_flags") or []
    if veto_flags:
        story.append(Paragraph("Catatan Veto", _H2))
        for flag in veto_flags:
            marker = "KERAS" if flag.get("hard", True) else "PERINGATAN"
            story.append(Paragraph(
                f"[{marker}] {flag.get('code', '?')} — {flag.get('reason', '')}", _BODY))

    narration = (layer0.get("narration") or "").strip()
    if narration:
        story.append(Spacer(1, 6))
        story.append(Paragraph(narration, _BODY))

    engine = (state.get("entities") or {}).get("stock_engine") or {}
    verdicts: dict[str, dict[str, Any]] = engine.get("verdicts") or {}
    if verdicts:
        story.append(Paragraph("Layer 1 — Verdik per Saham", _H2))
        rows = [["Ticker", "Band", "Skor", "Gate"]]
        for ticker, v in verdicts.items():
            band = _BAND_LABELS.get(str(v.get("band", "")), str(v.get("band", "-")))
            rows.append([ticker, band, _fmt_score(v.get("score")), str(v.get("gate_status", "-")).upper()])
        story.append(_table(rows))

    plan = state.get("allocation_plan") or {}
    weights = plan.get("weights") or []
    if weights:
        story.append(Paragraph("Rekomendasi Bobot Saham (Optimizer)", _H2))
        rows = [["Ticker", "Bobot yang Disarankan"]]
        rows += [[w.get("ticker", "?"), _fmt_pct(w.get("weight"))] for w in weights]
        story.append(_table(rows))
        story.append(Spacer(1, 6))
        # Without this, a weight like "BBCA 95%" reads as 95% of the user's
        # total funds — it's actually 95% of just the stock-sleeve amount
        # Layer 0 allocated to stocks, which can be a small slice of the
        # total (see the Kas/Saham/Bisnis split above).
        if plan.get("cash") is not None:
            story.append(Paragraph(
                f"Dana yang dianalisis: <b>{_fmt_rp(float(plan['cash']))}</b>", _BODY))
        if plan.get("cash_buffer") is not None:
            story.append(Paragraph(
                f"Buffer kas minimum disarankan: <b>{_fmt_pct(plan['cash_buffer'])}</b>", _BODY))
        plan_narration = (plan.get("narration") or "").strip()
        if plan_narration:
            story.append(Spacer(1, 6))
            story.append(Paragraph(plan_narration, _BODY))

    legal_status = state.get("legal_status")
    if legal_status is not None:
        status_value = getattr(legal_status, "value", str(legal_status))
        label = _LEGAL_LABELS.get(status_value, status_value)
        story.append(Paragraph("Validasi Legal", _H2))
        story.append(Paragraph(f"Status: <b>{label}</b>", _BODY))
        for c in state.get("legal_citations") or []:
            ref = str(c.get("source", "?"))
            if c.get("pasal"):
                ref += f" Pasal {c['pasal']}"
            if c.get("ayat"):
                ref += f" ayat ({c['ayat']})"
            span = (c.get("span") or "").strip()
            story.append(Paragraph(f"- {ref}" + (f" — {span}" if span else ""), _BODY))

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Laporan ini bersifat sebagai panduan analisis. Keputusan investasi akhir "
        "sepenuhnya ada di tangan Anda.", _BODY))

    doc.build(story)
    return buf.getvalue()
