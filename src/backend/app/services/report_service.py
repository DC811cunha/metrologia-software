"""Geração de relatório técnico em PDF (FR-009, research.md item 8).

Para cada métrica do catálogo, o relatório inclui valor medido, fórmula, fonte
bibliográfica e limites de especificação — a mesma definição usada no dashboard
(Princípio V: nenhuma métrica é exibida sem sua definição completa).
"""

from __future__ import annotations

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.analysis.metrics_catalog import METRICS_CATALOG
from app.services.trend_service import calculate_trend

# Fontes padrão do ReportLab (Helvetica/Times) não embutem um CMap Unicode, então
# acentuação em português é corrompida na extração de texto (e em alguns leitores de
# PDF). Registramos a TTF Bitstream Vera (incluída no próprio pacote reportlab) para
# garantir codificação Unicode correta.
_VERA_FONT_PATH = os.path.join(os.path.dirname(pdfmetrics.__file__), "..", "fonts", "Vera.ttf")
pdfmetrics.registerFont(TTFont("Vera", os.path.normpath(_VERA_FONT_PATH)))

_STYLES = getSampleStyleSheet()
for _style in _STYLES.byName.values():
    _style.fontName = "Vera"


def _measurement_table_data(measurements: list[dict]) -> list[list[str]]:
    header = ["Métrica", "Valor", "Status", "Limites (Conforme / Condicional)", "Fórmula", "Fonte"]
    rows = [header]
    for measurement in measurements:
        metric = METRICS_CATALOG[measurement["metrica_chave"]]
        valor = measurement["valor_medido"]
        # O Status já comunica "Não disponível"; repetir o texto completo aqui só
        # forçaria uma quebra de linha estranha na coluna estreita de Valor.
        valor_str = f"{valor}" if valor is not None else "—"
        limites = f"≤ {metric.limite_nominal} / ≤ {metric.limite_superior_condicional}"
        rows.append(
            [
                metric.nome,
                valor_str,
                measurement["status_conformidade"],
                limites,
                metric.formula,
                metric.fonte_bibliografica,
            ]
        )
    return rows


def _build_measurement_table(measurements: list[dict]) -> Table:
    data = _measurement_table_data(measurements)
    wrapped = [
        [Paragraph(str(cell), _STYLES["BodyText"]) for cell in row] for row in data
    ]
    table = Table(wrapped, colWidths=[3.8 * cm, 1.3 * cm, 2.6 * cm, 2.6 * cm, 3.9 * cm, 3.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return table


def build_single_analysis_report(
    *, repository_url: str, analysis_id: str, concluida_em: datetime | None, measurements: list[dict]
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    story = [
        Paragraph("SoftMeter — Relatório de Conformidade", _STYLES["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Repositório: {repository_url}", _STYLES["Normal"]),
        Paragraph(f"Análise: {analysis_id}", _STYLES["Normal"]),
        Paragraph(
            f"Data: {concluida_em.strftime('%d/%m/%Y %H:%M') if concluida_em else 'N/A'}",
            _STYLES["Normal"],
        ),
        Spacer(1, 0.5 * cm),
        _build_measurement_table(measurements),
    ]
    doc.build(story)
    return buffer.getvalue()


def build_history_report(
    *, repository_url: str, analyses: list[dict]
) -> bytes:
    """`analyses`: lista cronológica de `{id, concluida_em, measurements}`."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    story: list = [
        Paragraph("SoftMeter — Relatório de Histórico Completo", _STYLES["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Repositório: {repository_url}", _STYLES["Normal"]),
        Paragraph(f"Total de análises: {len(analyses)}", _STYLES["Normal"]),
        Spacer(1, 0.4 * cm),
    ]

    if len(analyses) >= 2:
        story.append(Paragraph("Tendência (entre as duas análises mais recentes)", _STYLES["Heading2"]))
        previous, latest = analyses[-2], analyses[-1]
        for chave, metric in METRICS_CATALOG.items():
            valor_anterior = next(
                (m["valor_medido"] for m in previous["measurements"] if m["metrica_chave"] == chave),
                None,
            )
            valor_atual = next(
                (m["valor_medido"] for m in latest["measurements"] if m["metrica_chave"] == chave),
                None,
            )
            tendencia = calculate_trend(chave, valor_anterior, valor_atual)
            story.append(
                Paragraph(
                    f"{metric.nome}: {tendencia or 'sem dados suficientes'}", _STYLES["BodyText"]
                )
            )
        story.append(Spacer(1, 0.5 * cm))

    for analysis in analyses:
        concluida_em = analysis["concluida_em"]
        story.append(
            Paragraph(
                f"Análise {analysis['id']} — "
                f"{concluida_em.strftime('%d/%m/%Y %H:%M') if concluida_em else 'N/A'}",
                _STYLES["Heading2"],
            )
        )
        story.append(_build_measurement_table(analysis["measurements"]))
        story.append(Spacer(1, 0.5 * cm))

    doc.build(story)
    return buffer.getvalue()
