"""
T063 — Isolamento de dados entre contas (FR-011, SC-006).

Garante que nenhum usuário pode ler ou escrever recursos de outro usuário,
cobrindo: repositórios, análises, histórico, tendência e relatórios.
"""
import shutil
from pathlib import Path

import pytest

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module
import app.core.config as config_module


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolated_reports_dir(tmp_path, monkeypatch):
    reports_dir = tmp_path / "generated_reports"
    monkeypatch.setattr(config_module.settings, "reports_dir", str(reports_dir))
    yield reports_dir
    shutil.rmtree(reports_dir, ignore_errors=True)


def _make_headers(client, email: str) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "super-secret-123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _register_repository(client, headers, monkeypatch, url="https://github.com/octocat/Hello-World"):
    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"]
    )
    return client.post("/api/v1/repositories", json={"url": url}, headers=headers).json()


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc123"
    root.mkdir(parents=True)
    (root / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return root


def _run_analysis(client, headers, monkeypatch, repository_id: str) -> dict:
    monkeypatch.setattr(
        analyses_module.GithubService, "fetch_repo_size_kb", lambda self, o, r: 10
    )
    monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)
    return client.post(
        f"/api/v1/repositories/{repository_id}/analyses", headers=headers
    ).json()


def _generate_report(client, headers, repository_id: str, analysis_id: str) -> dict:
    return client.post(
        f"/api/v1/repositories/{repository_id}/reports",
        json={"tipo": "analise_unica", "analise_id": analysis_id},
        headers=headers,
    ).json()


# ── testes ────────────────────────────────────────────────────────────────────

class TestRepositoryIsolation:
    """Repositórios de Alice não aparecem nem são acessíveis para Bob."""

    def test_list_returns_only_own_repositories(self, client, monkeypatch):
        alice = _make_headers(client, "alice@example.com")
        bob = _make_headers(client, "bob@example.com")

        _register_repository(client, alice, monkeypatch, "https://github.com/alice/repo1")
        _register_repository(client, alice, monkeypatch, "https://github.com/alice/repo2")
        _register_repository(client, bob, monkeypatch, "https://github.com/bob/repo1")

        alice_list = client.get("/api/v1/repositories", headers=alice).json()
        bob_list = client.get("/api/v1/repositories", headers=bob).json()

        assert len(alice_list) == 2
        assert len(bob_list) == 1
        alice_urls = {r["url"] for r in alice_list}
        assert "https://github.com/bob/repo1" not in alice_urls

    def test_get_repository_returns_404_for_other_user(self, client, monkeypatch):
        alice = _make_headers(client, "alice2@example.com")
        bob = _make_headers(client, "bob2@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)

        response = client.get(f"/api/v1/repositories/{alice_repo['id']}", headers=bob)
        assert response.status_code == 404

    def test_delete_repository_returns_404_for_other_user(self, client, monkeypatch):
        alice = _make_headers(client, "alice3@example.com")
        bob = _make_headers(client, "bob3@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)

        response = client.delete(f"/api/v1/repositories/{alice_repo['id']}", headers=bob)
        assert response.status_code == 404

        # repo still exists for alice
        still_exists = client.get(f"/api/v1/repositories/{alice_repo['id']}", headers=alice)
        assert still_exists.status_code == 200


class TestAnalysisIsolation:
    """Análises de Alice não são acessíveis para Bob."""

    def test_trigger_analysis_returns_404_for_other_user_repository(self, client, monkeypatch):
        alice = _make_headers(client, "alice4@example.com")
        bob = _make_headers(client, "bob4@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        monkeypatch.setattr(
            analyses_module.GithubService, "fetch_repo_size_kb", lambda self, o, r: 10
        )

        response = client.post(
            f"/api/v1/repositories/{alice_repo['id']}/analyses", headers=bob
        )
        assert response.status_code == 404

    def test_get_analysis_returns_404_for_other_user(self, client, monkeypatch):
        alice = _make_headers(client, "alice5@example.com")
        bob = _make_headers(client, "bob5@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        alice_analysis = _run_analysis(client, alice, monkeypatch, alice_repo["id"])

        response = client.get(
            f"/api/v1/repositories/{alice_repo['id']}/analyses/{alice_analysis['id']}",
            headers=bob,
        )
        assert response.status_code == 404

    def test_history_returns_404_for_other_user_repository(self, client, monkeypatch):
        alice = _make_headers(client, "alice6@example.com")
        bob = _make_headers(client, "bob6@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        _run_analysis(client, alice, monkeypatch, alice_repo["id"])

        response = client.get(
            f"/api/v1/repositories/{alice_repo['id']}/analyses", headers=bob
        )
        assert response.status_code == 404

    def test_metric_trend_returns_404_for_other_user_repository(self, client, monkeypatch):
        alice = _make_headers(client, "alice7@example.com")
        bob = _make_headers(client, "bob7@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        _run_analysis(client, alice, monkeypatch, alice_repo["id"])
        _run_analysis(client, alice, monkeypatch, alice_repo["id"])

        response = client.get(
            f"/api/v1/repositories/{alice_repo['id']}/analyses?metrica=complexidade_ciclomatica",
            headers=bob,
        )
        assert response.status_code == 404


class TestReportIsolation:
    """Relatórios de Alice não são geráveis nem baixáveis por Bob."""

    def test_create_report_returns_404_for_other_user_repository(self, client, monkeypatch):
        alice = _make_headers(client, "alice8@example.com")
        bob = _make_headers(client, "bob8@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        alice_analysis = _run_analysis(client, alice, monkeypatch, alice_repo["id"])

        response = client.post(
            f"/api/v1/repositories/{alice_repo['id']}/reports",
            json={"tipo": "analise_unica", "analise_id": alice_analysis["id"]},
            headers=bob,
        )
        assert response.status_code == 404

    def test_download_report_returns_404_for_other_user(self, client, monkeypatch):
        alice = _make_headers(client, "alice9@example.com")
        bob = _make_headers(client, "bob9@example.com")

        alice_repo = _register_repository(client, alice, monkeypatch)
        alice_analysis = _run_analysis(client, alice, monkeypatch, alice_repo["id"])
        alice_report = _generate_report(client, alice, alice_repo["id"], alice_analysis["id"])

        response = client.get(alice_report["download_url"], headers=bob)
        assert response.status_code == 404
