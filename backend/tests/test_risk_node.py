from unittest.mock import MagicMock, patch

import numpy as np
from langchain_core.messages import AIMessage

from app.agents.risk.node import risk_node
from app.agents.state import new_state


def test_risk_node_computes_var_and_mvo_for_provided_tickers() -> None:
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}

    rng = np.random.default_rng(0)
    fake_closes = {
        "BBCA": np.exp(np.cumsum(rng.normal(0.0005, 0.01, 252))) * 8000,
        "BMRI": np.exp(np.cumsum(rng.normal(0.0003, 0.012, 252))) * 6000,
    }

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Risiko terkendali.")

    with patch("app.agents.risk.node.fetch_close_prices",
               side_effect=lambda t, **kw: fake_closes[t]), \
         patch("app.agents.risk.node.get_chat_model", return_value=fake_llm):
        update = risk_node(state)

    risk = update["entities"]["risk_metrics"]
    assert risk["metrics"]["var_95"] > 0
    assert set(risk["suggested_weights"]) == {"BBCA", "BMRI"}
    assert abs(sum(risk["suggested_weights"].values()) - 1.0) < 1e-3


def test_risk_node_handles_single_ticker_without_crashing() -> None:
    """Live incident reproduction: np.cov() on a single-row array degenerates
    to a 0-d scalar (not a 1x1 matrix), which used to crash the cov_map
    dict-comprehension in risk_node with 'IndexError: invalid index to
    scalar variable' whenever a risk review named exactly one ticker."""
    state = new_state()
    state["entities"] = {"tickers": ["BBCA"]}

    rng = np.random.default_rng(0)
    fake_closes = {
        "BBCA": np.exp(np.cumsum(rng.normal(0.0005, 0.01, 252))) * 8000,
    }

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Risiko BBCA moderat.")

    with patch("app.agents.risk.node.fetch_close_prices",
               side_effect=lambda t, **kw: fake_closes[t]), \
         patch("app.agents.risk.node.get_chat_model", return_value=fake_llm):
        update = risk_node(state)

    risk = update["entities"]["risk_metrics"]
    assert set(risk["suggested_weights"]) == {"BBCA"}
    assert risk["suggested_weights"]["BBCA"] == 1.0
    assert risk["covariance"]["BBCA"]["BBCA"] > 0


def test_risk_node_survives_llm_narration_failure() -> None:
    """Live incident: a flaky LLM call (malformed response, provider error)
    used to crash the whole node — narration is decorative color on top of
    the already-computed VaR/Sharpe numbers (numpy/scipy math, never LLM),
    so a narration failure must degrade to an empty string, not lose the
    real analysis."""
    state = new_state()
    state["entities"] = {"tickers": ["BBCA", "BMRI"]}

    rng = np.random.default_rng(0)
    fake_closes = {
        "BBCA": np.exp(np.cumsum(rng.normal(0.0005, 0.01, 252))) * 8000,
        "BMRI": np.exp(np.cumsum(rng.normal(0.0003, 0.012, 252))) * 6000,
    }

    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = RuntimeError("malformed response from provider")

    with patch("app.agents.risk.node.fetch_close_prices",
               side_effect=lambda t, **kw: fake_closes[t]), \
         patch("app.agents.risk.node.get_chat_model", return_value=fake_llm):
        update = risk_node(state)

    risk = update["entities"]["risk_metrics"]
    assert risk["metrics"]["var_95"] > 0, "real computed metrics must survive"
    assert risk["narration"] == ""
