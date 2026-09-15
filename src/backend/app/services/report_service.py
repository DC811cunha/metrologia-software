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
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.analysis.metrics_catalog import METRICS_CATALOG, ConformityStatus
from app.services.trend_service import calculate_trend

# Fontes padrão do ReportLab (Helvetica/Times) não embutem um CMap Unicode, então
# acentuação em português é corrompida na extração de texto (e em alguns leitores de
# PDF). Registramos a TTF Bitstream Vera (incluída no próprio pacote reportlab) para
# garantir codificação Unicode correta.
_FONTS_DIR = os.path.normpath(os.path.join(os.path.dirname(pdfmetrics.__file__), "..", "fonts"))
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONTS_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(_FONTS_DIR, "VeraBd.ttf")))

_STYLES = getSampleStyleSheet()
for _style in _STYLES.byName.values():
    _style.fontName = "Vera"

# Estilo próprio para o cabeçalho da tabela: o `TEXTCOLOR` do TableStyle não tem
# efeito quando a célula contém um `Paragraph` (é um Flowable, não texto puro da
# tabela) — sem isto, o cabeçalho ficava com texto escuro sobre o fundo escuro
# (#0f172a), ilegível.
_HEADER_CELL_STYLE = ParagraphStyle(
    "TableHeaderCell", parent=_STYLES["BodyText"], textColor=colors.white, fontName="Vera-Bold"
)


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
    header, body = data[0], data[1:]
    wrapped = [[Paragraph(str(cell), _HEADER_CELL_STYLE) for cell in header]] + [
        [Paragraph(str(cell), _STYLES["BodyText"]) for cell in row] for row in body
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


_SCORE_BY_STATUS = {
    ConformityStatus.CONFORME.value: 100,
    ConformityStatus.CONDICIONAL.value: 50,
    ConformityStatus.NAO_CONFORME.value: 0,
}

_OVERALL_STATUS_INTRO = {
    ConformityStatus.CONFORME.value: "o repositório está em conformidade com os limites de especificação do catálogo de métricas.",
    ConformityStatus.CONDICIONAL.value: "o repositório está condicionalmente conforme — dentro de uma faixa aceitável, mas com pontos que merecem atenção antes de novas entregas.",
    ConformityStatus.NAO_CONFORME.value: "o repositório está fora de conformidade com um ou mais limites de especificação do catálogo de métricas.",
}

# Implicação prática de cada métrica estar fora do limite nominal — genérica por
# métrica (não específica de um repositório), fundamentada na mesma fonte
# bibliográfica já citada no catálogo (metrics_catalog.py).
_INSIGHT_FORA_DO_LIMITE = {
    "complexidade_ciclomatica": (
        "Funções com muitos caminhos de execução independentes exigem mais casos de "
        "teste para cobertura exaustiva e concentram maior risco de defeitos (McCabe, 1976)."
    ),
    "loc": (
        "Funções longas tendem a acumular múltiplas responsabilidades, o que dificulta "
        "leitura, revisão e manutenção (Martin, 2008)."
    ),
    "indice_manutenibilidade": (
        "Um índice de manutenibilidade baixo indica maior esforço esperado para "
        "futuras alterações e correções nesses arquivos."
    ),
    "cobertura_testes": (
        "Cobertura de testes abaixo do limite aumenta o risco de regressões não "
        "detectadas em alterações futuras."
    ),
    "acoplamento": (
        "Instabilidade de módulo alta indica dependência excessiva de outros "
        "componentes, dificultando alterações isoladas (Martin, 2002)."
    ),
    "score_duplicacao": (
        "Código duplicado eleva o custo de manutenção — uma correção precisa ser "
        "replicada em todos os pontos duplicados, sob risco de inconsistência."
    ),
}


def _build_interpretation_section(measurements: list[dict], overall_status: str) -> list:
    """Resumo interpretativo gerado a partir dos valores/status reais da análise —
    genérico para qualquer repositório, nunca texto fixo (FR-009 exige que o
    relatório seja rastreável às métricas medidas, não a uma narrativa solta)."""
    conformes = [m for m in measurements if m["status_conformidade"] == ConformityStatus.CONFORME.value]
    atencao = [
        m
        for m in measurements
        if m["status_conformidade"]
        in (ConformityStatus.CONDICIONAL.value, ConformityStatus.NAO_CONFORME.value)
    ]
    indisponiveis = [
        m for m in measurements if m["status_conformidade"] == ConformityStatus.NAO_DISPONIVEL.value
    ]

    def _label(m: dict) -> str:
        metric = METRICS_CATALOG[m["metrica_chave"]]
        valor = m["valor_medido"]
        valor_str = f"{valor}" if valor is not None else "—"
        return f"{metric.nome} ({valor_str})"

    story: list = [Paragraph("Resumo da análise", _STYLES["Heading2"])]
    intro = _OVERALL_STATUS_INTRO.get(overall_status, "")
    story.append(
        Paragraph(f"Conformidade geral: <b>{overall_status}</b> — {intro}", _STYLES["BodyText"])
    )
    story.append(Spacer(1, 0.25 * cm))

    if conformes:
        story.append(Paragraph("Pontos fortes", _STYLES["Heading3"]))
        for m in conformes:
            story.append(Paragraph(f"• {_label(m)} — dentro do limite recomendado.", _STYLES["BodyText"]))
        story.append(Spacer(1, 0.2 * cm))

    if atencao:
        story.append(Paragraph("Pontos de atenção", _STYLES["Heading3"]))
        for m in atencao:
            insight = _INSIGHT_FORA_DO_LIMITE.get(m["metrica_chave"], "")
            story.append(
                Paragraph(
                    f"• {_label(m)} — {m['status_conformidade']}. {insight}", _STYLES["BodyText"]
                )
            )
        story.append(Spacer(1, 0.2 * cm))

    if indisponiveis:
        story.append(Paragraph("Métricas não avaliadas", _STYLES["Heading3"]))
        for m in indisponiveis:
            metric = METRICS_CATALOG[m["metrica_chave"]]
            story.append(
                Paragraph(
                    f"• {metric.nome} — sem artefato disponível para leitura; excluída do "
                    "índice agregado (não conta como reprovação).",
                    _STYLES["BodyText"],
                )
            )
        story.append(Spacer(1, 0.2 * cm))

    avaliaveis = conformes + atencao
    if avaliaveis:
        soma = sum(_SCORE_BY_STATUS[m["status_conformidade"]] for m in avaliaveis)
        indice = soma / len(avaliaveis)
        story.append(
            Paragraph(
                f"Índice agregado: ({' + '.join(str(_SCORE_BY_STATUS[m['status_conformidade']]) for m in avaliaveis)}) "
                f"÷ {len(avaliaveis)} = {indice:.1f} "
                "— média dos escores por métrica avaliável (Conforme=100, Condicional=50, "
                "Não-Conforme=0), excluindo métricas não disponíveis.",
                _STYLES["BodyText"],
            )
        )

    story.append(Spacer(1, 0.5 * cm))
    return story


def build_single_analysis_report(
    *,
    repository_url: str,
    analysis_id: str,
    concluida_em: datetime | None,
    measurements: list[dict],
    overall_status: str,
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
        *_build_interpretation_section(measurements, overall_status),
        Paragraph("Detalhamento por métrica", _STYLES["Heading2"]),
        Spacer(1, 0.15 * cm),
        _build_measurement_table(measurements),
    ]
    doc.build(story)
    return buffer.getvalue()


def build_history_report(
    *, repository_url: str, analyses: list[dict]
) -> bytes:
    """`analyses`: lista cronológica de
    `{id, concluida_em, measurements, status_conformidade_geral}`."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    story: list = [
        Paragraph("SoftMeter — Relatório de Histórico Completo", _STYLES["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Repositório: {repository_url}", _STYLES["Normal"]),
        Paragraph(f"Total de análises: {len(analyses)}", _STYLES["Normal"]),
        Spacer(1, 0.4 * cm),
    ]

    latest_overall_status = analyses[-1].get("status_conformidade_geral") if analyses else None
    if latest_overall_status:
        story.extend(_build_interpretation_section(analyses[-1]["measurements"], latest_overall_status))

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
