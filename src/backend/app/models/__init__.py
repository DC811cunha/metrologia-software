"""Importa todos os módulos de modelo para registrá-los em `Base.registry` assim que
`app.models` é importado — os relacionamentos usam forward references de string
(`Mapped["User"]`, `Mapped["Repository"]` etc.) que o SQLAlchemy só resolve se todas as
classes referenciadas já tiverem sido importadas no processo corrente. Sem isso, cada
ponto de entrada (FastAPI, worker Celery, Alembic, scripts) tinha que "por acaso"
importar todos os modelos na ordem certa antes da primeira query — o que falhava
silenciosamente em qualquer processo com uma superfície de import mais estreita (ex.:
o worker Celery, que só importava `Analysis`/`Repository` e quebrava ao resolver
"User"). `alembic/env.py` já fazia esse import manualmente com o mesmo motivo;
centralizado aqui para não depender de cada entry point lembrar de repeti-lo.
"""

from app.models.analysis import Analysis, AnalysisStatus, Measurement  # noqa: F401
from app.models.report import Report, ReportType  # noqa: F401
from app.models.repository import AccessStatus, Repository  # noqa: F401
from app.models.user import User  # noqa: F401
