import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.analysis import Analysis, AnalysisStatus
from app.models.report import Report, ReportType
from app.models.repository import Repository
from app.models.user import User
from app.db.session import get_db
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services.report_service import build_history_report, build_single_analysis_report

router = APIRouter(prefix="/api/v1/repositories/{repository_id}/reports", tags=["reports"])


def _get_owned_repository(db: Session, repository_id: uuid.UUID, user: User) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None or repository.usuario_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")
    return repository


def _measurements_payload(analysis: Analysis) -> list[dict]:
    return [
        {
            "metrica_chave": m.metrica_chave,
            "valor_medido": float(m.valor_medido) if m.valor_medido is not None else None,
            "status_conformidade": m.status_conformidade,
        }
        for m in analysis.medicoes
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReportResponse)
def create_report(
    repository_id: uuid.UUID,
    payload: ReportCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReportResponse:
    repository = _get_owned_repository(db, repository_id, user)

    if payload.tipo == ReportType.ANALISE_UNICA.value:
        if payload.analise_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="analise_id é obrigatório para tipo=analise_unica",
            )
        analysis = db.get(Analysis, payload.analise_id)
        if (
            analysis is None
            or analysis.repositorio_id != repository_id
            or analysis.status != AnalysisStatus.CONCLUIDA
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Análise inexistente ou não concluída",
            )
        pdf_bytes = build_single_analysis_report(
            repository_url=repository.url,
            analysis_id=str(analysis.id),
            concluida_em=analysis.concluida_em,
            measurements=_measurements_payload(analysis),
        )
    elif payload.tipo == ReportType.HISTORICO_COMPLETO.value:
        analyses = (
            db.execute(
                select(Analysis)
                .where(
                    Analysis.repositorio_id == repository_id,
                    Analysis.status == AnalysisStatus.CONCLUIDA,
                )
                .order_by(Analysis.solicitada_em.asc())
            )
            .scalars()
            .all()
        )
        if not analyses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Repositório não possui nenhuma análise concluída",
            )
        pdf_bytes = build_history_report(
            repository_url=repository.url,
            analyses=[
                {
                    "id": str(a.id),
                    "concluida_em": a.concluida_em,
                    "measurements": _measurements_payload(a),
                }
                for a in analyses
            ],
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Tipo '{payload.tipo}' desconhecido"
        )

    report = Report(
        usuario_id=user.id,
        repositorio_id=repository_id,
        tipo=payload.tipo,
        analise_id=payload.analise_id,
        caminho_arquivo="",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    reports_dir = Path(settings.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    file_path = reports_dir / f"{report.id}.pdf"
    file_path.write_bytes(pdf_bytes)

    report.caminho_arquivo = str(file_path)
    db.commit()

    return ReportResponse(
        id=report.id,
        tipo=report.tipo,
        gerado_em=report.gerado_em,
        download_url=f"/api/v1/repositories/{repository_id}/reports/{report.id}/download",
    )


@router.get("/{report_id}/download")
def download_report(
    repository_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    _get_owned_repository(db, repository_id, user)
    report = db.get(Report, report_id)
    if report is None or report.repositorio_id != repository_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado")

    file_path = Path(report.caminho_arquivo)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo do relatório não encontrado")

    return FileResponse(file_path, media_type="application/pdf", filename=f"softmeter-relatorio-{report.id}.pdf")
