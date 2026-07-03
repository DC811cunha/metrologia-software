"""create repositories analyses measurements tables

Revision ID: 926e03a1f9c1
Revises: 074bc0300d80
Create Date: 2026-06-25 20:20:29.755131

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '926e03a1f9c1'
down_revision: str | None = '074bc0300d80'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('repositories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('owner_nome', sa.String(length=255), nullable=False),
    sa.Column('linguagens_detectadas', sa.JSON(), nullable=False),
    sa.Column('status_acesso', sa.String(length=20), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('usuario_id', 'url', name='uq_repository_usuario_url')
    )
    op.create_index(op.f('ix_repositories_usuario_id'), 'repositories', ['usuario_id'], unique=False)
    op.create_table('analyses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('repositorio_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('motivo_falha', sa.String(length=1000), nullable=True),
    sa.Column('solicitada_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('concluida_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status_conformidade_geral', sa.String(length=20), nullable=True),
    sa.ForeignKeyConstraint(['repositorio_id'], ['repositories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analyses_repositorio_id'), 'analyses', ['repositorio_id'], unique=False)
    op.create_table('measurements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('analise_id', sa.Uuid(), nullable=False),
    sa.Column('metrica_chave', sa.String(length=50), nullable=False),
    sa.Column('valor_medido', sa.Numeric(precision=10, scale=4), nullable=True),
    sa.Column('status_conformidade', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['analise_id'], ['analyses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_measurements_analise_id'), 'measurements', ['analise_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_measurements_analise_id'), table_name='measurements')
    op.drop_table('measurements')
    op.drop_index(op.f('ix_analyses_repositorio_id'), table_name='analyses')
    op.drop_table('analyses')
    op.drop_index(op.f('ix_repositories_usuario_id'), table_name='repositories')
    op.drop_table('repositories')
