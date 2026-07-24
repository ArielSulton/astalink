from __future__ import annotations

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    var_95: float | None = None
    var_99: float | None = None
    sharpe: float | None = None


class RiskAssessment(BaseModel):
    metrics: RiskMetrics = Field(default_factory=RiskMetrics)
    suggested_weights: dict[str, float] = Field(default_factory=dict)
    # Real annualized inputs derived from price history, exposed so the
    # optimizer (N5) can use them instead of naive priors. Empty when there
    # was insufficient data (the optimizer then falls back to its defaults).
    expected_returns: dict[str, float] = Field(default_factory=dict)
    covariance: dict[str, dict[str, float]] = Field(default_factory=dict)
    narration: str = ""
