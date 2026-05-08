"""Hybrid retriever for the Legal Agent.

Combines dense Pinecone search with sparse BM25 over the same chunk corpus
and fuses results via Reciprocal Rank Fusion. Sparse retrieval is critical
for queries like "Pasal 5 ayat (2)" where exact-token match dominates."""
from __future__ import annotations

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.agents.legal.schemas import Chunk
from app.core.gemini import get_embedding_model
from app.core.pinecone import get_index


def _tokenize(text: str) -> list[str]:
    """Lowercase + word-boundary split. Keep digits and parentheses so
    'pasal 5 ayat (2)' becomes ['pasal','5','ayat','(2)']."""
    return re.findall(r"\w+|\([^)]*\)", text.lower())


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], bm25: BM25Okapi) -> None:
        self._chunks = chunks
        self._bm25 = bm25

    @classmethod
    def from_chunks(cls, chunks: list[Chunk]) -> "BM25Retriever":
        tokenized = [_tokenize(c.text) for c in chunks]
        return cls(chunks, BM25Okapi(tokenized))

    def retrieve(self, query: str, k: int = 10) -> list[Chunk]:
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(scores, self._chunks), key=lambda p: p[0], reverse=True)[:k]
        out: list[Chunk] = []
        for score, chunk in ranked:
            c = chunk.model_copy(update={"score": float(score)})
            out.append(c)
        return out

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            # Pickle the chunks + the BM25 internal state.
            pickle.dump({"chunks": [c.model_dump() for c in self._chunks],
                         "bm25": self._bm25}, f)

    @classmethod
    def load(cls, path: Path) -> "BM25Retriever":
        with open(path, "rb") as f:
            data = pickle.load(f)
        chunks = [Chunk(**c) for c in data["chunks"]]
        return cls(chunks, data["bm25"])


class DenseRetriever:
    """Pinecone-backed dense retrieval. The chunk text is stored in metadata
    at ingest time so we can rebuild Chunks from query results without a
    second round-trip to Postgres."""

    def retrieve(self, query: str, k: int = 10) -> list[Chunk]:
        embed = get_embedding_model()
        vec = embed.embed_query(query)
        index = get_index()
        result = index.query(vector=vec, top_k=k, include_metadata=True)

        out: list[Chunk] = []
        for match in result.get("matches", []):
            md = match.get("metadata", {})
            out.append(
                Chunk(
                    text=md.get("text", ""),
                    source=md.get("source", "unknown"),
                    pasal=md.get("pasal"),
                    ayat=md.get("ayat"),
                    page=md.get("page"),
                    doc_hash=md.get("doc_hash", ""),
                    chunk_id=match["id"],
                    score=float(match.get("score", 0.0)),
                )
            )
        return out
