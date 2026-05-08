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
