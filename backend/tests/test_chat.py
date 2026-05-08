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
    """Exercises the chat endpoint end-to-end with mocked auth + Gemini.

    The chat_node should call `app.core.gemini.get_chat_model()` and use
    the returned (mocked) model — this verifies the Gemini wiring."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "test@example.com"}

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = AIMessage(content="Hello from Gemini!")

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.agents.chat_agent.get_chat_model", return_value=fake_llm):

        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello from Gemini!"
    assert "thread_id" in data
    fake_llm.invoke.assert_called_once()
