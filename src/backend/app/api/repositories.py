import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis, AnalysisStatus
from app.models.report import Report
from app.models.repository import Repository
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreateRequest,
    RepositoryListItemResponse,
    RepositoryResponse,
)
from app.services.analysis_runner import rate_limit_message
from app.services.stale_analyses import expire_stale_analyses
from app.services.github_service import (
    GithubRateLimitError,
    GithubService,
    GithubUnavailableError,
    RepositoryAccessError,
    UnsupportedLanguageError,
    parse_repo_url,
)

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])


def _get_owned_repository(db: Session, repository_id: uuid.UUID, user: User) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None or repository.usuario_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")
    return repository


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RepositoryResponse)
def create_repository(
    payload: RepositoryCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Repository:
    owner, repo = parse_repo_url(payload.url)
    # Forma única: sempre https, sem ".git" nem barra final. O GitHub ignora a caixa do nome, então a duplicata
    # também (antes, "Foo/Bar" e "foo/bar", ou com ".git", viravam dois cadastros até a primeira análise).
    canonical_url = f"https://github.com/{owner}/{repo}"
    already_registered = db.execute(
        select(Repository.id).where(
            Repository.usuario_id == user.id, func.lower(Repository.url) == canonical_url.lower()
        )
    ).first()
    if already_registered is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repositório já cadastrado")

    github_service = GithubService()
    try:
        languages = github_service.fetch_languages(owner, repo)
    except RepositoryAccessError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UnsupportedLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GithubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_limit_message(exc.retry_after),
            headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None,
        ) from exc
    except GithubUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="O GitHub está indisponível no momento. Tente novamente em instantes.",
        ) from exc
    finally:
        github_service.close()

    repository = Repository(
        usuario_id=user.id,
        url=canonical_url,
        owner_nome=f"{owner}/{repo}",
        linguagens_detectadas=languages,
    )
    db.add(repository)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Repositório já cadastrado"
        ) from exc
    db.refresh(repository)
    return repository


def _latest_analysis_per_repository(
    db: Session, repository_ids: list[uuid.UUID], *conditions: ColumnElement[bool]
) -> dict[uuid.UUID, tuple[uuid.UUID, str]]:
    """`{repositório: (id, status)}` da análise mais recente de cada um (entre as que atendem às
    `conditions`), com uma função de janela — uma única consulta para a lista toda."""
    if not repository_ids:
        return {}
    ranked = (
        select(
            Analysis.repositorio_id.label("repositorio_id"),
            Analysis.id.label("id"),
            Analysis.status.label("status"),
            func.row_number()
            .over(partition_by=Analysis.repositorio_id, order_by=Analysis.solicitada_em.desc())
            .label("position"),
        )
        .where(Analysis.repositorio_id.in_(repository_ids), *conditions)
        .subquery()
    )
    rows = db.execute(
        select(ranked.c.repositorio_id, ranked.c.id, ranked.c.status).where(ranked.c.position == 1)
    ).tuples()
    return {repository_id: (analysis_id, str(status)) for repository_id, analysis_id, status in rows}


@router.get("", response_model=list[RepositoryListItemResponse])
def list_repositories(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[RepositoryListItemResponse]:
    repositories = (
        db.execute(select(Repository).where(Repository.usuario_id == user.id)).scalars().all()
    )

    repository_ids = [repository.id for repository in repositories]
    expire_stale_analyses(db, repository_ids)
    # Duas consultas agrupadas para a lista toda (em vez de uma por repositório).
    analyses_per_repository: dict[uuid.UUID, int] = {
        repository_id: total
        for repository_id, total in db.execute(
            select(Analysis.repositorio_id, func.count())
            .where(Analysis.repositorio_id.in_(repository_ids))
            .group_by(Analysis.repositorio_id)
        ).tuples()
    }
    reports_per_repository: dict[uuid.UUID, int] = {
        repository_id: total
        for repository_id, total in db.execute(
            select(Report.repositorio_id, func.count())
            .where(Report.repositorio_id.in_(repository_ids))
            .group_by(Report.repositorio_id)
        ).tuples()
    }

    # Última tentativa e última CONCLUÍDA de cada repositório, cada uma em UMA consulta (antes: uma por repositório).
    last_attempt = _latest_analysis_per_repository(db, repository_ids)
    last_completed = _latest_analysis_per_repository(db, repository_ids, Analysis.status == AnalysisStatus.CONCLUIDA)

    results = []
    for repository in repositories:
        attempt = last_attempt.get(repository.id)
        completed = last_completed.get(repository.id)
        results.append(
            RepositoryListItemResponse(
                **RepositoryResponse.model_validate(repository).model_dump(),
                ultima_analise_status=attempt[1] if attempt else None,
                ultima_analise_id=attempt[0] if attempt else None,
                ultima_concluida_id=completed[0] if completed else None,
                total_analises=analyses_per_repository.get(repository.id, 0),
                total_relatorios=reports_per_repository.get(repository.id, 0),
            )
        )
    return results


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Repository:
    return _get_owned_repository(db, repository_id, user)


logger = logging.getLogger(__name__)


def _remove_report_files(paths: list[str]) -> None:
    """Apaga os PDFs de um repositório excluído. Melhor esforço: o registro já saiu do banco, então um
    arquivo ausente ou que não pode ser removido só é registrado em log. Só toca em arquivos dentro do
    diretório de relatórios, nunca em um caminho arbitrário vindo do banco."""
    reports_dir = Path(settings.reports_dir).resolve()
    for raw_path in paths:
        if not raw_path:
            continue
        try:
            path = Path(raw_path).resolve()
            if path.parent == reports_dir and path.suffix == ".pdf":
                path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Não foi possível remover o arquivo de relatório %s", raw_path)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    repository = _get_owned_repository(db, repository_id, user)
    # Os caminhos precisam ser lidos antes: depois do commit os relatórios deixam de existir no banco.
    report_files = [report.caminho_arquivo for report in repository.reports]
    db.delete(repository)
    db.commit()
    _remove_report_files(report_files)
