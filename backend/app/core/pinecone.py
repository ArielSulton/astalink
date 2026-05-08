"""Lazy singleton Pinecone client + index handle for AstaLink RAG (Phase 1).

The Pinecone SDK v5 separates the control-plane client (`Pinecone`) from a
data-plane handle (`client.Index(name)`). We cache both."""
from __future__ import annotations

from pinecone import Pinecone

from app.core.config import settings

_client: Pinecone | None = None
_index = None  # pinecone.Index — type omitted because the SDK doesn't export it cleanly


def get_pinecone_client() -> Pinecone:
    global _client
    if _client is None:
        _client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _client


def get_index():
    """Returns the configured index handle. Caller is responsible for ensuring
    the index has been created in the Pinecone console (one-time bootstrap)."""
    global _index
    if _index is None:
        client = get_pinecone_client()
        _index = client.Index(settings.PINECONE_INDEX_NAME)
    return _index
