from __future__ import annotations

from pydantic import BaseModel, Field


class HoldingView(BaseModel):
    """One accumulated position, marked to market when a price is available.
    Price-derived fields are None (not 0) when the current price can't be
    fetched — an honest UNKNOWN, consistent with the rest of the codebase."""
    ticker: str
    quantity: float
    avg_cost: float
    last_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None


class PortfolioResponse(BaseModel):
    workspace_id: str
    cash_balance: float
    holdings: list[HoldingView] = Field(default_factory=list)
    total_market_value: float | None = None
    total_unrealized_pnl: float | None = None
    total_realized_pnl: float = 0.0
    total_equity: float | None = None   # cash + market value (None if unpriced)


class SellRequest(BaseModel):
    quantity: float
    pin: str


class SellResponse(BaseModel):
    ticker: str
    sold_quantity: float
    sell_price: float
    proceeds: float
    realized_pnl: float
    remaining_quantity: float
    cash_balance: float
