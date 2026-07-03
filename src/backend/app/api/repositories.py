import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.repository import Repository
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreateRequest,
    RepositoryListItemResponse,
    RepositoryResponse,
)
from app.services.github_service import (
    GithubService,
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

    github_service = GithubService()
    try:
        languages = github_service.fetch_languages(owner, repo)
    except RepositoryAccessError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UnsupportedLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    repository = Repository(
        usuario_id=user.id,
        url=payload.url,
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


@router.get("", response_model=list[RepositoryListItemResponse])
def list_repositories(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[RepositoryListItemResponse]:
    repositories = (
        db.execute(select(Repository).where(Repository.usuario_id == user.id)).scalars().all()
    )

    results = []
    for repository in repositories:
        last_analysis = db.execute(
            select(Analysis)
            .where(Analysis.repositorio_id == repository.id)
            .order_by(Analysis.solicitada_em.desc())
            .limit(1)
        ).scalar_one_or_none()
        results.append(
            RepositoryListItemResponse(
                **RepositoryResponse.model_validate(repository).model_dump(),
                ultima_analise_status=last_analysis.status if last_analysis else None,
                ultima_analise_id=last_analysis.id if last_analysis else None,
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


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    repository = _get_owned_repository(db, repository_id, user)
    db.delete(repository)
    db.commit()
