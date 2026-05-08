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
