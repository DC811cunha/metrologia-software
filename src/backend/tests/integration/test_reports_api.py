import shutil
from pathlib import Path

import pytest

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module
import app.core.config as config_module


@pytest.fixture(autouse=True)
def _isolated_reports_dir(tmp_path, monkeypatch):
    reports_dir = tmp_path / "generated_reports"
    monkeypatch.setattr(config_module.settings, "reports_dir", str(reports_dir))
    yield reports_dir
    shutil.rmtree(reports_dir, ignore_errors=True)


def _register_repository(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", lambda self, owner, repo: ["python"]
    )
    return client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/octocat/Hello-World"},
        headers=auth_headers,
    ).json()


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc123"
    root.mkdir(parents=True)
    (root / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return root


def _trigger_analysis(client, auth_headers, monkeypatch, repository_id):
    monkeypatch.setattr(
        analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10
    )
    monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)
    return client.post(
        f"/api/v1/repositories/{repository_id}/analyses", headers=auth_headers
    ).json()


class TestCreateReport:
    def test_generates_single_analysis_report(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        analysis = _trigger_analysis(client, auth_headers, monkeypatch, repository["id"])

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/reports",
            json={"tipo": "analise_unica", "analise_id": analysis["id"]},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["tipo"] == "analise_unica"
        assert body["download_url"].endswith(f"/reports/{body['id']}/download")

    def test_rejects_single_report_without_analise_id(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/reports",
            json={"tipo": "analise_unica"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_rejects_history_report_without_completed_analyses(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/reports",
            json={"tipo": "historico_completo"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_generates_history_report_with_completed_analyses(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        _trigger_analysis(client, auth_headers, monkeypatch, repository["id"])
        _trigger_analysis(client, auth_headers, monkeypatch, repository["id"])

        response = client.post(
            f"/api/v1/repositories/{repository['id']}/reports",
            json={"tipo": "historico_completo"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["tipo"] == "historico_completo"


class TestDownloadReport:
    def test_downloads_generated_pdf(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        analysis = _trigger_analysis(client, auth_headers, monkeypatch, repository["id"])
        report = client.post(
            f"/api/v1/repositories/{repository['id']}/reports",
            json={"tipo": "analise_unica", "analise_id": analysis["id"]},
            headers=auth_headers,
        ).json()

        response = client.get(report["download_url"], headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_returns_404_for_unknown_report(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        response = client.get(
            f"/api/v1/repositories/{repository['id']}/reports/00000000-0000-0000-0000-000000000000/download",
            headers=auth_headers,
        )
        assert response.status_code == 404
