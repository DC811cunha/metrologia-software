import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.metrics_catalog import METRICS_CATALOG
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis, AnalysisStatus
from app.models.repository import AccessStatus, Repository
from app.models.user import User
from app.schemas.analysis import (
    AnalysisAcceptedResponse,
    AnalysisHistoryItemResponse,
    AnalysisResponse,
    MetricSeriesPointResponse,
    MetricTrendResponse,
)
from app.services.analysis_runner import dispatch_async_analysis, run_full_analysis
from app.services.github_service import GithubService, RepositoryAccessError, parse_repo_url
from app.services.trend_service import calculate_trend

router = APIRouter(prefix="/api/v1/repositories/{repository_id}/analyses", tags=["analyses"])


def _get_owned_repository(db: Session, repository_id: uuid.UUID, user: User) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None or repository.usuario_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")
    return repository


@router.post("")
def trigger_analysis(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repository = _get_owned_repository(db, repository_id, user)
    if repository.status_acesso == AccessStatus.INACESSIVEL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Repositório inacessível"
        )

    analysis = Analysis(repositorio_id=repository.id, status=AnalysisStatus.PENDENTE)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    github_service = GithubService()
    owner, repo = parse_repo_url(repository.url)
    try:
        size_kb = github_service.fetch_repo_size_kb(owner, repo)
    except RepositoryAccessError as exc:
        repository.status_acesso = AccessStatus.INACESSIVEL
        analysis.status = AnalysisStatus.FALHOU
        analysis.motivo_falha = f"Repositório inacessível: {exc}"
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    analysis.status = AnalysisStatus.PROCESSANDO
    db.commit()

    if size_kb <= settings.sync_analysis_size_limit_kb:
        run_full_analysis(db, analysis, repository, github_service)
        db.refresh(analysis)
        body = jsonable_encoder(AnalysisResponse.model_validate(analysis))
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=body)

    dispatch_async_analysis(analysis.id)
    body = jsonable_encoder(
        AnalysisAcceptedResponse(id=analysis.id, status=AnalysisStatus.PROCESSANDO.value)
    )
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body)


@router.get("")
def list_analyses(
    repository_id: uuid.UUID,
    metrica: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_repository(db, repository_id, user)
    analyses = (
        db.execute(
            select(Analysis)
            .where(Analysis.repositorio_id == repository_id)
            .order_by(Analysis.solicitada_em.asc())
        )
        .scalars()
        .all()
    )

    if metrica is None:
        return [AnalysisHistoryItemResponse.model_validate(a) for a in analyses]

    if metrica not in METRICS_CATALOG:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Métrica '{metrica}' desconhecida",
        )

    serie = []
    for analysis in analyses:
        if analysis.status != AnalysisStatus.CONCLUIDA:
            continue
        measurement = next((m for m in analysis.medicoes if m.metrica_chave == metrica), None)
        if measurement is None:
            continue
        serie.append(
            MetricSeriesPointResponse(
                analise_id=analysis.id,
                concluida_em=analysis.concluida_em,
                valor_medido=measurement.valor_medido,
                status_conformidade=measurement.status_conformidade,
            )
        )

    tendencia = None
    if len(serie) >= 2:
        tendencia = calculate_trend(metrica, serie[-2].valor_medido, serie[-1].valor_medido)

    return MetricTrendResponse(metrica_chave=metrica, tendencia=tendencia, serie=serie)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    repository_id: uuid.UUID,
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Analysis:
    _get_owned_repository(db, repository_id, user)
    analysis = db.get(Analysis, analysis_id)
    if analysis is None or analysis.repositorio_id != repository_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
    return analysis
