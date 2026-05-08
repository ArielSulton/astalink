from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.optimizer.node import optimizer_node
from app.agents.optimizer.schemas import SolverResult
from app.agents.state import LegalStatus, new_state


def test_optimizer_node_increments_revision_count() -> None:
    state = new_state()
    state["entities"] = {
        "tickers": ["BBCA", "BMRI"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [
            {"ticker": "BBCA", "last_close": 8000},
            {"ticker": "BMRI", "last_close": 6000},
        ]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.5},
            "suggested_weights": {"BBCA": 0.5, "BMRI": 0.5},
        },
    }
    state["revision_count"] = 0

    fake_result = SolverResult(status="optimal",
                               weights={"BBCA": 0.6, "BMRI": 0.35},
                               objective_value=0.07)
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi seimbang.")

    with patch("app.agents.optimizer.node.solve_with_relaxation",
               return_value=(fake_result, [])), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm):
        update = optimizer_node(state)

    assert update["revision_count"] == 1
    assert update["allocation_plan"]["weights"][0]["ticker"] in ("BBCA", "BMRI")
    assert update["allocation_plan"]["narration"]


def test_optimizer_node_uses_legal_feedback_to_forbid_tickers() -> None:
    """When legal_status=rejected and citations carry forbidden_tickers,
    the next optimizer pass must respect them."""
    state = new_state()
    state["entities"] = {
        "tickers": ["BBCA", "GGRM"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [
            {"ticker": "BBCA", "last_close": 8000},
            {"ticker": "GGRM", "last_close": 50000},
        ]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.0},
            "suggested_weights": {"BBCA": 0.5, "GGRM": 0.5},
        },
    }
    state["legal_status"] = LegalStatus.REJECTED
    state["legal_citations"] = [{
        "source": "OJK", "pasal": "3", "ayat": "1",
        "chunk_id": "x", "span": "saham emiten rokok dilarang",
        "forbidden_tickers": ["GGRM"],
    }]
    state["revision_count"] = 1

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.95, "GGRM": 0.0}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi disesuaikan.")

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm):
        update = optimizer_node(state)

    assert "GGRM" in captured[0].forbidden_tickers
    assert update["revision_count"] == 2
    assert update["allocation_plan"]["weights"]
