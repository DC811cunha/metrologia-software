"""
Testes para os middlewares de segurança: limite de tamanho de payload e rate limiting.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import reset_rate_limits
from app.main import app


@pytest.fixture(autouse=True)
def _clear_rate_limit_state():
    reset_rate_limits()
    yield
    reset_rate_limits()


class TestContentSizeLimit:
    def test_rejects_request_with_oversized_content_length(self, client):
        response = client.post(
            "/api/v1/auth/login",
            content=b"x",
            headers={"Content-Length": str(65 * 1024), "Content-Type": "application/json"},
        )
        assert response.status_code == 413

    def test_rejects_chunked_body_without_content_length(self, client):
        def chunks():
            for _ in range(70):
                yield b"x" * 1024  # 70 KB no total, sem Content-Length

        response = client.post(
            "/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 413
        assert "64 KB" in response.json()["detail"]

    def test_accepts_small_chunked_body(self, client):
        def chunks():
            yield b'{"email": "a@example.com",'
            yield b' "password": "wrong"}'

        response = client.post(
            "/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 401

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
        assert int(response.headers["Retry-After"]) > 0

    def test_does_not_rate_limit_other_endpoints(self, client, auth_headers):
        for _ in range(12):
            response = client.get("/api/v1/repositories", headers=auth_headers)
            assert response.status_code == 200

    def test_each_ip_has_its_own_window(self, client):
        payload = {"email": "brute@example.com", "password": "wrong-password"}
        for _ in range(11):
            client.post("/api/v1/auth/login", json=payload)

        other_user = TestClient(app, client=("203.0.113.9", 50000))
        response = other_user.post("/api/v1/auth/login", json=payload)

        assert response.status_code == 401


class TestProductionRateLimits:
    """Cadastro, refresh e criação de análises só são limitados em produção — em
    desenvolvimento, testes e E2E, criar várias contas em sequência é o fluxo normal."""

    @pytest.fixture
    def production(self, monkeypatch):
        monkeypatch.setattr(settings, "environment", "production")

    def test_register_is_not_limited_in_development(self, client):
        for index in range(15):
            response = client.post(
                "/api/v1/auth/register",
                json={"email": f"dev{index}@example.com", "password": "super-secret-123"},
            )
            assert response.status_code == 201

    def test_register_is_limited_in_production(self, client, production):
        for index in range(10):
            response = client.post(
                "/api/v1/auth/register",
                json={"email": f"prod{index}@example.com", "password": "super-secret-123"},
            )
            assert response.status_code == 201

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "prod-extra@example.com", "password": "super-secret-123"},
        )

        assert response.status_code == 429

    def test_refresh_is_limited_in_production(self, client, production):
        client.cookies.clear()
        statuses = [client.post("/api/v1/auth/refresh").status_code for _ in range(31)]

        assert statuses[:30] == [401] * 30
        assert statuses[30] == 429

    def test_analysis_creation_is_limited_in_production(self, client, auth_headers, production):
        url = f"/api/v1/repositories/{uuid.uuid4()}/analyses"
        statuses = [client.post(url, headers=auth_headers).status_code for _ in range(21)]

        assert 429 not in statuses[:20]
        assert statuses[20] == 429

    def test_analysis_limit_is_shared_across_repositories_of_the_same_ip(self, client, auth_headers, production):
        for _ in range(20):
            client.post(f"/api/v1/repositories/{uuid.uuid4()}/analyses", headers=auth_headers)

        response = client.post(f"/api/v1/repositories/{uuid.uuid4()}/analyses", headers=auth_headers)

        assert response.status_code == 429


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
