"""Open Finance funds-verification adapter. Sandbox impl returns True; real
impl deferred."""
from __future__ import annotations

from typing import Protocol


class OpenFinanceAdapter(Protocol):
    def verify_funds(self, *, user_id: str, amount: float) -> bool: ...


class SandboxOpenFinance:
    def verify_funds(self, *, user_id: str, amount: float) -> bool:
        return True
