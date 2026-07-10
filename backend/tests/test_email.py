from unittest.mock import MagicMock, patch

from app.core.email import render_template, send_email


def test_render_template_replaces_placeholder(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.email._TEMPLATE_DIR", tmp_path)
    (tmp_path / "sample.html").write_text("<a href='{{ACTION_LINK}}'>Go</a>", encoding="utf-8")

    result = render_template("sample.html", action_link="https://example.com/verify")

    assert result == "<a href='https://example.com/verify'>Go</a>"


def test_send_email_calls_resend_with_correct_params(monkeypatch) -> None:
    monkeypatch.setattr("app.core.email.settings.RESEND_FROM_EMAIL", "noreply@astalink.my.id")

    with patch("app.core.email.resend") as mock_resend:
        send_email("user@example.com", "Test Subject", "<p>Hi</p>")

    mock_resend.Emails.send.assert_called_once_with({
        "from": "noreply@astalink.my.id",
        "to": "user@example.com",
        "subject": "Test Subject",
        "html": "<p>Hi</p>",
    })
