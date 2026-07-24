from __future__ import annotations

from pydantic import BaseModel, Field


class HoldingView(BaseModel):
    """One accumulated position, marked to market when a price is available.
    Price-derived fields are None (not 0) when the current price can't be
    fetched — an honest UNKNOWN, consistent with the rest of the codebase."""
    ticker: str
    quantity: float
    avg_cost: float
    cost_basis: float                          # Modal investasi awal (quantity * avg_cost)
    last_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None   # Persentase kenaikan/penurunan ((last_price - avg_cost) / avg_cost)


class PortfolioResponse(BaseModel):
    workspace_id: str
    cash_balance: float
    holdings: list[HoldingView] = Field(default_factory=list)
    total_market_value: float | None = None
    total_unrealized_pnl: float | None = None
    total_realized_pnl: float = 0.0
    total_equity: float | None = None   # cash + market value (None if unpriced)


class BuyRequest(BaseModel):
    ticker: str
    amount: float                      # Total Rp yang dialokasikan/diinvestasikan (misal 10,000,000)
    pin: str | None = None


class BuyResponse(BaseModel):
    ticker: str
    allocated_amount: float
    quantity: float
    buy_price: float
    cash_balance: float
    holding: HoldingView


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

