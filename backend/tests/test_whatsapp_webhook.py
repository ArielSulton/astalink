import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


def test_webhook_get_verifies_subscription(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "appsec")
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "secret123",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_get_rejects_wrong_verify_token(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 403


def test_webhook_post_dedupes_replays(client: TestClient, monkeypatch) -> None:
    """Same Meta message_id arriving twice must invoke the graph at most once."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.MSG-ABC",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "alokasikan ke BBCA"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    # First call: row doesn't exist — insert succeeds.
    # Second call: insert fails on PK conflict — caught and treated as already-seen.
    insert_mock = fake_admin.table.return_value.insert
    insert_mock.return_value.execute.side_effect = [
        MagicMock(data=[{}]),       # first
        Exception("duplicate key"),  # second
    ]
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    invoke_mock = MagicMock(return_value={"messages": [], "transactions": [],
                                          "audit_id": "abc", "user_approval": "approved"})

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", invoke_mock), \
         patch("app.api.v1.whatsapp.send_text"):
        # First delivery
        r1 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})
        # Replay
        r2 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})

    assert r1.status_code == 200 and r2.status_code == 200
    assert invoke_mock.call_count == 1, "graph must run exactly once for a replayed message_id"

    # _thread_id must match the config thread_id so intent_node can persist
    # it to audit_log for approvals.py to resume the same run later.
    initial_state, call_kwargs = invoke_mock.call_args[0][0], invoke_mock.call_args.kwargs
    assert initial_state["_thread_id"] == call_kwargs["config"]["configurable"]["thread_id"]


def _post_wa_message(client: TestClient, monkeypatch, *, message_id: str, text: str,
                     final_state: dict) -> str:
    """Send one signed WhatsApp webhook payload and return the text passed to
    send_text (an AttributeError is raised if send_text was never called)."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": message_id,
            "from": "6281234567890",
            "type": "text",
            "text": {"body": text},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=final_state), \
         patch("app.api.v1.whatsapp.send_text") as send_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})
        assert resp.status_code == 200
        send_mock.assert_called_once()
        return send_mock.call_args.kwargs["body"]


def test_whatsapp_reply_for_informational_intent_has_no_approval_link(monkeypatch, client: TestClient) -> None:
    """Before this fix, ANY reply with user_approval is None — including
    EXPLAIN/evaluate_business/risk_review answers, which never touch HITL —
    was wrongly sent as 'Saya sudah menyiapkan rekomendasi alokasi, review
    & approve di: .../approvals/{audit_id}'. An informational answer must be
    relayed as-is, with no approval link appended."""
    final_state = {
        "audit_id": "audit-explain-1",
        "intent": "explain",
        "messages": [AIMessage(content="RSI (Relative Strength Index) mengukur momentum harga.")],
        "legal_status": None,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.EXPLAIN-1",
                            text="apa itu RSI?", final_state=final_state)

    assert body == "RSI (Relative Strength Index) mengukur momentum harga."
    assert "approvals" not in body.lower()
    assert "rekomendasi alokasi" not in body.lower()


def test_whatsapp_reply_appends_approval_link_when_awaiting_hitl(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus

    final_state = {
        "audit_id": "audit-hitl-1",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.HITL-1",
                            text="alokasikan 10jt ke BBCA", final_state=final_state)

    assert "Approvals" in body
    assert "audit-hitl-1" in body
    assert body.endswith("/approvals/audit-hitl-1")


def test_whatsapp_reply_appends_audit_link_after_execution(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus, UserApproval

    final_state = {
        "audit_id": "audit-exec-1",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": UserApproval.APPROVED,
        "transactions": [
            {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled", "broker_ref": "r1"},
        ],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.EXEC-1",
                            text="ya, setuju", final_state=final_state)

    assert "BBCA" in body
    assert "berhasil dieksekusi" in body.lower()
    assert body.endswith("/audit/audit-exec-1")


def test_whatsapp_sends_fallback_reply_when_pipeline_raises(monkeypatch, client: TestClient) -> None:
    """Reproduces a live incident: optimizer_node crashed with an unhandled
    TypeError (comparing a string "amount" entity to a float balance), the
    exception propagated all the way up through this webhook handler, the
    request 500'd, and send_text() was never reached — the user saw no
    reply at all with zero indication anything failed. The pipeline must
    never be allowed to fail silently."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.CRASH-1",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "rekomendasi invest dana 20 juta rupiah"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke",
               side_effect=TypeError("'<' not supported between instances of 'float' and 'str'")), \
         patch("app.api.v1.whatsapp.send_text") as send_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})

    assert resp.status_code == 200
    send_mock.assert_called_once()
    reply = send_mock.call_args.kwargs["body"]
    assert reply
    assert "maaf" in reply.lower()


def _post_wa_message_with_chart_mocks(client: TestClient, monkeypatch, *, message_id: str,
                                      text: str, final_state: dict):
    """Same signed-payload setup as _post_wa_message, but also mocks
    render_allocation_chart/render_report_table_chart/send_image/send_document
    so all can be asserted on. Returns
    (send_text_mock, send_image_mock, render_chart_mock, document_mock)."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": message_id,
            "from": "6281234567890",
            "type": "text",
            "text": {"body": text},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=final_state), \
         patch("app.api.v1.whatsapp.render_allocation_chart", return_value=b"fake-png-bytes") as render_mock, \
         patch("app.api.v1.whatsapp.render_report_table_chart", return_value=b"fake-table-png"), \
         patch("app.api.v1.whatsapp.render_allocation_pdf", return_value=None), \
         patch("app.api.v1.whatsapp.send_image") as image_mock, \
         patch("app.api.v1.whatsapp.send_document") as document_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})
        assert resp.status_code == 200
        return text_mock, image_mock, render_mock, document_mock


def test_whatsapp_sends_chart_image_when_hitl_pending(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus

    final_state = {
        "audit_id": "audit-chart-1",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": None,
        "allocation_plan": {
            "weights": [{"ticker": "BBCA", "weight": 0.6}, {"ticker": "TLKM", "weight": 0.3}],
            "cash": 2_000_000, "cash_buffer": 0.1,
            "narration": "n", "relaxations_applied": [],
        },
        "transactions": [],
        "errors": [],
    }
    text_mock, image_mock, render_mock, document_mock = _post_wa_message_with_chart_mocks(
        client, monkeypatch, message_id="wamid.CHART-1",
        text="alokasikan 20jt ke BBCA dan TLKM", final_state=final_state,
    )

    render_mock.assert_called_once_with(final_state["allocation_plan"]["weights"], 0.1)
    # Allocation donut + the verdict/weight table image.
    assert image_mock.call_count == 2
    assert image_mock.call_args_list[0].kwargs["image_bytes"] == b"fake-png-bytes"
    assert image_mock.call_args_list[0].kwargs["to_phone_e164"] == "6281234567890"
    assert image_mock.call_args_list[1].kwargs["image_bytes"] == b"fake-table-png"
    document_mock.assert_not_called()  # render_allocation_pdf mocked to None here
    text_mock.assert_called_once()  # the link/text reply must still be sent


def test_whatsapp_sends_chart_image_after_execution(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus, UserApproval

    final_state = {
        "audit_id": "audit-chart-2",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": UserApproval.APPROVED,
        "allocation_plan": {
            "weights": [{"ticker": "BBCA", "weight": 0.9}],
            "cash": 1_000_000, "cash_buffer": 0.1,
            "narration": "n", "relaxations_applied": [],
        },
        "transactions": [
            {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled", "broker_ref": "r1"},
        ],
        "errors": [],
    }
    text_mock, image_mock, render_mock, document_mock = _post_wa_message_with_chart_mocks(
        client, monkeypatch, message_id="wamid.CHART-2",
        text="ya, setuju", final_state=final_state,
    )

    render_mock.assert_called_once()
    assert image_mock.call_count == 2  # allocation donut + verdict/weight table
    text_mock.assert_called_once()


def test_whatsapp_does_not_send_chart_for_informational_reply(monkeypatch, client: TestClient) -> None:
    """explain/evaluate_business/risk_review/portfolio_status replies have
    no allocation_plan at all — no chart to send."""
    final_state = {
        "audit_id": "audit-chart-3",
        "intent": "explain",
        "messages": [AIMessage(content="RSI mengukur momentum harga.")],
        "legal_status": None,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }
    text_mock, image_mock, render_mock, document_mock = _post_wa_message_with_chart_mocks(
        client, monkeypatch, message_id="wamid.CHART-3",
        text="apa itu RSI?", final_state=final_state,
    )

    render_mock.assert_not_called()
    image_mock.assert_not_called()
    text_mock.assert_called_once()


def test_whatsapp_chart_failure_does_not_block_text_reply(monkeypatch, client: TestClient) -> None:
    """A chart render/upload failure must never prevent the text reply
    (which carries the actual approve/detail link) from sending."""
    from app.agents.state import LegalStatus

    final_state = {
        "audit_id": "audit-chart-4",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": None,
        "allocation_plan": {
            "weights": [{"ticker": "BBCA", "weight": 0.6}],
            "cash": 1_000_000, "cash_buffer": 0.4,
            "narration": "n", "relaxations_applied": [],
        },
        "transactions": [],
        "errors": [],
    }

    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.CHART-4",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "alokasikan 20jt ke BBCA"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=final_state), \
         patch("app.api.v1.whatsapp.render_allocation_chart", side_effect=Exception("render blew up")), \
         patch("app.api.v1.whatsapp.render_report_table_chart", return_value=b"fake-table-png"), \
         patch("app.api.v1.whatsapp.render_allocation_pdf", return_value=None), \
         patch("app.api.v1.whatsapp.send_image") as image_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})

    assert resp.status_code == 200
    # The donut chart failed, but the verdict/weight table image is an
    # independent try/except and must still send.
    image_mock.assert_called_once()
    assert image_mock.call_args.kwargs["image_bytes"] == b"fake-table-png"
    text_mock.assert_called_once()
    assert "approve" in text_mock.call_args.kwargs["body"].lower() or \
           "approvals" in text_mock.call_args.kwargs["body"].lower()


def test_whatsapp_sends_buttons_instead_of_text_when_composition_gate_pauses(
    monkeypatch, client: TestClient,
) -> None:
    """A fresh ALLOCATE_CAPITAL pause must offer tappable Ya/Tidak buttons,
    not just a plain-text instruction to type ya/tidak."""
    final_state = {
        "audit_id": "audit-comp-1",
        "intent": "allocate_capital",
        "messages": [AIMessage(content="Berikut komposisi kas/saham/bisnis Anda.")],
        "legal_status": None,
        "user_approval": None,
        "transactions": [],
        "errors": [],
        "layer0_result": {
            "status": "recommended",
            "allocation": {"cash": 0.25, "stocks": 0.25, "business": 0.5},
        },
        "__interrupt__": [object()],
    }

    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.COMP-1",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "50 juta mending buat modal bisnis atau beli saham BBCA?"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=final_state), \
         patch("app.api.v1.whatsapp.render_composition_chart", return_value=b"fake-comp-png") as chart_mock, \
         patch("app.api.v1.whatsapp.send_image") as image_mock, \
         patch("app.api.v1.whatsapp.send_buttons") as buttons_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})

    assert resp.status_code == 200
    chart_mock.assert_called_once_with(0.25, 0.25, 0.5)
    image_mock.assert_called_once()
    buttons_mock.assert_called_once()
    assert buttons_mock.call_args.kwargs["to_phone_e164"] == "6281234567890"
    assert buttons_mock.call_args.kwargs["buttons"] == [
        ("ya", "Ya, Lanjutkan"), ("tidak", "Tidak, Batalkan"),
    ]
    text_mock.assert_not_called()  # buttons replace the plain-text prompt


def test_whatsapp_button_tap_resumes_composition_gate(monkeypatch, client: TestClient) -> None:
    """An inbound interactive button_reply (id="ya"/"tidak") must resume the
    paused graph exactly like a typed "ya"/"tidak" text reply."""
    resumed_state = {
        "audit_id": "audit-comp-2",
        "intent": "allocate_capital",
        "messages": [AIMessage(content="Lanjut ke analisis saham.")],
        "legal_status": None,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }

    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.COMP-BTN-1",
            "from": "6281234567890",
            "type": "interactive",
            "interactive": {"type": "button_reply", "button_reply": {"id": "ya", "title": "Ya, Lanjutkan"}},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.find_pending_composition_audit", return_value="audit-comp-2"), \
         patch("app.api.v1.whatsapp.resume_composition", return_value=resumed_state) as resume_mock, \
         patch("app.api.v1.whatsapp.graph.invoke") as invoke_mock, \
         patch("app.api.v1.whatsapp.send_text") as text_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})

    assert resp.status_code == 200
    resume_mock.assert_called_once()
    assert resume_mock.call_args.args[1] == "approved"
    invoke_mock.assert_not_called()  # resumed, not a fresh turn
    text_mock.assert_called_once()
