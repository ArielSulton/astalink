import uuid
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.models.journey import JourneyHomeResponse, NextAction, ReadinessSummary


def test_journey_home_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/journey/home?workspace_id=ws-1").status_code == 401


def test_journey_home_rejects_unowned_workspace(client: TestClient) -> None:
    with (
        patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}),
        patch("app.api.v1.journey.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.v1.journey.assert_workspace_owned",
            side_effect=HTTPException(403, "forbidden"),
        ),
    ):
        response = client.get(
            "/api/v1/journey/home?workspace_id=ws-1",
            headers={"Authorization": "Bearer x"},
        )
    assert response.status_code == 403


def test_journey_home_returns_projection(client: TestClient) -> None:
    payload = JourneyHomeResponse(
        workspace_id="ws-1",
        workspace_name="Personal",
        workspace_type="personal",
        generated_at="2026-09-20T03:30:00Z",
        readiness_summary=ReadinessSummary(status="needs_input"),
        next_action=NextAction(
            kind="ask_asta",
            title="Mulai",
            rationale="Mulai",
            href="/chatbot",
            rule_id="fallback",
        ),
    )
    with (
        patch("app.api.deps.verify_token", return_value={"sub": str(uuid.uuid4())}),
        patch("app.api.v1.journey.get_admin_client", return_value=MagicMock()),
        patch("app.api.v1.journey.assert_workspace_owned"),
        patch("app.api.v1.journey.build_journey_home", return_value=payload),
    ):
        response = client.get(
            "/api/v1/journey/home?workspace_id=ws-1",
            headers={"Authorization": "Bearer x"},
        )
    assert response.status_code == 200
    assert response.json()["next_action"]["kind"] == "ask_asta"
