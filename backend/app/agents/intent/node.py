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
from app.agents.optimizer.sectors import sector_to_tickers
from app.agents.state import AgentState
from app.core.gemini import get_chat_model
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.6

# Same 4 blue-chip IDX tickers as app/api/v1/market.py's DEFAULT_TICKERS
# (kept as a separate bare-code list here rather than imported, since that
# constant lives in the API/route layer and is formatted for a query-param
# default, not for entities.tickers).
DEFAULT_ALLOCATION_TICKERS = ["BBCA", "TLKM", "ASII", "BBRI"]

SYSTEM = """\
You are an Indonesian financial-assistant intent classifier.
Map the user message to one of:
- allocate_stocks: user wants to invest cash into stocks/portfolio
- allocate_capital: user is weighing where money should go between options —
  e.g. stocks vs their own/someone's business ("mending taruh di saham atau
  suntik ke usaha teman?", "uang 100 juta ini buat modal warung atau beli
  saham?"). Extract business_name if a specific business is mentioned.
- evaluate_business: user wants their own business valued
- risk_review: user wants risk metrics on existing holdings
- portfolio_status: user is asking about current holdings/positions
- explain: DEFAULT for every non-actionable message that expects a substantive
  answer — explanations of concepts/terms, general finance or business
  questions, brainstorming and open discussion (market outlook, comparing
  sectors, opinions like "menurutmu bagaimana prospek bank digital?"),
  follow-up questions about a previous answer or analysis, and casual
  conversation. Extract `tickers` when specific stocks are mentioned.
- unknown: cannot determine at all

Only choose allocate_stocks/allocate_capital when the user actually asks to
allocate/invest money (usually with an amount); asking ABOUT a stock, sector,
or idea is explain, not an allocation. Examples:
- "menurutmu prospek BBCA gimana?" -> explain (entities.tickers=["BBCA"])
- "lagi mikir mau buka usaha kopi, worth it nggak?" -> explain
- "alokasikan 10 juta ke BBCA dan TLKM" -> allocate_stocks
- "50 juta ini mending buat saham atau modal warung saya?" -> allocate_capital

Extract relevant entities (amount, tickers, sector, risk_profile, business_name,
etc.) into the `entities` dict. For evaluate_business, `business_name` should be
the specific business name the user mentioned, if any (e.g. "Toko Maju Jaya") —
omit the key entirely if the user didn't name a specific business. Estimate
`confidence` honestly: if the message is ambiguous, set confidence < 0.6 and
provide a `clarification_question` in Indonesian.

The clarification_question is the ONLY thing the user sees when confidence is
low — it must stand alone as a complete, friendly sentence a first-time user
would understand with no other context, never a bare word or fragment like
"gimana?" or "maksudnya?". State what was unclear and give a concrete example,
e.g. "Maaf, saya kurang paham maksud pesan Anda. Bisa dijelaskan lebih detail?
Misalnya: \"alokasikan 10 juta ke BBCA\" atau \"apa itu RSI?\"."
"""


@lru_cache(maxsize=1)
def _build_chain():
    """Bind the structured output schema once. Cached because LLM client
    bindings are expensive to rebuild per invocation."""
    llm = get_chat_model()
    return llm.with_structured_output(IntentDecision)


def _extract_sectors(entities: dict[str, Any]) -> list[str]:
    """The intent LLM isn't schema-constrained for entities (free-form
    dict), so a stated sector shows up inconsistently — a single string
    under "sector", or a list under "sectors" (observed live: "bank atau
    telco gitu" -> {"sectors": ["banking", "telecommunications"]}, not
    {"sector": ...}). Normalize both shapes so a real request doesn't
    silently miss the resolution below just because of key naming."""
    raw = entities.get("sector") or entities.get("sectors")
    if raw is None:
        return []
    return [raw] if isinstance(raw, str) else [s for s in raw if isinstance(s, str)]


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
            "thread_id": state.get("_thread_id"),  # set by API entry point; lets
                                                    # approvals.py resume this
                                                    # exact paused graph run
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
    entities = decision.entities
    if (
        decision.intent in (Intent.ALLOCATE_STOCKS, Intent.ALLOCATE_CAPITAL)
        and not needs_clarification
        and not entities.get("tickers")
    ):
        sectors = _extract_sectors(entities)
        if sectors:
            # A stated sector ("bank atau telco gitu") resolves to that
            # sector's real constituents — NOT the generic blue-chip basket
            # below, which would ignore what the user actually asked for
            # (ASII/TLKM aren't bank stocks). Without this, Layer 0's stocks
            # leg falls back to the baseline stand-in (engine.py's
            # `effective_stock_score`), producing an uninformative
            # baseline-vs-baseline 50/50 split no matter the user's request.
            sector_tickers: list[str] = []
            for s in sectors:
                for t in sector_to_tickers(s):
                    if t not in sector_tickers:
                        sector_tickers.append(t)
            if sector_tickers:
                entities = {**entities, "tickers": sector_tickers}
        else:
            # "rekomendasi investasi untuk dana 20 juta" names no ticker AND
            # no sector — a genuine recommendation request, not something to
            # bounce back asking the user to name a stock. Fall back to the
            # same blue-chip basket already used as the Market watchlist's
            # default (app/api/v1/market.py's DEFAULT_TICKERS).
            entities = {**entities, "tickers": DEFAULT_ALLOCATION_TICKERS}

    update: dict[str, Any] = {
        "intent": decision.intent.value,
        "entities": entities,
        "_needs_clarification": needs_clarification,
    }

    if needs_clarification:
        question = decision.clarification_question or \
            "Bisa dijelaskan lagi tujuan Anda? Misal: alokasi dana, valuasi bisnis, atau review risiko."
        update["messages"] = [*state.get("messages", []),
                              AIMessage(content=question)]
    return update
