from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_signup_creates_user_and_sends_confirmation_email(client: TestClient) -> None:
    fake_admin = MagicMock()
    fake_link_res = MagicMock()
    fake_link_res.properties.action_link = "https://supabase.example/verify?token=abc"
    fake_admin.auth.admin.generate_link.return_value = fake_link_res

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.auth.render_template", return_value="<html>confirm</html>") as mock_render, \
         patch("app.api.v1.auth.send_email") as mock_send:
        resp = client.post("/api/v1/auth/signup", json={
            "email": "user@example.com", "password": "supersecret",
        })

    assert resp.status_code == 200
    fake_admin.auth.admin.create_user.assert_called_once_with({
        "email": "user@example.com", "password": "supersecret", "email_confirm": False,
    })
    generate_link_call = fake_admin.auth.admin.generate_link.call_args[0][0]
    assert generate_link_call["type"] == "signup"
    assert generate_link_call["email"] == "user@example.com"
    mock_render.assert_called_once_with(
        "confirm_signup.html", action_link="https://supabase.example/verify?token=abc",
    )
    mock_send.assert_called_once_with(
        "user@example.com", "Konfirmasi akun Astalink kamu", "<html>confirm</html>",
    )


def test_signup_rejects_short_password(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/signup", json={
        "email": "user@example.com", "password": "abc",
    })
    assert resp.status_code == 422


def test_signup_returns_400_when_create_user_fails(client: TestClient) -> None:
    fake_admin = MagicMock()
    fake_admin.auth.admin.create_user.side_effect = Exception("User already registered")

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin):
        resp = client.post("/api/v1/auth/signup", json={
            "email": "user@example.com", "password": "supersecret",
        })

    assert resp.status_code == 400


def test_signup_deletes_orphaned_user_when_confirmation_email_fails(client: TestClient) -> None:
    fake_admin = MagicMock()
    fake_user = MagicMock()
    fake_user.id = "user-123"
    fake_admin.auth.admin.create_user.return_value = MagicMock(user=fake_user)
    fake_admin.auth.admin.generate_link.side_effect = Exception("Resend API down")

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin):
        resp = client.post("/api/v1/auth/signup", json={
            "email": "user@example.com", "password": "supersecret",
        })

    assert resp.status_code == 500
    fake_admin.auth.admin.delete_user.assert_called_once_with("user-123")


def test_forgot_password_sends_email_when_user_exists(client: TestClient) -> None:
    fake_admin = MagicMock()
    fake_link_res = MagicMock()
    fake_link_res.properties.action_link = "https://supabase.example/verify?token=xyz"
    fake_admin.auth.admin.generate_link.return_value = fake_link_res

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.auth.render_template", return_value="<html>reset</html>"), \
         patch("app.api.v1.auth.send_email") as mock_send:
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})

    assert resp.status_code == 200
    assert resp.json()["message"] == "Jika email terdaftar, kami sudah mengirim link reset password."
    mock_send.assert_called_once()
    generate_link_call = fake_admin.auth.admin.generate_link.call_args[0][0]
    assert generate_link_call["type"] == "recovery"
    assert generate_link_call["email"] == "user@example.com"


def test_forgot_password_returns_same_message_when_email_not_registered(client: TestClient) -> None:
    fake_admin = MagicMock()
    fake_admin.auth.admin.generate_link.side_effect = Exception("User not found")

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.auth.send_email") as mock_send:
        resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert resp.status_code == 200
    assert resp.json()["message"] == "Jika email terdaftar, kami sudah mengirim link reset password."
    mock_send.assert_not_called()


def test_forgot_password_message_identical_regardless_of_email_existence(client: TestClient) -> None:
    """The anti-enumeration property, proven directly: the two responses
    must be byte-identical so a client (or attacker) cannot distinguish a
    registered email from an unregistered one."""
    fake_admin_found = MagicMock()
    fake_link_res = MagicMock()
    fake_link_res.properties.action_link = "https://supabase.example/verify?token=xyz"
    fake_admin_found.auth.admin.generate_link.return_value = fake_link_res

    fake_admin_missing = MagicMock()
    fake_admin_missing.auth.admin.generate_link.side_effect = Exception("not found")

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin_found), \
         patch("app.api.v1.auth.render_template", return_value="<html></html>"), \
         patch("app.api.v1.auth.send_email"):
        resp_found = client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})

    with patch("app.api.v1.auth.get_admin_client", return_value=fake_admin_missing):
        resp_missing = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})

    assert resp_found.status_code == resp_missing.status_code == 200
    assert resp_found.json() == resp_missing.json()


def test_me_reports_is_admin_true_for_configured_admin(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "astalink21@gmail.com"}
    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"]):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert resp.status_code == 200
    assert resp.json() == {"email": "astalink21@gmail.com", "is_admin": True}


def test_me_reports_is_admin_false_for_non_admin(client: TestClient) -> None:
    mock_user = {"sub": "user-2", "email": "user@example.com"}
    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.deps.settings.ADMIN_EMAILS", ["astalink21@gmail.com"]):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert resp.status_code == 200
    assert resp.json() == {"email": "user@example.com", "is_admin": False}


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
