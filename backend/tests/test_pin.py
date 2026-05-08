from datetime import datetime, timedelta, timezone

import pytest

from app.core.pin import (
    LOCKOUT_DURATION,
    LockoutError,
    MAX_ATTEMPTS,
    hash_pin,
    register_failed_attempt,
    reset_attempts,
    verify_pin,
)


def test_hash_pin_returns_argon2_string() -> None:
    h = hash_pin("123456")
    assert h.startswith("$argon2"), "must use argon2 format"
    assert h != "123456"


def test_verify_pin_succeeds_with_correct_pin() -> None:
    h = hash_pin("123456")
    assert verify_pin("123456", h) is True


def test_verify_pin_fails_with_wrong_pin() -> None:
    h = hash_pin("123456")
    assert verify_pin("000000", h) is False


def test_register_failed_attempt_locks_after_max() -> None:
    """Returns the lockout-until timestamp once attempts hit MAX_ATTEMPTS."""
    state = {"attempts": MAX_ATTEMPTS - 1, "last_failed_at": None, "locked_until": None}
    register_failed_attempt(state)
    assert state["attempts"] == MAX_ATTEMPTS
    assert state["locked_until"] is not None
    assert state["locked_until"] > datetime.now(timezone.utc)


def test_locked_account_raises_until_lockout_expires() -> None:
    state = {"attempts": MAX_ATTEMPTS,
             "locked_until": datetime.now(timezone.utc) + LOCKOUT_DURATION}
    with pytest.raises(LockoutError):
        register_failed_attempt(state)


def test_reset_attempts_clears_state() -> None:
    state = {"attempts": 3, "last_failed_at": datetime.now(timezone.utc),
             "locked_until": None}
    reset_attempts(state)
    assert state["attempts"] == 0
    assert state["last_failed_at"] is None
