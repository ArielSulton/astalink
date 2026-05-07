# AstaLink Phase 1 — Legal Agent + RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Phase 0 must be complete before starting.**

**Goal:** Build the Legal & Compliance Agent (N3) — the bottleneck of the AstaLink pipeline. It receives a proposed allocation, retrieves grounded passages from regulatory PDFs (OJK / UUPM / perpajakan / banking) using a hybrid Pinecone+BM25 retriever fused via RRF, asks Gemini to produce a structured legal decision with cited pasal references, then runs a separate LLM Grader pass to drop any citation that isn't actually supported by the retrieved chunks. Without grounding, no claim. The phase ships a standalone API (`POST /api/v1/legal/check`) that lets us validate the agent in isolation before Phase 2 wires it into the graph, plus a DeepEval suite that gates merges on a hallucination metric ≥ 0.95.

**Architecture:**
- **Ingestion** (`backend/scripts/ingest_regulations.py`) is run once per regulation: parses PDF into pasal-aware chunks, embeds via Gemini, pushes to Pinecone with `{source, pasal, ayat, page}` metadata, appends raw text+metadata to a serialized BM25 index on disk, and inserts a row into `regulation_documents`.
- **Retrieval** (`app/agents/legal/retriever.py`): two parallel calls (dense via Pinecone, sparse via BM25), fused with Reciprocal Rank Fusion. Sparse retrieval is critical for exact "Pasal X ayat (Y)" queries that dense embeddings often blur.
- **Generation + Grading** (`app/agents/legal/node.py`, `grader.py`): Gemini produces a structured `LegalDecision` with citations. The grader pass takes each citation and asks Gemini "does chunk text actually contain this pasal/ayat? Yes/No + span." Citations the grader can't ground are dropped; if every citation is dropped, the decision is forced to `rejected` with reason "no grounded basis."
- **Persistence:** every decision writes to `audit_log` keyed by `audit_id`.
- **API surface:** `POST /api/v1/legal/check` accepts `{audit_id, allocation_plan, workspace_id}`, returns `LegalDecision`. Phase 2 will reuse the same node code from inside the graph.

**Tech Stack:** Gemini chat + embeddings (from Phase 0 singletons), Pinecone v5 (dense), `rank-bm25` (sparse), `pypdf` (PDF parsing), `langchain-pinecone` (vector store wrapper), DeepEval (faithfulness + hallucination metrics), pytest with async + fixture-based mocks.

**Scope cuts (hackathon discipline):** ingest only 3 documents to start (one OJK regulation, UUPM excerpt, one perpajakan rule); chunk size = 800 chars with 100 overlap (one tunable knob, don't over-engineer); dense-only fallback path for retriever if BM25 file missing (graceful degradation); DeepEval runs as a `--slow` pytest marker so it can be skipped during fast inner-loop dev.

---

## File Structure

```
astalink/
├── backend/
│   ├── data/
│   │   ├── regulations/                      # CREATE: source PDFs (gitignored — too large; checked-in samples allowed if <1MB each)
│   │   │   └── README.md                     # CREATE: where to obtain PDFs, checksums
│   │   ├── bm25_index.pkl                    # CREATE at ingest time (gitignored)
│   │   └── chunks.jsonl                      # CREATE at ingest time, optional cache for re-embedding
│   ├── scripts/
│   │   └── ingest_regulations.py             # CREATE: end-to-end ingest CLI
│   ├── app/
│   │   ├── agents/
│   │   │   └── legal/
│   │   │       ├── __init__.py               # CREATE
│   │   │       ├── schemas.py                # CREATE: LegalDecision, Citation, Chunk pydantic models
│   │   │       ├── chunker.py                # CREATE: pasal-aware PDF chunker
│   │   │       ├── retriever.py              # CREATE: hybrid retriever with RRF
│   │   │       ├── grader.py                 # CREATE: citation grader (anti-hallucination)
│   │   │       └── node.py                   # CREATE: LangGraph node + standalone runner
│   │   └── api/
│   │       └── v1/
│   │           ├── legal.py                  # CREATE: POST /api/v1/legal/check
│   │           └── router.py                 # MODIFY: register legal router
│   └── tests/
│       ├── test_legal_chunker.py             # CREATE
│       ├── test_legal_schemas.py             # CREATE
│       ├── test_legal_retriever.py           # CREATE: dense, sparse, RRF fusion
│       ├── test_legal_grader.py              # CREATE
│       ├── test_legal_node.py                # CREATE
│       ├── test_legal_endpoint.py            # CREATE
│       ├── test_legal_hallucination.py       # CREATE: DeepEval suite (slow marker)
│       ├── data/
│       │   ├── tiny_ojk_fixture.txt          # CREATE: synthetic regulation text for unit tests
│       │   └── eval_prompts.json             # CREATE: 20 hand-labeled prompts for DeepEval
│       └── conftest.py                       # MODIFY: add fixtures for fake retriever, fake LLM
├── .gitignore                                # MODIFY: ignore backend/data/regulations/*.pdf, *.pkl
└── pyproject.toml                            # MODIFY: register `--slow` pytest marker
```

---

## Task Group A — Schemas & Chunker

### Task A1: Define LegalDecision / Citation / Chunk schemas

**Files:**
- Create: `backend/app/agents/legal/__init__.py` (empty)
- Create: `backend/app/agents/legal/schemas.py`
- Create: `backend/tests/test_legal_schemas.py`

These are the contracts every other Phase 1 module imports. Defining them first prevents drift.

- [ ] **Step 1: Write failing test**

`backend/tests/test_legal_schemas.py`:

```python
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
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement schemas**

`backend/app/agents/legal/__init__.py`:

```python
```

`backend/app/agents/legal/schemas.py`:

```python
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
    reasoning — the grader checks this is present in the chunk text."""
    source: str
    pasal: str
    ayat: str | None = None
    chunk_id: str
    span: str


class LegalDecision(BaseModel):
    status: LegalStatus
    reasoning: str = Field(..., description="Plain-language explanation citing pasal references.")
    citations: list[Citation] = Field(default_factory=list)
    alternative_actions: list[str] = Field(
        default_factory=list,
        description="If status is partial/rejected, concrete alternatives (never bare 'no').",
    )
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_schemas.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/__init__.py backend/app/agents/legal/schemas.py backend/tests/test_legal_schemas.py
git commit -m "feat(legal): add Chunk, Citation, LegalDecision schemas"
```

---

### Task A2: Pasal-aware PDF chunker

**Files:**
- Create: `backend/app/agents/legal/chunker.py`
- Create: `backend/tests/data/tiny_ojk_fixture.txt`
- Create: `backend/tests/test_legal_chunker.py`

A naïve sliding-window chunker would split mid-pasal, wrecking retrieval. Our chunker keeps "Pasal X ayat (Y)" boundaries intact: it scans for pasal markers, anchors chunks at those boundaries, and only falls back to a sliding window inside long pasal bodies.

- [ ] **Step 1: Create text fixture**

`backend/tests/data/tiny_ojk_fixture.txt`:

```
PERATURAN OTORITAS JASA KEUANGAN
NOMOR 1/POJK.04/2020

Pasal 1
Dalam Peraturan Otoritas Jasa Keuangan ini yang dimaksud dengan:
1. Emiten adalah Pihak yang melakukan Penawaran Umum.
2. Investor Ritel adalah perorangan dengan total aset di bawah Rp 5 miliar.

Pasal 2
ayat (1) Setiap Emiten wajib menyampaikan laporan keuangan tahunan paling lambat 4 bulan setelah tahun buku berakhir.
ayat (2) Laporan keuangan sebagaimana dimaksud pada ayat (1) wajib diaudit oleh Akuntan Publik.

Pasal 3
ayat (1) Investor Ritel dilarang membeli saham Emiten yang bergerak di bidang produksi rokok.
ayat (2) Pelanggaran terhadap ayat (1) dikenakan sanksi administratif berupa pembatalan transaksi.
```

- [ ] **Step 2: Write failing test**

`backend/tests/test_legal_chunker.py`:

```python
from pathlib import Path
from app.agents.legal.chunker import chunk_regulation_text

FIXTURE = Path(__file__).parent / "data" / "tiny_ojk_fixture.txt"


def test_chunker_emits_one_chunk_per_pasal_when_short() -> None:
    text = FIXTURE.read_text()
    chunks = chunk_regulation_text(
        text=text,
        source="OJK",
        doc_hash="ojk-test",
        max_chars=2000,
        overlap=100,
    )
    pasals = sorted({c.pasal for c in chunks if c.pasal})
    assert pasals == ["1", "2", "3"], f"expected pasal 1/2/3, got {pasals}"


def test_chunker_records_ayat_when_pasal_has_ayats() -> None:
    text = FIXTURE.read_text()
    chunks = chunk_regulation_text(
        text=text, source="OJK", doc_hash="ojk-test", max_chars=2000, overlap=100,
    )
    pasal_3_chunks = [c for c in chunks if c.pasal == "3"]
    assert pasal_3_chunks, "pasal 3 must produce at least one chunk"
    # Pasal 3 has ayat (1) and (2); chunker may merge them into one chunk or split
    ayat_set = {c.ayat for c in pasal_3_chunks if c.ayat}
    # Either both ayats present, or chunk covers both with ayat=None (whole pasal)
    assert ayat_set <= {"1", "2"}


def test_chunker_chunk_id_is_deterministic() -> None:
    text = FIXTURE.read_text()
    a = chunk_regulation_text(text=text, source="OJK", doc_hash="h", max_chars=2000, overlap=100)
    b = chunk_regulation_text(text=text, source="OJK", doc_hash="h", max_chars=2000, overlap=100)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_chunker_splits_long_pasal_with_overlap() -> None:
    """A pasal longer than max_chars must be split, with overlap so context
    isn't lost across boundaries."""
    long_text = "Pasal 1\n" + ("kata kunci penting " * 200) + "\nPasal 2\nIsi pasal 2."
    chunks = chunk_regulation_text(
        text=long_text, source="OJK", doc_hash="h",
        max_chars=500, overlap=100,
    )
    pasal_1 = [c for c in chunks if c.pasal == "1"]
    assert len(pasal_1) >= 2, "long pasal must be split into multiple chunks"
    # Verify overlap: consecutive chunks share at least `overlap` characters
    for prev, curr in zip(pasal_1, pasal_1[1:]):
        assert any(token in prev.text and token in curr.text for token in curr.text.split()[:20])
```

- [ ] **Step 3: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_chunker.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement chunker**

`backend/app/agents/legal/chunker.py`:

```python
"""Pasal-aware chunker for Indonesian regulatory text.

Splits text into chunks anchored on `Pasal N` boundaries. If a pasal body
exceeds `max_chars`, it is sub-split with overlap so a token near a chunk
boundary is still discoverable in both neighbors.

This is a one-pass scanner over the text; we deliberately don't build a full
parse tree because (a) Indonesian regulations have surprisingly inconsistent
formatting and (b) the chunker is only a discovery aid for retrieval — the
LLM Grader is what actually validates citations."""
from __future__ import annotations

import re

from app.agents.legal.schemas import Chunk

# Matches "Pasal 12" or "Pasal 12A" at start of line.
PASAL_RE = re.compile(r"^\s*Pasal\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
# Matches "ayat (1)" mid-text.
AYAT_RE = re.compile(r"ayat\s*\((\d+)\)")


def _split_into_pasal_blocks(text: str) -> list[tuple[str | None, str]]:
    """Returns a list of (pasal, body) pairs. Text before the first Pasal
    marker is returned with pasal=None."""
    matches = list(PASAL_RE.finditer(text))
    if not matches:
        return [(None, text)]

    blocks: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        blocks.append((None, text[: matches[0].start()].strip()))

    for i, m in enumerate(matches):
        pasal = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        if body:
            blocks.append((pasal, body))
    return blocks


def _split_long_body(body: str, max_chars: int, overlap: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    pieces: list[str] = []
    step = max_chars - overlap
    for start in range(0, len(body), step):
        pieces.append(body[start : start + max_chars])
        if start + max_chars >= len(body):
            break
    return pieces


def _pick_dominant_ayat(piece: str) -> str | None:
    """If the piece contains exactly one ayat reference, return it.
    Otherwise None (the chunk spans multiple ayats)."""
    found = AYAT_RE.findall(piece)
    return found[0] if len(set(found)) == 1 else None


def chunk_regulation_text(
    *,
    text: str,
    source: str,
    doc_hash: str,
    max_chars: int = 800,
    overlap: int = 100,
    page: int | None = None,
) -> list[Chunk]:
    """Splits text into pasal-anchored chunks.

    Chunk_id format: `{source}-{pasal or 'preamble'}-{ayat or '_'}-{page or '_'}-{idx}`
    so the same input text always produces the same ids."""
    chunks: list[Chunk] = []
    for pasal, body in _split_into_pasal_blocks(text):
        pieces = _split_long_body(body, max_chars=max_chars, overlap=overlap)
        for idx, piece in enumerate(pieces):
            ayat = _pick_dominant_ayat(piece)
            chunk_id = (
                f"{source}-{pasal or 'preamble'}-{ayat or '_'}-{page or '_'}-{idx}"
            )
            chunks.append(
                Chunk(
                    text=piece.strip(),
                    source=source,
                    pasal=pasal,
                    ayat=ayat,
                    page=page,
                    doc_hash=doc_hash,
                    chunk_id=chunk_id,
                )
            )
    return chunks
```

- [ ] **Step 5: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_chunker.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/legal/chunker.py backend/tests/test_legal_chunker.py backend/tests/data/tiny_ojk_fixture.txt
git commit -m "feat(legal): add pasal-aware regulation chunker with overlap for long pasals"
```

---

## Task Group B — Hybrid Retriever

### Task B1: Sparse (BM25) retriever

**Files:**
- Create: `backend/app/agents/legal/retriever.py` (sparse half)
- Create: `backend/tests/test_legal_retriever.py`

We build BM25 first because it's deterministic and offline-testable. Dense follows in B2; fusion in B3.

- [ ] **Step 1: Write failing test for BM25**

`backend/tests/test_legal_retriever.py`:

```python
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
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py -v`
Expected: FAIL — `BM25Retriever` doesn't exist yet.

- [ ] **Step 3: Implement BM25Retriever**

`backend/app/agents/legal/retriever.py`:

```python
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
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/retriever.py backend/tests/test_legal_retriever.py
git commit -m "feat(legal): add BM25 sparse retriever with save/load"
```

---

### Task B2: Dense (Pinecone) retriever

**Files:**
- Modify: `backend/app/agents/legal/retriever.py`
- Modify: `backend/tests/test_legal_retriever.py`

- [ ] **Step 1: Append failing tests**

Add to `backend/tests/test_legal_retriever.py`:

```python
from unittest.mock import MagicMock, patch
from app.agents.legal.retriever import DenseRetriever


def test_dense_retriever_calls_pinecone_with_query_embedding(sample_chunks: list[Chunk]) -> None:
    fake_index = MagicMock()
    fake_index.query.return_value = {
        "matches": [
            {"id": "OJK-3-1-_-0", "score": 0.92,
             "metadata": {"text": sample_chunks[1].text, "source": "OJK",
                          "pasal": "3", "ayat": "1", "doc_hash": "h", "page": None}},
            {"id": "UUPM-1-_-_-0", "score": 0.71,
             "metadata": {"text": sample_chunks[0].text, "source": "UUPM",
                          "pasal": "1", "ayat": None, "doc_hash": "h", "page": None}},
        ]
    }
    fake_embed = MagicMock()
    fake_embed.embed_query.return_value = [0.1] * 768

    with patch("app.agents.legal.retriever.get_index", return_value=fake_index), \
         patch("app.agents.legal.retriever.get_embedding_model", return_value=fake_embed):
        retr = DenseRetriever()
        hits = retr.retrieve("rokok", k=2)

    fake_embed.embed_query.assert_called_once_with("rokok")
    fake_index.query.assert_called_once()
    assert hits[0].chunk_id == "OJK-3-1-_-0"
    assert hits[0].score == 0.92
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py::test_dense_retriever_calls_pinecone_with_query_embedding -v`
Expected: FAIL — `DenseRetriever` not exported.

- [ ] **Step 3: Append DenseRetriever to retriever.py**

```python
# Append to backend/app/agents/legal/retriever.py

from app.core.gemini import get_embedding_model
from app.core.pinecone import get_index


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
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py::test_dense_retriever_calls_pinecone_with_query_embedding -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/retriever.py backend/tests/test_legal_retriever.py
git commit -m "feat(legal): add dense Pinecone retriever using Gemini embeddings"
```

---

### Task B3: Hybrid retriever with RRF fusion

**Files:**
- Modify: `backend/app/agents/legal/retriever.py`
- Modify: `backend/tests/test_legal_retriever.py`

Reciprocal Rank Fusion: each chunk's fused score = Σ 1/(k + rank_i). The constant k=60 is the canonical TREC value. Chunks appearing in both retrievers' top-N are boosted; chunks unique to one are still considered.

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py -v -k "rrf or hybrid_falls_back"`
Expected: FAIL.

- [ ] **Step 3: Append HybridRetriever**

```python
# Append to backend/app/agents/legal/retriever.py

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
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_retriever.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/retriever.py backend/tests/test_legal_retriever.py
git commit -m "feat(legal): add HybridRetriever with Reciprocal Rank Fusion + dense-only fallback"
```

---

## Task Group C — LLM Grader

### Task C1: Citation grader (anti-hallucination gate)

**Files:**
- Create: `backend/app/agents/legal/grader.py`
- Create: `backend/tests/test_legal_grader.py`

The grader takes the LLM's draft `LegalDecision` plus the retrieved chunks. For each `Citation`, it asks Gemini "Is the cited span actually present in the chunk text? Yes/No." Citations that don't ground are dropped. If all citations drop, status is forced to `rejected` with reason `no_grounded_basis`.

- [ ] **Step 1: Write failing test**

`backend/tests/test_legal_grader.py`:

```python
from unittest.mock import MagicMock, patch
from app.agents.legal.grader import grade_decision
from app.agents.legal.schemas import Chunk, Citation, LegalDecision, LegalStatus


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(text=text, source="OJK", pasal="3", ayat="1",
                 doc_hash="h", chunk_id=chunk_id)


def test_grader_keeps_citation_when_span_present_in_chunk() -> None:
    chunks = [_chunk("OJK-3-1-_-0", "Investor Ritel dilarang membeli saham rokok.")]
    decision = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="Sektor rokok dibatasi.",
        citations=[Citation(source="OJK", pasal="3", ayat="1",
                            chunk_id="OJK-3-1-_-0", span="dilarang membeli")],
    )

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": true, "evidence": "dilarang membeli"}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    assert len(graded.citations) == 1
    assert graded.status == LegalStatus.PARTIAL


def test_grader_drops_citation_when_span_not_in_chunk() -> None:
    chunks = [_chunk("OJK-3-1-_-0", "Investor Ritel dilarang membeli saham rokok.")]
    decision = LegalDecision(
        status=LegalStatus.PARTIAL,
        reasoning="...",
        citations=[Citation(source="OJK", pasal="3", ayat="1",
                            chunk_id="OJK-3-1-_-0", span="hadiah saham gratis")],
    )

    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": false, "evidence": ""}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    assert len(graded.citations) == 0
    # All citations dropped → forced rejection
    assert graded.status == LegalStatus.REJECTED
    assert "ground" in graded.reasoning.lower() or "basis" in graded.reasoning.lower()


def test_grader_drops_citation_when_chunk_id_unknown() -> None:
    """Cited chunk_id that wasn't in retrieval is structural hallucination —
    drop it WITHOUT calling the LLM (no need to ask, it's wrong by definition)."""
    chunks = [_chunk("OJK-3-1-_-0", "...")]
    decision = LegalDecision(
        status=LegalStatus.APPROVED,
        reasoning="...",
        citations=[
            Citation(source="OJK", pasal="3", ayat="1", chunk_id="OJK-3-1-_-0", span="..."),
            Citation(source="OJK", pasal="99", ayat="1", chunk_id="OJK-99-1-_-0", span="..."),
        ],
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = '{"grounded": true, "evidence": "..."}'

    with patch("app.agents.legal.grader.get_chat_model", return_value=fake_llm):
        graded = grade_decision(decision, chunks)

    # The unknown-chunk citation must be dropped; the known one survives
    assert len(graded.citations) == 1
    assert graded.citations[0].chunk_id == "OJK-3-1-_-0"
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_grader.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement grader**

`backend/app/agents/legal/grader.py`:

```python
"""Citation grader: the anti-hallucination gate of the Legal Agent.

For each Citation in a draft LegalDecision, ask Gemini whether the cited span
actually appears in the cited chunk's text. Drop citations that fail. If every
citation is dropped, force the decision to status=rejected with a reasoning
explaining the lack of grounded basis."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.legal.schemas import Chunk, Citation, LegalDecision, LegalStatus
from app.core.gemini import get_chat_model

logger = logging.getLogger(__name__)

GRADER_SYSTEM = """\
You are a strict citation auditor for Indonesian financial regulation.
You will receive (1) a chunk of regulatory text and (2) a span of text that an
agent claims appears verbatim (or near-verbatim) inside the chunk.

Return ONLY a JSON object: {"grounded": <true|false>, "evidence": "<exact substring of chunk text supporting the claim, or empty string>"}.

A citation is GROUNDED iff the meaning of the span is supported by an exact or
near-exact substring of the chunk. Trivial paraphrase (e.g. word order) is OK;
adding facts not in the chunk is NOT.
Return false if uncertain. Never fabricate evidence.
"""


def _is_grounded(chunk: Chunk, citation: Citation) -> bool:
    llm = get_chat_model()
    user = (
        f"CHUNK TEXT:\n{chunk.text}\n\n"
        f"CLAIMED SPAN: {citation.span!r}\n\n"
        f"Is the claimed span grounded in the chunk text? Respond JSON only."
    )
    resp = llm.invoke([SystemMessage(content=GRADER_SYSTEM), HumanMessage(content=user)])
    try:
        data = json.loads(resp.content)
        return bool(data.get("grounded", False))
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning("grader: failed to parse LLM response %r: %s", resp.content, exc)
        return False


def grade_decision(decision: LegalDecision, retrieved: list[Chunk]) -> LegalDecision:
    """Validate every citation against the retrieved chunk corpus.
    Returns a new LegalDecision with ungrounded citations removed."""
    by_id = {c.chunk_id: c for c in retrieved}
    surviving: list[Citation] = []

    for cit in decision.citations:
        chunk = by_id.get(cit.chunk_id)
        if chunk is None:
            logger.info("grader: citation %s references unknown chunk_id, dropping", cit.chunk_id)
            continue
        if not _is_grounded(chunk, cit):
            logger.info("grader: citation %s not grounded, dropping", cit.chunk_id)
            continue
        surviving.append(cit)

    if decision.citations and not surviving:
        # Every citation failed grading → no grounded basis to support any claim.
        return decision.model_copy(update={
            "status": LegalStatus.REJECTED,
            "citations": [],
            "reasoning": "Tidak ada dasar regulasi yang dapat dibuktikan untuk klaim ini "
                         "(no grounded basis).",
        })

    return decision.model_copy(update={"citations": surviving})
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_grader.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/grader.py backend/tests/test_legal_grader.py
git commit -m "feat(legal): add citation grader to drop ungrounded LLM citations"
```

---

## Task Group D — Legal Agent Node

### Task D1: Legal Agent node — retrieve, generate, grade, persist

**Files:**
- Create: `backend/app/agents/legal/node.py`
- Create: `backend/tests/test_legal_node.py`

The node orchestrates: build retrieval query from `allocation_plan`, call hybrid retriever, prompt Gemini for a structured `LegalDecision`, run grader, persist to `audit_log`, return updated `AgentState`.

- [ ] **Step 1: Write failing test**

`backend/tests/test_legal_node.py`:

```python
from unittest.mock import MagicMock, patch

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
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_node.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement node**

`backend/app/agents/legal/node.py`:

```python
"""Legal & Compliance Agent (N3) — the bottleneck of the AstaLink pipeline.

Reads `allocation_plan` from AgentState, runs hybrid retrieval, prompts Gemini
for a structured LegalDecision, runs the grader, persists to audit_log, returns
a partial state update with `legal_status` and `legal_citations`."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.legal.grader import grade_decision
from app.agents.legal.retriever import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
)
from app.agents.legal.schemas import Chunk, LegalDecision, LegalStatus
from app.agents.state import AgentState
from app.core.gemini import get_chat_model
from app.core.supabase_admin import get_admin_client

logger = logging.getLogger(__name__)

BM25_PATH = Path(__file__).parent.parent.parent.parent / "data" / "bm25_index.pkl"

LEGAL_SYSTEM = """\
You are a strict Indonesian financial-regulation compliance officer.
Given a proposed asset allocation and retrieved regulation chunks, decide if
the allocation is approved, partial (some legs blocked), or rejected.

You MUST cite specific chunks by chunk_id, pasal, and ayat. Never invent pasal
references. If the retrieved chunks do not support a claim, do not make it.

Return STRICT JSON matching this schema:
{
  "status": "approved" | "partial" | "rejected",
  "reasoning": "...",
  "citations": [
    {"source": "...", "pasal": "...", "ayat": "..." | null, "chunk_id": "...", "span": "..."}
  ],
  "alternative_actions": ["...", ...]   // ALWAYS include alternatives if status != approved
}
"""


@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    bm25: BM25Retriever | None = None
    if BM25_PATH.exists():
        bm25 = BM25Retriever.load(BM25_PATH)
    else:
        logger.warning("legal: BM25 index missing at %s — running dense-only", BM25_PATH)
    return HybridRetriever(bm25=bm25, dense=DenseRetriever())


def _build_query(plan: dict[str, Any]) -> str:
    weights = plan.get("weights", [])
    parts = [f"{w.get('ticker', '?')}: {w.get('weight', 0)}" for w in weights]
    return (
        "Periksa legalitas alokasi berikut terhadap regulasi OJK / UUPM / perpajakan: "
        + ", ".join(parts)
        + f". Jumlah cash: {plan.get('cash', 0)}."
    )


def _format_chunks(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"[chunk_id={c.chunk_id} | source={c.source} | pasal={c.pasal} | ayat={c.ayat}]\n{c.text}"
        for c in chunks
    )


def _generate_decision(plan: dict[str, Any], chunks: list[Chunk]) -> LegalDecision:
    """Prompt Gemini for a structured LegalDecision. Returns a parsed
    LegalDecision; raises ValueError on malformed JSON."""
    llm = get_chat_model()
    user = (
        f"PROPOSED ALLOCATION:\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
        f"RETRIEVED REGULATION CHUNKS:\n{_format_chunks(chunks)}\n\n"
        f"Decide and return JSON only."
    )
    resp = llm.invoke([SystemMessage(content=LEGAL_SYSTEM), HumanMessage(content=user)])
    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Legal LLM returned non-JSON: {resp.content!r}") from exc
    return LegalDecision.model_validate(data)


def _persist(audit_id: str, plan: dict[str, Any], decision: LegalDecision) -> None:
    """Write the decision to audit_log and allocation_plans via service-role."""
    client = get_admin_client()
    try:
        client.table("audit_log").update(
            {"payload": {"legal": decision.model_dump()}},
        ).eq("audit_id", audit_id).execute()
        client.table("allocation_plans").insert({
            "audit_id": audit_id,
            "plan_json": plan,
            "legal_status": decision.status.value,
            "legal_citations": [c.model_dump() for c in decision.citations],
        }).execute()
    except Exception as exc:  # surface but don't crash the pipeline
        logger.error("legal: failed to persist decision: %s", exc)


def legal_node(state: AgentState) -> AgentState:
    """LangGraph node entry point. Returns a partial AgentState update."""
    plan = state.get("allocation_plan") or {}
    audit_id = state["audit_id"]

    try:
        retriever = get_hybrid_retriever()
        query = _build_query(plan)
        chunks = retriever.retrieve(query, k=10)

        if not chunks:
            decision = LegalDecision(
                status=LegalStatus.REJECTED,
                reasoning="Retrieval returned no regulation chunks; cannot ground a decision.",
            )
            _persist(audit_id, plan, decision)
            return {
                "legal_status": decision.status,
                "legal_citations": [],
                "errors": [*state.get("errors", []), {"node": "legal", "reason": "empty_retrieval"}],
            }

        decision = _generate_decision(plan, chunks)
        decision = grade_decision(decision, chunks)
        _persist(audit_id, plan, decision)

        return {
            "legal_status": decision.status,
            "legal_citations": [c.model_dump() for c in decision.citations],
        }

    except Exception as exc:
        logger.exception("legal_node failed: %s", exc)
        return {
            "legal_status": LegalStatus.REJECTED,
            "legal_citations": [],
            "errors": [*state.get("errors", []), {"node": "legal", "reason": str(exc)}],
        }
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_node.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/legal/node.py backend/tests/test_legal_node.py
git commit -m "feat(legal): add LangGraph node for retrieve → generate → grade → persist"
```

---

## Task Group E — Standalone API Endpoint

### Task E1: POST /api/v1/legal/check

**Files:**
- Create: `backend/app/api/v1/legal.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_legal_endpoint.py`

The endpoint lets us validate the agent in isolation before Phase 2 wires it into the graph. It accepts an explicit `audit_id` (so the caller controls trace identity) and an `allocation_plan` dict.

- [ ] **Step 1: Write failing test**

`backend/tests/test_legal_endpoint.py`:

```python
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_legal_check_endpoint_returns_decision(client: TestClient) -> None:
    audit_id = str(uuid.uuid4())
    user = {"sub": str(uuid.uuid4()), "email": "u@test.com"}

    fake_state_update = {
        "legal_status": "partial",
        "legal_citations": [{
            "source": "OJK", "pasal": "3", "ayat": "1",
            "chunk_id": "OJK-3-1-_-0", "span": "dilarang"}],
    }

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.legal.legal_node", return_value=fake_state_update):
        resp = client.post(
            "/api/v1/legal/check",
            json={
                "audit_id": audit_id,
                "workspace_id": str(uuid.uuid4()),
                "allocation_plan": {
                    "weights": [{"ticker": "GGRM", "weight": 1.0}],
                    "cash": 10_000_000,
                },
            },
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["legal_status"] == "partial"
    assert body["legal_citations"][0]["pasal"] == "3"


def test_legal_check_endpoint_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/legal/check", json={})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run to confirm fail**

Run: `cd backend && uv run python -m pytest tests/test_legal_endpoint.py -v`
Expected: FAIL — endpoint not registered.

- [ ] **Step 3: Implement endpoint**

`backend/app/api/v1/legal.py`:

```python
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.legal.node import legal_node
from app.agents.state import AgentState
from app.api.deps import get_current_user

router = APIRouter()


class LegalCheckRequest(BaseModel):
    audit_id: str
    workspace_id: str
    allocation_plan: dict[str, Any] = Field(..., description="Proposed allocation to validate.")


class LegalCheckResponse(BaseModel):
    legal_status: str
    legal_citations: list[dict[str, Any]]
    errors: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/check", response_model=LegalCheckResponse)
async def check_legal(
    body: LegalCheckRequest,
    user: dict = Depends(get_current_user),
) -> LegalCheckResponse:
    """Run the Legal Agent in isolation. Used for testing and ad-hoc compliance
    queries; the same node is reused inside the graph in Phase 2."""
    state = AgentState(
        audit_id=body.audit_id,
        messages=[],
        intent=None,
        entities={},
        allocation_plan=body.allocation_plan,
        revision_count=0,
        legal_status=None,
        legal_citations=[],
        user_approval=None,
        transactions=[],
        errors=[],
    )
    update = legal_node(state)
    return LegalCheckResponse(
        legal_status=str(update.get("legal_status", "rejected")),
        legal_citations=update.get("legal_citations", []),
        errors=update.get("errors", []),
    )
```

`backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import chat, health, legal

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(legal.router, prefix="/legal", tags=["legal"])
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && uv run python -m pytest tests/test_legal_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/legal.py backend/app/api/v1/router.py backend/tests/test_legal_endpoint.py
git commit -m "feat(legal): expose POST /api/v1/legal/check endpoint"
```

---

## Task Group F — Ingestion Pipeline

### Task F1: ingest_regulations.py CLI

**Files:**
- Create: `backend/scripts/ingest_regulations.py`
- Create: `backend/data/regulations/README.md`
- Modify: `.gitignore`

A one-shot CLI: `uv run python scripts/ingest_regulations.py backend/data/regulations/`. Walks the directory, for each PDF: hash, chunk, embed in batches, upsert to Pinecone, append to BM25 corpus, write `regulation_documents` row. Idempotent on `doc_hash` (skip if already indexed).

- [ ] **Step 1: Update .gitignore**

Append to `.gitignore`:

```
# Regulation corpus (large PDFs, license-restricted)
backend/data/regulations/*.pdf
backend/data/bm25_index.pkl
backend/data/chunks.jsonl
```

- [ ] **Step 2: Create regulations directory README**

`backend/data/regulations/README.md`:

```markdown
# Regulation corpus

Place source PDFs here. The ingestion script walks this directory and
indexes every `.pdf` file.

## Suggested starting set

| File | Source | Purpose |
|------|--------|---------|
| `pojk-ojk-1-2020.pdf` | OJK | Sample retail-investor restriction rules |
| `uupm-1995-excerpt.pdf` | UU Pasar Modal | Emiten obligations |
| `pp-perpajakan-saham.pdf` | DJP | Tax on stock transactions |

## Where to obtain

- OJK: https://ojk.go.id/id/regulasi
- UUPM: https://peraturan.bpk.go.id (search "Pasar Modal")
- Perpajakan: https://pajak.go.id

The team is responsible for confirming licensing terms before redistributing
any PDF. We do NOT commit PDFs to git.

## Re-ingesting

Re-running the ingestion script is idempotent — files with an unchanged
`doc_hash` are skipped.
```

- [ ] **Step 3: Implement the script**

`backend/scripts/ingest_regulations.py`:

```python
"""Ingest regulation PDFs into Pinecone (dense) + BM25 (sparse).

Usage:
    cd backend
    uv run python scripts/ingest_regulations.py data/regulations/

Idempotent on doc_hash — re-running skips already-indexed files."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from app.agents.legal.chunker import chunk_regulation_text
from app.agents.legal.retriever import BM25Retriever
from app.agents.legal.schemas import Chunk
from app.core.gemini import get_embedding_model
from app.core.pinecone import get_index
from app.core.supabase_admin import get_admin_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")
log = logging.getLogger("ingest")

EMBED_BATCH = 100
PINECONE_BATCH = 100


def _doc_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _already_indexed(doc_hash: str) -> bool:
    res = get_admin_client().table("regulation_documents").select("id").eq("doc_hash", doc_hash).execute()
    return bool(res.data)


def _extract_text(path: Path) -> Iterable[tuple[int, str]]:
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages, start=1):
        yield i, page.extract_text() or ""


def _source_from_filename(path: Path) -> str:
    name = path.stem.lower()
    if "ojk" in name:
        return "OJK"
    if "uupm" in name:
        return "UUPM"
    if "pajak" in name or "perpajakan" in name:
        return "Perpajakan"
    return path.stem


def _embed_in_batches(chunks: list[Chunk]) -> list[list[float]]:
    embed = get_embedding_model()
    out: list[list[float]] = []
    for i in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[i : i + EMBED_BATCH]
        out.extend(embed.embed_documents([c.text for c in batch]))
        log.info("embedded %d/%d", i + len(batch), len(chunks))
    return out


def _upsert_to_pinecone(chunks: list[Chunk], vectors: list[list[float]]) -> None:
    index = get_index()
    items = []
    for c, v in zip(chunks, vectors):
        items.append({
            "id": c.chunk_id,
            "values": v,
            "metadata": {
                "text": c.text,
                "source": c.source,
                "pasal": c.pasal,
                "ayat": c.ayat,
                "page": c.page,
                "doc_hash": c.doc_hash,
            },
        })
    for i in range(0, len(items), PINECONE_BATCH):
        index.upsert(vectors=items[i : i + PINECONE_BATCH])
    log.info("upserted %d chunks to Pinecone", len(items))


def _save_bm25(all_chunks: list[Chunk], path: Path) -> None:
    BM25Retriever.from_chunks(all_chunks).save(path)
    log.info("saved BM25 index with %d chunks → %s", len(all_chunks), path)


def _record_document(path: Path, doc_hash: str, source: str) -> None:
    get_admin_client().table("regulation_documents").insert({
        "source": source,
        "title": path.stem,
        "doc_hash": doc_hash,
    }).execute()


def ingest_directory(dir_path: Path, bm25_path: Path) -> None:
    pdfs = sorted(dir_path.glob("*.pdf"))
    if not pdfs:
        log.error("no PDFs found in %s", dir_path)
        sys.exit(1)

    all_chunks: list[Chunk] = []
    for pdf in pdfs:
        h = _doc_hash(pdf)
        if _already_indexed(h):
            log.info("skipping %s (doc_hash %s already indexed)", pdf.name, h)
            continue
        source = _source_from_filename(pdf)
        log.info("ingesting %s as source=%s", pdf.name, source)

        doc_chunks: list[Chunk] = []
        for page_num, text in _extract_text(pdf):
            doc_chunks.extend(chunk_regulation_text(
                text=text, source=source, doc_hash=h, page=page_num,
            ))
        log.info("  produced %d chunks", len(doc_chunks))

        if doc_chunks:
            vectors = _embed_in_batches(doc_chunks)
            _upsert_to_pinecone(doc_chunks, vectors)
        _record_document(pdf, h, source)
        all_chunks.extend(doc_chunks)

    if all_chunks:
        # Rebuild BM25 from union of newly-ingested + existing chunks. For the
        # hackathon we just rebuild from the new run; production would merge
        # with the existing index.
        if bm25_path.exists():
            existing = BM25Retriever.load(bm25_path)
            all_chunks = list(existing._chunks) + all_chunks  # type: ignore[attr-defined]
        _save_bm25(all_chunks, bm25_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--bm25-path", type=Path,
                        default=Path(__file__).parent.parent / "data" / "bm25_index.pkl")
    args = parser.parse_args()
    ingest_directory(args.directory, args.bm25_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Manual smoke test**

Place at least one PDF in `backend/data/regulations/`. Then:

```bash
cd backend && uv run python scripts/ingest_regulations.py data/regulations/
```

Expected log lines: `ingesting <name> as source=...`, `produced N chunks`, `embedded N/N`, `upserted N chunks to Pinecone`, `saved BM25 index with N chunks`. Verify in Pinecone console: index has vectors. Verify in Supabase: `regulation_documents` has a new row.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/ingest_regulations.py backend/data/regulations/README.md .gitignore
git commit -m "feat(legal): add ingestion CLI for Pinecone + BM25 with idempotent doc_hash"
```

---

## Task Group G — DeepEval Quality Gate

### Task G1: Hallucination evaluation suite

**Files:**
- Create: `backend/tests/data/eval_prompts.json`
- Create: `backend/tests/test_legal_hallucination.py`
- Modify: `backend/pyproject.toml` (register `slow` marker)

DeepEval's `HallucinationMetric` and `FaithfulnessMetric` measure whether the LLM's output is supported by the retrieval context. We curate 20 hand-labeled prompts spanning approval, partial, and rejection cases.

- [ ] **Step 1: Register `slow` marker in pyproject.toml**

Add under `[tool.pytest.ini_options]`:

```toml
markers = [
    "slow: tests that hit external services (Gemini, Pinecone) or take >5s",
]
```

- [ ] **Step 2: Create curated eval prompts**

`backend/tests/data/eval_prompts.json` (20 entries; sample shown — fill the rest from the team's regulation knowledge):

```json
[
  {
    "prompt": "Saya investor ritel ingin alokasi 100% saham GGRM (rokok). Apakah diperbolehkan?",
    "expected_status": "rejected",
    "expected_citations_must_include_pasal": "3"
  },
  {
    "prompt": "Alokasi 60% BBCA, 40% obligasi pemerintah. Profile moderate.",
    "expected_status": "approved",
    "expected_citations_must_include_pasal": null
  },
  {
    "prompt": "Investasi 80% saham Emiten yang belum lapor keuangan tahunan.",
    "expected_status": "rejected",
    "expected_citations_must_include_pasal": "2"
  }
]
```

(Team adds 17 more prompts following the same shape.)

- [ ] **Step 3: Write the suite**

`backend/tests/test_legal_hallucination.py`:

```python
"""DeepEval-based quality gate for the Legal Agent.

These tests hit the real retrieval + LLM stack and are SLOW. Marked with
@pytest.mark.slow so the fast inner-loop test suite skips them by default.
Run before merging changes that touch the Legal Agent:

    cd backend && uv run python -m pytest tests/test_legal_hallucination.py -v -m slow
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

EVAL_PATH = Path(__file__).parent / "data" / "eval_prompts.json"


def _load_prompts() -> list[dict]:
    return json.loads(EVAL_PATH.read_text())


@pytest.mark.parametrize("case", _load_prompts())
def test_status_matches_expectation(case: dict) -> None:
    """End-to-end: build allocation plan from prompt → run legal_node → assert
    status matches expected. Allows partial→partial / approved→approved /
    rejected→rejected, but flags drift."""
    from app.agents.legal.node import legal_node
    from app.agents.state import new_state

    state = new_state()
    state["allocation_plan"] = {"prompt": case["prompt"]}
    update = legal_node(state)
    assert str(update["legal_status"]) == case["expected_status"], \
        f"Drift on prompt: {case['prompt']!r}"


def test_aggregate_hallucination_metric() -> None:
    """Aggregate DeepEval metric across the eval set must be ≥ 0.95.
    A failing run blocks merges to main."""
    from deepeval.metrics import HallucinationMetric
    from deepeval.test_case import LLMTestCase

    from app.agents.legal.node import get_hybrid_retriever, _generate_decision
    from app.agents.legal.schemas import LegalDecision  # noqa: F401

    metric = HallucinationMetric(threshold=0.95)
    failures: list[str] = []
    for case in _load_prompts():
        plan = {"prompt": case["prompt"]}
        chunks = get_hybrid_retriever().retrieve(case["prompt"], k=10)
        decision = _generate_decision(plan, chunks)
        tc = LLMTestCase(
            input=case["prompt"],
            actual_output=decision.reasoning,
            context=[c.text for c in chunks],
        )
        metric.measure(tc)
        if metric.score < 0.95:
            failures.append(f"{case['prompt']!r}: score={metric.score:.2f}")

    assert not failures, f"Hallucination metric below 0.95 on:\n" + "\n".join(failures)
```

- [ ] **Step 4: Run the slow suite (manual)**

```bash
cd backend && uv run python -m pytest tests/test_legal_hallucination.py -v -m slow
```

Expected: PASS on all 20 prompts; aggregate hallucination ≥ 0.95.

If failures: tune the chunker (smaller `max_chars`?), the retriever (top_k?), or the prompt. Document the tuning round in a Phase 1 retro note.

- [ ] **Step 5: Verify default suite skips slow tests**

```bash
cd backend && uv run python -m pytest tests/ -v
```

Expected: the slow suite is collected but skipped (DeepEval tests show as `SKIPPED [N] ...`). All other tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_legal_hallucination.py backend/tests/data/eval_prompts.json backend/pyproject.toml
git commit -m "feat(legal): add DeepEval hallucination quality gate (slow marker)"
```

---

## Phase 1 Definition of Done

- [ ] Phase 0 DoD already satisfied (foundation in place).
- [ ] At least 3 regulation PDFs ingested end-to-end. Pinecone shows chunks; `backend/data/bm25_index.pkl` exists; `regulation_documents` has rows.
- [ ] All non-slow tests pass: `cd backend && uv run python -m pytest tests/ -v`.
- [ ] DeepEval slow suite passes: `... -m slow` — hallucination ≥ 0.95 across the 20-prompt eval set.
- [ ] Manual API check: `curl -X POST http://localhost:8000/api/v1/legal/check -H "Authorization: Bearer <real JWT>" -d '{"audit_id":"...","workspace_id":"...","allocation_plan":{...}}'` returns a `LegalDecision` with grounded citations.
- [ ] Adversarial prompt test: a question about a fictional pasal ("Pasal 999 ayat (5)") returns `rejected` or no citation — never a fabricated reference.
- [ ] Phase 1 retro paragraph captured (what worked, what surprised us, settings to tune).
