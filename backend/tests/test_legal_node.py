import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from app.agents.legal.node import legal_node
from app.agents.legal.schemas import Chunk, Citation, LegalDecision, LegalStatus
from app.agents.state import new_state


def test_legal_node_writes_status_and_citations_into_agentstate() -> None:
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 0.5}, {"ticker": "GGRM", "weight": 0.5}],
        "cash": 10_000_000,
    }

    fake_chunks = [
        Chunk(text="Investor Ritel dilarang membeli saham rokok.",
              source="OJK", pasal="3", ayat="1", doc_hash="h", chunk_id="OJK-3-1-_-0"),
    ]
    fake_decision = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="GGRM (rokok) dibatasi.",
        citations=[Citation(source="OJK", pasal="3", ayat="1",
                            chunk_id="OJK-3-1-_-0", span="dilarang membeli")],
        alternative_actions=["Realokasi 50% dari GGRM ke ETF konsumsi non-rokok."],
    )

    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = fake_chunks
    fake_admin = MagicMock()  # supabase admin client

    with patch("app.agents.legal.node.get_hybrid_retriever", return_value=fake_retriever), \
         patch("app.agents.legal.node._generate_decision", return_value=fake_decision), \
         patch("app.agents.legal.node.grade_decision", return_value=fake_decision), \
         patch("app.agents.legal.node.get_admin_client", return_value=fake_admin):
        new_substate = legal_node(state)

    assert new_substate["legal_status"] == LegalStatus.PARTIAL
    assert len(new_substate["legal_citations"]) == 1
    assert new_substate["legal_citations"][0]["pasal"] == "3"
    fake_admin.table.assert_called()  # audit_log write happened


def test_legal_node_falls_back_to_rejected_on_retrieval_failure() -> None:
    """If retrieval crashes or returns empty, we MUST NOT pass through to a
    naive LLM call — that's the textbook hallucination scenario."""
    state = new_state()
    state["allocation_plan"] = {"weights": [], "cash": 0}

    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = []
    fake_admin = MagicMock()

    with patch("app.agents.legal.node.get_hybrid_retriever", return_value=fake_retriever), \
         patch("app.agents.legal.node.get_admin_client", return_value=fake_admin):
        new_substate = legal_node(state)

    assert new_substate["legal_status"] == LegalStatus.REJECTED
    # Reasoning should explain why
    assert new_substate.get("errors") or "retrieval" in str(new_substate).lower()


def test_legal_node_accepts_citation_with_no_specific_pasal() -> None:
    """Live incident reproduction: a retrieved chunk has no specific pasal
    (a general/preamble provision), Gemini cites it with pasal=null in its
    raw JSON, and this must parse successfully — not crash into a
    misleading LegalStatus.REJECTED via the node's broad except."""
    state = new_state()
    state["allocation_plan"] = {
        "weights": [{"ticker": "BBCA", "weight": 1.0}],
        "cash": 20_000_000,
    }

    fake_chunks = [
        Chunk(text="Ketentuan umum mengenai investasi ritel.",
              source="UUPM", pasal=None, ayat=None, doc_hash="h", chunk_id="UUPM-_-_-1-0"),
    ]
    fake_retriever = MagicMock()
    fake_retriever.retrieve.return_value = fake_chunks

    raw_llm_json = json.dumps({
        "status": "approved",
        "reasoning": "Alokasi sesuai ketentuan umum investasi ritel.",
        "citations": [{
            "source": "UUPM", "pasal": None, "ayat": None,
            "chunk_id": "UUPM-_-_-1-0", "span": "Ketentuan umum",
            "forbidden_tickers": [], "partial_tickers": {},
        }],
        "alternative_actions": [],
    })
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content=raw_llm_json)
    fake_admin = MagicMock()

    with patch("app.agents.legal.node.get_hybrid_retriever", return_value=fake_retriever), \
         patch("app.agents.legal.node.get_chat_model", return_value=fake_llm), \
         patch("app.agents.legal.node.grade_decision", side_effect=lambda d, chunks: d), \
         patch("app.agents.legal.node.get_admin_client", return_value=fake_admin):
        new_substate = legal_node(state)

    assert new_substate["legal_status"] == LegalStatus.APPROVED
    assert new_substate["legal_citations"][0]["pasal"] is None
    assert not new_substate.get("errors")
