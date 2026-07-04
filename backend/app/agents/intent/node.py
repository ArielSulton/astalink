"""Intent Classifier (N1) — first node of every pipeline run.

Generates `audit_id` via new_state() if not present, classifies the latest
user message into an Intent enum, extracts entities, and either continues or
appends a clarification question for low-confidence cases."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.intent.schemas import IntentDecision
from app.agents.intents import Intent
from app.agents.state import AgentState
from app.core.gemini import get_chat_model
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.6

SYSTEM = """\
You are an Indonesian financial-assistant intent classifier.
Map the user message to one of:
- allocate_stocks: user wants to invest cash into stocks/portfolio
- evaluate_business: user wants their own business valued
- risk_review: user wants risk metrics on existing holdings
- portfolio_status: user is asking about current holdings/positions
- explain: user wants an explanation of a concept/term
- unknown: cannot determine

Extract relevant entities (amount, tickers, sector, risk_profile, etc.) into
the `entities` dict. Estimate `confidence` honestly: if the message is
ambiguous, set confidence < 0.6 and provide a `clarification_question` in
Indonesian.
"""


@lru_cache(maxsize=1)
def _build_chain():
    """Bind the structured output schema once. Cached because LLM client
    bindings are expensive to rebuild per invocation."""
    llm = get_chat_model()
    return llm.with_structured_output(IntentDecision)


def _last_user_text(state: AgentState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def _record_audit(state: AgentState, decision: IntentDecision) -> None:
    """Insert or update the audit_log row for this run."""
    try:
        get_admin_client().table("audit_log").upsert({
            "audit_id": state["audit_id"],
            "intent": decision.intent.value,
            "status": "in_progress",
            "payload": {"intent": decision.model_dump()},
            "workspace_id": state.get("entities", {}).get("workspace_id")
                            or state.get("_workspace_id"),  # set by API entry point
            "user_id": state.get("_user_id"),
        }).execute()
    except Exception as exc:
        log.error("intent_node: audit_log upsert failed: %s", exc)


@track_node_duration("n1_intent")
def intent_node(state: AgentState) -> AgentState:
    user_text = _last_user_text(state)
    if not user_text:
        return {"intent": Intent.UNKNOWN.value, "entities": {}, "_needs_clarification": True}

    chain = _build_chain()
    try:
        decision: IntentDecision = chain.invoke([
            SystemMessage(content=SYSTEM),
            HumanMessage(content=user_text),
        ])
    except Exception as exc:
        log.exception("intent_node: classification failed: %s", exc)
        return {
            "intent": Intent.UNKNOWN.value,
            "entities": {},
            "_needs_clarification": True,
            "errors": [*state.get("errors", []),
                       {"node": "intent", "reason": str(exc)}],
        }

    _record_audit(state, decision)

    needs_clarification = (
        decision.confidence < CONFIDENCE_FLOOR or decision.intent == Intent.UNKNOWN
    )
    update: dict[str, Any] = {
        "intent": decision.intent.value,
        "entities": decision.entities,
        "_needs_clarification": needs_clarification,
    }

    if needs_clarification:
        question = decision.clarification_question or \
            "Bisa dijelaskan lagi tujuan Anda? Misal: alokasi dana, valuasi bisnis, atau review risiko."
        update["messages"] = [*state.get("messages", []),
                              AIMessage(content=question)]
    return update
