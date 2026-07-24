"""Portfolio (sandbox) — accumulated holdings, mark-to-market, and manual sell.

Buys flow through the agent pipeline (execution N7 upserts holdings); this
router serves the read view and a direct PIN-gated sell that the /portfolio
page's "Jual" button calls. All money is virtual (SandboxBroker + the
workspace's `cash_balance`), so a sell just credits cash and books realized
P&L into the transactions ledger."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.agents.execution.schemas import OrderSide
from app.api.deps import get_current_user, verify_user_pin
from app.core.holdings import apply_sell, get_holding
from app.core.holdings import realized_pnl as calc_realized
from app.core.ownership import assert_workspace_owned
from app.core.supabase_admin import get_admin_client
from app.core.wallet import credit_workspace_balance, get_workspace_balance
from app.integrations.broker import SandboxBroker
from app.models.portfolio import (
    HoldingView,
    PortfolioResponse,
    SellRequest,
    SellResponse,
)

log = logging.getLogger(__name__)
router = APIRouter()


def _last_price(ticker: str) -> float | None:
    """Best-effort current price. None (never 0) when unavailable."""
    try:
        from app.agents.market.yfinance_client import (
            fetch_price_series_with_indicators,
        )
        return fetch_price_series_with_indicators(ticker).get("last_close")
    except Exception as exc:  # network / data source hiccup
        log.warning("portfolio: price fetch failed for %s: %s", ticker, exc)
        return None


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    workspace_id: str, user: dict = Depends(get_current_user)
) -> PortfolioResponse:
    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])

    rows = (
        sb.table("holdings").select("*")
        .eq("workspace_id", workspace_id).execute()
    ).data or []

    holdings: list[HoldingView] = []
    total_mv = 0.0
    total_upnl = 0.0
    any_priced = False
    for r in rows:
        qty = float(r["quantity"])
        avg = float(r["avg_cost"])
        cost_basis = qty * avg
        price = _last_price(r["ticker"])
        mv = upnl = upnl_pct = None
        if price is not None:
            any_priced = True
            mv = qty * price
            upnl = mv - cost_basis
            upnl_pct = (upnl / cost_basis) if cost_basis else None
            total_mv += mv
            total_upnl += upnl
        holdings.append(HoldingView(
            ticker=r["ticker"], quantity=qty, avg_cost=avg, last_price=price,
            market_value=mv, unrealized_pnl=upnl, unrealized_pnl_pct=upnl_pct,
        ))

    cash = get_workspace_balance(sb, workspace_id) or 0.0

    realized_rows = (
        sb.table("transactions").select("realized_pnl")
        .eq("workspace_id", workspace_id).eq("side", "sell").execute()
    ).data or []
    total_realized = sum(
        float(x["realized_pnl"]) for x in realized_rows
        if x.get("realized_pnl") is not None
    )

    return PortfolioResponse(
        workspace_id=workspace_id,
        cash_balance=cash,
        holdings=holdings,
        total_market_value=total_mv if any_priced else None,
        total_unrealized_pnl=total_upnl if any_priced else None,
        total_realized_pnl=total_realized,
        total_equity=(cash + total_mv) if any_priced else None,
    )


@router.post("/{ticker}/sell", response_model=SellResponse)
async def sell_holding(
    ticker: str,
    workspace_id: str,
    body: SellRequest,
    user: dict = Depends(get_current_user),
) -> SellResponse:
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")

    sb = get_admin_client()
    assert_workspace_owned(sb, workspace_id, user["sub"])
    verify_user_pin(user["sub"], body.pin)

    holding = get_holding(sb, workspace_id, ticker)
    if not holding:
        raise HTTPException(status_code=404, detail="holding not found")

    held_qty = float(holding["quantity"])
    if body.quantity > held_qty + 1e-9:
        raise HTTPException(
            status_code=400,
            detail=f"cannot sell {body.quantity}; only {held_qty} held",
        )

    price = _last_price(ticker)
    if price is None:
        raise HTTPException(status_code=502, detail="current price unavailable")

    qty = body.quantity
    avg = float(holding["avg_cost"])
    proceeds = qty * price
    realized = calc_realized(qty, price, avg)

    # Sandbox broker sell (always fills — no real market).
    SandboxBroker().place_order(
        ticker=ticker, qty=qty, side=OrderSide.SELL, account_id=workspace_id,
    )

    new_cash = credit_workspace_balance(sb, workspace_id, proceeds)
    if new_cash is None:
        raise HTTPException(status_code=409, detail="balance update conflict; retry")

    remaining = apply_sell(sb, holding, qty)

    try:
        sb.table("transactions").insert({
            "workspace_id": workspace_id,
            "ticker": ticker,
            "side": OrderSide.SELL.value,
            "quantity": qty,
            "price": price,
            "realized_pnl": realized,
            "status": "filled",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "payload": {"account_id": workspace_id, "manual": True},
        }).execute()
    except Exception as exc:
        log.warning("portfolio: sell transaction insert failed: %s", exc)

    return SellResponse(
        ticker=ticker,
        sold_quantity=qty,
        sell_price=price,
        proceeds=proceeds,
        realized_pnl=realized,
        remaining_quantity=remaining,
        cash_balance=new_cash,
    )
