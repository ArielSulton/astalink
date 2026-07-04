from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.optimizer.node import optimizer_node
from app.agents.optimizer.schemas import SolverResult
from app.agents.state import LegalStatus, new_state


def test_optimizer_node_increments_revision_count() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
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
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 50_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation",
               return_value=(fake_result, [])), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        update = optimizer_node(state)

    assert update["revision_count"] == 1
    assert update["allocation_plan"]["weights"][0]["ticker"] in ("BBCA", "BMRI")
    assert update["allocation_plan"]["narration"]


def test_optimizer_node_uses_legal_feedback_to_forbid_tickers() -> None:
    """When legal_status=rejected and citations carry forbidden_tickers,
    the next optimizer pass must respect them."""
    state = new_state()
    state["_workspace_id"] = "ws-1"
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
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 50_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        update = optimizer_node(state)

    assert "GGRM" in captured[0].forbidden_tickers
    assert update["revision_count"] == 2
    assert update["allocation_plan"]["weights"]


def test_optimizer_node_maps_conservative_risk_profile_to_tighter_constraints() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {
        "tickers": ["BBCA", "BMRI"],
        "amount": 10_000_000,
        "risk_profile": "konservatif",
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

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.5, "BMRI": 0.35}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi konservatif.")
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 50_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        optimizer_node(state)

    assert captured[0].max_per_asset == 0.25
    assert captured[0].min_cash_buffer == 0.15


def test_optimizer_node_uses_default_constraints_when_risk_profile_absent() -> None:
    """No risk_profile in entities must behave exactly as before this
    change — same defaults OptimizerInputs already declared."""
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {
        "tickers": ["BBCA"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [{"ticker": "BBCA", "last_close": 8000}]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.5},
            "suggested_weights": {"BBCA": 1.0},
        },
    }
    state["revision_count"] = 0

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.9}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi standar.")
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 50_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        optimizer_node(state)

    assert captured[0].max_per_asset == 0.4
    assert captured[0].min_cash_buffer == 0.05
    assert captured[0].cash == 10_000_000


def test_optimizer_node_wires_partial_tickers_from_legal_citations() -> None:
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {
        "tickers": ["BBCA", "UNVR"],
        "amount": 10_000_000,
        "market_snapshot": {"tickers": [
            {"ticker": "BBCA", "last_close": 8000},
            {"ticker": "UNVR", "last_close": 4000},
        ]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.0},
            "suggested_weights": {"BBCA": 0.5, "UNVR": 0.5},
        },
    }
    state["legal_status"] = LegalStatus.PARTIAL
    state["legal_citations"] = [{
        "source": "OJK", "pasal": "4", "ayat": "1",
        "chunk_id": "x", "span": "dibatasi maksimal 10%",
        "partial_tickers": {"UNVR": 0.1},
    }]
    state["revision_count"] = 1

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.9, "UNVR": 0.1}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi disesuaikan.")
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 50_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        optimizer_node(state)

    assert captured[0].partial_tickers == {"UNVR": 0.1}


def test_optimizer_node_caps_cash_at_real_workspace_balance() -> None:
    """User asked to allocate 500jt, but the workspace only has 10jt left —
    the optimizer must use the real balance as the ceiling, not the
    requested amount."""
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {
        "tickers": ["BBCA"],
        "amount": 500_000_000,
        "market_snapshot": {"tickers": [{"ticker": "BBCA", "last_close": 8000}]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.5},
            "suggested_weights": {"BBCA": 1.0},
        },
    }
    state["revision_count"] = 0

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.9}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi dibatasi saldo.")
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 10_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        optimizer_node(state)

    assert captured[0].cash == 10_000_000


def test_optimizer_node_uses_full_balance_when_no_amount_stated() -> None:
    """User didn't state an amount at all (entities.amount absent) — default
    to the workspace's full available balance rather than cash=0."""
    state = new_state()
    state["_workspace_id"] = "ws-1"
    state["entities"] = {
        "tickers": ["BBCA"],
        "market_snapshot": {"tickers": [{"ticker": "BBCA", "last_close": 8000}]},
        "risk_metrics": {
            "metrics": {"var_95": 0.02, "var_99": 0.03, "sharpe": 1.5},
            "suggested_weights": {"BBCA": 1.0},
        },
    }
    state["revision_count"] = 0

    captured: list = []

    def _capture_solve(inputs):
        captured.append(inputs)
        return SolverResult(status="optimal", weights={"BBCA": 0.9}), []

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Alokasi penuh saldo.")
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"cash_balance": 25_000_000}])

    with patch("app.agents.optimizer.node.solve_with_relaxation", side_effect=_capture_solve), \
         patch("app.agents.optimizer.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.optimizer.node.get_admin_client", return_value=fake_admin):
        optimizer_node(state)

    assert captured[0].cash == 25_000_000
