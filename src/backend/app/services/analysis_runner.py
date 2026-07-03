"""Orquestra a execução completa de uma Análise: download do repositório, cálculo das
6 métricas do catálogo, classificação de conformidade e persistência (FR-003 a FR-007).
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.analysis import coupling, duplication, metric_engine
from app.analysis.coverage_reader import read_coverage_percentage
from app.models.analysis import Analysis, AnalysisStatus, Measurement
from app.models.repository import AccessStatus, Repository
from app.services.conformity_service import calculate_overall_status, classify_measurements
from app.services.github_service import GithubService, RepositoryAccessError, parse_repo_url


def _compute_metric_values(root: Path, languages: list[str]) -> dict[str, float | None]:
    repo_metrics = metric_engine.analyze_repository(root, languages)
    return {
        "complexidade_ciclomatica": repo_metrics.avg_complexity,
        "loc": repo_metrics.avg_loc,
        "indice_manutenibilidade": repo_metrics.avg_maintainability_index,
        "cobertura_testes": read_coverage_percentage(root),
        "acoplamento": coupling.calculate_average_instability(root, languages),
        "score_duplicacao": duplication.calculate_duplication_score(root, languages),
    }


def _persist_success(db: Session, analysis: Analysis, values: dict[str, float | None]) -> None:
    measurements = classify_measurements(values)
    overall_status = calculate_overall_status(measurements)

    for measurement in measurements:
        db.add(
            Measurement(
                analise_id=analysis.id,
                metrica_chave=measurement.metrica_chave,
                valor_medido=measurement.valor_medido,
                status_conformidade=measurement.status_conformidade.value,
            )
        )

    analysis.status = AnalysisStatus.CONCLUIDA
    analysis.status_conformidade_geral = overall_status.value
    analysis.concluida_em = datetime.now(timezone.utc)
    db.commit()


def _persist_failure(db: Session, analysis: Analysis, motivo: str) -> None:
    analysis.status = AnalysisStatus.FALHOU
    analysis.motivo_falha = motivo[:1000]
    analysis.concluida_em = datetime.now(timezone.utc)
    db.commit()


def run_full_analysis(
    db: Session,
    analysis: Analysis,
    repository: Repository,
    github_service: GithubService | None = None,
) -> None:
    """Executa o pipeline completo; nunca propaga exceção — falhas são persistidas em
    `Analysis.motivo_falha` (FR-014: repositório inacessível, limite de API excedido etc.)."""
    service = github_service or GithubService()
    owner, repo = parse_repo_url(repository.url)

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = service.download_and_extract(owner, repo, Path(tmp_dir))
            values = _compute_metric_values(root, repository.linguagens_detectadas)
        _persist_success(db, analysis, values)
    except RepositoryAccessError as exc:
        repository.status_acesso = AccessStatus.INACESSIVEL
        db.commit()
        _persist_failure(db, analysis, f"Repositório inacessível: {exc}")
    except Exception as exc:  # noqa: BLE001 - falha de análise nunca deve derrubar o worker
        _persist_failure(db, analysis, f"Falha ao executar análise: {exc}")


def dispatch_async_analysis(analysis_id: uuid.UUID) -> None:
    from app.workers.analysis_tasks import run_analysis_task

    run_analysis_task.delay(str(analysis_id))
