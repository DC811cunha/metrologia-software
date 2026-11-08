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
from app.services.analysis_runner import dispatch_async_analysis, rate_limit_message, run_full_analysis
from app.services.github_service import (
    GithubRateLimitError,
    GithubService,
    GithubUnavailableError,
    RepositoryAccessError,
    parse_repo_url,
)
from app.services.trend_service import calculate_trend

router = APIRouter(prefix="/api/v1/repositories/{repository_id}/analyses", tags=["analyses"])


def _get_owned_repository(db: Session, repository_id: uuid.UUID, user: User) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None or repository.usuario_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")
    return repository


def _fail_analysis(db: Session, analysis: Analysis, message: str) -> None:
    analysis.status = AnalysisStatus.FALHOU
    analysis.motivo_falha = message
    db.commit()


@router.post("")
def trigger_analysis(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repository = _get_owned_repository(db, repository_id, user)

    analysis = Analysis(repositorio_id=repository.id, status=AnalysisStatus.PENDENTE)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    github_service = GithubService()
    try:
        return _run_trigger(db, analysis, repository, github_service)
    finally:
        github_service.close()


def _run_trigger(db: Session, analysis: Analysis, repository: Repository, github_service: GithubService):
    owner, repo = parse_repo_url(repository.url)
    try:
        size_kb = github_service.fetch_repo_size_kb(owner, repo)
    except RepositoryAccessError as exc:
        repository.status_acesso = AccessStatus.INACESSIVEL
        _fail_analysis(db, analysis, f"Repositório inacessível: {exc}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except GithubRateLimitError as exc:
        # Cota esgotada é temporária: a análise falha com o motivo, mas o repositório segue ativo.
        message = rate_limit_message(exc.retry_after)
        _fail_analysis(db, analysis, message)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None,
        ) from exc
    except GithubUnavailableError as exc:
        message = "O GitHub está indisponível no momento. Tente novamente em instantes."
        _fail_analysis(db, analysis, message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message) from exc

    # O repositório respondeu: se estava marcado como inacessível (ex.: por uma resposta temporária
    # antiga), volta a ficar ativo — nada mais fazia essa transição.
    if repository.status_acesso == AccessStatus.INACESSIVEL:
        repository.status_acesso = AccessStatus.ATIVO
        db.commit()

    if size_kb > settings.max_repo_size_kb:
        # Recusa em vez de só mudar para o modo assíncrono: um repositório gigante enche o disco do
        # worker mesmo rodando em segundo plano.
        message = (
            f"Repositório grande demais para análise ({size_kb // 1024} MB; "
            f"máximo {settings.max_repo_size_kb // 1024} MB)"
        )
        _fail_analysis(db, analysis, message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    analysis.status = AnalysisStatus.PROCESSANDO
    db.commit()

    if size_kb <= settings.sync_analysis_size_limit_kb:
        run_full_analysis(db, analysis, repository, github_service)
        db.refresh(analysis)
        body = jsonable_encoder(AnalysisResponse.model_validate(analysis))
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=body)

    try:
        dispatch_async_analysis(analysis.id)
    except Exception as exc:  # noqa: BLE001 - fila fora do ar (Redis/broker) não pode deixar a análise "processando"
        message = "Não foi possível enfileirar a análise agora. Tente novamente em instantes."
        _fail_analysis(db, analysis, message)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message) from exc
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
