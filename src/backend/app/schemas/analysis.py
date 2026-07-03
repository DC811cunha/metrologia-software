import uuid
from datetime import datetime

from pydantic import BaseModel


class MeasurementResponse(BaseModel):
    metrica_chave: str
    valor_medido: float | None
    status_conformidade: str

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    repositorio_id: uuid.UUID
    status: str
    motivo_falha: str | None = None
    solicitada_em: datetime
    concluida_em: datetime | None = None
    status_conformidade_geral: str | None = None
    medicoes: list[MeasurementResponse] = []

    model_config = {"from_attributes": True}


class AnalysisAcceptedResponse(BaseModel):
    id: uuid.UUID
    status: str


class AnalysisHistoryItemResponse(BaseModel):
    id: uuid.UUID
    concluida_em: datetime | None = None
    status_conformidade_geral: str | None = None
    medicoes: list[MeasurementResponse] = []

    model_config = {"from_attributes": True}


class MetricSeriesPointResponse(BaseModel):
    analise_id: uuid.UUID
    concluida_em: datetime | None
    valor_medido: float | None
    status_conformidade: str


class MetricTrendResponse(BaseModel):
    metrica_chave: str
    tendencia: str | None
    serie: list[MetricSeriesPointResponse]
