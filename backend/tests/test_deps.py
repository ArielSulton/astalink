import pytest
from fastapi import HTTPException

from app.api.deps import is_admin_email, require_admin


def test_is_admin_email_true_for_configured_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"])
    assert is_admin_email("astalink21@gmail.com") is True


def test_is_admin_email_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"])
    assert is_admin_email("Astalink21@Gmail.com") is True


def test_is_admin_email_false_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"])
    assert is_admin_email("user@example.com") is False


def test_is_admin_email_false_for_none() -> None:
    assert is_admin_email(None) is False


def test_is_admin_email_false_when_admin_list_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", [])
    assert is_admin_email("astalink21@gmail.com") is False


def test_require_admin_passes_through_for_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"])
    user = {"sub": "user-1", "email": "astalink21@gmail.com"}
    assert require_admin(user) == user


def test_require_admin_raises_403_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"])
    with pytest.raises(HTTPException) as exc_info:
        require_admin({"sub": "user-1", "email": "user@example.com"})
    assert exc_info.value.status_code == 403
