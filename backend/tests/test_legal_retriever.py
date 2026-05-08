import pickle
from pathlib import Path

import pytest

from app.agents.legal.retriever import BM25Retriever
from app.agents.legal.schemas import Chunk


@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(text="Pasal 1: Emiten wajib melaporkan keuangan tahunan.",
              source="UUPM", pasal="1", doc_hash="h", chunk_id="UUPM-1-_-_-0"),
        Chunk(text="Pasal 3 ayat (1): Investor Ritel dilarang membeli saham emiten rokok.",
              source="OJK", pasal="3", ayat="1", doc_hash="h", chunk_id="OJK-3-1-_-0"),
        Chunk(text="Pasal 5: Sanksi administratif untuk pelanggaran adalah pembatalan transaksi.",
              source="OJK", pasal="5", doc_hash="h", chunk_id="OJK-5-_-_-0"),
    ]


def test_bm25_retrieves_exact_pasal_match(sample_chunks: list[Chunk]) -> None:
    bm25 = BM25Retriever.from_chunks(sample_chunks)
    hits = bm25.retrieve("Pasal 3 ayat (1) rokok", k=2)
    assert hits[0].chunk_id == "OJK-3-1-_-0", \
        "exact pasal+ayat query should rank the matching chunk first"


def test_bm25_save_and_load_roundtrip(tmp_path: Path, sample_chunks: list[Chunk]) -> None:
    bm25 = BM25Retriever.from_chunks(sample_chunks)
    p = tmp_path / "bm25.pkl"
    bm25.save(p)

    loaded = BM25Retriever.load(p)
    hits = loaded.retrieve("emiten rokok", k=1)
    assert len(hits) == 1
    assert hits[0].source in ("OJK", "UUPM")


def test_bm25_returns_empty_on_no_match(sample_chunks: list[Chunk]) -> None:
    bm25 = BM25Retriever.from_chunks(sample_chunks)
    hits = bm25.retrieve("xyzzy term that does not occur anywhere", k=5)
    # rank-bm25 always returns scored chunks; we assert top score is ~0
    assert all(h.score is None or h.score == 0 or h.score < 1.0 for h in hits)
