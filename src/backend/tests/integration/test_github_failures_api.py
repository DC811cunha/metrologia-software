"""Falhas do GitHub nos endpoints (issues #90 e #91): nada de 500, nada de análise presa em
"Pendente"/"Processando" e nada de repositório "inacessível para sempre" por causa de cota."""

import uuid
from pathlib import Path

import app.api.analyses as analyses_module
from app.models.analysis import Analysis, AnalysisStatus
from app.models.repository import AccessStatus, Repository
from app.services.github_service import (
    GithubRateLimitError,
    GithubService,
    GithubUnavailableError,
    RepositoryAccessError,
)

URL = "https://github.com/octocat/Hello-World"


def register_repository(client, auth_headers, monkeypatch) -> dict:
    monkeypatch.setattr(GithubService, "fetch_languages", lambda self, owner, repo: ["python"])
    return client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers).json()


def raising(error: Exception):
    def _raise(self, *args, **kwargs):
        raise error

    return _raise


def analyses_of(db_session, repository_id: str) -> list[Analysis]:
    return db_session.query(Analysis).filter(Analysis.repositorio_id == uuid.UUID(repository_id)).all()


def trigger(client, auth_headers, repository: dict):
    return client.post(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers)


class TestRegisteringWhileGithubMisbehaves:
    def test_rate_limit_is_a_429_with_retry_after_instead_of_inaccessible(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(GithubService, "fetch_languages", raising(GithubRateLimitError("limite", retry_after=600)))

        response = client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "600"
        assert "10 min" in response.json()["detail"]
        assert "inacessível" not in response.json()["detail"]

    def test_rate_limit_without_a_known_wait_still_answers_429(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(GithubService, "fetch_languages", raising(GithubRateLimitError("limite")))

        response = client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers)

        assert response.status_code == 429
        assert "Retry-After" not in response.headers

    def test_github_outage_is_a_502_with_a_clear_message(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(GithubService, "fetch_languages", raising(GithubUnavailableError("timeout")))

        response = client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers)

        assert response.status_code == 502
        assert "indisponível" in response.json()["detail"]

    def test_a_genuinely_missing_repository_is_still_a_422(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(GithubService, "fetch_languages", raising(RepositoryAccessError("não existe")))

        response = client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers)

        assert response.status_code == 422

    def test_the_http_client_is_closed_after_the_request(self, client, auth_headers, monkeypatch):
        closed: list[bool] = []
        monkeypatch.setattr(GithubService, "fetch_languages", lambda self, owner, repo: ["python"])
        monkeypatch.setattr(GithubService, "close", lambda self: closed.append(True))

        client.post("/api/v1/repositories", json={"url": URL}, headers=auth_headers)

        assert closed == [True]


class TestTriggeringWhileGithubMisbehaves:
    def test_rate_limit_fails_the_analysis_but_keeps_the_repository_active(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", raising(GithubRateLimitError("limite", retry_after=1800)))

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "1800"
        assert "30 min" in response.json()["detail"]
        [analysis] = analyses_of(db_session, repository["id"])
        assert analysis.status == AnalysisStatus.FALHOU
        assert "Limite de requisições" in analysis.motivo_falha
        stored = db_session.get(Repository, uuid.UUID(repository["id"]))
        db_session.refresh(stored)
        assert stored.status_acesso == AccessStatus.ATIVO

    def test_a_later_analysis_works_once_the_limit_renews(self, client, auth_headers, monkeypatch):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", raising(GithubRateLimitError("limite")))
        assert trigger(client, auth_headers, repository).status_code == 429

        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10)
        monkeypatch.setattr(GithubService, "download_and_extract", _fake_download)

        assert trigger(client, auth_headers, repository).status_code == 201

    def test_github_outage_is_a_502_and_never_leaves_the_analysis_pending(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", raising(GithubUnavailableError("timeout")))

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 502
        [analysis] = analyses_of(db_session, repository["id"])
        assert analysis.status == AnalysisStatus.FALHOU
        assert "indisponível" in analysis.motivo_falha

    def test_a_repository_that_answers_again_is_no_longer_inaccessible(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        stored = db_session.get(Repository, uuid.UUID(repository["id"]))
        stored.status_acesso = AccessStatus.INACESSIVEL  # marcado por uma resposta temporária antiga
        db_session.commit()
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10)
        monkeypatch.setattr(GithubService, "download_and_extract", _fake_download)

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 201
        db_session.refresh(stored)
        assert stored.status_acesso == AccessStatus.ATIVO

    def test_a_repository_that_really_vanished_stays_inaccessible(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", raising(RepositoryAccessError("removido")))

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 409
        stored = db_session.get(Repository, uuid.UUID(repository["id"]))
        db_session.refresh(stored)
        assert stored.status_acesso == AccessStatus.INACESSIVEL

    def test_queue_outage_fails_the_analysis_instead_of_leaving_it_processing(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 50_000)

        def broker_down(analysis_id):
            raise ConnectionError("redis fora do ar")

        monkeypatch.setattr(analyses_module, "dispatch_async_analysis", broker_down)

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 503
        [analysis] = analyses_of(db_session, repository["id"])
        assert analysis.status == AnalysisStatus.FALHOU
        assert "enfileirar" in analysis.motivo_falha

    def test_limit_hit_while_downloading_fails_the_analysis_without_blocking_the_repository(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10)
        monkeypatch.setattr(
            GithubService, "download_and_extract", raising(GithubRateLimitError("limite", retry_after=120))
        )

        response = trigger(client, auth_headers, repository)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "falhou"
        assert "Limite de requisições" in body["motivo_falha"]
        stored = db_session.get(Repository, uuid.UUID(repository["id"]))
        db_session.refresh(stored)
        assert stored.status_acesso == AccessStatus.ATIVO

    def test_outage_while_downloading_fails_the_analysis_with_a_clear_reason(
        self, client, auth_headers, monkeypatch
    ):
        repository = register_repository(client, auth_headers, monkeypatch)
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", lambda self, owner, repo: 10)
        monkeypatch.setattr(GithubService, "download_and_extract", raising(GithubUnavailableError("ReadTimeout")))

        body = trigger(client, auth_headers, repository).json()

        assert body["status"] == "falhou"
        assert "indisponível" in body["motivo_falha"]

    def test_the_http_client_is_closed_after_triggering(self, client, auth_headers, monkeypatch):
        repository = register_repository(client, auth_headers, monkeypatch)
        closed: list[bool] = []
        monkeypatch.setattr(GithubService, "fetch_repo_size_kb", raising(GithubUnavailableError("x")))
        monkeypatch.setattr(GithubService, "close", lambda self: closed.append(True))

        trigger(client, auth_headers, repository)

        assert closed == [True]


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc123"
    root.mkdir(parents=True)
    (root / "main.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n",
        encoding="utf-8",
    )
    return root

