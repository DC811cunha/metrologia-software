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
