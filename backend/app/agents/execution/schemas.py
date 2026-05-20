from __future__ import annotations
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class BrokerOrder(BaseModel):
    ticker: str
    qty: float
    side: OrderSide
    broker_ref: str
    status: str   # "filled" | "pending" | "failed"
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    orders: list[BrokerOrder]
