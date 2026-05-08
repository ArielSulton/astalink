from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessValuation(BaseModel):
    enterprise_value: float
    discount_rate: float
    terminal_growth: float
    cashflows: list[float]
    narration: str = Field(default="")
