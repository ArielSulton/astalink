import pytest
from app.integrations.broker import SandboxBroker
from app.agents.execution.schemas import BrokerOrder, OrderSide


def test_sandbox_returns_filled_order_with_deterministic_ref() -> None:
    b = SandboxBroker(seed=42)
    order = b.place_order(ticker="BBCA", qty=10, side=OrderSide.BUY, account_id="acct-1")
    assert isinstance(order, BrokerOrder)
    assert order.status == "filled"
    assert order.ticker == "BBCA"
    assert order.qty == 10
    assert order.side == OrderSide.BUY
    assert order.broker_ref.startswith("sandbox-")


def test_sandbox_rejects_zero_or_negative_qty() -> None:
    b = SandboxBroker()
    with pytest.raises(ValueError):
        b.place_order(ticker="BBCA", qty=0, side=OrderSide.BUY, account_id="x")


def test_real_broker_raises_until_creds_wired() -> None:
    from app.integrations.broker import RealBroker
    b = RealBroker(api_key="", base_url="")
    with pytest.raises(NotImplementedError):
        b.place_order(ticker="BBCA", qty=1, side=OrderSide.BUY, account_id="x")
