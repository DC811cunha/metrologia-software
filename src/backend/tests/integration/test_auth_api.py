def test_register_creates_user_and_returns_tokens(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dev@example.com", "password": "super-secret-123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" not in body


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

    def fake_delay(to_email, reset_link):
        sent["to_email"] = to_email
        sent["reset_link"] = reset_link

    monkeypatch.setattr(auth_module.send_password_reset_email_task, "delay", fake_delay)
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


REFRESH_COOKIE = "softmeter_refresh_token"
STRONG = "super-secret-123"


class TestPasswordLength:
    """bcrypt >= 5 recusa mais de 72 BYTES; isso nunca pode virar erro 500."""

    def test_register_accepts_exactly_72_bytes(self, client):
        response = client.post(
            "/api/v1/auth/register", json={"email": "limit@example.com", "password": "a" * 72}
        )
        assert response.status_code == 201

    def test_register_rejects_73_bytes_with_422(self, client):
        response = client.post(
            "/api/v1/auth/register", json={"email": "long@example.com", "password": "a" * 73}
        )
        assert response.status_code == 422

    def test_register_counts_bytes_not_characters(self, client):
        # 37 caracteres "é" = 74 bytes em UTF-8
        response = client.post(
            "/api/v1/auth/register", json={"email": "utf8@example.com", "password": "é" * 37}
        )
        assert response.status_code == 422

    def test_reset_password_rejects_over_72_bytes_with_422(self, client):
        response = client.post(
            "/api/v1/auth/reset-password", json={"token": "qualquer", "new_password": "a" * 100}
        )
        assert response.status_code == 422

    def test_login_with_long_password_returns_401_for_existing_account(self, client):
        client.post("/api/v1/auth/register", json={"email": "exists@example.com", "password": STRONG})

        response = client.post(
            "/api/v1/auth/login", json={"email": "exists@example.com", "password": "a" * 100}
        )

        assert response.status_code == 401

    def test_login_with_long_password_returns_401_for_unknown_account(self, client):
        response = client.post(
            "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "a" * 100}
        )

        assert response.status_code == 401

    def test_login_for_unknown_email_pays_the_hashing_cost(self, client, monkeypatch):
        import app.api.auth as auth_module

        calls = []
        monkeypatch.setattr(auth_module, "equalize_login_timing", lambda password: calls.append(password))

        client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": STRONG})

        assert calls == [STRONG]


class TestSessionHardening:
    def test_login_response_does_not_expose_the_refresh_token(self, client):
        client.post("/api/v1/auth/register", json={"email": "body@example.com", "password": STRONG})

        response = client.post(
            "/api/v1/auth/login", json={"email": "body@example.com", "password": STRONG}
        )

        assert "refresh_token" not in response.json()
        assert REFRESH_COOKIE in response.cookies

    def test_refresh_cookie_has_a_lifetime_matching_the_token(self, client):
        response = client.post(
            "/api/v1/auth/register", json={"email": "maxage@example.com", "password": STRONG}
        )

        set_cookie = response.headers["set-cookie"]
        assert "Max-Age=604800" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" not in set_cookie

    def test_refresh_cookie_is_secure_when_configured(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "cookie_secure", True)

        response = client.post(
            "/api/v1/auth/register", json={"email": "secure@example.com", "password": STRONG}
        )

        assert "Secure" in response.headers["set-cookie"]

    def test_password_reset_ends_existing_sessions(self, client, monkeypatch):
        sent = _fake_email_capture(monkeypatch)
        register = client.post(
            "/api/v1/auth/register", json={"email": "stolen@example.com", "password": STRONG}
        )
        old_access = register.json()["access_token"]
        old_refresh = client.cookies.get(REFRESH_COOKIE)
        assert client.post("/api/v1/auth/refresh").status_code == 200

        client.post("/api/v1/auth/forgot-password", json={"email": "stolen@example.com"})
        token = sent["reset_link"].split("token=")[1]
        client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-pass-1"})

        client.cookies.clear()
        client.cookies.set(REFRESH_COOKIE, old_refresh, path="/api/v1/auth")
        assert client.post("/api/v1/auth/refresh").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/logout", headers={"Authorization": f"Bearer {old_access}"}
            ).status_code
            == 401
        )

    def test_logout_revokes_the_refresh_token_on_the_server(self, client):
        register = client.post(
            "/api/v1/auth/register", json={"email": "bye@example.com", "password": STRONG}
        )
        access = register.json()["access_token"]
        leaked_refresh = client.cookies.get(REFRESH_COOKIE)

        logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"})
        assert logout.status_code == 204

        client.cookies.clear()
        client.cookies.set(REFRESH_COOKIE, leaked_refresh, path="/api/v1/auth")
        assert client.post("/api/v1/auth/refresh").status_code == 401

    def test_new_login_after_logout_works(self, client):
        payload = {"email": "again@example.com", "password": STRONG}
        access = client.post("/api/v1/auth/register", json=payload).json()["access_token"]
        client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"})

        response = client.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 200
        assert client.post("/api/v1/auth/refresh").status_code == 200
