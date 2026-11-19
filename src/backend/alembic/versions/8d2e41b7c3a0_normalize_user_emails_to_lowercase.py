"""normaliza e-mails de usuários para minúsculas

Antes, "Pessoa@Example.com" e "pessoa@example.com" eram contas diferentes e o login com outra caixa
falhava. A API passou a normalizar o e-mail para minúsculas; esta migração leva as contas existentes
para o mesmo formato. Se duas contas só diferirem pela caixa, a migração para com a lista dos
e-mails em conflito (unir contas é decisão humana).

Revision ID: 8d2e41b7c3a0
Revises: 5c1f0d7a9b42
Create Date: 2026-11-18 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '8d2e41b7c3a0'
down_revision: str | None = '5c1f0d7a9b42'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    conflicts = bind.execute(
        sa.text("SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1")
    ).scalars().all()
    if conflicts:
        raise RuntimeError(
            "Contas que só diferem pela caixa do e-mail — resolva antes de migrar: " + ", ".join(conflicts)
        )
    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")


def downgrade() -> None:
    # A caixa original não é recuperável: nada a desfazer.
    pass
