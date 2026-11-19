"""Uma análise em andamento por repositório (409) e teto de análises síncronas simultâneas (fila quando lotado)."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module
from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatus
from app.services.stale_analyses import STALE_ANALYSIS_MESSAGE
from app.services.sync_slots import SyncAnalysisSlots, sync_slots


def _register(client, auth_headers, monkeypatch, url="https://github.com/octocat/Hello-World") -> dict:
    monkeypatch.setattr(repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"])
    return client.post("/api/v1/repositories", json={"url": url}, headers=auth_headers).json()


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-abc123"
    root.mkdir(parents=True)
    (root / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return root


@pytest.fixture()
def small_repository_on_github(monkeypatch):
    monkeypatch.setattr(analyses_module.GithubService, "fetch_repo_size_kb", lambda self, o, r: 10)
    monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)


def _trigger(client, auth_headers, repository):
    return client.post(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers)


def _add_analysis(db_session, repository_id: str, status: AnalysisStatus, age_s: int = 0) -> Analysis:
    analysis = Analysis(
        repositorio_id=uuid.UUID(repository_id),
        status=status,
        solicitada_em=datetime.now(UTC) - timedelta(seconds=age_s),
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


class TestOneAnalysisInProgressPerRepository:
    @pytest.mark.parametrize("running", [AnalysisStatus.PENDENTE, AnalysisStatus.PROCESSANDO])
    def test_a_second_request_while_one_is_running_is_a_conflict(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github, running
    ):
        repository = _register(client, auth_headers, monkeypatch)
        _add_analysis(db_session, repository["id"], running)

        response = _trigger(client, auth_headers, repository)

        assert response.status_code == 409
        assert response.json()["detail"] == analyses_module.IN_PROGRESS_MESSAGE
        assert db_session.query(Analysis).count() == 1  # nenhuma tentativa nova foi criada

    def test_a_finished_analysis_does_not_block_a_new_one(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github
    ):
        repository = _register(client, auth_headers, monkeypatch)
        _add_analysis(db_session, repository["id"], AnalysisStatus.CONCLUIDA)
        _add_analysis(db_session, repository["id"], AnalysisStatus.FALHOU)

        assert _trigger(client, auth_headers, repository).status_code == 201

    def test_other_repositories_are_independent(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github
    ):
        busy = _register(client, auth_headers, monkeypatch)
        free = _register(client, auth_headers, monkeypatch, "https://github.com/octocat/Spoon-Knife")
        _add_analysis(db_session, busy["id"], AnalysisStatus.PROCESSANDO)

        assert _trigger(client, auth_headers, busy).status_code == 409
        assert _trigger(client, auth_headers, free).status_code == 201

    def test_a_lost_analysis_does_not_block_the_repository_forever(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github
    ):
        repository = _register(client, auth_headers, monkeypatch)
        lost = _add_analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=settings.stale_analysis_after_s + 60)

        response = _trigger(client, auth_headers, repository)

        assert response.status_code == 201
        db_session.refresh(lost)
        assert lost.status == AnalysisStatus.FALHOU
        assert lost.motivo_falha == STALE_ANALYSIS_MESSAGE

    def test_two_requests_racing_past_the_check_create_only_one(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github
    ):
        # Simula a corrida: a checagem não vê a análise em curso, então só o índice único do banco a impede.
        repository = _register(client, auth_headers, monkeypatch)
        _add_analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO)
        monkeypatch.setattr(analyses_module, "_analysis_in_progress", lambda db, repository_id: False)

        response = _trigger(client, auth_headers, repository)

        assert response.status_code == 409
        assert response.json()["detail"] == analyses_module.IN_PROGRESS_MESSAGE
        assert db_session.query(Analysis).count() == 1

    def test_the_database_itself_refuses_two_analyses_in_progress(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        _add_analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO)

        db_session.add(Analysis(repositorio_id=uuid.UUID(repository["id"]), status=AnalysisStatus.PENDENTE))
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestSyncAnalysisSlots:
    def test_counter_respects_the_configured_limit(self, monkeypatch):
        monkeypatch.setattr(settings, "max_concurrent_sync_analyses", 2)
        slots = SyncAnalysisSlots()

        assert slots.try_acquire() and slots.try_acquire()
        assert slots.try_acquire() is False
        slots.release()
        assert slots.try_acquire() is True

    def test_release_never_goes_below_zero(self):
        slots = SyncAnalysisSlots()

        slots.release()
        slots.release()

        assert slots.active == 0

    def test_a_full_server_sends_the_analysis_to_the_queue(
        self, client, auth_headers, monkeypatch, db_session, small_repository_on_github
    ):
        monkeypatch.setattr(settings, "max_concurrent_sync_analyses", 1)
        dispatched: list[uuid.UUID] = []
        monkeypatch.setattr(analyses_module, "dispatch_async_analysis", lambda analysis_id: dispatched.append(analysis_id))
        repository = _register(client, auth_headers, monkeypatch)
        assert sync_slots.try_acquire()  # outra análise síncrona ocupa a única vaga
        try:
            response = _trigger(client, auth_headers, repository)
        finally:
            sync_slots.release()

        assert response.status_code == 202
        assert response.json()["status"] == "processando"
        assert dispatched == [uuid.UUID(response.json()["id"])]

    def test_with_a_free_slot_a_small_repository_still_runs_synchronously(
        self, client, auth_headers, monkeypatch, small_repository_on_github
    ):
        repository = _register(client, auth_headers, monkeypatch)

        response = _trigger(client, auth_headers, repository)

        assert response.status_code == 201
        assert response.json()["status"] == "concluida"
        assert sync_slots.active == 0  # a vaga foi devolvida

    def test_the_slot_is_returned_even_when_the_analysis_blows_up(
        self, client, auth_headers, monkeypatch, small_repository_on_github
    ):
        def boom(db, analysis, repository, github_service=None):
            raise RuntimeError("erro inesperado")

        monkeypatch.setattr(analyses_module, "run_full_analysis", boom)
        repository = _register(client, auth_headers, monkeypatch)

        with pytest.raises(RuntimeError):
            _trigger(client, auth_headers, repository)

        assert sync_slots.active == 0
