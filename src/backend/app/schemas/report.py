import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    tipo: str
    analise_id: uuid.UUID | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    gerado_em: datetime
    download_url: str
