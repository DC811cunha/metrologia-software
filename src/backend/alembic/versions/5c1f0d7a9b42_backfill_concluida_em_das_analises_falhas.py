"""backfill concluida_em das análises que falharam

Falhas registradas pela API (GitHub fora do ar, cota esgotada, repositório inacessível...) ficaram sem
`concluida_em` e o histórico as exibia como "em andamento". A data real do término não foi guardada;
`solicitada_em` é a melhor aproximação (essas falhas ocorrem na própria requisição).

Revision ID: 5c1f0d7a9b42
Revises: 122e5149a748
Create Date: 2026-11-17 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = '5c1f0d7a9b42'
down_revision: str | None = '122e5149a748'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE analyses SET concluida_em = solicitada_em "
        "WHERE status = 'falhou' AND concluida_em IS NULL"
    )


def downgrade() -> None:
    # Não há como distinguir as linhas corrigidas das que já tinham data: nada a desfazer.
    pass
