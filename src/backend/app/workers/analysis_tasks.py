import uuid

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.analysis import Analysis
from app.models.repository import Repository
from app.services.analysis_runner import run_full_analysis
from app.services.github_service import GithubService


@celery_app.task(name="run_analysis")
def run_analysis_task(analysis_id: str) -> None:
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, uuid.UUID(analysis_id))
        if analysis is None:
            return
        repository = db.get(Repository, analysis.repositorio_id)
        if repository is None:
            return
        run_full_analysis(db, analysis, repository, GithubService())
    finally:
        db.close()
