import uuid

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Analysis, Repository
from app.services.analysis_runner import run_full_analysis
from app.services.github_service import GithubService


# O prazo cooperativo (`analysis_time_limit_s`) dispara primeiro; estes limites do Celery são a rede
# de segurança caso a análise trave fora de um laço por arquivo (ex.: em uma biblioteca nativa).
@celery_app.task(
    name="run_analysis",
    soft_time_limit=settings.analysis_time_limit_s + 30,
    time_limit=settings.analysis_time_limit_s + 60,
)
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
