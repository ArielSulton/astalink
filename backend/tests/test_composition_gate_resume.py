from unittest.mock import MagicMock, patch

from app.agents.composition_gate.resume import (
    detect_composition_reply,
    find_pending_composition_audit,
)


def test_detect_composition_reply_recognizes_yes_variants() -> None:
    for text in ["ya", "Ya", "YA!", "iya", "setuju", "oke", "ok", "lanjut", "lanjutkan."]:
        assert detect_composition_reply(text) == "approved", text


def test_detect_composition_reply_recognizes_no_variants() -> None:
    for text in ["tidak", "Tidak.", "gak", "ga", "nggak", "batal", "stop", "berhenti"]:
        assert detect_composition_reply(text) == "rejected", text


def test_detect_composition_reply_returns_none_for_longer_phrases() -> None:
    """A confidently-worded longer reply (e.g. "ya, setuju") must NOT be
    guessed at — only an exact single-word yes/no counts, so a genuinely new
    message never gets silently swallowed as a gate reply."""
    assert detect_composition_reply("ya, setuju") is None
    assert detect_composition_reply("alokasikan 20 juta ke BBCA") is None
    assert detect_composition_reply("") is None


def test_find_pending_composition_audit_returns_latest_audit_id() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"audit_id": "audit-42"}],
        )
    assert find_pending_composition_audit(fake_admin, "thread-1") == "audit-42"


def test_find_pending_composition_audit_returns_none_when_empty() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    assert find_pending_composition_audit(fake_admin, "thread-1") is None


def test_find_pending_composition_audit_degrades_gracefully_on_error() -> None:
    fake_admin = MagicMock()
    fake_admin.table.side_effect = Exception("db down")
    assert find_pending_composition_audit(fake_admin, "thread-1") is None
