"""Legal & Compliance Agent (N3) — the bottleneck of the AstaLink pipeline.

Reads `allocation_plan` from AgentState, runs hybrid retrieval, prompts Gemini
for a structured LegalDecision, runs the grader, persists to audit_log, returns
a partial state update with `legal_status` and `legal_citations`."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.legal.grader import grade_decision
from app.agents.legal.retriever import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
)
from app.agents.legal.schemas import Chunk, LegalDecision, LegalStatus
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import record_legal_status, track_node_duration
from app.core.supabase_admin import get_admin_client

logger = logging.getLogger(__name__)

BM25_PATH = Path(__file__).parent.parent.parent.parent / "data" / "bm25_index.pkl"

LEGAL_SYSTEM = """\
You are an Indonesian financial-regulation compliance officer. Given a
proposed asset allocation and retrieved regulation chunks, decide if the
allocation is approved, partial (some legs blocked), or rejected.

Default to APPROVED. Only move to "partial" or "rejected" when a retrieved
chunk EXPLICITLY states a rule, limit, or prohibition that actually applies
to one of the proposed tickers or to the allocation as a whole (e.g. an
ownership cap, a sector ban, a concentration limit with a stated threshold).
General background information, market commentary, or context that mentions
a topic without stating a concrete rule is NOT grounds for a restriction —
if nothing in the retrieved chunks imposes an actual, applicable restriction,
return "approved" with an EMPTY citations list. Do not manufacture a
citation, invent a restriction, or stretch a general remark into a formal
rule just to justify caution — an allocation with no applicable regulation
is legitimately approved, not suspicious, and citations are only required to
justify "partial"/"rejected", never to justify "approved".

When you DO cite a chunk to justify "partial" or "rejected", cite it by
chunk_id, pasal, and ayat, and the citation's "span" must be an excerpt or
faithful paraphrase of what that chunk actually says — never invent pasal
references, and never cite a chunk for a rule it doesn't actually state.

If a citation's regulation explicitly bans specific tickers from the proposed
allocation, list them in that citation's "forbidden_tickers". If a citation
caps (rather than bans) a specific ticker's weight, list it in
"partial_tickers" as {"TICKER": max_weight_as_fraction}. Only include tickers
that are IN THE PROPOSED ALLOCATION — never invent tickers not mentioned in
the input. Leave both empty ([] / {}) when a citation doesn't concern a
specific ticker.

Return STRICT JSON matching this schema:
{
  "status": "approved" | "partial" | "rejected",
  "reasoning": "...",
  "citations": [
    {"source": "...", "pasal": "...", "ayat": "..." | null, "chunk_id": "...", "span": "...",
     "forbidden_tickers": ["..."], "partial_tickers": {"TICKER": 0.1}}
  ],
  "alternative_actions": ["...", ...]   // ALWAYS include alternatives if status != approved
}

"citations" MUST be [] when status is "approved" and no retrieved chunk
imposes an actual restriction on this allocation.
"""


@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    bm25: BM25Retriever | None = None
    if BM25_PATH.exists():
        bm25 = BM25Retriever.load(BM25_PATH)
    else:
        logger.warning("legal: BM25 index missing at %s — running dense-only", BM25_PATH)
    return HybridRetriever(bm25=bm25, dense=DenseRetriever())


def _build_query(plan: dict[str, Any]) -> str:
    weights = plan.get("weights", [])
    parts = [f"{w.get('ticker', '?')}: {w.get('weight', 0)}" for w in weights]
    return (
        "Periksa legalitas alokasi berikut terhadap regulasi OJK / UUPM / perpajakan: "
        + ", ".join(parts)
        + f". Jumlah cash: {plan.get('cash', 0)}."
    )


def _format_chunks(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"[chunk_id={c.chunk_id} | source={c.source} | pasal={c.pasal} | ayat={c.ayat}]\n{c.text}"
        for c in chunks
    )


def _generate_decision(plan: dict[str, Any], chunks: list[Chunk]) -> LegalDecision:
    """Prompt Gemini for a structured LegalDecision. Returns a parsed
    LegalDecision; raises ValueError on malformed JSON."""
    llm = get_chat_model()
    user = (
        f"PROPOSED ALLOCATION:\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
        f"RETRIEVED REGULATION CHUNKS:\n{_format_chunks(chunks)}\n\n"
        f"Decide and return JSON only."
    )
    resp = llm.invoke([SystemMessage(content=LEGAL_SYSTEM), HumanMessage(content=user)])
    text = extract_text(resp.content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Legal LLM returned non-JSON: {text!r}") from exc
    return LegalDecision.model_validate(data)


def _persist(audit_id: str, plan: dict[str, Any], decision: LegalDecision) -> None:
    """Write the decision to audit_log and allocation_plans via service-role."""
    client = get_admin_client()
    try:
        client.table("audit_log").update(
            {"payload": {"legal": decision.model_dump()}},
        ).eq("audit_id", audit_id).execute()
        client.table("allocation_plans").insert({
            "audit_id": audit_id,
            "plan_json": plan,
            "legal_status": decision.status.value,
            "legal_citations": [c.model_dump() for c in decision.citations],
        }).execute()
    except Exception as exc:  # surface but don't crash the pipeline
        logger.error("legal: failed to persist decision: %s", exc)


@track_node_duration("n3_legal")
def legal_node(state: AgentState) -> AgentState:
    """LangGraph node entry point. Returns a partial AgentState update."""
    plan = state.get("allocation_plan") or {}
    audit_id = state["audit_id"]

    try:
        retriever = get_hybrid_retriever()
        query = _build_query(plan)
        chunks = retriever.retrieve(query, k=10)

        if not chunks:
            decision = LegalDecision(
                status=LegalStatus.REJECTED,
                reasoning="Retrieval returned no regulation chunks; cannot ground a decision.",
            )
            _persist(audit_id, plan, decision)
            return {
                "legal_status": decision.status,
                "legal_citations": [],
                "errors": [*state.get("errors", []), {"node": "legal", "reason": "empty_retrieval"}],
            }

        decision = _generate_decision(plan, chunks)
        decision = grade_decision(decision, chunks)
        record_legal_status(decision.status.value)
        _persist(audit_id, plan, decision)

        return {
            "legal_status": decision.status,
            "legal_citations": [c.model_dump() for c in decision.citations],
        }

    except Exception as exc:
        logger.exception("legal_node failed: %s", exc)
        return {
            "legal_status": LegalStatus.REJECTED,
            "legal_citations": [],
            "errors": [*state.get("errors", []), {"node": "legal", "reason": str(exc)}],
        }
