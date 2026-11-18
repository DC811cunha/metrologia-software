"""Análises perdidas (worker caiu/reiniciou) e o link do dashboard depois de uma tentativa que falhou."""

import uuid
from datetime import datetime, timedelta, timezone

import app.api.repositories as repositories_module
from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatus
from app.services.stale_analyses import STALE_ANALYSIS_MESSAGE, expire_stale_analyses


def _register(client, auth_headers, monkeypatch, url="https://github.com/octocat/Hello-World") -> dict:
    monkeypatch.setattr(repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"])
    return client.post("/api/v1/repositories", json={"url": url}, headers=auth_headers).json()


def _analysis(db_session, repository_id: str, status: AnalysisStatus, *, age_s: int = 0) -> Analysis:
    analysis = Analysis(
        repositorio_id=uuid.UUID(repository_id),
        status=status,
        solicitada_em=datetime.now(timezone.utc) - timedelta(seconds=age_s),
        concluida_em=datetime.now(timezone.utc) if status in (AnalysisStatus.CONCLUIDA, AnalysisStatus.FALHOU) else None,
        status_conformidade_geral="Conforme" if status is AnalysisStatus.CONCLUIDA else None,
    )
    db_session.add(analysis)
    db_session.commit()
    return analysis


OLD = settings.stale_analysis_after_s + 60


class TestExpireStaleAnalyses:
    def test_marks_old_pending_and_processing_analyses_as_failed(self, client, auth_headers, monkeypatch, db_session):
        # Dois repositórios: só pode haver UMA análise em andamento por repositório (índice único parcial).
        repository = _register(client, auth_headers, monkeypatch)
        other = _register(client, auth_headers, monkeypatch, "https://github.com/octocat/Spoon-Knife")
        stuck_processing = _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=OLD)
        stuck_pending = _analysis(db_session, other["id"], AnalysisStatus.PENDENTE, age_s=OLD)

        assert expire_stale_analyses(db_session, [uuid.UUID(repository["id"]), uuid.UUID(other["id"])]) == 2

        for analysis in (stuck_processing, stuck_pending):
            db_session.refresh(analysis)
            assert analysis.status == AnalysisStatus.FALHOU
            assert analysis.motivo_falha == STALE_ANALYSIS_MESSAGE
            assert analysis.concluida_em is not None

    def test_leaves_recent_and_finished_analyses_alone(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        recent = _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=30)
        done = _analysis(db_session, repository["id"], AnalysisStatus.CONCLUIDA, age_s=OLD)

        assert expire_stale_analyses(db_session, [uuid.UUID(repository["id"])]) == 0

        db_session.refresh(recent)
        db_session.refresh(done)
        assert recent.status == AnalysisStatus.PROCESSANDO
        assert done.status == AnalysisStatus.CONCLUIDA

    def test_does_nothing_without_repositories(self, db_session):
        assert expire_stale_analyses(db_session, []) == 0

    def test_listing_the_history_expires_stuck_analyses(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=OLD)

        history = client.get(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers).json()

        assert history[0]["status"] == "falhou"
        assert history[0]["motivo_falha"] == STALE_ANALYSIS_MESSAGE

    def test_reading_one_analysis_expires_it(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        stuck = _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=OLD)

        body = client.get(
            f"/api/v1/repositories/{repository['id']}/analyses/{stuck.id}", headers=auth_headers
        ).json()

        assert body["status"] == "falhou"

    def test_listing_the_repositories_expires_stuck_analyses(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO, age_s=OLD)

        [item] = client.get("/api/v1/repositories", headers=auth_headers).json()

        assert item["ultima_analise_status"] == "falhou"


class TestLatestCompletedAnalysisInTheList:
    def test_points_to_the_latest_completed_analysis_even_after_a_failed_attempt(
        self, client, auth_headers, monkeypatch, db_session
    ):
        repository = _register(client, auth_headers, monkeypatch)
        _analysis(db_session, repository["id"], AnalysisStatus.CONCLUIDA, age_s=300)
        latest_done = _analysis(db_session, repository["id"], AnalysisStatus.CONCLUIDA, age_s=200)
        failed = _analysis(db_session, repository["id"], AnalysisStatus.FALHOU, age_s=100)

        [item] = client.get("/api/v1/repositories", headers=auth_headers).json()

        assert item["ultima_analise_id"] == str(failed.id)
        assert item["ultima_analise_status"] == "falhou"
        assert item["ultima_concluida_id"] == str(latest_done.id)

    def test_is_null_when_nothing_ever_completed(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch)
        _analysis(db_session, repository["id"], AnalysisStatus.FALHOU, age_s=100)

        [item] = client.get("/api/v1/repositories", headers=auth_headers).json()

        assert item["ultima_concluida_id"] is None


class TestWorkerWhenTheRepositoryIsDeletedMidAnalysis:
    """Log real de 13/11: StaleDataError + PendingRollbackError com traceback no worker."""

    def test_the_task_discards_the_result_instead_of_crashing(self, client, auth_headers, monkeypatch, db_session):
        import app.workers.analysis_tasks as tasks_module
        from sqlalchemy.orm.exc import StaleDataError

        repository = _register(client, auth_headers, monkeypatch)
        analysis = _analysis(db_session, repository["id"], AnalysisStatus.PROCESSANDO)

        def deleted_meanwhile(db, analysis, repository, github_service=None):
            raise StaleDataError("UPDATE statement on table 'analyses' expected to update 1 row(s); 0 were matched.")

        monkeypatch.setattr(tasks_module, "run_full_analysis", deleted_meanwhile)
        monkeypatch.setattr(tasks_module, "SessionLocal", lambda: db_session)
        monkeypatch.setattr(db_session, "close", lambda: None)  # a sessão do teste segue aberta

        tasks_module.run_analysis_task(str(analysis.id))  # não deve levantar
