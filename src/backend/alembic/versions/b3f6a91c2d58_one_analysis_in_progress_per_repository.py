"""no máximo uma análise em andamento por repositório

Índice único parcial: duas requisições simultâneas (duplo clique, duas abas) não conseguem mais criar duas
análises `pendente`/`processando` do mesmo repositório — a segunda recebe 409. Antes de criar o índice, as
análises em andamento duplicadas já existentes (restos de worker que caiu) são encerradas como `falhou`,
mantendo só a mais recente de cada repositório.

Revision ID: b3f6a91c2d58
Revises: 8d2e41b7c3a0
Create Date: 2026-11-18 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3f6a91c2d58'
down_revision: str | None = '8d2e41b7c3a0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IN_PROGRESS = "status IN ('pendente', 'processando')"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE analyses
           SET status = 'falhou',
               motivo_falha = 'A análise foi interrompida antes de terminar (substituída por uma mais recente).',
               concluida_em = COALESCE(concluida_em, now())
         WHERE {IN_PROGRESS}
           AND id NOT IN (
               SELECT DISTINCT ON (repositorio_id) id
                 FROM analyses
                WHERE {IN_PROGRESS}
                ORDER BY repositorio_id, solicitada_em DESC
           )
        """
    )
    op.create_index(
        'uq_analyses_one_in_progress_per_repository',
        'analyses',
        ['repositorio_id'],
        unique=True,
        postgresql_where=sa.text(IN_PROGRESS),
    )


def downgrade() -> None:
    op.drop_index('uq_analyses_one_in_progress_per_repository', table_name='analyses')
