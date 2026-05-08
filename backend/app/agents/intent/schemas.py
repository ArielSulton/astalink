from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.agents.intents import Intent


class IntentDecision(BaseModel):
    intent: Intent
    entities: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    clarification_question: str | None = Field(
        default=None,
        description="Set when intent=UNKNOWN or confidence < 0.6.",
    )
