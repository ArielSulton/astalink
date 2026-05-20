"""Broker adapter Protocol + Sandbox + RealBroker stub.

The hackathon demo runs against SandboxBroker. RealBroker raises
NotImplementedError until the team wires real credentials and an HTTP client
for the chosen Indonesian retail broker."""
from __future__ import annotations

import random
from typing import Protocol, runtime_checkable

from app.agents.execution.schemas import BrokerOrder, OrderSide


@runtime_checkable
class BrokerAdapter(Protocol):
    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder: ...


class SandboxBroker:
    """Deterministic test broker. Always fills, generates a fake broker_ref."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder:
        if qty <= 0:
            raise ValueError("qty must be > 0")
        ref = f"sandbox-{self._rng.randint(10_000_000, 99_999_999)}"
        return BrokerOrder(
            ticker=ticker, qty=qty, side=side, broker_ref=ref, status="filled",
            payload={"account_id": account_id},
        )


class RealBroker:
    """HTTP-backed real broker. Implementation deferred until creds + chosen
    provider are confirmed. Keeping the class so the wiring code is stable."""

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url

    def place_order(self, *, ticker: str, qty: float, side: OrderSide, account_id: str) -> BrokerOrder:
        raise NotImplementedError(
            "RealBroker is a placeholder; wire HTTP client and broker-specific "
            "endpoints before enabling in production."
        )
