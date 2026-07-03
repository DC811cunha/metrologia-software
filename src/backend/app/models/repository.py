import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.user import User


class AccessStatus(str, Enum):
    ATIVO = "ativo"
    INACESSIVEL = "inacessivel"


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("usuario_id", "url", name="uq_repository_usuario_url"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    owner_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    linguagens_detectadas: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status_acesso: Mapped[AccessStatus] = mapped_column(
        String(20), nullable=False, default=AccessStatus.ATIVO
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="repositories")
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
