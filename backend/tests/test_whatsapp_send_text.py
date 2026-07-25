from unittest.mock import MagicMock, patch

from app.integrations.whatsapp import _normalize_for_whatsapp, send_text


def _configure_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("app.integrations.whatsapp.settings.WHATSAPP_PHONE_NUMBER_ID", "123456")


def test_normalize_converts_double_and_triple_asterisk_bold_to_single() -> None:
    """WhatsApp only renders single-asterisk *bold* — an LLM defaulting to
    standard Markdown (**bold** / ***bold***) would otherwise show up as
    literal asterisks in the delivered message."""
    assert _normalize_for_whatsapp("Harga **BBCA** naik") == "Harga *BBCA* naik"
    assert _normalize_for_whatsapp("***Penting***: cek dulu") == "*Penting*: cek dulu"


def test_normalize_converts_markdown_headers_to_plain_bold_line() -> None:
    assert _normalize_for_whatsapp("### Analisis\nIsi teks") == "*Analisis*\nIsi teks"


def test_normalize_strips_em_and_en_dashes() -> None:
    assert _normalize_for_whatsapp("Harga naik — tren positif") == "Harga naik - tren positif"
    assert _normalize_for_whatsapp("50–100") == "50-100"


def test_normalize_leaves_already_whatsapp_safe_text_untouched() -> None:
    text = "Harga *BBCA* saat ini stabil, dengan tren naik tipis."
    assert _normalize_for_whatsapp(text) == text


def test_send_text_normalizes_body_before_sending(monkeypatch) -> None:
    _configure_settings(monkeypatch)
    message_resp = MagicMock()

    with patch("app.integrations.whatsapp.httpx.post", return_value=message_resp) as mock_post:
        send_text(to_phone_e164="628123", body="**Harga** naik — tipis")

    sent_json = mock_post.call_args.kwargs["json"]
    assert sent_json["text"]["body"] == "*Harga* naik - tipis"
