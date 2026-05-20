from unittest.mock import MagicMock, patch
from app.agents.legal.grader import grade_decision
from app.agents.legal.schemas import Chunk, Citation, LegalDecision, LegalStatus


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(text=text, source="OJK", pasal="3", ayat="1",
                 doc_hash="h", chunk_id=chunk_id)


def test_grader_keeps_citation_when_span_present_in_chunk() -> None:
    chunks = [_chunk("OJK-3-1-_-0", "Investor Ritel dilarang membeli saham rokok.")]
    decision = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="Sektor rokok dibatasi.",
        citations=[Citation(source="OJK", pasal="3", ayat="1",
                            chunk_id="OJK-3-1-_-0", span="dilarang membeli")],
    )

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": true, "evidence": "dilarang membeli"}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    assert len(graded.citations) == 1
    assert graded.status == LegalStatus.PARTIAL


def test_grader_drops_citation_when_span_not_in_chunk() -> None:
    chunks = [_chunk("OJK-3-1-_-0", "Investor Ritel dilarang membeli saham rokok.")]
    decision = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="...",
        citations=[Citation(source="OJK", pasal="3", ayat="1",
                            chunk_id="OJK-3-1-_-0", span="hadiah saham gratis")],
    )

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": false, "evidence": ""}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    assert len(graded.citations) == 0
    # All citations dropped → forced rejection
    assert graded.status == LegalStatus.REJECTED
    assert "ground" in graded.reasoning.lower() or "basis" in graded.reasoning.lower()


def test_grader_drops_citation_when_chunk_id_unknown() -> None:
    """Cited chunk_id that wasn't in retrieval is structural hallucination —
    drop it WITHOUT calling the LLM (no need to ask, it's wrong by definition)."""
    chunks = [_chunk("OJK-3-1-_-0", "...")]
    decision = LegalDecision(
        status=LegalStatus.APPROVED,
        reasoning="...",
        citations=[
            Citation(source="OJK", pasal="3", ayat="1", chunk_id="OJK-3-1-_-0", span="..."),
            Citation(source="OJK", pasal="99", ayat="1", chunk_id="OJK-99-1-_-0", span="..."),
        ],
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": true, "evidence": "..."}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    # The unknown-chunk citation must be dropped; the known one survives
    assert len(graded.citations) == 1
    assert graded.citations[0].chunk_id == "OJK-3-1-_-0"
