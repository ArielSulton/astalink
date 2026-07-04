"""Business Evaluator (N2b).

Reads the workspace's registered businesses and their per-period financial
records (backend/migrations/0010_businesses.sql) and runs a DCF using
`profit` as a free-cash-flow proxy — a deliberate simplification: this app
only collects aset/omset/profit, not a full cash flow statement."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.business.dcf import discounted_cash_flow
from app.agents.business.schemas import BusinessValuation
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

DEFAULT_DISCOUNT = 0.10
DEFAULT_TERMINAL = 0.03

NARRATE_SYSTEM = """\
You are a business valuation analyst. Given an enterprise value computed via
DCF along with the underlying cashflows, write ONE short paragraph in
Indonesian (≤80 words) summarizing the result. Do NOT introduce new numbers."""


def _select_business(workspace_id: str, business_name: str | None) -> dict | None:
    """Returns the matching business row, or None if there's no single
    unambiguous match (zero matches, or multiple with no name to disambiguate)."""
    sb = get_admin_client()
    query = sb.table("businesses").select("id,name").eq("workspace_id", workspace_id)
    if business_name:
        query = query.ilike("name", f"%{business_name}%")
    rows = query.execute().data or []
    return rows[0] if len(rows) == 1 else None


@track_node_duration("n2b_business")
def business_node(state: AgentState) -> AgentState:
    workspace_id = state.get("_workspace_id")
    business_name = state.get("entities", {}).get("business_name")

    if not workspace_id:
        return {"entities": {**state.get("entities", {}), "business_valuation": None}}

    business = _select_business(workspace_id, business_name)
    if not business:
        return {
            "entities": {**state.get("entities", {}), "business_valuation": None},
            "errors": [*state.get("errors", []),
                       {"node": "business", "reason": "no_matching_business"}],
        }

    records_res = (
        get_admin_client().table("business_financial_records")
        .select("period_year,profit")
        .eq("business_id", business["id"])
        .order("period_year")
        .execute()
    )
    records = records_res.data or []
    if not records:
        return {
            "entities": {**state.get("entities", {}), "business_valuation": None},
            "errors": [*state.get("errors", []),
                       {"node": "business", "reason": "no_financial_records"}],
        }

    try:
        cashflows = [float(r["profit"]) for r in records]
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

    try:
        llm = get_chat_model()
        narration = extract_text(llm.invoke([
            SystemMessage(content=NARRATE_SYSTEM),
            HumanMessage(content=f"Bisnis={business['name']}, EV={ev:,.0f}, "
                                 f"cashflows={cashflows}, r={DEFAULT_DISCOUNT}, "
                                 f"g={DEFAULT_TERMINAL}"),
        ]).content)
    except Exception as exc:
        log.error("business_node: LLM narration failed: %s", exc)
        return {
            "entities": {**state.get("entities", {}), "business_valuation": None},
            "errors": [*state.get("errors", []),
                       {"node": "business", "reason": str(exc)}],
        }

    val = BusinessValuation(
        business_name=business["name"],
        enterprise_value=ev,
        discount_rate=DEFAULT_DISCOUNT,
        terminal_growth=DEFAULT_TERMINAL,
        cashflows=cashflows,
        narration=narration,
    )
    return {"entities": {**state.get("entities", {}),
                         "business_valuation": val.model_dump()}}
