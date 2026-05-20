"""PIN hashing + verification + lockout state machine.

State is a plain dict so the API layer can persist it to Supabase via the
service-role client; this module is pure logic, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

MAX_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

_ph = PasswordHasher()


class LockoutError(Exception):
    """Raised when an action is attempted on a locked account."""


def hash_pin(pin: str) -> str:
    return _ph.hash(pin)


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pin)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def is_locked(state: dict[str, Any]) -> bool:
    until = state.get("locked_until")
    if until is None:
        return False
    if isinstance(until, str):
        until = datetime.fromisoformat(until)
    return until > datetime.now(timezone.utc)


def register_failed_attempt(state: dict[str, Any]) -> None:
    """Mutates state in place. Raises LockoutError if already locked."""
    if is_locked(state):
        raise LockoutError("Account is locked")
    state["attempts"] = int(state.get("attempts", 0)) + 1
    state["last_failed_at"] = datetime.now(timezone.utc)
    if state["attempts"] >= MAX_ATTEMPTS:
        state["locked_until"] = datetime.now(timezone.utc) + LOCKOUT_DURATION


def reset_attempts(state: dict[str, Any]) -> None:
    state["attempts"] = 0
    state["last_failed_at"] = None
    state["locked_until"] = None
