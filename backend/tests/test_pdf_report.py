"""Tests for app.integrations.pdf_report.render_allocation_pdf — the PDF
export sent to WhatsApp as a document message. Mirrors test_report.py's
fixtures since the PDF reuses the same state shape as the markdown report."""
from io import BytesIO

from pypdf import PdfReader

from app.agents.state import LegalStatus, new_state
from app.integrations.pdf_report import render_allocation_pdf


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _layer0_result(**overrides) -> dict:
    base = {
        "status": "recommended",
        "allocation": {"cash": 0.15, "stocks": 0.85, "business": 0.0},
        "confidence": 62,
        "confidence_label": "MEDIUM",
        "veto_flags": [
            {"code": "HIGH_INTEREST_DEBT", "target": "both",
             "reason": "Ada utang konsumtif berbunga tinggi.", "hard": False},
        ],
        "narration": "Alokasi condong ke saham karena tidak ada leg bisnis.",
        "business_id": None,
        "business_name": None,
    }
    base.update(overrides)
    return base


def _full_state() -> dict:
    state = new_state()
    state["audit_id"] = "audit-pdf-1"
    state["intent"] = "allocate_stocks"
    state["legal_status"] = LegalStatus.APPROVED
    state["layer0_result"] = _layer0_result()
    state["entities"] = {
        "workspace_id": "ws-1",
        "stock_engine": {
            "verdicts": {
                "BBCA": {"ticker": "BBCA", "band": "buy", "score": 71.0, "gate_status": "pass"},
            },
        },
    }
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 10_000_000.0,
        "cash_buffer": 0.1,
        "narration": "Bobot terbesar ke BBCA.",
        "relaxations_applied": [],
    }
    state["legal_citations"] = [
        {"source": "POJK No. 1/2024", "pasal": "5", "ayat": "2", "span": "batas konsentrasi"},
    ]
    return state


def test_render_allocation_pdf_returns_valid_pdf_bytes() -> None:
    pdf = render_allocation_pdf(_full_state())
    assert pdf is not None
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 500


def test_render_allocation_pdf_returns_none_without_layer0_result() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    assert render_allocation_pdf(state) is None


def test_render_allocation_pdf_returns_none_for_insufficient_data() -> None:
    state = new_state()
    state["layer0_result"] = _layer0_result(status="insufficient_data", allocation=None)
    assert render_allocation_pdf(state) is None


def test_render_allocation_pdf_surfaces_stock_sleeve_cash_not_total_funds() -> None:
    """Regression: a weight like "BBCA 95%" is 95% of Layer 0's stock-sleeve
    slice (allocation_plan.cash), not 95% of the user's total funds — the
    PDF must state that rupiah amount so it doesn't read as "95% of
    everything" alongside a Kas/Saham/Bisnis split that says 25% stocks."""
    state = _full_state()
    state["allocation_plan"]["cash"] = 12_415_000.0
    state["allocation_plan"]["cash_buffer"] = 0.05
    text = _pdf_text(render_allocation_pdf(state))
    assert "Dana yang dianalisis" in text
    assert "12.415.000" in text
    assert "Buffer kas minimum" in text


def test_render_allocation_pdf_handles_missing_optional_sections() -> None:
    """No stock_engine, no legal_citations, no legal_status — must still
    render a valid PDF with just the Layer 0 section."""
    state = new_state()
    state["audit_id"] = "audit-pdf-minimal"
    state["layer0_result"] = _layer0_result(
        allocation={"cash": 1.0, "stocks": 0.0, "business": 0.0},
    )
    pdf = render_allocation_pdf(state)
    assert pdf is not None
    assert pdf.startswith(b"%PDF-")
