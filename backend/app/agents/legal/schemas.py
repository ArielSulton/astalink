"""Schemas for the Legal Agent (N3).

LegalStatus is re-exported from app.agents.state so the graph state and the
agent output share a single source of truth — both Phase 1 (this module) and
Phase 2 (graph wiring) import from here."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.state import LegalStatus

__all__ = ["Chunk", "Citation", "LegalDecision", "LegalStatus"]


class Chunk(BaseModel):
    """A chunk of regulatory text retrieved from the corpus.

    `chunk_id` is deterministic (`{source}-{pasal}-{ayat}-{page}-{idx}`) so we
    can join Pinecone hits with BM25 hits during fusion."""
    text: str
    source: str
    pasal: str | None = None
    ayat: str | None = None
    page: int | None = None
    doc_hash: str
    chunk_id: str
    score: float | None = None  # populated post-retrieval


class Citation(BaseModel):
    """A specific pasal/ayat reference cited by the LLM.

    `chunk_id` ties the citation back to the retrieved chunk so the grader can
    verify it. `span` is the literal substring the LLM claims supports its
    reasoning — the grader checks this is present in the chunk text.

    `forbidden_tickers`/`partial_tickers` let a citation carry the specific
    instruments a regulation bans or caps — app.agents.optimizer.constraints
    aggregates these across all citations into solver constraints.

    `pasal` is nullable — mirrors Chunk.pasal, since a citation can point at
    a general/preamble provision that has no specific article number."""
    source: str
    pasal: str | None = None
    ayat: str | None = None
    chunk_id: str
    span: str
    forbidden_tickers: list[str] = Field(default_factory=list)
    partial_tickers: dict[str, float] = Field(
        default_factory=dict,
        description="ticker → max-allowed weight (e.g. 0.1 for partial-only).",
    )


class LegalDecision(BaseModel):
    status: LegalStatus
    reasoning: str = Field(..., description="Plain-language explanation citing pasal references.")
    citations: list[Citation] = Field(default_factory=list)
    alternative_actions: list[str] = Field(
        default_factory=list,
        description="If status is partial/rejected, concrete alternatives (never bare 'no').",
    )
