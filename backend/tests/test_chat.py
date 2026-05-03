import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


def test_chat_endpoint_without_auth_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/",
        json={"message": "Hello"},
    )
    assert response.status_code == 401


def test_chat_endpoint_with_mocked_auth_and_agent(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4()), "email": "test@example.com"}

    mock_result = {
        "messages": [
            MagicMock(spec=AIMessage, content="Hello from AI!")
        ]
    }

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.agents.chat_agent.chat_graph.invoke", return_value=mock_result):

        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "thread_id" in data
    assert data["message"] == "Hello from AI!"
