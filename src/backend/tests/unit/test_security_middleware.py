"""
Testes para os middlewares de segurança: limite de tamanho de payload e rate limiting de login.
"""
import pytest

from app.main import _login_window


@pytest.fixture(autouse=True)
def _clear_rate_limit_state():
    _login_window.clear()
    yield
    _login_window.clear()


class TestContentSizeLimit:
    def test_rejects_request_with_oversized_content_length(self, client):
        response = client.post(
            "/api/v1/auth/login",
            content=b"x",
            headers={"Content-Length": str(65 * 1024), "Content-Type": "application/json"},
        )
        assert response.status_code == 413

    def test_accepts_request_within_size_limit(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "wrong"},
        )
        assert response.status_code != 413


class TestLoginRateLimit:
    def test_returns_429_after_exceeding_limit(self, client):
        payload = {"email": "brute@example.com", "password": "wrong-password"}
        for _ in range(10):
            client.post("/api/v1/auth/login", json=payload)

        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_does_not_rate_limit_other_endpoints(self, client, auth_headers):
        for _ in range(12):
            response = client.get("/api/v1/repositories", headers=auth_headers)
            assert response.status_code == 200


class TestRepositoryUrlValidation:
    def test_rejects_non_github_url_at_schema_level(self, client, auth_headers):
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://gitlab.com/owner/repo"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_rejects_url_without_repo_path(self, client, auth_headers):
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/only-owner"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_accepts_valid_github_https_url(self, client, auth_headers, monkeypatch):
        import app.api.repositories as repositories_module

        monkeypatch.setattr(
            repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"]
        )
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        )
        assert response.status_code == 201
