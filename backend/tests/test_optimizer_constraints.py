from app.agents.optimizer.constraints import (
    forbidden_from_citations,
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
