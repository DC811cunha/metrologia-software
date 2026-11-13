import pytest

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


class TestDeleteRepositoryWithReports:
    """Regressão: excluir um repositório que já gerou relatório PDF dava erro 500 no Postgres
    (relatórios apontam para o repositório e para as análises e não tinham cascade)."""

    @pytest.fixture(autouse=True)
    def _isolated_reports_dir(self, tmp_path, monkeypatch):
        import app.core.config as config_module

        self.reports_dir = tmp_path / "generated_reports"
        monkeypatch.setattr(config_module.settings, "reports_dir", str(self.reports_dir))

    def _repository_with_analyses(self, client, auth_headers, monkeypatch):
        import app.api.analyses as analyses_module

        _patch_languages(monkeypatch, ["python"])
        repository = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers=auth_headers,
        ).json()
        monkeypatch.setattr(analyses_module.GithubService, "fetch_repo_size_kb", lambda self, o, r: 10)

        def fake_download(self, owner, repo, dest_dir):
            root = dest_dir / f"{owner}-{repo}-abc"
            root.mkdir(parents=True)
            (root / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            return root

        monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", fake_download)
        analyses = [
            client.post(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers).json()
            for _ in range(2)
        ]
        return repository, analyses

    def test_deletes_a_repository_that_has_single_and_history_reports(
        self, client, auth_headers, monkeypatch, db_session
    ):
        from app.models.analysis import Analysis
        from app.models.report import Report

        repository, analyses = self._repository_with_analyses(client, auth_headers, monkeypatch)
        base = f"/api/v1/repositories/{repository['id']}"
        single = client.post(
            f"{base}/reports", json={"tipo": "analise_unica", "analise_id": analyses[0]["id"]}, headers=auth_headers
        )
        history = client.post(f"{base}/reports", json={"tipo": "historico_completo"}, headers=auth_headers)
        assert single.status_code == 201 and history.status_code == 201

        response = client.delete(base, headers=auth_headers)

        assert response.status_code == 204
        assert client.get(base, headers=auth_headers).status_code == 404
        assert db_session.query(Report).count() == 0
        assert db_session.query(Analysis).count() == 0

    def test_removes_the_generated_pdf_files_too(self, client, auth_headers, monkeypatch):
        repository, analyses = self._repository_with_analyses(client, auth_headers, monkeypatch)
        base = f"/api/v1/repositories/{repository['id']}"
        client.post(
            f"{base}/reports", json={"tipo": "analise_unica", "analise_id": analyses[0]["id"]}, headers=auth_headers
        )
        client.post(f"{base}/reports", json={"tipo": "historico_completo"}, headers=auth_headers)
        assert len(list(self.reports_dir.glob("*.pdf"))) == 2

        assert client.delete(base, headers=auth_headers).status_code == 204

        assert list(self.reports_dir.glob("*.pdf")) == []

    def test_deleting_one_repository_keeps_the_reports_of_another(self, client, auth_headers, monkeypatch, db_session):
        from app.models.report import Report

        first, first_analyses = self._repository_with_analyses(client, auth_headers, monkeypatch)
        _patch_languages(monkeypatch, ["python"])
        second = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Spoon-Knife"},
            headers=auth_headers,
        ).json()
        client.post(
            f"/api/v1/repositories/{first['id']}/reports",
            json={"tipo": "analise_unica", "analise_id": first_analyses[0]["id"]},
            headers=auth_headers,
        )
        second_analysis = client.post(
            f"/api/v1/repositories/{second['id']}/analyses", headers=auth_headers
        ).json()
        client.post(
            f"/api/v1/repositories/{second['id']}/reports",
            json={"tipo": "analise_unica", "analise_id": second_analysis["id"]},
            headers=auth_headers,
        )

        assert client.delete(f"/api/v1/repositories/{first['id']}", headers=auth_headers).status_code == 204

        remaining = db_session.query(Report).all()
        assert len(remaining) == 1 and str(remaining[0].repositorio_id) == second["id"]
        assert len(list(self.reports_dir.glob("*.pdf"))) == 1

    def test_a_missing_pdf_file_does_not_block_the_deletion(self, client, auth_headers, monkeypatch):
        repository, analyses = self._repository_with_analyses(client, auth_headers, monkeypatch)
        base = f"/api/v1/repositories/{repository['id']}"
        client.post(f"{base}/reports", json={"tipo": "historico_completo"}, headers=auth_headers)
        for pdf in self.reports_dir.glob("*.pdf"):
            pdf.unlink()  # arquivo já removido à mão

        assert client.delete(base, headers=auth_headers).status_code == 204

    def test_never_deletes_a_file_outside_the_reports_directory(
        self, client, auth_headers, monkeypatch, db_session, tmp_path
    ):
        from app.models.report import Report

        repository, _ = self._repository_with_analyses(client, auth_headers, monkeypatch)
        precious = tmp_path / "importante.pdf"
        precious.write_bytes(b"nao apague")
        report = db_session.query(Report).first()
        if report is None:
            from app.models.user import User

            user = db_session.query(User).first()
            report = Report(
                usuario_id=user.id,
                repositorio_id=__import__("uuid").UUID(repository["id"]),
                tipo="historico_completo",
                caminho_arquivo="",
            )
            db_session.add(report)
        report.caminho_arquivo = str(precious)  # caminho adulterado: fora de reports_dir
        db_session.commit()

        assert client.delete(f"/api/v1/repositories/{repository['id']}", headers=auth_headers).status_code == 204

        assert precious.exists()
