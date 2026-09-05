import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _binding_admin() -> MagicMock:
    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"},
    )
    return fake_admin


def test_photo_message_routes_to_capture_not_advisory_graph(monkeypatch, client: TestClient) -> None:
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.PHOTO-1",
            "from": "6281234567890",
            "type": "image",
            "image": {"id": "media-abc"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)

    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.download_media", return_value=(b"jpeg-bytes", "image/jpeg")), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_buttons") as buttons_mock:
        fake_capture_graph.invoke.return_value = {
            "__interrupt__": [type("I", (), {"value": {
                "transaction_id": "txn-1", "item_description": "Struk belanja",
                "amount": 50000.0, "type": "expense", "plausibility_flag": False,
            }})()],
        }
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    fake_capture_graph.invoke.assert_called_once()
    advisory_invoke_mock.assert_not_called()
    buttons_mock.assert_called_once()
    assert buttons_mock.call_args.kwargs["buttons"] == [("txn_ya", "Ya, Benar"), ("txn_tidak", "Tidak, Batalkan")]


def test_gate_failed_sends_clarifying_text_not_confirmation_card(monkeypatch, client: TestClient) -> None:
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.AMBIGUOUS-1", "from": "6281234567890",
            "type": "text", "text": {"body": "jual sesuatu entah berapa"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.looks_like_transaction", return_value=True), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        fake_capture_graph.invoke.return_value = {"gate_failed": True, "extraction": None}
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    advisory_invoke_mock.assert_not_called()
    text_mock.assert_called_once()
    assert "tidak" in text_mock.call_args.kwargs["body"].lower() or \
           "maaf" in text_mock.call_args.kwargs["body"].lower()


def test_advisory_question_with_no_transaction_signal_is_not_misrouted(monkeypatch, client: TestClient) -> None:
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.ADVISORY-1", "from": "6281234567890",
            "type": "text",
            "text": {"body": "bisnis warung saya lagi rame, pengaruhnya ke rekomendasi gimana?"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    advisory_final = {"audit_id": "a1", "intent": "explain", "messages": [], "legal_status": None,
                      "user_approval": None, "transactions": [], "errors": []}

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.looks_like_transaction", return_value=False), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=advisory_final), \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    fake_capture_graph.invoke.assert_not_called()
    text_mock.assert_called_once()


def test_pending_confirmation_reply_resumes_capture_not_advisory(monkeypatch, client: TestClient) -> None:
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.CONFIRM-1", "from": "6281234567890",
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "ya", "title": "Ya, Benar"}},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value="txn-1"), \
         patch("app.api.v1.whatsapp.resume_transaction", return_value={"confirmed": True}) as resume_mock, \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    resume_mock.assert_called_once_with("wa-txn-6281234567890-w1", "confirmed")
    advisory_invoke_mock.assert_not_called()
    text_mock.assert_called_once()


def test_new_photo_while_confirmation_pending_is_deflected_not_overwritten(monkeypatch, client: TestClient) -> None:
    """A second photo arriving while a confirmation is still pending must
    NOT start a fresh capture_graph.invoke() on the same thread (that would
    silently overwrite the paused checkpoint and orphan the first row) —
    it gets deflected back to "answer the pending one first"."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.SECOND-PHOTO-1", "from": "6281234567890",
            "type": "image", "image": {"id": "media-y"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value="txn-existing"), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.download_media") as download_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    download_mock.assert_not_called()
    fake_capture_graph.invoke.assert_not_called()
    text_mock.assert_called_once()
    assert "menunggu konfirmasi" in text_mock.call_args.kwargs["body"].lower()


def test_zero_or_multiple_businesses_redirects_to_dashboard(monkeypatch, client: TestClient) -> None:
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.NOBIZ-1", "from": "6281234567890",
            "type": "image", "image": {"id": "media-x"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value=None), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    fake_capture_graph.invoke.assert_not_called()
    advisory_invoke_mock.assert_not_called()
    text_mock.assert_called_once()
    assert "dashboard" in text_mock.call_args.kwargs["body"].lower() or \
           "aplikasi" in text_mock.call_args.kwargs["body"].lower()


def test_photo_capture_exception_sends_fallback_reply_not_500(monkeypatch, client: TestClient) -> None:
    """Reproduces the same failure mode test_whatsapp_sends_fallback_reply_when_pipeline_raises
    guards against on the advisory path: _already_seen() marks the message id as processed
    BEFORE any pipeline logic runs, so if capture_graph.invoke() raises (e.g. a Supabase write
    failure inside a node), the webhook must still return 200 and the user must still get a
    reply — a 500 here, or silence, would leave a WhatsApp retry of the same message_id silently
    swallowed with zero indication anything failed."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.PHOTO-CRASH-1",
            "from": "6281234567890",
            "type": "image",
            "image": {"id": "media-crash"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.download_media", return_value=(b"jpeg-bytes", "image/jpeg")), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.send_text") as text_mock, \
         patch("app.api.v1.whatsapp.send_buttons") as buttons_mock:
        fake_capture_graph.invoke.side_effect = Exception("db write failed")
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    buttons_mock.assert_not_called()
    text_mock.assert_called_once()
    reply = text_mock.call_args.kwargs["body"]
    assert reply
    assert "maaf" in reply.lower()


def test_ambiguous_text_capture_exception_sends_fallback_reply_not_500(monkeypatch, client: TestClient) -> None:
    """Same failure mode as test_photo_capture_exception_sends_fallback_reply_not_500, but for
    the ambiguous-text branch's capture_graph.invoke() call site."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.TEXT-CRASH-1", "from": "6281234567890",
            "type": "text", "text": {"body": "jual nasi goreng 15rb"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value=None), \
         patch("app.api.v1.whatsapp.looks_like_transaction", return_value=True), \
         patch("app.api.v1.whatsapp.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        fake_capture_graph.invoke.side_effect = Exception("checkpoint write failed")
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    advisory_invoke_mock.assert_not_called()
    text_mock.assert_called_once()
    reply = text_mock.call_args.kwargs["body"]
    assert reply
    assert "maaf" in reply.lower()


def test_pending_confirmation_resume_exception_sends_fallback_reply_not_500(monkeypatch, client: TestClient) -> None:
    """Same failure mode again, for the pending-confirmation branch's resume_transaction() call
    site — a failure here (e.g. persist_node's Supabase write) must not 500 or go silent."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.CONFIRM-CRASH-1", "from": "6281234567890",
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "ya", "title": "Ya, Benar"}},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    fake_admin = _binding_admin()

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.resolve_single_business", return_value="biz-1"), \
         patch("app.api.v1.whatsapp.find_pending_transaction", return_value="txn-1"), \
         patch("app.api.v1.whatsapp.resume_transaction", side_effect=Exception("persist failed")), \
         patch("app.api.v1.whatsapp.graph.invoke") as advisory_invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})

    assert resp.status_code == 200
    advisory_invoke_mock.assert_not_called()
    text_mock.assert_called_once()
    reply = text_mock.call_args.kwargs["body"]
    assert reply
    assert "maaf" in reply.lower()
