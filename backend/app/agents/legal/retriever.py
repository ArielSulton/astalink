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
from app.core.pinecone import DEFAULT_NAMESPACE, get_index


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
    """Pinecone-backed dense retrieval via Pinecone's hosted integrated
    embedding model (multilingual-e5-large, configured on the index itself).
    Pinecone embeds the query text server-side, so no separate embedding
    call is needed here."""

    def retrieve(self, query: str, k: int = 10) -> list[Chunk]:
        index = get_index()
        result = index.search(
            namespace=DEFAULT_NAMESPACE,
            query={"top_k": k, "inputs": {"text": query}},
        )

        out: list[Chunk] = []
        for hit in result.result.hits:
            fields = hit.fields
            out.append(
                Chunk(
                    text=fields.get("text", ""),
                    source=fields.get("source", "unknown"),
                    pasal=fields.get("pasal"),
                    ayat=fields.get("ayat"),
                    page=fields.get("page"),
                    doc_hash=fields.get("doc_hash", ""),
                    chunk_id=hit._id,
                    score=float(hit._score),
                )
            )
        return out


class HybridRetriever:
    """Reciprocal Rank Fusion of dense + sparse retrievers.

    RRF score for a chunk c: Σ over each retriever 1 / (k_rrf + rank(c)).
    Canonical k_rrf = 60. Chunks in both rankings get added scores; chunks
    in only one still contribute a single term."""

    K_RRF = 60

    def __init__(
        self,
        bm25: BM25Retriever | None,
        dense: DenseRetriever,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense

    def retrieve(self, query: str, k: int = 10) -> list[Chunk]:
        dense_hits = self._dense.retrieve(query, k=k * 2)
        sparse_hits = self._bm25.retrieve(query, k=k * 2) if self._bm25 else []

        fused: dict[str, tuple[float, Chunk]] = {}
        for rank, chunk in enumerate(dense_hits):
            fused[chunk.chunk_id] = (1.0 / (self.K_RRF + rank + 1), chunk)
        for rank, chunk in enumerate(sparse_hits):
            score, c = fused.get(chunk.chunk_id, (0.0, chunk))
            fused[chunk.chunk_id] = (score + 1.0 / (self.K_RRF + rank + 1), c)

        ranked = sorted(fused.values(), key=lambda pair: pair[0], reverse=True)[:k]
        return [c.model_copy(update={"score": s}) for s, c in ranked]
