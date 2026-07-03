import uuid
from pathlib import Path

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module
from app.services.github_service import RepositoryAccessError


def _register_repository(client, auth_headers, monkeypatch, url="https://github.com/octocat/Hello-World"):
    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", lambda self, owner, repo: ["python"]
    )
    return client.post("/api/v1/repositories", json={"url": url}, headers=auth_headers).json()


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc123"
    root.mkdir(parents=True)
    (root / "main.py").write_text(
        "\n".join(
            [
                "def add(a, b):",
                "    return a + b",
                "",
                "def divide(a, b):",
                "    if b == 0:",
                "        return None",
                "    return a / b",
            ]
        ),
        encoding="utf-8",
    )
    return root


class TestTriggerAnalysisSync:
    def test_runs_synchronously_for_small_repository(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(
            analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10
        )
        monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "concluida"
        assert len(body["medicoes"]) == 6
        assert body["status_conformidade_geral"] in ("Conforme", "Condicional", "Não-Conforme")

    def test_returns_404_for_repository_owned_by_another_user(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        other_token = client.post(
            "/api/v1/auth/register",
            json={"email": "intruder@example.com", "password": "super-secret-123"},
        ).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=other_headers
        )
        assert response.status_code == 404

    def test_returns_409_when_repository_is_inaccessible(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        def fail(self, owner, repo):
            raise RepositoryAccessError("repositório removido")

        monkeypatch.setattr(analyses_module.GithubService, "fetch_repo_size_kb", fail)

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers
        )
        assert response.status_code == 409

        repo_after = client.get(
            f"/api/v1/repositories/{repository['id']}", headers=auth_headers
        ).json()
        assert repo_after["status_acesso"] == "inacessivel"


class TestTriggerAnalysisAsync:
    def test_dispatches_celery_task_for_large_repository(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(
            analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 999_999
        )
        dispatched: list[uuid.UUID] = []
        monkeypatch.setattr(
            analyses_module, "dispatch_async_analysis", lambda analysis_id: dispatched.append(analysis_id)
        )

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers
        )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "processando"
        assert len(dispatched) == 1


class TestGetAnalysis:
    def test_returns_404_for_unknown_analysis(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_polling_returns_completed_analysis(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(
            analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10
        )
        monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)

        created = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers
        ).json()

        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses/{created['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "concluida"

    def test_repository_list_exposes_last_analysis_id(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(
            analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10
        )
        monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)

        created = client.post(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers
        ).json()

        repositories = client.get("/api/v1/repositories", headers=auth_headers).json()
        assert repositories[0]["ultima_analise_id"] == created["id"]
        assert repositories[0]["ultima_analise_status"] == "concluida"
