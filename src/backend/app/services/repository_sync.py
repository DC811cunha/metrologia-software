"""Mantém o cadastro do repositório alinhado com o GitHub (nome/URL canônicos e id).

O GitHub mantém um redirecionamento do nome antigo para o novo quando um repositório é renomeado ou
transferido, e o SoftMeter o segue; esta sincronização atualiza o cadastro para o nome atual e guarda o
id numérico. O id também detecta o caso perigoso: o nome cadastrado passou a apontar para OUTRO
repositório (o nome antigo foi reutilizado) — nesse caso a análise é barrada em vez de medir o repositório errado.
"""

import logging
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.services.github_service import RepoIdentity

logger = logging.getLogger(__name__)


class SyncOutcome(str, Enum):
    UNCHANGED = "unchanged"
    RENAMED = "renamed"
    RENAME_SKIPPED = "rename_skipped"  # outro cadastro da mesma conta já usa a URL atual
    DIFFERENT_REPOSITORY = "different_repository"  # o nome cadastrado aponta para outro repositório


def sync_repository_identity(db: Session, repository: Repository, identity: RepoIdentity | None) -> SyncOutcome:
    if identity is None:
        return SyncOutcome.UNCHANGED

    if repository.github_id is not None and repository.github_id != identity.github_id:
        return SyncOutcome.DIFFERENT_REPOSITORY

    changed = False
    if repository.github_id is None:
        repository.github_id = identity.github_id
        changed = True

    canonical_url = f"https://github.com/{identity.full_name}"
    outcome = SyncOutcome.UNCHANGED
    if repository.url != canonical_url or repository.owner_nome != identity.full_name:
        taken = db.execute(
            select(Repository.id).where(
                Repository.usuario_id == repository.usuario_id,
                Repository.url == canonical_url,
                Repository.id != repository.id,
            )
        ).first()
        if taken is not None:
            # Duplicata (ex.: o mesmo repositório cadastrado pelo nome antigo e pelo novo): não renomeia e
            # não funde históricos automaticamente — fundir é destrutivo e fica a critério do usuário.
            logger.warning(
                "Cadastro %s não renomeado para %s: a conta já tem outro cadastro com essa URL",
                repository.id,
                canonical_url,
            )
            outcome = SyncOutcome.RENAME_SKIPPED
        else:
            logger.info("Repositório %s renomeado: %s -> %s", repository.id, repository.url, canonical_url)
            repository.url = canonical_url
            repository.owner_nome = identity.full_name
            outcome = SyncOutcome.RENAMED
            changed = True

    if changed:
        db.commit()
    return outcome
