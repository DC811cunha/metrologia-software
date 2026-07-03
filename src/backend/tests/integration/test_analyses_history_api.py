from pathlib import Path

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module


def _register_repository(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", lambda self, owner, repo: ["python"]
    )
    return client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/octocat/Hello-World"},
        headers=auth_headers,
    ).json()


def _make_fake_download(snippet: str):
    def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
        root = dest_dir / f"{owner}-{repo}-abc123"
        root.mkdir(parents=True)
        (root / "main.py").write_text(snippet, encoding="utf-8")
        return root

    return _fake_download


SIMPLE_SNIPPET = "def add(a, b):\n    return a + b\n"
COMPLEX_SNIPPET = "\n".join(
    [
        "def add(a, b):",
        "    if a > 0:",
        "        if b > 0:",
        "            return a + b",
        "        return a",
        "    return b",
    ]
)


def _trigger_analysis(client, auth_headers, monkeypatch, repository_id, snippet):
    monkeypatch.setattr(
        analyses_module.GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10
    )
    monkeypatch.setattr(
        analyses_module.GithubService, "download_and_extract", _make_fake_download(snippet)
    )
    return client.post(
        f"/api/v1/repositories/{repository_id}/analyses", headers=auth_headers
    ).json()


class TestListAnalysesHistory:
    def test_returns_chronological_history(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        first = _trigger_analysis(client, auth_headers, monkeypatch, repository["id"], SIMPLE_SNIPPET)
        second = _trigger_analysis(client, auth_headers, monkeypatch, repository["id"], COMPLEX_SNIPPET)

        response = client.get(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert [item["id"] for item in body] == [first["id"], second["id"]]
        assert all(len(item["medicoes"]) == 6 for item in body)

    def test_rejects_unknown_metric(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses",
            params={"metrica": "metrica_inexistente"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_returns_no_trend_with_a_single_analysis(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        _trigger_analysis(client, auth_headers, monkeypatch, repository["id"], SIMPLE_SNIPPET)

        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses",
            params={"metrica": "complexidade_ciclomatica"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["tendencia"] is None
        assert len(body["serie"]) == 1

    def test_computes_trend_between_two_most_recent_analyses(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)
        _trigger_analysis(client, auth_headers, monkeypatch, repository["id"], SIMPLE_SNIPPET)
        _trigger_analysis(client, auth_headers, monkeypatch, repository["id"], COMPLEX_SNIPPET)

        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses",
            params={"metrica": "complexidade_ciclomatica"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["serie"]) == 2
        # COMPLEX_SNIPPET tem mais pontos de decisão -> complexidade maior -> piora
        assert body["tendencia"] == "piorando"

    def test_returns_404_for_repository_owned_by_another_user(self, client, auth_headers, monkeypatch):
        repository = _register_repository(client, auth_headers, monkeypatch)

        other_token = client.post(
            "/api/v1/auth/register",
            json={"email": "history_intruder@example.com", "password": "super-secret-123"},
        ).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses", headers=other_headers
        )
        assert response.status_code == 404
