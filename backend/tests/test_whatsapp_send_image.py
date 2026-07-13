from unittest.mock import MagicMock, patch

from app.integrations.whatsapp import send_image


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "123456")


def test_send_image_uploads_then_sends_with_returned_media_id(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    upload_resp = MagicMock()
    upload_resp.json.return_value = {"id": "media-abc"}
    message_resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post",
               side_effect=[upload_resp, message_resp]) as mock_post:
        send_image(to_phone_e164="628123", image_bytes=b"\x89PNGfake", caption="Alokasi kamu")

    assert mock_post.call_count == 2

    upload_call = mock_post.call_args_list[0]
    assert upload_call.args[0] == "https://graph.facebook.com/v20.0/123456/media"
    assert upload_call.kwargs["files"]["file"][2] == "image/png"

    message_call = mock_post.call_args_list[1]
    assert message_call.args[0] == "https://graph.facebook.com/v20.0/123456/messages"
    sent_json = message_call.kwargs["json"]
    assert sent_json["type"] == "image"
    assert sent_json["image"] == {"id": "media-abc", "caption": "Alokasi kamu"}
    assert sent_json["to"] == "628123"

    upload_resp.raise_for_status.assert_called_once()
    message_resp.raise_for_status.assert_called_once()


def test_send_image_omits_caption_key_when_none(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    upload_resp = MagicMock()
    upload_resp.json.return_value = {"id": "media-xyz"}
    message_resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post",
               side_effect=[upload_resp, message_resp]) as mock_post:
        send_image(to_phone_e164="628123", image_bytes=b"\x89PNGfake")

    sent_json = mock_post.call_args_list[1].kwargs["json"]
    assert sent_json["image"] == {"id": "media-xyz"}


def test_send_image_skips_silently_when_credentials_unset(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "")

    with patch("app.integrations.whatsapp.httpx.post") as mock_post:
        send_image(to_phone_e164="628123", image_bytes=b"\x89PNGfake")

    mock_post.assert_not_called()


def test_send_image_catches_exception_from_upload_failure(monkeypatch) -> None:
    """Never let a WhatsApp API failure bubble up and crash the webhook
    handler — same defense-in-depth principle as the pipeline's own
    try/except in _process_message."""
    _configure_settings(monkeypatch)

    with patch("app.integrations.whatsapp.httpx.post", side_effect=Exception("network error")):
        send_image(to_phone_e164="628123", image_bytes=b"\x89PNGfake")  # must not raise
