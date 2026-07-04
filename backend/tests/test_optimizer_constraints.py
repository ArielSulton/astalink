from app.agents.optimizer.constraints import (
    forbidden_from_citations,
    partial_tickers_from_citations,
    sector_caps_from_citations,
)


def test_forbidden_tickers_extracted_from_legal_citations() -> None:
    """A citation with `forbidden_tickers` metadata in payload must surface."""
    citations = [
        {"source": "OJK", "pasal": "3", "ayat": "1",
         "chunk_id": "x", "span": "dilarang membeli",
         "forbidden_tickers": ["GGRM", "HMSP"]},
        {"source": "OJK", "pasal": "5", "ayat": "1",
         "chunk_id": "y", "span": "sanksi"},
    ]
    assert forbidden_from_citations(citations) == ["GGRM", "HMSP"]


def test_sector_caps_inferred_from_pasal_when_explicit_field_absent() -> None:
    """Fallback: if a citation mentions a sector by name, cap it at 0%."""
    citations = [
        {"source": "OJK", "pasal": "3", "ayat": "1",
         "chunk_id": "x", "span": "saham emiten rokok dilarang"},
    ]
    caps = sector_caps_from_citations(citations)
    assert caps.get("tobacco") == 0.0


def test_no_constraints_when_citations_empty() -> None:
    assert forbidden_from_citations([]) == []
    assert sector_caps_from_citations([]) == {}


def test_partial_tickers_extracted_and_merged_across_citations() -> None:
    """Mirrors test_forbidden_tickers_extracted_from_legal_citations — same
    aggregation shape, different constraint type (cap, not ban)."""
    citations = [
        {"source": "OJK", "pasal": "4", "ayat": "1",
         "chunk_id": "x", "span": "dibatasi maksimal 10%",
         "partial_tickers": {"UNVR": 0.1}},
        {"source": "OJK", "pasal": "6", "ayat": "2",
         "chunk_id": "y", "span": "dibatasi maksimal 5%",
         "partial_tickers": {"INDF": 0.05}},
        {"source": "OJK", "pasal": "9", "ayat": "1",
         "chunk_id": "z", "span": "sanksi administratif"},  # no partial_tickers key
    ]
    assert partial_tickers_from_citations(citations) == {"UNVR": 0.1, "INDF": 0.05}


def test_partial_tickers_takes_the_stricter_cap_on_conflict() -> None:
    """If two citations disagree on the same ticker's cap, the tighter
    (lower) cap must win — legal constraints are never relaxed by picking
    the more permissive of two conflicting rules."""
    citations = [
        {"source": "OJK", "pasal": "4", "ayat": "1",
         "chunk_id": "x", "span": "a", "partial_tickers": {"UNVR": 0.1}},
        {"source": "OJK", "pasal": "6", "ayat": "1",
         "chunk_id": "y", "span": "b", "partial_tickers": {"UNVR": 0.05}},
    ]
    assert partial_tickers_from_citations(citations) == {"UNVR": 0.05}


def test_no_partial_tickers_when_citations_empty() -> None:
    assert partial_tickers_from_citations([]) == {}
