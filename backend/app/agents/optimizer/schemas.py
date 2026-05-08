from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WeightLeg(BaseModel):
    ticker: str
    weight: float


class AllocationPlan(BaseModel):
    weights: list[WeightLeg]
    cash: float
    cash_buffer: float = Field(default=0.0)
    narration: str = ""
    relaxations_applied: list[str] = Field(default_factory=list)


SolverStatus = Literal["optimal", "infeasible", "fallback_equal"]


class SolverResult(BaseModel):
    status: SolverStatus
    weights: dict[str, float] = Field(default_factory=dict)
    objective_value: float | None = None
    message: str | None = None


class OptimizerInputs(BaseModel):
    tickers: list[str]
    expected_returns: list[float]
    cov: list[list[float]]
    cash: float
    forbidden_tickers: list[str] = Field(default_factory=list)
    partial_tickers: dict[str, float] = Field(
        default_factory=dict,
        description="ticker → max-allowed weight (e.g. 0.1 for partial-only).",
    )
    sector_caps: dict[str, float] = Field(default_factory=dict)
    max_per_asset: float = 0.4
    min_cash_buffer: float = 0.05
    risk_aversion: float = 2.0
