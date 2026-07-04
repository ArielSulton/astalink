import pytest

# Skip locally if talib isn't installed — graph.py now imports market_node which imports talib.
pytest.importorskip("talib")

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.agents.state import LegalStatus, UserApproval


def test_agent_run_returns_final_state(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4()), "email": "u@test.com"}
    workspace_id = str(uuid.uuid4())

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": workspace_id}])

    fake_final = {
        "audit_id": "abc",
        "intent": "allocate_stocks",
        "legal_status": LegalStatus.APPROVED,
        "user_approval": UserApproval.APPROVED,
        "allocation_plan": {"weights": [{"ticker": "BBCA", "weight": 1.0}]},
        "transactions": [{"ticker": "BBCA", "weight": 1.0, "status": "simulated"}],
        "messages": [],
        "errors": [],
        "legal_citations": [],
        "revision_count": 1,
        "entities": {},
    }

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.agent.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.agent.graph.invoke", return_value=fake_final):
        resp = client.post(
            "/api/v1/agent/run",
            json={"message": "alokasikan 10jt ke BBCA", "workspace_id": workspace_id},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["legal_status"] == "approved"
    assert body["transactions"][0]["status"] == "simulated"


def test_agent_run_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/agent/run", json={"message": "x", "workspace_id": "x"})
    assert resp.status_code == 401
