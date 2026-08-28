"""layer0_node prescreen wiring (STEP 3 stocks leg).

Regression coverage for the "saham always equals baseline" bug: l0_allocation
must run the A1-A4 engine and pass its aggregate score into run_layer0 as
`stock_score` BEFORE the split is decided, not rely on the baseline stand-in
that engine.py falls back to when nothing is passed."""
from __future__ import annotations

from unittest.mock import patch

from app.agents.allocation.node import layer0_node
from app.agents.allocation.schemas import Layer0Result, Layer0Status
from app.agents.intents import Intent
from app.agents.state import new_state


def _state_with(intent: str, tickers: list[str], amount: float | None = None) -> dict:
    state = new_state()
    state["_workspace_id"] = None  # skip DB profile loads entirely
    state["intent"] = intent
    entities = {"tickers": tickers}
    if amount is not None:
        entities["amount"] = amount
    state["entities"] = entities
    return state


def test_allocate_stocks_prescreens_before_deciding_split():
    engine_dump = {
        "verdicts": {"TLKM": {"score": 80.0}, "EXCL": {"score": 60.0}},
        "eligible_tickers": ["TLKM", "EXCL"],
    }
    with patch("app.agents.allocation.node.prescreen_stock_score",
              return_value=(70.0, engine_dump)) as mock_prescreen, \
         patch("app.agents.allocation.node.run_layer0") as mock_run_layer0:
        mock_run_layer0.return_value = Layer0Result(status=Layer0Status.RECOMMENDED)
        layer0_node(_state_with(Intent.ALLOCATE_STOCKS.value, ["TLKM", "EXCL"], amount=1_000_000.0))

    mock_prescreen.assert_called_once_with(["TLKM", "EXCL"], 1_000_000.0)
    _, kwargs = mock_run_layer0.call_args
    assert kwargs["stock_score"] == 70.0


def test_prescreen_result_is_stashed_in_entities_for_market_node_reuse():
    engine_dump = {"verdicts": {"TLKM": {"score": 80.0}}, "eligible_tickers": ["TLKM"]}
    with patch("app.agents.allocation.node.prescreen_stock_score",
              return_value=(80.0, engine_dump)), \
         patch("app.agents.allocation.node.run_layer0") as mock_run_layer0:
        mock_run_layer0.return_value = Layer0Result(status=Layer0Status.RECOMMENDED)
        update = layer0_node(_state_with(Intent.ALLOCATE_STOCKS.value, ["TLKM"]))

    assert update["entities"]["stock_engine"] == engine_dump
    assert update["entities"]["eligible_tickers"] == ["TLKM"]


def test_no_tickers_yields_none_stock_score_without_crashing():
    with patch("app.agents.allocation.node.prescreen_stock_score",
              return_value=(None, None)) as mock_prescreen, \
         patch("app.agents.allocation.node.run_layer0") as mock_run_layer0:
        mock_run_layer0.return_value = Layer0Result(status=Layer0Status.RECOMMENDED)
        update = layer0_node(_state_with(Intent.ALLOCATE_CAPITAL.value, []))

    mock_prescreen.assert_called_once_with([], None)
    _, kwargs = mock_run_layer0.call_args
    assert kwargs["stock_score"] is None
    assert "stock_engine" not in update.get("entities", {})
