from unittest.mock import MagicMock, patch

from app.integrations.whatsapp import send_document


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "123456")


def test_send_document_uploads_then_sends_with_returned_media_id(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    upload_resp = MagicMock()
    upload_resp.json.return_value = {"id": "media-doc-1"}
    message_resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post",
               side_effect=[upload_resp, message_resp]) as mock_post:
        send_document(
            to_phone_e164="628123", doc_bytes=b"%PDF-fake",
            filename="Laporan-Analisis.pdf", caption="Laporan lengkap",
        )

    assert mock_post.call_count == 2

    upload_call = mock_post.call_args_list[0]
    assert upload_call.args[0] == "https://graph.facebook.com/v20.0/123456/media"
    assert upload_call.kwargs["files"]["file"][2] == "application/pdf"
    assert upload_call.kwargs["data"]["type"] == "application/pdf"

    message_call = mock_post.call_args_list[1]
    sent_json = message_call.kwargs["json"]
    assert sent_json["type"] == "document"
    assert sent_json["document"] == {
        "id": "media-doc-1", "filename": "Laporan-Analisis.pdf", "caption": "Laporan lengkap",
    }
    upload_resp.raise_for_status.assert_called_once()
    message_resp.raise_for_status.assert_called_once()


def test_send_document_omits_caption_key_when_none(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    upload_resp = MagicMock()
    upload_resp.json.return_value = {"id": "media-doc-2"}
    message_resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post",
               side_effect=[upload_resp, message_resp]) as mock_post:
        send_document(to_phone_e164="628123", doc_bytes=b"%PDF-fake", filename="a.pdf")

    sent_json = mock_post.call_args_list[1].kwargs["json"]
    assert sent_json["document"] == {"id": "media-doc-2", "filename": "a.pdf"}


def test_send_document_skips_silently_when_credentials_unset(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "")

    with patch("app.integrations.whatsapp.httpx.post") as mock_post:
        send_document(to_phone_e164="628123", doc_bytes=b"%PDF-fake", filename="a.pdf")

    mock_post.assert_not_called()


def test_send_document_catches_exception_from_upload_failure(monkeypatch) -> None:
    _configure_settings(monkeypatch)

    with patch("app.integrations.whatsapp.httpx.post", side_effect=Exception("network error")):
        send_document(to_phone_e164="628123", doc_bytes=b"%PDF-fake", filename="a.pdf")  # must not raise
