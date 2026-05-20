from __future__ import annotations

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    var_95: float | None = None
    var_99: float | None = None
    sharpe: float | None = None


class RiskAssessment(BaseModel):
    metrics: RiskMetrics = Field(default_factory=RiskMetrics)
    suggested_weights: dict[str, float] = Field(default_factory=dict)
    narration: str = ""
