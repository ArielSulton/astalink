from unittest.mock import MagicMock, patch

from app.integrations.whatsapp import download_media


def test_download_media_returns_none_when_creds_unset(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "")
    assert download_media("media-123") is None


def test_download_media_fetches_bytes_and_mime_type(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "tok")

    meta_resp = MagicMock()
    meta_resp.json.return_value = {"url": "https://lookaside/media-123", "mime_type": "image/jpeg"}
    meta_resp.raise_for_status.return_value = None

    media_resp = MagicMock()
    media_resp.content = b"fake-jpeg-bytes"
    media_resp.raise_for_status.return_value = None

    with patch("app.integrations.whatsapp.httpx.get", side_effect=[meta_resp, media_resp]) as get_mock:
        result = download_media("media-123")

    assert result == (b"fake-jpeg-bytes", "image/jpeg")
    assert get_mock.call_count == 2
    assert get_mock.call_args_list[0].args[0].endswith("/media-123")
    assert get_mock.call_args_list[1].args[0] == "https://lookaside/media-123"


def test_download_media_returns_none_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "tok")
    with patch("app.integrations.whatsapp.httpx.get", side_effect=Exception("network error")):
        assert download_media("media-123") is None


def test_download_media_returns_none_when_url_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "tok")
    meta_resp = MagicMock()
    meta_resp.json.return_value = {"mime_type": "image/jpeg"}  # no "url" key
    meta_resp.raise_for_status.return_value = None

    with patch("app.integrations.whatsapp.httpx.get", return_value=meta_resp):
        assert download_media("media-123") is None


def test_download_media_uses_mime_type_fallback(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "tok")

    meta_resp = MagicMock()
    meta_resp.json.return_value = {"url": "https://lookaside/media-123"}  # no "mime_type" key
    meta_resp.raise_for_status.return_value = None

    media_resp = MagicMock()
    media_resp.content = b"fake-bytes"
    media_resp.raise_for_status.return_value = None

    with patch("app.integrations.whatsapp.httpx.get", side_effect=[meta_resp, media_resp]):
        result = download_media("media-123")

    assert result == (b"fake-bytes", "application/octet-stream")
