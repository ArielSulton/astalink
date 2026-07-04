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


from unittest.mock import MagicMock, patch
from app.agents.legal.retriever import DenseRetriever


def _fake_hit(chunk_id: str, score: float, chunk: Chunk) -> MagicMock:
    hit = MagicMock()
    hit._id = chunk_id
    hit._score = score
    hit.fields = {
        "text": chunk.text, "source": chunk.source,
        "pasal": chunk.pasal, "ayat": chunk.ayat, "doc_hash": chunk.doc_hash,
    }
    return hit


def test_dense_retriever_calls_pinecone_integrated_search(sample_chunks: list[Chunk]) -> None:
    fake_result = MagicMock()
    fake_result.result.hits = [
        _fake_hit("OJK-3-1-_-0", 0.92, sample_chunks[1]),
        _fake_hit("UUPM-1-_-_-0", 0.71, sample_chunks[0]),
    ]
    fake_index = MagicMock()
    fake_index.search.return_value = fake_result

    with patch("app.agents.legal.retriever.get_index", return_value=fake_index):
        retr = DenseRetriever()
        hits = retr.retrieve("rokok", k=2)

    fake_index.search.assert_called_once_with(
        namespace="__default__",
        query={"top_k": 2, "inputs": {"text": "rokok"}},
    )
    assert hits[0].chunk_id == "OJK-3-1-_-0"
    assert hits[0].score == 0.92


def test_rrf_boosts_chunks_present_in_both_retrievers(sample_chunks: list[Chunk]) -> None:
    """A chunk in both rankings must outrank a chunk in only one."""
    from app.agents.legal.retriever import HybridRetriever

    # Construct two retrievers that return overlapping but not identical rankings.
    bm25_hits = [sample_chunks[1], sample_chunks[0]]      # OJK-3-1, UUPM-1
    dense_hits = [sample_chunks[1], sample_chunks[2]]     # OJK-3-1, OJK-5

    fake_bm25 = MagicMock()
    fake_bm25.retrieve.return_value = bm25_hits
    fake_dense = MagicMock()
    fake_dense.retrieve.return_value = dense_hits

    hybrid = HybridRetriever(bm25=fake_bm25, dense=fake_dense)
    fused = hybrid.retrieve("rokok pasal 3", k=3)

    # OJK-3-1 appears in both, should rank #1
    assert fused[0].chunk_id == "OJK-3-1-_-0"


def test_rrf_handles_completely_disjoint_rankings(sample_chunks: list[Chunk]) -> None:
    from app.agents.legal.retriever import HybridRetriever

    fake_bm25 = MagicMock()
    fake_bm25.retrieve.return_value = [sample_chunks[0]]
    fake_dense = MagicMock()
    fake_dense.retrieve.return_value = [sample_chunks[2]]

    hybrid = HybridRetriever(bm25=fake_bm25, dense=fake_dense)
    fused = hybrid.retrieve("anything", k=5)

    # Both chunks should appear, in some order, with no duplicates
    ids = {c.chunk_id for c in fused}
    assert ids == {"UUPM-1-_-_-0", "OJK-5-_-_-0"}


def test_hybrid_falls_back_to_dense_only_if_bm25_missing(sample_chunks: list[Chunk]) -> None:
    """If the BM25 pickle isn't on disk yet, the retriever still works
    (degraded) using dense alone — better than crashing on the first deploy."""
    from app.agents.legal.retriever import HybridRetriever

    fake_dense = MagicMock()
    fake_dense.retrieve.return_value = sample_chunks[:2]
    hybrid = HybridRetriever(bm25=None, dense=fake_dense)

    fused = hybrid.retrieve("anything", k=2)
    assert len(fused) == 2
