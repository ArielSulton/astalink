import logging
from collections.abc import Callable

from app.core.wallet import get_workspace_balance
from app.models.portfolio import HoldingView, PortfolioResponse

log = logging.getLogger(__name__)

PriceLoader = Callable[[str], float | None]


def fetch_last_price(ticker: str) -> float | None:
    """Return the latest close, or ``None`` when the market source is unavailable."""
    try:
        from app.agents.market.yfinance_client import (
            fetch_price_series_with_indicators,
        )

        return fetch_price_series_with_indicators(ticker).get("last_close")
    except Exception as exc:
        log.warning("portfolio: price fetch failed for %s: %s", ticker, exc)
        return None


def build_portfolio(
    sb,
    workspace_id: str,
    price_loader: PriceLoader | None = None,
) -> PortfolioResponse:
    load_price = price_loader or fetch_last_price
    rows = (
        sb.table("holdings").select("*")
        .eq("workspace_id", workspace_id).execute()
    ).data or []

    holdings: list[HoldingView] = []
    total_market_value = 0.0
    total_unrealized = 0.0
    any_priced = False
    for row in rows:
        quantity = float(row["quantity"])
        average = float(row["avg_cost"])
        cost_basis = quantity * average
        price = load_price(row["ticker"])
        market_value = unrealized = unrealized_pct = None
        if price is not None:
            any_priced = True
            market_value = quantity * price
            unrealized = market_value - cost_basis
            unrealized_pct = unrealized / cost_basis if cost_basis else None
            total_market_value += market_value
            total_unrealized += unrealized
        holdings.append(HoldingView(
            ticker=row["ticker"],
            quantity=quantity,
            avg_cost=average,
            cost_basis=cost_basis,
            last_price=price,
            market_value=market_value,
            unrealized_pnl=unrealized,
            unrealized_pnl_pct=unrealized_pct,
        ))

    cash = get_workspace_balance(sb, workspace_id) or 0.0
    realized_rows = (
        sb.table("transactions").select("realized_pnl")
        .eq("workspace_id", workspace_id).eq("side", "sell").execute()
    ).data or []
    realized = sum(
        float(row["realized_pnl"])
        for row in realized_rows
        if row.get("realized_pnl") is not None
    )

    return PortfolioResponse(
        workspace_id=workspace_id,
        cash_balance=cash,
        holdings=holdings,
        total_market_value=total_market_value if any_priced else None,
        total_unrealized_pnl=total_unrealized if any_priced else None,
        total_realized_pnl=realized,
        total_equity=(cash + total_market_value) if any_priced else None,
    )
