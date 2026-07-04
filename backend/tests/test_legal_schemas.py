from app.agents.legal.schemas import Citation, Chunk, LegalDecision, LegalStatus


def test_chunk_has_required_metadata() -> None:
    c = Chunk(
        text="Pasal 5 ayat (1): Setiap Emiten wajib...",
        source="UUPM",
        pasal="5",
        ayat="1",
        page=12,
        doc_hash="abc123",
        chunk_id="UUPM-5-1-12-0",
    )
    assert c.source == "UUPM"
    assert c.pasal == "5"


def test_citation_must_reference_a_chunk() -> None:
    cit = Citation(
        source="UUPM",
        pasal="5",
        ayat="1",
        chunk_id="UUPM-5-1-12-0",
        span="Setiap Emiten wajib",
    )
    assert cit.chunk_id == "UUPM-5-1-12-0"


def test_citation_carries_optional_forbidden_and_partial_tickers() -> None:
    """The optimizer's forbidden_tickers/partial_tickers constraints (see
    app.agents.optimizer.constraints) are only as real as what the Legal LLM
    can actually put on a citation — these fields are how it does that."""
    cit_default = Citation(
        source="UUPM", pasal="5", ayat="1",
        chunk_id="UUPM-5-1-12-0", span="Setiap Emiten wajib",
    )
    assert cit_default.forbidden_tickers == []
    assert cit_default.partial_tickers == {}

    cit_explicit = Citation(
        source="OJK", pasal="3", ayat="1",
        chunk_id="OJK-3-1-_-0", span="dilarang membeli saham rokok",
        forbidden_tickers=["GGRM", "HMSP"],
        partial_tickers={"UNVR": 0.1},
    )
    assert cit_explicit.forbidden_tickers == ["GGRM", "HMSP"]
    assert cit_explicit.partial_tickers == {"UNVR": 0.1}
    # model_dump() is what legal_node._persist / optimizer/node._build_inputs
    # actually consume — verify the keys survive serialization.
    dumped = cit_explicit.model_dump()
    assert dumped["forbidden_tickers"] == ["GGRM", "HMSP"]
    assert dumped["partial_tickers"] == {"UNVR": 0.1}


def test_legal_decision_carries_status_citations_and_alternatives() -> None:
    d = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="Sektor tembakau dibatasi untuk investor ritel.",
        citations=[
            Citation(
                source="OJK",
                pasal="3",
                ayat="2",
                chunk_id="OJK-3-2-1-0",
                span="dibatasi",
            )
        ],
        alternative_actions=["Pertimbangkan ETF non-tembakau"],
    )
    assert d.status == "partial"
    assert len(d.citations) == 1
    assert "ETF" in d.alternative_actions[0]


def test_legal_decision_status_enum_values() -> None:
    """LegalStatus values must match the enum defined in app.agents.state
    so the LangGraph state in Phase 2 can consume them directly."""
    from app.agents.state import LegalStatus as StateLegalStatus
    assert LegalStatus.APPROVED.value == StateLegalStatus.APPROVED.value
    assert LegalStatus.REJECTED.value == StateLegalStatus.REJECTED.value
