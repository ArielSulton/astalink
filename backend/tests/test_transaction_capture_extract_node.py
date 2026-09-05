from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.node import extract_node
from app.agents.transaction_capture.schemas import TransactionExtraction


def test_extract_node_passes_gate_for_a_confident_transaction() -> None:
    state = {
        "source": "whatsapp_text", "text_body": "jual nasi goreng 15rb",
        "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123",
    }
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description="Nasi goreng", amount=15000.0,
        type="income", confidence=0.9, raw_input="jual nasi goreng 15rb",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is False
    assert update["extraction"]["amount"] == 15000.0
    assert update["media_bytes"] is None
    assert update["media_mime_type"] is None


def test_extract_node_gates_out_a_non_transaction() -> None:
    state = {"source": "whatsapp_text", "text_body": "halo apa kabar",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_extraction = TransactionExtraction(
        is_transaction=False, confidence=0.2, raw_input="halo apa kabar",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True


def test_extract_node_gates_out_low_confidence_even_if_is_transaction_true() -> None:
    state = {"source": "whatsapp_text", "text_body": "mungkin jual sesuatu?",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description="?", amount=1000.0,
        type="income", confidence=0.3, raw_input="mungkin jual sesuatu?",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True


def test_extract_node_gates_out_null_amount_even_if_confident() -> None:
    state = {"source": "whatsapp_text", "text_body": "dapat uang dari seseorang",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description=None, amount=None,
        type="income", confidence=0.9, raw_input="dapat uang dari seseorang",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True


def test_extract_node_gates_out_null_type_even_if_confident() -> None:
    state = {"source": "whatsapp_text", "text_body": "ada transaksi 15rb",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description="?", amount=15000.0,
        type=None, confidence=0.9, raw_input="ada transaksi 15rb",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True


def test_extract_node_gates_out_non_positive_amount() -> None:
    state = {"source": "whatsapp_text", "text_body": "jual barang -500",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description="Barang", amount=-500.0,
        type="income", confidence=0.9, raw_input="jual barang -500",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True


def test_extract_node_builds_multimodal_content_for_a_photo() -> None:
    state = {
        "source": "whatsapp_photo", "media_bytes": b"fake-jpeg-bytes",
        "media_mime_type": "image/jpeg", "business_id": "biz-1",
        "workspace_id": "ws-1", "phone_e164": "628123",
    }
    fake_extraction = TransactionExtraction(
        is_transaction=True, item_description="Struk belanja", amount=50000.0,
        type="expense", confidence=0.85, raw_input="struk: total 50.000",
    )
    fake_chain = MagicMock()
    fake_chain.invoke.return_value = fake_extraction

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        extract_node(state)

    sent_messages = fake_chain.invoke.call_args[0][0]
    human_content = sent_messages[-1].content
    assert isinstance(human_content, list)
    media_block = next(b for b in human_content if b.get("type") == "media")
    assert media_block["mime_type"] == "image/jpeg"


def test_build_chain_uses_vision_model_for_photo_source() -> None:
    """SumoPod's DeepSeek proxy doesn't accept images — photo extraction
    must always use get_vision_model() (pinned to Gemini), never
    get_chat_model() (which follows LLM_PROVIDER)."""
    from app.agents.transaction_capture.node import _build_chain
    _build_chain.cache_clear()
    fake_vision_llm = MagicMock()
    fake_vision_llm.with_structured_output.return_value = "vision-chain"

    with patch("app.agents.transaction_capture.node.get_vision_model", return_value=fake_vision_llm) as vision_mock, \
         patch("app.agents.transaction_capture.node.get_chat_model") as chat_mock:
        chain = _build_chain("whatsapp_photo")

    vision_mock.assert_called_once()
    chat_mock.assert_not_called()
    fake_vision_llm.with_structured_output.assert_called_once_with(TransactionExtraction, method="json_schema")
    assert chain == "vision-chain"
    _build_chain.cache_clear()


def test_build_chain_uses_vision_model_for_voice_source() -> None:
    """Same reasoning as photo — voice notes are also multimodal input the
    DeepSeek proxy can't accept."""
    from app.agents.transaction_capture.node import _build_chain
    _build_chain.cache_clear()
    fake_vision_llm = MagicMock()
    fake_vision_llm.with_structured_output.return_value = "vision-chain"

    with patch("app.agents.transaction_capture.node.get_vision_model", return_value=fake_vision_llm) as vision_mock, \
         patch("app.agents.transaction_capture.node.get_chat_model") as chat_mock:
        chain = _build_chain("whatsapp_voice")

    vision_mock.assert_called_once()
    chat_mock.assert_not_called()
    assert chain == "vision-chain"
    _build_chain.cache_clear()


def test_build_chain_uses_chat_model_for_text_source() -> None:
    """Plain text extraction keeps following LLM_PROVIDER via
    get_chat_model() — only multimodal sources are pinned to Gemini."""
    from app.agents.transaction_capture.node import _build_chain
    _build_chain.cache_clear()
    fake_chat_llm = MagicMock()
    fake_chat_llm.with_structured_output.return_value = "text-chain"

    with patch("app.agents.transaction_capture.node.get_chat_model", return_value=fake_chat_llm) as chat_mock, \
         patch("app.agents.transaction_capture.node.get_vision_model") as vision_mock:
        chain = _build_chain("whatsapp_text")

    chat_mock.assert_called_once()
    vision_mock.assert_not_called()
    assert chain == "text-chain"
    _build_chain.cache_clear()


def test_extract_node_handles_llm_exception_gracefully() -> None:
    state = {"source": "whatsapp_text", "text_body": "jual nasi goreng 15rb",
             "business_id": "biz-1", "workspace_id": "ws-1", "phone_e164": "628123"}
    fake_chain = MagicMock()
    fake_chain.invoke.side_effect = RuntimeError("LLM quota exceeded")

    with patch("app.agents.transaction_capture.node._build_chain", return_value=fake_chain):
        update = extract_node(state)

    assert update["gate_failed"] is True
    assert update["extraction"] is None
