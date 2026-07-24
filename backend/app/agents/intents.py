"""User intents the Intent Classifier (N1) maps natural language to.

Stored lowercased in audit_log.intent; the enum value IS the persisted form."""
from __future__ import annotations

from enum import StrEnum


class Intent(StrEnum):
    ALLOCATE_STOCKS = "allocate_stocks"
    # "should this money go to stocks or my/a business?" — runs the full
    # Layer 0 capital-allocation flow (intake, vetoes, quality, DA) before
    # any stock analysis
    ALLOCATE_CAPITAL = "allocate_capital"
    EVALUATE_BUSINESS = "evaluate_business"
    RISK_REVIEW = "risk_review"
    PORTFOLIO_STATUS = "portfolio_status"
    EXPLAIN = "explain"
    UNKNOWN = "unknown"
