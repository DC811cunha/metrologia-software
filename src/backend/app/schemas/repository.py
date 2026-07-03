import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/[\w.-]+/[\w.-]+?(?:\.git)?/?$"
)


class RepositoryCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=512)

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not _GITHUB_URL_RE.match(v):
            raise ValueError(
                "URL deve ser um repositório GitHub válido (https://github.com/owner/repo)"
            )
        return v


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    url: str
    owner_nome: str
    linguagens_detectadas: list[str]
    status_acesso: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class RepositoryListItemResponse(RepositoryResponse):
    ultima_analise_status: str | None = None
    ultima_analise_id: uuid.UUID | None = None
