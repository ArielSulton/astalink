from unittest.mock import MagicMock, patch

from app.integrations.whatsapp import send_buttons


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "123456")


def test_send_buttons_posts_interactive_button_payload(monkeypatch) -> None:
    _configure_settings(monkeypatch)
    resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post", return_value=resp) as mock_post:
        send_buttons(
            to_phone_e164="628123", body="Setuju dengan komposisi ini?",
            buttons=[("ya", "Ya, Lanjutkan"), ("tidak", "Tidak, Batalkan")],
        )

    mock_post.assert_called_once()
    call = mock_post.call_args
    assert call.args[0] == "https://graph.facebook.com/v20.0/123456/messages"
    sent = call.kwargs["json"]
    assert sent["to"] == "628123"
    assert sent["type"] == "interactive"
    assert sent["interactive"]["type"] == "button"
    assert sent["interactive"]["body"]["text"] == "Setuju dengan komposisi ini?"
    reply_buttons = sent["interactive"]["action"]["buttons"]
    assert reply_buttons == [
        {"type": "reply", "reply": {"id": "ya", "title": "Ya, Lanjutkan"}},
        {"type": "reply", "reply": {"id": "tidak", "title": "Tidak, Batalkan"}},
    ]
    resp.raise_for_status.assert_called_once()


def test_send_buttons_caps_at_three_and_truncates_long_titles(monkeypatch) -> None:
    _configure_settings(monkeypatch)
    resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post", return_value=resp) as mock_post:
        send_buttons(
            to_phone_e164="628123", body="pick one",
            buttons=[("a", "Ini judul tombol yang sangat panjang sekali"),
                     ("b", "two"), ("c", "three"), ("d", "four (dropped)")],
        )

    reply_buttons = mock_post.call_args.kwargs["json"]["interactive"]["action"]["buttons"]
    assert len(reply_buttons) == 3
    assert len(reply_buttons[0]["reply"]["title"]) <= 20
    assert [b["reply"]["id"] for b in reply_buttons] == ["a", "b", "c"]


def test_send_buttons_skips_silently_when_credentials_unset(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "")

    with patch("app.integrations.whatsapp.httpx.post") as mock_post:
        send_buttons(to_phone_e164="628123", body="x", buttons=[("ya", "Ya")])

    mock_post.assert_not_called()


def test_send_buttons_catches_exception(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    with patch("app.integrations.whatsapp.httpx.post", side_effect=Exception("network error")):
        send_buttons(to_phone_e164="628123", body="x", buttons=[("ya", "Ya")])  # must not raise
