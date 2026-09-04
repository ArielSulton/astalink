from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TransactionExtraction(BaseModel):
    is_transaction: bool
    item_description: str | None = None
    amount: float | None = None
    type: Literal["income", "expense"] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    raw_input: str
