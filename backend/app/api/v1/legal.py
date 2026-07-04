import hashlib
import io
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from pypdf import PdfReader

from app.agents.legal.chunker import chunk_regulation_text
from app.agents.legal.node import legal_node
from app.agents.legal.retriever import BM25Retriever
from app.agents.state import AgentState
from app.api.deps import get_current_user
from app.core.pinecone import DEFAULT_NAMESPACE, get_index
from app.core.supabase_admin import get_admin_client

router = APIRouter()

# Pinecone's integrated-embedding records API caps ~96 texts per upsert call
# for hosted embedding models; batch defensively for large regulations.
_PINECONE_UPSERT_BATCH = 90


class LegalCheckRequest(BaseModel):
    audit_id: str
    workspace_id: str
    allocation_plan: dict[str, Any] = Field(..., description="Proposed allocation to validate.")


class LegalCheckResponse(BaseModel):
    legal_status: str
    legal_citations: list[dict[str, Any]]
    errors: list[dict[str, Any]] = Field(default_factory=list)


class RegulationDocumentOut(BaseModel):
    id: str
    source: str
    title: str
    version: str | None = None
    indexed_at: str


# BM25 index path — resolves to backend/data/bm25_index.pkl
_BM25_PATH = Path(__file__).parent.parent.parent.parent / "data" / "bm25_index.pkl"


@router.get("/documents", response_model=list[RegulationDocumentOut])
async def list_documents() -> list[RegulationDocumentOut]:
    sb = get_admin_client()
    res = (
        sb.table("regulation_documents")
        .select("id,source,title,version,indexed_at")
        .order("indexed_at", desc=True)
        .execute()
    )
    return [RegulationDocumentOut(**row) for row in (res.data or [])]


@router.post("/documents/upload", response_model=RegulationDocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    source: str = "user",
    title: str = "",
    user: dict = Depends(get_current_user),
) -> RegulationDocumentOut:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
    content = await file.read()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF must be ≤ 10 MB.")
    doc_hash = hashlib.sha256(content).hexdigest()

    # Extract text from PDF
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    # Chunk and update BM25 index
    chunks = chunk_regulation_text(
        text=text,
        source=source or (file.filename or "upload"),
        doc_hash=doc_hash,
    )
    _BM25_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _BM25_PATH.exists():
        existing = BM25Retriever.load(_BM25_PATH)
        all_chunks = existing._chunks + chunks
    else:
        all_chunks = chunks
    new_retriever = BM25Retriever.from_chunks(all_chunks)
    new_retriever.save(_BM25_PATH)

    # Insert metadata into Supabase
    sb = get_admin_client()
    row = (
        sb.table("regulation_documents")
        .insert({
            "source": source,
            "title": title or (file.filename or "Uploaded Document"),
            "doc_hash": doc_hash,
            "metadata": {"pages": len(reader.pages), "chunks": len(chunks)},
        })
        .execute()
    )
    if not row.data:
        raise HTTPException(status_code=409, detail="Document already indexed.")
    inserted = row.data[0]

    # Dense index (Pinecone integrated embedding — text is embedded server-side).
    index = get_index()
    records = [
        {
            "_id": c.chunk_id,
            "text": c.text,
            "source": c.source,
            "doc_hash": c.doc_hash,
            **({"pasal": c.pasal} if c.pasal else {}),
            **({"ayat": c.ayat} if c.ayat else {}),
            **({"page": c.page} if c.page is not None else {}),
        }
        for c in chunks
    ]
    for i in range(0, len(records), _PINECONE_UPSERT_BATCH):
        index.upsert_records(
            namespace=DEFAULT_NAMESPACE,
            records=records[i : i + _PINECONE_UPSERT_BATCH],
        )

    return RegulationDocumentOut(**inserted)


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
