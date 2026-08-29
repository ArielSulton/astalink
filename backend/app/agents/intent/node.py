"""Intent Classifier (N1) — first node of every pipeline run.

Generates `audit_id` via new_state() if not present, classifies the latest
user message into an Intent enum, extracts entities, and either continues or
appends a clarification question for low-confidence cases."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.intent.schemas import IntentDecision
from app.agents.intents import Intent
from app.agents.optimizer.sectors import sector_to_tickers
from app.agents.state import AgentState
from app.core.config import settings
from app.core.gemini import get_chat_model
from app.core.metrics import track_node_duration
from app.core.supabase_admin import get_admin_client

log = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.6

# Recent turns given to the classifier so it can recognize a genuine
# follow-up ("kenapa bisnis nya 0%?" right after a report that said exactly
# that) instead of scoring it low-confidence in isolation and dead-ending at
# END before n8_qa (which already has its own, larger history window — see
# qa.py's _MAX_HISTORY) ever gets a chance to actually answer it. Small on
# purpose: this fires on every single turn, unlike qa_node which only runs
# for EXPLAIN, so keep it cheap.
_MAX_HISTORY = 6

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

Prior conversation turns (if any) are included before the current message —
use them. A message that looks ambiguous in isolation, like "kenapa bisnis
nya 0%?" or "kenapa segitu?", is a confident, ordinary explain (follow-up
about the prior answer) once you can see what "bisnis"/"segitu" refers to in
that history — do NOT drop confidence below 0.6 for that reason alone.

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

Respond with a single JSON object matching this shape, and nothing else:
{"intent": "<one of the values above>", "entities": {...}, "confidence": <0-1>,
"clarification_question": "<string or null>"}
"""


@lru_cache(maxsize=1)
def _build_chain():
    """Bind the structured output schema once. Cached because LLM client
    bindings are expensive to rebuild per invocation.

    method is picked per provider, NOT a single universal choice — the two
    working methods aren't interchangeable across providers for this exact
    schema:

    - sumopod: method="function_calling". with_structured_output()'s
      default ("json_schema", OpenAI's newer strict response_format) 400s
      outright on SumoPod's proxy regardless of any other setting ("This
      response_format type is unavailable now") — a proxy-level gap.
      function_calling uses a forced tool_choice instead, which DeepSeek's
      default "thinking" mode itself rejects ("Thinking mode does not
      support this tool_choice") — fixed at the client level, not here: see
      get_chat_model()'s extra_body={"thinking": {"type": "disabled"}} for
      this provider (api-docs.deepseek.com/guides/thinking_mode). With
      thinking disabled, function_calling works and is schema-validated via
      the tool-call arguments themselves — more reliable than
      method="json_mode" (confirmed live: json_mode returned syntactically
      malformed JSON at least once; function_calling has produced none).
    - gemini: method="json_schema" (the with_structured_output() default).
      function_calling breaks entities extraction here specifically —
      confirmed live: IntentDecision.entities is `dict[str, Any]`, and
      Gemini's function-calling schema translation can't represent that
      openly-typed a field ("Key '$defs' is not supported in schema,
      ignoring"), so entities silently comes back {} every time under that
      method. json_schema handles it correctly, as it always has."""
    llm = get_chat_model()
    method = "function_calling" if settings.LLM_PROVIDER == "sumopod" else "json_schema"
    return llm.with_structured_output(IntentDecision, method=method)


def _sector_candidates(entities: dict[str, Any]) -> list[str]:
    """The intent LLM isn't schema-constrained for entities (free-form
    dict), so a stated sector shows up under wildly inconsistent key names
    across calls — observed live, all for the same "bank atau telco gitu"
    phrasing: {"sector": "bank"}, {"sectors": ["banking", "telecommunications"]},
    {"sector_preference": ["bank", "telco"]}. Chasing each new key name
    one-by-one is a losing game, so this matches any key containing "sector"
    (covers all three observed variants, and any future one like
    "sector_focus") rather than an exact-name allowlist.

    Deliberately NOT a scan of every entity value: callers rely on knowing
    whether a sector was stated AT ALL (this function's non-emptiness),
    separately from whether it resolved to real tickers — a *stated but
    unmapped* sector (e.g. "perkebunan") must NOT fall through to the
    generic blue-chip basket, since ASII/TLKM/etc. aren't plantation stocks
    and that would quietly answer a different question. Scanning unrelated
    keys like risk_profile/business_name would blur that line; keying off
    "sector" in the field name keeps it precise to what was actually about
    a sector."""
    candidates: list[str] = []
    for key, value in entities.items():
        if "sector" not in key.lower():
            continue
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, list):
            candidates.extend(v for v in value if isinstance(v, str))
    return candidates


def _resolve_sector_tickers(candidates: list[str]) -> list[str]:
    tickers: list[str] = []
    for candidate in candidates:
        for t in sector_to_tickers(candidate):
            if t not in tickers:
                tickers.append(t)
    return tickers


def _last_user_text(state: AgentState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return m.content
    return ""


def _history(state: AgentState) -> list[BaseMessage]:
    """Prior human/AI turns, excluding the current (last) human message —
    same pattern as qa.py's _history(), just a smaller window (see
    _MAX_HISTORY)."""
    messages = [m for m in state.get("messages") or []
                if isinstance(m, (HumanMessage, AIMessage))]
    if messages and isinstance(messages[-1], HumanMessage):
        messages = messages[:-1]
    return messages[-_MAX_HISTORY:]


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
            *_history(state),
            HumanMessage(content=user_text),
        ])
    except Exception as exc:
        log.exception("intent_node: classification failed: %s", exc)
        # _needs_clarification routes straight to END with no further nodes,
        # and build_chat_reply's "N1 couldn't classify" rule just relays
        # messages[-1] — without a message appended here, that's still the
        # user's own HumanMessage, so the reply silently echoes their input
        # back at them instead of surfacing that something actually broke.
        return {
            "intent": Intent.UNKNOWN.value,
            "entities": {},
            "_needs_clarification": True,
            "errors": [*state.get("errors", []),
                       {"node": "intent", "reason": str(exc)}],
            "messages": [*state.get("messages", []), AIMessage(
                content="Maaf, saya lagi mengalami gangguan teknis dan belum "
                        "bisa memproses pesan Anda. Coba kirim ulang sebentar "
                        "lagi.")],
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
        sector_candidates = _sector_candidates(entities)
        if sector_candidates:
            # A stated sector ("bank atau telco gitu") resolves to that
            # sector's real constituents — NOT the generic blue-chip basket
            # below, which would ignore what the user actually asked for
            # (ASII/TLKM aren't bank stocks). Without this, Layer 0's stocks
            # leg falls back to the baseline stand-in (engine.py's
            # `effective_stock_score`), producing an uninformative
            # baseline-vs-baseline 50/50 split no matter the user's request.
            #
            # If the sector was stated but doesn't map to anything (e.g.
            # "perkebunan"), deliberately leave tickers unset rather than
            # falling through to the basket below — same reasoning as above,
            # just for the unmapped case.
            sector_tickers = _resolve_sector_tickers(sector_candidates)
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
