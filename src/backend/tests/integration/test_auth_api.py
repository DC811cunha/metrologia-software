def test_register_creates_user_and_returns_tokens(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dev@example.com", "password": "super-secret-123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "super-secret-123"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_with_correct_credentials_returns_tokens(client):
    payload = {"email": "login@example.com", "password": "super-secret-123"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_returns_401(client):
    payload = {"email": "wrongpass@example.com", "password": "super-secret-123"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "incorrect-password"},
    )
    assert response.status_code == 401


def test_refresh_returns_new_access_token(client):
    payload = {"email": "refresh@example.com", "password": "super-secret-123"}
    client.post("/api/v1/auth/register", json=payload)

    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_without_cookie_returns_401(client):
    client.cookies.clear()
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_clears_refresh_cookie(client):
    payload = {"email": "logout@example.com", "password": "super-secret-123"}
    register_response = client.post("/api/v1/auth/register", json=payload)
    access_token = register_response.json()["access_token"]

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204


def test_protected_route_without_token_returns_401(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


def _fake_email_capture(monkeypatch):
    import app.api.auth as auth_module

    sent = {}

    def fake_send(to_email, reset_link):
        sent["to_email"] = to_email
        sent["reset_link"] = reset_link

    monkeypatch.setattr(auth_module, "send_password_reset_email", fake_send)
    return sent


class TestForgotPassword:
    def test_returns_generic_message_for_unknown_email(self, client):
        response = client.post(
            "/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}
        )
        assert response.status_code == 200
        assert "receberá um link" in response.json()["message"]

    def test_returns_same_generic_message_for_known_email(self, client, monkeypatch):
        sent = _fake_email_capture(monkeypatch)
        payload = {"email": "known@example.com", "password": "super-secret-123"}
        client.post("/api/v1/auth/register", json=payload)

        response = client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})

        assert response.status_code == 200
        assert "receberá um link" in response.json()["message"]
        assert sent["to_email"] == payload["email"]
        assert "token=" in sent["reset_link"]


class TestResetPassword:
    def test_rejects_unknown_token(self, client):
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "does-not-exist", "new_password": "new-password-123"},
        )
        assert response.status_code == 400

    def test_full_flow_changes_password_and_invalidates_token(self, client, monkeypatch):
        sent = _fake_email_capture(monkeypatch)
        payload = {"email": "resetflow@example.com", "password": "old-password-123"}
        client.post("/api/v1/auth/register", json=payload)
        client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
        token = sent["reset_link"].split("token=")[1]

        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "new-password-456"},
        )
        assert reset_response.status_code == 204

        old_password_login = client.post("/api/v1/auth/login", json=payload)
        assert old_password_login.status_code == 401

        new_password_login = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": "new-password-456"},
        )
        assert new_password_login.status_code == 200

        # token de uso único — a segunda tentativa com o mesmo token falha
        reused_response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "yet-another-789"},
        )
        assert reused_response.status_code == 400

    def test_rejects_expired_token(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "password_reset_token_expires_minutes", -1)
        sent = _fake_email_capture(monkeypatch)
        payload = {"email": "expired@example.com", "password": "old-password-123"}
        client.post("/api/v1/auth/register", json=payload)
        client.post("/api/v1/auth/forgot-password", json={"email": payload["email"]})
        token = sent["reset_link"].split("token=")[1]

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "new-password-456"},
        )
        assert response.status_code == 400
