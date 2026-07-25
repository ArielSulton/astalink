"""Tests for app.integrations.pdf_report.render_allocation_pdf — the PDF
export sent to WhatsApp as a document message. Mirrors test_report.py's
fixtures since the PDF reuses the same state shape as the markdown report."""
from app.agents.state import LegalStatus, new_state
from app.integrations.pdf_report import render_allocation_pdf


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
