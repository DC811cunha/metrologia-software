"""Análises que nunca terminam: o worker caiu, foi reiniciado ou a fila perdeu a tarefa.

O Celery confirma a tarefa antes de executá-la, então se o processo morrer no meio (ou o limite duro de tempo
matar o worker) nada atualiza a análise: ela ficaria `pendente`/`processando` para sempre e a tela a mostraria
como "em andamento" indefinidamente. Em vez de um processo agendado só para isso, as consultas que listam ou
leem análises chamam `expire_stale_analyses`, que as marca como `falhou` quando passam do prazo.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatus

STALE_ANALYSIS_MESSAGE = (
    "A análise foi interrompida antes de terminar (o servidor reiniciou ou excedeu o tempo). "
    "Tente novamente."
)


def expire_stale_analyses(db: Session, repository_ids: Sequence[uuid.UUID]) -> int:
    """Marca como `falhou` as análises desses repositórios que seguem `pendente`/`processando` além do
    prazo (`settings.stale_analysis_after_s`, bem acima do limite de tempo da própria análise). Devolve
    quantas foram marcadas."""
    if not repository_ids:
        return 0
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.stale_analysis_after_s)
    stale = (
        db.execute(
            select(Analysis).where(
                Analysis.repositorio_id.in_(repository_ids),
                Analysis.status.in_((AnalysisStatus.PENDENTE, AnalysisStatus.PROCESSANDO)),
                Analysis.solicitada_em < cutoff,
            )
        )
        .scalars()
        .all()
    )
    for analysis in stale:
        analysis.status = AnalysisStatus.FALHOU
        analysis.motivo_falha = STALE_ANALYSIS_MESSAGE
        analysis.concluida_em = now
    if stale:
        db.commit()
    return len(stale)
