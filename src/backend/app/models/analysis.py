import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class AnalysisStatus(str, Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDA = "concluida"
    FALHOU = "falhou"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repositorio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id"), nullable=False, index=True
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        String(20), nullable=False, default=AnalysisStatus.PENDENTE
    )
    motivo_falha: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    solicitada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_conformidade_geral: Mapped[str | None] = mapped_column(String(20), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="analyses")
    medicoes: Mapped[list["Measurement"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id"), nullable=False, index=True)
    metrica_chave: Mapped[str] = mapped_column(String(50), nullable=False)
    valor_medido: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    status_conformidade: Mapped[str] = mapped_column(String(20), nullable=False)

    analysis: Mapped["Analysis"] = relationship(back_populates="medicoes")
