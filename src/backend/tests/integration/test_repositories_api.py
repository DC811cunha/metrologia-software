import uuid

import app.api.repositories as repositories_module
from app.services.github_service import RepositoryAccessError, UnsupportedLanguageError


def _patch_languages(monkeypatch, result):
    def fake_fetch_languages(self, owner, repo):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", fake_fetch_languages
    )


class TestCreateRepository:
    def test_creates_repository_with_supported_language(self, client, auth_headers, monkeypatch):
        _patch_languages(monkeypatch, ["python"])

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["owner_nome"] == "octocat/Hello-World"
        assert body["linguagens_detectadas"] == ["python"]
        assert body["status_acesso"] == "ativo"

    def test_rejects_unsupported_language(self, client, auth_headers, monkeypatch):
        _patch_languages(monkeypatch, UnsupportedLanguageError("sem linguagem suportada"))

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/only-html"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_rejects_inaccessible_repository(self, client, auth_headers, monkeypatch):
        _patch_languages(monkeypatch, RepositoryAccessError("inacessível"))

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/private-repo"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_rejects_duplicate_repository_for_same_user(self, client, auth_headers, monkeypatch):
        _patch_languages(monkeypatch, ["python"])
        payload = {"url": "https://github.com/octocat/Hello-World"}

        first = client.post("/api/v1/repositories", json=payload, headers=auth_headers)
        assert first.status_code == 201

        second = client.post("/api/v1/repositories", json=payload, headers=auth_headers)
        assert second.status_code == 409

    def test_rejects_invalid_url(self, client, auth_headers):
        response = client.post(
            "/api/v1/repositories",
            json={"url": "not-a-github-url"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client):
        response = client.post(
            "/api/v1/repositories", json={"url": "https://github.com/octocat/Hello-World"}
        )
        assert response.status_code == 401


class TestListAndGetRepository:
    def test_list_only_returns_repositories_owned_by_current_user(
        self, client, auth_headers, monkeypatch
    ):
        _patch_languages(monkeypatch, ["python"])
        client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        )

        other_user_token = client.post(
            "/api/v1/auth/register",
            json={"email": "other@example.com", "password": "super-secret-123"},
        ).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_user_token}"}

        own_list = client.get("/api/v1/repositories", headers=auth_headers).json()
        other_list = client.get("/api/v1/repositories", headers=other_headers).json()

        assert len(own_list) == 1
        assert other_list == []

    def test_get_returns_404_for_repository_owned_by_another_user(
        self, client, auth_headers, monkeypatch
    ):
        _patch_languages(monkeypatch, ["python"])
        created = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        ).json()

        other_user_token = client.post(
            "/api/v1/auth/register",
            json={"email": "other2@example.com", "password": "super-secret-123"},
        ).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_user_token}"}

        response = client.get(f"/api/v1/repositories/{created['id']}", headers=other_headers)
        assert response.status_code == 404

    def test_get_returns_404_for_unknown_id(self, client, auth_headers):
        response = client.get(f"/api/v1/repositories/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestDeleteRepository:
    def test_deletes_owned_repository(self, client, auth_headers, monkeypatch):
        _patch_languages(monkeypatch, ["python"])
        created = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        ).json()

        delete_response = client.delete(
            f"/api/v1/repositories/{created['id']}", headers=auth_headers
        )
        assert delete_response.status_code == 204

        get_response = client.get(f"/api/v1/repositories/{created['id']}", headers=auth_headers)
        assert get_response.status_code == 404
