"""Tests for app.agents.report.build_allocation_report — the deterministic
markdown report the /chat endpoint returns for allocation runs (style="report").

The formatter reads only what is already in the final AgentState; every
section must degrade gracefully when its data is absent (stock engine
skipped, no citations, 0%-stocks terminal, ...)."""
from app.agents.report import build_allocation_report
from app.agents.state import LegalStatus, UserApproval, new_state


def _layer0_result(**overrides) -> dict:
    base = {
        "status": "allocated",
        "allocation": {"cash": 0.15, "stocks": 0.85, "business": 0.0},
        "confidence": 62,
        "confidence_label": "MEDIUM",
        "completeness": 1.0,
        "completeness_tier": "ok",
        "questions": [],
        "veto_flags": [
            {"code": "HIGH_INTEREST_DEBT", "target": "both",
             "reason": "Ada utang konsumtif berbunga tinggi — pertimbangkan melunasinya dulu.",
             "hard": False},
        ],
        "business_score": None,
        "stock_score": 50.0,
        "baseline_score": 50.0,
        "quality": None,
        "devils_advocate": [],
        "why_not_all_stocks": "Buffer kas minimal tetap dijaga untuk kebutuhan darurat.",
        "why_not_all_business": "",
        "rejected_reasons": [],
        "narration": "Alokasi condong ke saham karena tidak ada leg bisnis.",
        "business_id": None,
        "business_name": None,
    }
    base.update(overrides)
    return base


def _verdict(ticker: str, band: str = "buy", score: float = 70.0) -> dict:
    return {
        "ticker": ticker,
        "band": band,
        "score": score,
        "horizon": "3-6 bulan",
        "invalidation_condition": f"tesis batal jika close {ticker} < entry x 0.92",
        "components": {"a1_news": 60.0, "a2_macro": 55.0, "a4_flow": 80.0},
        "gate_status": "pass",
        "manipulation_risk": "low",
        "evidence_gaps": ["data net asing tidak tersedia"],
        "detail": [f"OBV {ticker} naik searah harga", "berita didominasi sumber primer"],
        "as_of": "2026-07-16",
    }


def _full_state() -> dict:
    state = new_state()
    state["audit_id"] = "audit-report-1"
    state["intent"] = "allocate_stocks"
    state["legal_status"] = LegalStatus.APPROVED
    state["layer0_result"] = _layer0_result()
    state["entities"] = {
        "workspace_id": "ws-1",
        "stock_engine": {
            "verdicts": {
                "BBCA": _verdict("BBCA", band="buy", score=71.0),
                "TLKM": _verdict("TLKM", band="watchlist", score=55.0),
            },
            "eligible_tickers": ["BBCA", "TLKM"],
        },
    }
    state["allocation_plan"] = {
        "weights": [
            {"ticker": "BBCA", "weight": 0.6},
            {"ticker": "TLKM", "weight": 0.4},
        ],
        "cash": 42_500_000.0,
        "cash_buffer": 0.1,
        "narration": "Bobot terbesar ke BBCA karena skor flow tertinggi.",
        "relaxations_applied": ["max_per_asset dinaikkan ke 0.6"],
    }
    state["legal_citations"] = [
        {"source": "POJK No. 1/2024", "pasal": "5", "ayat": "2",
         "span": "batas konsentrasi per emiten"},
    ]
    return state


def test_full_state_produces_complete_report() -> None:
    report = build_allocation_report(_full_state())
    assert report is not None
    # header + trace
    assert "Laporan" in report
    assert "audit-report-1" in report
    # layer 0 split percentages
    assert "85%" in report and "15%" in report
    # veto reason surfaces
    assert "utang konsumtif" in report.lower()
    # why-not panel
    assert "Buffer kas minimal" in report
    # layer 1 verdicts per ticker
    assert "BBCA" in report and "TLKM" in report
    assert "tesis batal" in report.lower()
    # optimizer weights as percentages + narration
    assert "60%" in report and "40%" in report
    assert "Bobot terbesar ke BBCA" in report
    # legal status + citation
    assert "POJK No. 1/2024" in report
    assert "Pasal 5" in report
    # next step points at approvals
    assert "approv" in report.lower() or "setuju" in report.lower()


def test_returns_none_without_layer0_result() -> None:
    state = new_state()
    state["legal_status"] = LegalStatus.APPROVED
    state["audit_id"] = "audit-x"
    assert build_allocation_report(state) is None


def test_returns_none_for_insufficient_data() -> None:
    """INSUFFICIENT_DATA keeps the staged-questions message from
    allocation/node.py::_format_terminal_message — the report must step aside."""
    state = new_state()
    state["layer0_result"] = _layer0_result(
        status="insufficient_data", allocation=None, confidence=0)
    assert build_allocation_report(state) is None


def test_zero_stocks_terminal_still_reports_without_stock_sections() -> None:
    state = new_state()
    state["audit_id"] = "audit-cash"
    state["layer0_result"] = _layer0_result(
        allocation={"cash": 1.0, "stocks": 0.0, "business": 0.0},
        veto_flags=[{"code": "EMERGENCY_FUND", "target": "both",
                     "reason": "Dana darurat di bawah 6x pengeluaran bulanan.",
                     "hard": True}],
    )
    report = build_allocation_report(state)
    assert report is not None
    assert "100%" in report
    assert "dana darurat" in report.lower()
    # no layer-1/optimizer/legal sections without their data
    assert "Verdik" not in report
    assert "Optimizer" not in report


def test_missing_stock_engine_and_citations_sections_skipped() -> None:
    state = _full_state()
    state["entities"].pop("stock_engine")
    state["legal_citations"] = []
    report = build_allocation_report(state)
    assert report is not None
    assert "Verdik" not in report
    # legal status line still present even without citations
    assert "legal" in report.lower()
    # optimizer section still there
    assert "60%" in report


def test_executed_transactions_reported_honestly() -> None:
    state = _full_state()
    state["user_approval"] = UserApproval.APPROVED
    state["transactions"] = [
        {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled"},
        {"ticker": "TLKM", "side": "buy", "quantity": 5,
         "status": "rejected_insufficient_balance"},
    ]
    report = build_allocation_report(state)
    assert report is not None
    assert "BBCA" in report and "TLKM" in report
    assert "tidak mencukupi" in report.lower() or "ditolak" in report.lower()


def test_legal_rejected_report_explains_rejection() -> None:
    state = _full_state()
    state["legal_status"] = LegalStatus.REJECTED
    report = build_allocation_report(state)
    assert report is not None
    assert "ditolak" in report.lower()
    assert "audit-report-1" in report
