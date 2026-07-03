import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ReportType(str, Enum):
    ANALISE_UNICA = "analise_unica"
    HISTORICO_COMPLETO = "historico_completo"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    repositorio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id"), nullable=False, index=True
    )
    tipo: Mapped[ReportType] = mapped_column(String(20), nullable=False)
    analise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analyses.id"), nullable=True
    )
    gerado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    caminho_arquivo: Mapped[str] = mapped_column(String(500), nullable=False)
