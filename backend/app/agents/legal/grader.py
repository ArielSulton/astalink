"""Citation grader: the anti-hallucination gate of the Legal Agent.

For each Citation in a draft LegalDecision, ask Gemini whether the cited span
actually appears in the cited chunk's text. Drop citations that fail. If every
citation is dropped, force the decision to status=rejected with a reasoning
explaining the lack of grounded basis."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.legal.schemas import Chunk, Citation, LegalDecision, LegalStatus
from app.core.gemini import get_chat_model

logger = logging.getLogger(__name__)

GRADER_SYSTEM = """\
You are a strict citation auditor for Indonesian financial regulation.
You will receive (1) a chunk of regulatory text and (2) a span of text that an
agent claims appears verbatim (or near-verbatim) inside the chunk.

Return ONLY a JSON object: {"grounded": <true|false>, "evidence": "<exact substring of chunk text supporting the claim, or empty string>"}.

A citation is GROUNDED iff the meaning of the span is supported by an exact or
near-exact substring of the chunk. Trivial paraphrase (e.g. word order) is OK;
adding facts not in the chunk is NOT.
Return false if uncertain. Never fabricate evidence.
"""


def _is_grounded(chunk: Chunk, citation: Citation) -> bool:
    llm = get_chat_model()
    user = (
        f"CHUNK TEXT:\n{chunk.text}\n\n"
        f"CLAIMED SPAN: {citation.span!r}\n\n"
        f"Is the claimed span grounded in the chunk text? Respond JSON only."
    )
    resp = llm.invoke([SystemMessage(content=GRADER_SYSTEM), HumanMessage(content=user)])
    try:
        data = json.loads(resp.content)
        return bool(data.get("grounded", False))
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("grader: failed to parse LLM response %r: %s", resp.content, exc)
        return False


def grade_decision(decision: LegalDecision, retrieved: list[Chunk]) -> LegalDecision:
    """Validate every citation against the retrieved chunk corpus.
    Returns a new LegalDecision with ungrounded citations removed."""
    by_id = {c.chunk_id: c for c in retrieved}
    surviving: list[Citation] = []

    for cit in decision.citations:
        chunk = by_id.get(cit.chunk_id)
        if chunk is None:
            logger.info("grader: citation %s references unknown chunk_id, dropping", cit.chunk_id)
            continue
        if not _is_grounded(chunk, cit):
            logger.info("grader: citation %s not grounded, dropping", cit.chunk_id)
            continue
        surviving.append(cit)

    if decision.citations and not surviving:
        # Every citation failed grading → no grounded basis to support any claim.
        return decision.model_copy(update={
            "status": LegalStatus.REJECTED,
            "citations": [],
            "reasoning": "Tidak ada dasar regulasi yang dapat dibuktikan untuk klaim ini "
                         "(no grounded basis).",
        })

    return decision.model_copy(update={"citations": surviving})
