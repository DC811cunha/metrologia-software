"""Nome canônico do repositório: o cadastro acompanha renomeações/transferências do GitHub e uma troca
de dono do nome (nome reutilizado por outro repositório) barra a análise em vez de medir o errado."""

import uuid
from pathlib import Path

import httpx

import app.api.analyses as analyses_module
from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatus
from app.models.repository import Repository
from app.models.user import User
from app.services.github_service import GithubService, RepoIdentity
from app.services.repository_sync import SyncOutcome, sync_repository_identity

OLD_URL = "https://github.com/SandroMachiniski-SE/Viaje-Mais"
NEW_NAME = "SandroMachiniski-SE/NomadPlan"
NEW_URL = f"https://github.com/{NEW_NAME}"


def register(client, auth_headers, monkeypatch, url=OLD_URL) -> dict:
    monkeypatch.setattr(GithubService, "fetch_languages", lambda self, owner, repo: ["python"])
    return client.post("/api/v1/repositories", json={"url": url}, headers=auth_headers).json()


def github_says(monkeypatch, identity: RepoIdentity | None, size_kb: int = 10) -> None:
    """Simula a consulta de metadados: devolve o tamanho e registra a identidade observada."""

    def fake(self, owner, repo):
        self.repo_identity = identity
        return size_kb

    monkeypatch.setattr(GithubService, "fetch_repo_size_kb", fake)
    monkeypatch.setattr(GithubService, "download_and_extract", _fake_download)


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc"
    root.mkdir(parents=True)
    (root / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return root


def analyze(client, auth_headers, repository):
    return client.post(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers)


def stored(db_session, repository: dict) -> Repository:
    row = db_session.get(Repository, uuid.UUID(repository["id"]))
    db_session.refresh(row)
    return row


class TestFollowsARename:
    def test_the_registration_is_updated_to_the_current_name_and_url(self, client, auth_headers, monkeypatch, db_session):
        repository = register(client, auth_headers, monkeypatch)
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))

        response = analyze(client, auth_headers, repository)

        assert response.status_code == 201
        row = stored(db_session, repository)
        assert (row.url, row.owner_nome, row.github_id) == (NEW_URL, NEW_NAME, 1207506410)

    def test_the_list_shows_the_new_name(self, client, auth_headers, monkeypatch):
        repository = register(client, auth_headers, monkeypatch)
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))
        analyze(client, auth_headers, repository)

        listed = client.get("/api/v1/repositories", headers=auth_headers).json()

        assert [item["owner_nome"] for item in listed] == [NEW_NAME]
        assert [item["url"] for item in listed] == [NEW_URL]

    def test_later_analyses_keep_working_with_the_updated_registration(self, client, auth_headers, monkeypatch):
        repository = register(client, auth_headers, monkeypatch)
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))
        assert analyze(client, auth_headers, repository).status_code == 201

        assert analyze(client, auth_headers, repository).status_code == 201

    def test_a_case_only_difference_is_normalised_to_the_canonical_spelling(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register(client, auth_headers, monkeypatch, "https://github.com/Pallets/Click")
        github_says(monkeypatch, RepoIdentity(42, "pallets/click"))

        analyze(client, auth_headers, repository)

        assert stored(db_session, repository).owner_nome == "pallets/click"

    def test_the_first_analysis_records_the_github_id_even_without_a_rename(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register(client, auth_headers, monkeypatch, "https://github.com/octocat/Hello-World")
        github_says(monkeypatch, RepoIdentity(1296269, "octocat/Hello-World"))

        analyze(client, auth_headers, repository)

        row = stored(db_session, repository)
        assert row.github_id == 1296269
        assert row.url == "https://github.com/octocat/Hello-World"

    def test_without_identity_information_nothing_changes(self, client, auth_headers, monkeypatch, db_session):
        repository = register(client, auth_headers, monkeypatch)
        github_says(monkeypatch, None)

        response = analyze(client, auth_headers, repository)

        assert response.status_code == 201
        row = stored(db_session, repository)
        assert (row.url, row.github_id) == (OLD_URL, None)


class TestADifferentRepositoryUnderTheSameName:
    def test_the_analysis_is_blocked_and_the_registration_is_left_untouched(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register(client, auth_headers, monkeypatch)
        row = stored(db_session, repository)
        row.github_id = 111  # o cadastro foi feito quando o nome apontava para o repositório 111
        db_session.commit()
        github_says(monkeypatch, RepoIdentity(222, "someone-else/Viaje-Mais"))

        response = analyze(client, auth_headers, repository)

        assert response.status_code == 409
        assert "aponta para outro repositório" in response.json()["detail"]
        row = stored(db_session, repository)
        assert (row.url, row.github_id) == (OLD_URL, 111)
        analysis = db_session.query(Analysis).filter_by(repositorio_id=row.id).one()
        assert analysis.status == AnalysisStatus.FALHOU

    def test_no_download_or_metrics_happen_when_blocked(self, client, auth_headers, monkeypatch, db_session):
        repository = register(client, auth_headers, monkeypatch)
        row = stored(db_session, repository)
        row.github_id = 111
        db_session.commit()
        github_says(monkeypatch, RepoIdentity(222, "someone-else/Viaje-Mais"))
        downloads: list[str] = []
        monkeypatch.setattr(
            analyses_module.GithubService, "download_and_extract", lambda self, o, r, d: downloads.append(r)
        )

        analyze(client, auth_headers, repository)

        assert downloads == []

    def test_the_same_id_after_a_rename_is_accepted(self, client, auth_headers, monkeypatch, db_session):
        repository = register(client, auth_headers, monkeypatch)
        row = stored(db_session, repository)
        row.github_id = 1207506410
        db_session.commit()
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))

        assert analyze(client, auth_headers, repository).status_code == 201


class TestDuplicateRegistrations:
    def test_a_rename_is_skipped_when_the_account_already_has_the_new_url(
        self, client, auth_headers, monkeypatch, db_session
    ):
        old = register(client, auth_headers, monkeypatch, OLD_URL)
        new = register(client, auth_headers, monkeypatch, NEW_URL)
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))

        response = analyze(client, auth_headers, old)

        assert response.status_code == 201  # a análise segue, sem erro de chave única
        assert stored(db_session, old).url == OLD_URL
        assert stored(db_session, new).url == NEW_URL

    def test_another_users_registration_does_not_count_as_a_duplicate(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = register(client, auth_headers, monkeypatch, OLD_URL)
        other = User(email="other@example.com", password_hash="x")
        db_session.add(other)
        db_session.commit()
        db_session.add(
            Repository(usuario_id=other.id, url=NEW_URL, owner_nome=NEW_NAME, linguagens_detectadas=["python"])
        )
        db_session.commit()
        github_says(monkeypatch, RepoIdentity(1207506410, NEW_NAME))

        analyze(client, auth_headers, repository)

        assert stored(db_session, repository).url == NEW_URL


class TestSyncUnit:
    def make(self, db_session, url=OLD_URL, github_id=None) -> Repository:
        user = User(email=f"{uuid.uuid4()}@example.com", password_hash="x")
        db_session.add(user)
        db_session.commit()
        repository = Repository(
            usuario_id=user.id,
            url=url,
            owner_nome="/".join(url.split("/")[-2:]),
            linguagens_detectadas=["python"],
            github_id=github_id,
        )
        db_session.add(repository)
        db_session.commit()
        return repository

    def test_outcomes(self, db_session):
        repository = self.make(db_session)

        assert sync_repository_identity(db_session, repository, None) is SyncOutcome.UNCHANGED
        assert sync_repository_identity(db_session, repository, RepoIdentity(1, NEW_NAME)) is SyncOutcome.RENAMED
        assert sync_repository_identity(db_session, repository, RepoIdentity(1, NEW_NAME)) is SyncOutcome.UNCHANGED
        assert sync_repository_identity(db_session, repository, RepoIdentity(2, NEW_NAME)) is SyncOutcome.DIFFERENT_REPOSITORY


class TestServiceCapturesTheIdentity:
    def service(self, handler) -> GithubService:
        return GithubService(
            client=httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
        )

    def test_reads_the_current_identity_after_following_the_redirect(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", None)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/SandroMachiniski-SE/Viaje-Mais":
                return httpx.Response(301, headers={"location": "https://api.github.com/repositories/1207506410"})
            return httpx.Response(200, json={"id": 1207506410, "full_name": NEW_NAME, "size": 182699})

        service = self.service(handler)
        assert service.repo_identity is None

        assert service.fetch_repo_size_kb("SandroMachiniski-SE", "Viaje-Mais") == 182699
        assert service.repo_identity == RepoIdentity(1207506410, NEW_NAME)

    def test_ignores_a_malformed_or_missing_identity(self):
        for body in ({"size": 5}, {"id": "x", "full_name": NEW_NAME, "size": 5}, {"id": 1, "full_name": "sem barra", "size": 5}):
            service = self.service(lambda request, body=body: httpx.Response(200, json=body))
            assert service.fetch_repo_size_kb("o", "r") == 5
            assert service.repo_identity is None
