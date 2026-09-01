"""Pydantic response schemas for GET /api/v1/recommendations."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.market.synthesizer import StockVerdict


class RecommendationItem(BaseModel):
    ticker: str                      # bare, e.g. "BBCA"
    sector: str
    rank: int
    content_score: float
    user_score: float
    hybrid_score: float
    verdict: StockVerdict | None = None   # populated for the top-ranked items only


class RecommendationsResponse(BaseModel):
    workspace_id: str
    personalized: bool
    fallback_reason: str | None = None
    items: list[RecommendationItem] = Field(default_factory=list)
    as_of: str
