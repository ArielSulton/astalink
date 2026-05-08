from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.business.node import business_node
from app.agents.state import new_state


def test_business_node_runs_dcf_when_financials_provided() -> None:
    state = new_state()
    state["entities"] = {"financials_csv": str(Path(__file__).parent / "data" / "sample_financials.csv")}

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Valuasi positif.")

    with patch("app.agents.business.node.get_chat_model", return_value=fake_llm):
        update = business_node(state)

    val = update["entities"]["business_valuation"]
    assert val["enterprise_value"] > 0
    assert val["narration"]


def test_business_node_skips_when_no_financials() -> None:
    state = new_state()  # no financials_csv key
    update = business_node(state)
    assert update["entities"]["business_valuation"] is None
