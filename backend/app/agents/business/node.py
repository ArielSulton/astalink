"""Business Evaluator (N2b)."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.business.dcf import discounted_cash_flow
from app.agents.business.erp_connector import CSVConnector
from app.agents.business.schemas import BusinessValuation
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration

log = logging.getLogger(__name__)

DEFAULT_DISCOUNT = 0.10
DEFAULT_TERMINAL = 0.03

NARRATE_SYSTEM = """\
You are a business valuation analyst. Given an enterprise value computed via
DCF along with the underlying cashflows, write ONE short paragraph (≤80 words)
summarizing the result. Do NOT introduce new numbers."""


@track_node_duration("n2b_business")
def business_node(state: AgentState) -> AgentState:
    csv_path = state.get("entities", {}).get("financials_csv")
    if not csv_path:
        return {"entities": {**state.get("entities", {}), "business_valuation": None}}

    try:
        cashflows = CSVConnector(csv_path).fetch_cashflows()
        ev = discounted_cash_flow(
            cashflows=cashflows,
            discount_rate=DEFAULT_DISCOUNT,
            terminal_growth=DEFAULT_TERMINAL,
        )
    except Exception as exc:
        log.error("business_node: DCF failed: %s", exc)
        return {
            "entities": {**state.get("entities", {}), "business_valuation": None},
            "errors": [*state.get("errors", []),
                       {"node": "business", "reason": str(exc)}],
        }

    llm = get_chat_model()
    narration = extract_text(llm.invoke([
        SystemMessage(content=NARRATE_SYSTEM),
        HumanMessage(content=f"EV={ev:,.0f}, cashflows={cashflows}, "
                             f"r={DEFAULT_DISCOUNT}, g={DEFAULT_TERMINAL}"),
    ]).content)

    val = BusinessValuation(
        enterprise_value=ev,
        discount_rate=DEFAULT_DISCOUNT,
        terminal_growth=DEFAULT_TERMINAL,
        cashflows=cashflows,
        narration=narration,
    )
    return {"entities": {**state.get("entities", {}),
                         "business_valuation": val.model_dump()}}
