"""Geração do Laudo de Conformidade de Software em PDF (FR-009, research.md item 8).

Para cada métrica do catálogo, o laudo traz valor medido, faixas de especificação (com o sentido
correto de cada limite), fórmula e fonte bibliográfica — a mesma definição usada no dashboard
(Princípio V: nenhuma métrica é exibida sem sua definição completa) — além de índice de conformidade,
comparação com a análise anterior, pontos de atenção com sugestão de ação e, no relatório de histórico,
gráficos de evolução. Identidade visual e formatação ficam em `report_theme`; os gráficos, em
`report_charts`.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.analysis.metrics_catalog import (
    METRICS_CATALOG,
    SCOPE_NOTE,
    ConformityStatus,
    Direcao,
    MetricDefinition,
)
from app.services.report_charts import (
    band_gauge,
    index_bar,
    legend_row,
    line_chart,
    metric_bands,
    scale_for,
    trend_icon,
)
from app.services.report_theme import (
    BRAND,
    BRAND_SOFT,
    LINE,
    MUTED,
    NAVY,
    STYLES,
    WHITE,
    ZEBRA,
    format_date,
    format_datetime,
    format_number,
    format_value,
    format_value_with_unit,
    limits_text,
    status_soft_color,
    status_solid_color,
    status_text_color,
)
from app.services.trend_service import calculate_trend

PAGE_W, PAGE_H = A4
MARGIN_X = 1.8 * cm
CONTENT_W = PAGE_W - 2 * MARGIN_X

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

# Implicação prática de cada métrica estar fora do limite nominal — genérica por métrica (não
# específica de um repositório), fundamentada na mesma fonte bibliográfica do catálogo.
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

# Sugestão de ação — genérica por métrica; o relatório não conhece o código do repositório.
_SUGESTAO = {
    "complexidade_ciclomatica": "Quebrar funções com muitos desvios (if/else, laços) em funções menores e usar retornos antecipados.",
    "loc": "Dividir funções longas por responsabilidade, extraindo trechos com nome próprio.",
    "indice_manutenibilidade": "Reduzir tamanho e complexidade dos arquivos mais pesados e remover código morto.",
    "cobertura_testes": "Cobrir primeiro os módulos de maior risco e publicar o relatório de cobertura como artifact do CI.",
    "acoplamento": "Reduzir imports entre módulos e isolar as fronteiras com interfaces claras.",
    "score_duplicacao": "Extrair os blocos repetidos para funções ou módulos compartilhados.",
}

# Cabeçalhos curtos para a matriz de análises do histórico.
_SHORT_NAME = {
    "complexidade_ciclomatica": "Compl.<br/>ciclom.",
    "loc": "LOC",
    "indice_manutenibilidade": "Manut.",
    "cobertura_testes": "Cobert.<br/>testes",
    "acoplamento": "Acopl.",
    "score_duplicacao": "Duplic.",
}


# ---------------------------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------------------------
def _hex(color: colors.Color) -> str:
    return "#" + color.hexval()[2:]


def _p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def _repo_label(repository_url: str) -> str:
    """`owner/repo` a partir da URL (cai para a própria URL se não for do GitHub)."""
    marker = "github.com/"
    return repository_url.rstrip("/").split(marker, 1)[1] if marker in repository_url else repository_url


def _ordered(measurements: list[dict]) -> list[dict]:
    """Medições na ordem do catálogo (a ordem vinda do banco não é garantida)."""
    order = {chave: i for i, chave in enumerate(METRICS_CATALOG)}
    return sorted(measurements, key=lambda m: order.get(m["metrica_chave"], len(order)))


def _by_key(measurements: list[dict]) -> dict[str, dict]:
    return {m["metrica_chave"]: m for m in measurements}


def _index(measurements: list[dict]) -> float | None:
    """Índice agregado: média dos escores das métricas avaliáveis ("Não disponível" fica de fora)."""
    scores = [_SCORE_BY_STATUS[m["status_conformidade"]] for m in measurements if m["status_conformidade"] in _SCORE_BY_STATUS]
    return sum(scores) / len(scores) if scores else None


def _counts(measurements: list[dict]) -> dict[str, int]:
    result = {"Conforme": 0, "Condicional": 0, "Não-Conforme": 0, "Não disponível": 0}
    for m in measurements:
        result[m["status_conformidade"]] = result.get(m["status_conformidade"], 0) + 1
    return result


def _decimals_for(chave: str) -> int:
    return 2 if chave == "acoplamento" else 1


def _signed(value: float, decimals: int = 1) -> str:
    """Variação com sinal; o que arredonda para zero não ganha sinal ("−0" confunde)."""
    rounded = round(value, decimals)
    text = format_number(abs(rounded), decimals)
    if rounded > 0:
        return f"+{text}"
    if rounded < 0:
        return f"−{text}"
    return text


def _effective_trend(chave: str, previous: float | None, current: float | None) -> str | None:
    """Tendência considerando só o que aparece no papel: variação que arredonda para zero é estável."""
    if previous is None or current is None:
        return None
    if round(current - previous, _decimals_for(chave)) == 0:
        return "estavel"
    return calculate_trend(chave, previous, current)


def _delta_cell(chave: str, previous: float | None, current: float | None) -> list:
    """Variação em relação à análise anterior, colorida pelo efeito (melhorou/piorou)."""
    trend = _effective_trend(chave, previous, current)
    if trend is None or previous is None or current is None:
        return [_p("—", "cell_center")]
    label = {"melhorando": "melhorou", "piorando": "piorou", "estavel": "estável"}[trend]
    color = {"melhorando": "#15803D", "piorando": "#B91C1C", "estavel": "#475569"}[trend]
    return [
        Paragraph(
            f'<font color="{color}"><b>{_signed(current - previous, _decimals_for(chave))}</b></font>',
            STYLES["cell_center"],
        ),
        Paragraph(label, STYLES["tiny"]),
    ]


def _status_cell(status: str) -> Paragraph:
    return Paragraph(f'<font color="{_hex(status_text_color(status))}">{escape(status)}</font>', STYLES["chip"])


def _status_style(row: int, col: int, status: str) -> list:
    return [("BACKGROUND", (col, row), (col, row), status_soft_color(status))]


def _card(flowables: list, accent, background=ZEBRA, width: float = CONTENT_W) -> Table:
    """Bloco com faixa lateral colorida — usado nos pontos fortes/de atenção e nas notas."""
    table = Table([[flowables]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------------------------
# moldura das páginas (cabeçalho, rodapé "Página X de Y")
# ---------------------------------------------------------------------------------------------
class _NumberedCanvas(pdf_canvas.Canvas):
    """Canvas que conhece o total de páginas, para o rodapé "Página X de Y"."""

    footer_left = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict] = []

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        self.saveState()
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(MARGIN_X, 1.35 * cm, PAGE_W - MARGIN_X, 1.35 * cm)
        self.setFont("Vera", 7)
        self.setFillColor(MUTED)
        self.drawString(MARGIN_X, 0.9 * cm, self.footer_left)
        self.drawRightString(PAGE_W - MARGIN_X, 0.9 * cm, f"Página {self._pageNumber} de {total}")
        self.restoreState()


def _draw_logo(canvas, x: float, y: float, size: float) -> None:
    """Marca do SoftMeter: quadrado azul com um medidor (arco e ponteiro)."""
    canvas.setFillColor(BRAND)
    canvas.roundRect(x, y, size, size, size * 0.24, stroke=0, fill=1)
    canvas.setStrokeColor(WHITE)
    canvas.setLineWidth(size * 0.085)
    canvas.setLineCap(1)
    cx, cy, radius = x + size / 2, y + size * 0.34, size * 0.3
    canvas.arc(cx - radius, cy - radius, cx + radius, cy + radius, 20, 140)
    canvas.line(cx, cy, cx + radius * 0.62, cy + radius * 0.7)
    canvas.setFillColor(WHITE)
    canvas.circle(cx, cy, size * 0.06, stroke=0, fill=1)


def _make_page_decorators(repo_label: str, document_label: str):
    def first_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 1.55 * cm, PAGE_W, 1.55 * cm, stroke=0, fill=1)
        _draw_logo(canvas, MARGIN_X, PAGE_H - 1.27 * cm, 0.98 * cm)
        canvas.setFont("Vera-Bold", 15)
        canvas.setFillColor(WHITE)
        canvas.drawString(MARGIN_X + 1.25 * cm, PAGE_H - 0.98 * cm, "Soft")
        offset = canvas.stringWidth("Soft", "Vera-Bold", 15)
        canvas.setFillColor(colors.HexColor("#93C5FD"))
        canvas.drawString(MARGIN_X + 1.25 * cm + offset, PAGE_H - 0.98 * cm, "Meter")
        canvas.setFont("Vera", 8.5)
        canvas.setFillColor(colors.HexColor("#BFDBFE"))
        canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 0.95 * cm, document_label)
        canvas.restoreState()

    def later_pages(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_X, PAGE_H - 1.35 * cm, PAGE_W - MARGIN_X, PAGE_H - 1.35 * cm)
        _draw_logo(canvas, MARGIN_X, PAGE_H - 1.22 * cm, 0.5 * cm)
        canvas.setFont("Vera-Bold", 8)
        canvas.setFillColor(NAVY)
        canvas.drawString(MARGIN_X + 0.7 * cm, PAGE_H - 1.04 * cm, "SoftMeter")
        canvas.setFont("Vera", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 1.04 * cm, f"{document_label} · {repo_label}")
        canvas.restoreState()

    return first_page, later_pages


def _render(story: list, *, title: str, repo_label: str, document_label: str, generated_at: datetime) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=2.2 * cm,
        bottomMargin=1.9 * cm,
        title=title,
        author="SoftMeter",
        subject=f"Laudo de conformidade — {repo_label}",
        creator="SoftMeter",
    )
    first_page, later_pages = _make_page_decorators(repo_label, document_label)
    canvas_cls = type(
        "SoftMeterCanvas",
        (_NumberedCanvas,),
        {"footer_left": f"Gerado pelo SoftMeter em {format_datetime(generated_at)} (horário de Brasília) · {repo_label}"},
    )
    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages, canvasmaker=canvas_cls)
    return buffer.getvalue()


# ---------------------------------------------------------------------------------------------
# blocos do laudo
# ---------------------------------------------------------------------------------------------
def _title_block(eyebrow: str, repository_url: str, meta: list[tuple[str, str]]) -> list:
    rows = [[_p(escape(label), "label"), _p(value, "cell")] for label, value in meta]
    table = Table(rows, colWidths=[3.6 * cm, CONTENT_W - 3.6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [
        _p(escape(eyebrow), "eyebrow"),
        Spacer(1, 0.1 * cm),
        _p("Laudo de Conformidade de Software", "h1"),
        Spacer(1, 0.15 * cm),
        _p(escape(_repo_label(repository_url)), "repo"),
        Spacer(1, 0.3 * cm),
        table,
        Spacer(1, 0.4 * cm),
    ]


def _verdict_card(overall_status: str, measurements: list[dict], previous_index: float | None, previous_date: datetime | None) -> list:
    index = _index(measurements)
    counts = _counts(measurements)

    status_cell = [_p("CONFORMIDADE GERAL", "label"), Paragraph(
        f'<font color="{_hex(status_text_color(overall_status))}">{escape(overall_status)}</font>',
        STYLES["big_status"],
    )]
    index_cell = [_p("ÍNDICE DE CONFORMIDADE", "label")]
    if index is not None:
        index_cell.append(Paragraph(f'{format_number(index, 1)} <font size="10" color="#64748B">/ 100</font>', STYLES["big_number"]))
        if previous_index is not None:
            delta = round(index - previous_index, 1)
            color = "#15803D" if delta > 0 else "#B91C1C" if delta < 0 else "#475569"
            summary = (
                f"sem variação desde a análise de {format_date(previous_date)}"
                if delta == 0
                else f'<font color="{color}"><b>{_signed(delta)}</b></font> '
                f"desde a análise de {format_date(previous_date)} ({format_number(previous_index, 1)})"
            )
            index_cell.append(Paragraph(summary, STYLES["small"]))
    else:
        index_cell.append(_p("—", "big_number"))

    def counter(label: str, status: str) -> Paragraph:
        color = _hex(status_text_color(status))
        return Paragraph(f'<font color="{color}"><b>{counts[status]}</b></font>&nbsp; {label}', STYLES["cell"])

    counters = [
        counter("Conformes", "Conforme"),
        counter("Condicionais", "Condicional"),
        counter("Não-Conformes", "Não-Conforme"),
        counter("Sem dados (fora do índice)", "Não disponível"),
    ]
    table = Table([[status_cell, index_cell, counters]], colWidths=[4.9 * cm, 5.6 * cm, CONTENT_W - 10.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), status_soft_color(overall_status)),
                ("BACKGROUND", (1, 0), (2, 0), ZEBRA),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEAFTER", (0, 0), (1, 0), 0.6, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story: list = [table, Spacer(1, 0.25 * cm), index_bar(index, CONTENT_W)]
    story.append(
        _p(
            "Faixas do índice: Conforme a partir de 90 · Condicional de 70 a 89 · Não-Conforme abaixo de 70. "
            "O marcador mostra onde esta análise está.",
            "small",
        )
    )
    return story


def _measurement_overview(measurements: list[dict], previous: list[dict] | None) -> Table:
    previous_by_key = _by_key(previous) if previous else {}
    has_prev = bool(previous_by_key)
    widths = [4.5 * cm, 2.7 * cm, CONTENT_W - 4.5 * cm - 2.7 * cm - 3.0 * cm - (2.1 * cm if has_prev else 0), 3.0 * cm]
    if has_prev:
        widths.append(2.1 * cm)
    header = [_p("Métrica", "head"), _p("Valor medido", "head_center"), _p("Posição nas faixas de especificação", "head"), _p("Status", "head_center")]
    if has_prev:
        header.append(_p("vs. anterior", "head_center"))
    rows = [header]
    style: list = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, m in enumerate(measurements, start=1):
        metric = METRICS_CATALOG[m["metrica_chave"]]
        value = m["valor_medido"]
        name = Paragraph(f"<b>{escape(metric.nome)}</b><br/><font size=\"7\" color=\"#64748B\">{escape(metric.unidade)}</font>", STYLES["cell"])
        gauge = (
            band_gauge(metric, value, widths[2] - 0.5 * cm)
            if value is not None
            else _p("Sem fonte de dados disponível — fora do índice", "small")
        )
        row = [name, Paragraph(f"<b>{escape(format_value_with_unit(metric.chave, value))}</b>", STYLES["cell_center"]), gauge, _status_cell(m["status_conformidade"])]
        if has_prev:
            prev_value = previous_by_key.get(metric.chave, {}).get("valor_medido")
            row.append(_delta_cell(metric.chave, prev_value, value))
        rows.append(row)
        style += _status_style(i, 3, m["status_conformidade"])
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (2, i), ZEBRA))
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    return table


def _gap_text(metric: MetricDefinition, value: float) -> str:
    """O que falta para a métrica chegar ao limite Conforme."""
    target = metric.limite_nominal
    if metric.direcao is Direcao.MAIOR_MELHOR:
        return (
            f"Para chegar a Conforme, aumentar de {format_value_with_unit(metric.chave, value)} para pelo menos "
            f"{format_value_with_unit(metric.chave, target, strip=True)} (faltam {format_number(target - value, 2)})."
        )
    return (
        f"Para chegar a Conforme, reduzir de {format_value_with_unit(metric.chave, value)} para no máximo "
        f"{format_value_with_unit(metric.chave, target, strip=True)} (excesso de {format_number(value - target, 2)})."
    )


def _summary_section(measurements: list[dict], overall_status: str) -> list:
    """Resumo interpretativo gerado a partir dos valores/status reais da análise — genérico para
    qualquer repositório, nunca texto fixo (FR-009 exige rastreabilidade às métricas medidas)."""
    conformes = [m for m in measurements if m["status_conformidade"] == ConformityStatus.CONFORME.value]
    atencao = [m for m in measurements if m["status_conformidade"] in (ConformityStatus.CONDICIONAL.value, ConformityStatus.NAO_CONFORME.value)]
    indisponiveis = [m for m in measurements if m["status_conformidade"] == ConformityStatus.NAO_DISPONIVEL.value]

    story: list = [
        _p("Resumo da análise", "h2"),
        Paragraph(
            f"Conformidade geral: <b>{escape(overall_status)}</b> — {_OVERALL_STATUS_INTRO.get(overall_status, '')}",
            STYLES["body"],
        ),
        Spacer(1, 0.2 * cm),
    ]

    lead = story[:]  # título + conformidade geral: ficam junto do primeiro cartão
    story = []
    if conformes:
        items = [_p("Pontos fortes", "h3")]
        for m in conformes:
            metric = METRICS_CATALOG[m["metrica_chave"]]
            items.append(
                Paragraph(
                    f"<b>{escape(metric.nome)}</b> — {escape(format_value_with_unit(metric.chave, m['valor_medido']))}, "
                    "dentro do limite recomendado.",
                    STYLES["bullet"],
                    bulletText="•",
                )
            )
        story += [_card(items, status_solid_color("Conforme"), status_soft_color("Conforme")), Spacer(1, 0.25 * cm)]

    if atencao:
        items = [_p("Pontos de atenção", "h3")]
        for m in atencao:
            metric = METRICS_CATALOG[m["metrica_chave"]]
            value = m["valor_medido"]
            color = _hex(status_text_color(m["status_conformidade"]))
            items.append(
                Paragraph(
                    f"<b>{escape(metric.nome)}</b> — {escape(format_value_with_unit(metric.chave, value))} · "
                    f'<font color="{color}"><b>{escape(m["status_conformidade"])}</b></font>. '
                    f"{_INSIGHT_FORA_DO_LIMITE.get(metric.chave, '')}",
                    STYLES["bullet"],
                    bulletText="•",
                )
            )
            if value is not None:
                items.append(Paragraph(f"<i>{_gap_text(metric, value)}</i>", STYLES["small"]))
            if metric.chave in _SUGESTAO:
                items.append(
                    Paragraph(f"<b>Sugestão:</b> {_SUGESTAO[metric.chave]}", STYLES["small"]),
                )
            items.append(Spacer(1, 0.12 * cm))
        story += [_card(items, status_solid_color("Condicional"), status_soft_color("Condicional")), Spacer(1, 0.25 * cm)]

    if indisponiveis:
        items = [_p("Métricas não avaliadas", "h3")]
        for m in indisponiveis:
            metric = METRICS_CATALOG[m["metrica_chave"]]
            items.append(
                Paragraph(
                    f"<b>{escape(metric.nome)}</b> — sem dado disponível para leitura nesta análise; excluída do "
                    "índice agregado (não conta como reprovação).",
                    STYLES["bullet"],
                    bulletText="•",
                )
            )
        story += [_card(items, status_solid_color("Não disponível"), status_soft_color("Não disponível")), Spacer(1, 0.25 * cm)]

    if story:
        story = [KeepTogether([*lead, story[0]]), *story[1:]]
    else:
        story = lead

    avaliaveis = conformes + atencao
    if avaliaveis:
        scores = [_SCORE_BY_STATUS[m["status_conformidade"]] for m in avaliaveis]
        index = sum(scores) / len(scores)
        story.append(
            Paragraph(
                f"<b>Índice agregado:</b> ({' + '.join(str(s) for s in scores)}) ÷ {len(scores)} = "
                f"<b>{format_number(index, 1)}</b> — média dos escores por métrica avaliável "
                "(Conforme = 100, Condicional = 50, Não-Conforme = 0), excluindo métricas não disponíveis.",
                STYLES["small"],
            )
        )
    return story


def _technical_sheet(measurements: list[dict]) -> list:
    """Ficha de cada métrica: definição, fórmula, fonte e faixas — a rastreabilidade metrológica."""
    heading = _p("Ficha técnica das métricas", "h2")
    story: list = []
    for m in measurements:
        metric = METRICS_CATALOG[m["metrica_chave"]]
        status = m["status_conformidade"]
        rows = [
            [Paragraph(f"<b>{escape(metric.nome)}</b>", STYLES["cell"]), "", _status_cell(status)],
            [_p("Valor medido", "label"), Paragraph(f"<b>{escape(format_value_with_unit(metric.chave, m['valor_medido']))}</b> &nbsp;<font color=\"#64748B\">({escape(metric.unidade)})</font>", STYLES["cell"]), ""],
            [_p("Especificação", "label"), _p(escape(limits_text(metric)), "cell"), ""],
            [_p("Fórmula", "label"), _p(escape(metric.formula), "cell"), ""],
            [_p("Fonte", "label"), _p(escape(metric.fonte_bibliografica), "cell"), ""],
        ]
        table = Table(rows, colWidths=[2.8 * cm, CONTENT_W - 2.8 * cm - 3.2 * cm, 3.2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (1, 0)),
                    ("SPAN", (1, 1), (2, 1)),
                    ("SPAN", (1, 2), (2, 2)),
                    ("SPAN", (1, 3), (2, 3)),
                    ("SPAN", (1, 4), (2, 4)),
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_SOFT),
                    ("BACKGROUND", (2, 0), (2, 0), status_soft_color(status)),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, status_solid_color(status)),
                    ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("VALIGN", (0, 1), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        # O título acompanha o primeiro bloco (keepWithNext não atravessa um KeepTogether).
        story += [KeepTogether([heading, table] if not story else [table]), Spacer(1, 0.25 * cm)]
    return story


def _how_to_read() -> list:
    return [
        _p("Como ler este laudo", "h2"),
        _p(
            "<b>Faixas de especificação.</b> Cada métrica tem limites fixos, definidos na literatura e iguais para "
            "todos os repositórios: dentro do limite nominal o resultado é <b>Conforme</b>; entre o nominal e o "
            "superior, <b>Condicional</b>; além do superior, <b>Não-Conforme</b>. Em métricas em que mais é melhor "
            "(cobertura de testes, índice de manutenibilidade) a comparação é invertida.",
        ),
        Spacer(1, 0.15 * cm),
        _p(
            "<b>Índice de conformidade.</b> Média dos escores das métricas avaliáveis (Conforme = 100, Condicional = 50, "
            "Não-Conforme = 0), todas com o mesmo peso. Métricas &quot;Não disponível&quot; ficam fora da conta. "
            "Índice a partir de 90 é Conforme; de 70 a 89, Condicional; abaixo de 70, Não-Conforme. Por isso uma única "
            "métrica Não-Conforme pode tornar o resultado geral Condicional mesmo com as demais Conformes.",
        ),
        Spacer(1, 0.25 * cm),
        _card([_p(escape(SCOPE_NOTE), "scope")], BRAND, BRAND_SOFT),
        Spacer(1, 0.15 * cm),
        _p(
            "<b>Limitações.</b> A análise é estática: o SoftMeter lê o código-fonte do repositório e nunca o executa. "
            "A cobertura de testes vem dos relatórios que o próprio repositório publica (artifacts de CI, "
            "<i>coverage.xml</i>, <i>lcov.info</i> ou badge); sem eles, a métrica fica &quot;Não disponível&quot;. As "
            "sugestões de ação são genéricas por métrica e não substituem a revisão do código.",
            "small",
        ),
    ]


def _references() -> list:
    seen: list[str] = []
    for metric in METRICS_CATALOG.values():
        if metric.fonte_bibliografica not in seen:
            seen.append(metric.fonte_bibliografica)
    story: list = [_p("Referências", "h2")]
    for source in seen:
        story.append(Paragraph(escape(source), STYLES["small"], bulletText="•"))
    return story


# ---------------------------------------------------------------------------------------------
# relatório de análise única
# ---------------------------------------------------------------------------------------------
def build_single_analysis_report(
    *,
    repository_url: str,
    analysis_id: str,
    concluida_em: datetime | None,
    measurements: list[dict],
    overall_status: str,
    linguagens: list[str] | None = None,
    previous: dict | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """`previous`: `{concluida_em, measurements, status_conformidade_geral}` da análise concluída
    imediatamente anterior do mesmo repositório (opcional) — habilita a comparação."""
    generated_at = generated_at or datetime.now(UTC)
    measurements = _ordered(measurements)
    meta = [
        ("Repositório", escape(repository_url)),
        ("Linguagens detectadas", escape(", ".join(linguagens)) if linguagens else "—"),
        ("Análise", escape(analysis_id)),
        ("Data da análise", f"{format_datetime(concluida_em)} (horário de Brasília)"),
    ]
    previous_measurements = _ordered(previous["measurements"]) if previous else None
    previous_index = _index(previous_measurements) if previous_measurements else None

    story: list = [
        *_title_block("ANÁLISE INDIVIDUAL", repository_url, meta),
        *_verdict_card(overall_status, measurements, previous_index, previous["concluida_em"] if previous else None),
        Spacer(1, 0.2 * cm),
        _p("Medições", "h2"),
        _measurement_overview(measurements, previous_measurements),
        Spacer(1, 0.1 * cm),
        legend_row(CONTENT_W),
        *_summary_section(measurements, overall_status),
        *_technical_sheet(measurements),
        KeepTogether([*_how_to_read(), *_references()]),
    ]
    return _render(
        story,
        title=f"Laudo de Conformidade — {_repo_label(repository_url)}",
        repo_label=_repo_label(repository_url),
        document_label="Laudo de Conformidade de Software",
        generated_at=generated_at,
    )


# ---------------------------------------------------------------------------------------------
# relatório de histórico
# ---------------------------------------------------------------------------------------------
def _trend_label(trend: str | None) -> str:
    return {"melhorando": "Melhorando", "piorando": "Piorando", "estavel": "Estável"}.get(trend or "", "Sem dados")


def _variation_table(analyses: list[dict]) -> Table:
    first, last = analyses[0], analyses[-1]
    first_by, last_by = _by_key(first["measurements"]), _by_key(last["measurements"])
    prev_by = _by_key(analyses[-2]["measurements"]) if len(analyses) >= 2 else {}
    rows = [[
        _p("Métrica", "head"),
        _p("Primeira análise", "head_center"),
        _p("Mais recente", "head_center"),
        _p("Variação total", "head_center"),
        _p("Tendência (últimas duas)", "head"),
    ]]
    for chave, metric in METRICS_CATALOG.items():
        v_first = first_by.get(chave, {}).get("valor_medido")
        v_last = last_by.get(chave, {}).get("valor_medido")
        v_prev = prev_by.get(chave, {}).get("valor_medido") if prev_by else None
        total = _effective_trend(chave, v_first, v_last)
        recent = _effective_trend(chave, v_prev, v_last) if prev_by else None
        if v_first is not None and v_last is not None:
            color = {"melhorando": "#15803D", "piorando": "#B91C1C"}.get(total or "", "#475569")
            variation = Paragraph(f'<font color="{color}"><b>{_signed(v_last - v_first, _decimals_for(chave))}</b></font>', STYLES["cell_center"])
        else:
            variation = _p("—", "cell_center")
        trend_cell = Table([[trend_icon(recent), _p(_trend_label(recent), "cell")]], colWidths=[0.55 * cm, 3.2 * cm])
        trend_cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        rows.append([
            Paragraph(f"<b>{escape(metric.nome)}</b>", STYLES["cell"]),
            _p(escape(format_value_with_unit(chave, v_first)), "cell_center"),
            Paragraph(f"<b>{escape(format_value_with_unit(chave, v_last))}</b>", STYLES["cell_center"]),
            variation,
            trend_cell,
        ])
    table = Table(rows, colWidths=[5.0 * cm, 3.0 * cm, 3.0 * cm, 2.6 * cm, CONTENT_W - 13.6 * cm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(2, len(rows), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    table.setStyle(TableStyle(style))
    return table


def _index_chart(analyses: list[dict]) -> list:
    points = []
    for analysis in analyses:
        index = _index(analysis["measurements"])
        points.append((format_date(analysis["concluida_em"])[:5], index, analysis.get("status_conformidade_geral") or "Não disponível"))
    bands: list[tuple[float, float, str]] = [(0, 70, "Não-Conforme"), (70, 90, "Condicional"), (90, 100, "Conforme")]
    chart = line_chart(points, width=CONTENT_W, height=5.6 * cm, y_range=(0, 100), bands=bands, y_ticks=[0, 70, 90, 100], value_fmt=lambda v: format_number(v, 0 if v == int(v) else 1))
    return [chart, legend_row(CONTENT_W)]


def _metric_charts(analyses: list[dict]) -> Table:
    cells = []
    width = (CONTENT_W - 0.4 * cm) / 2
    for chave, metric in METRICS_CATALOG.items():
        values = [_by_key(a["measurements"]).get(chave, {}).get("valor_medido") for a in analyses]
        statuses = [_by_key(a["measurements"]).get(chave, {}).get("status_conformidade", "Não disponível") for a in analyses]
        lo, hi = scale_for(chave, values)
        points = [(format_date(a["concluida_em"])[:5], v, s) for a, v, s in zip(analyses, values, statuses, strict=True)]
        decimals = 2 if chave == "acoplamento" else 0 if hi >= 50 else 1
        cells.append(
            line_chart(
                points,
                width=width,
                height=4.3 * cm,
                y_range=(lo, hi),
                bands=metric_bands(metric, hi),
                y_ticks=[metric.limite_nominal, metric.limite_superior_condicional, hi, lo],
                value_fmt=lambda v, d=decimals: format_number(v, d),
                title=metric.nome,
                compact=True,
            )
        )
    rows = [cells[i : i + 2] for i in range(0, len(cells), 2)]
    table = Table(rows, colWidths=[width + 0.2 * cm, width + 0.2 * cm])
    table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return table


def _analyses_matrix(analyses: list[dict]) -> Table:
    header = [_p("Análise", "head")] + [Paragraph(_SHORT_NAME[k], STYLES["head_center"]) for k in METRICS_CATALOG] + [
        _p("Índice", "head_center"),
        _p("Geral", "head_center"),
    ]
    rows = [header]
    style: list = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i, analysis in enumerate(analyses, start=1):
        by_key = _by_key(analysis["measurements"])
        label = Paragraph(
            f"<b>{format_datetime(analysis['concluida_em'])}</b><br/><font size=\"6\" color=\"#64748B\">{escape(str(analysis['id']))}</font>",
            STYLES["cell"],
        )
        row: list = [label]
        for col, chave in enumerate(METRICS_CATALOG, start=1):
            measurement = by_key.get(chave)
            status = measurement["status_conformidade"] if measurement else "Não disponível"
            row.append(_p(escape(format_value(chave, measurement["valor_medido"] if measurement else None)), "cell_center"))
            style += _status_style(i, col, status)
        index = _index(analysis["measurements"])
        row.append(Paragraph(f"<b>{format_number(index, 1)}</b>" if index is not None else "—", STYLES["cell_center"]))
        overall = analysis.get("status_conformidade_geral") or "Não disponível"
        row.append(_status_cell(overall))
        style += _status_style(i, len(METRICS_CATALOG) + 2, overall)
        rows.append(row)
    widths = [4.3 * cm] + [1.5 * cm] * len(METRICS_CATALOG) + [1.3 * cm, CONTENT_W - 4.3 * cm - 1.5 * cm * len(METRICS_CATALOG) - 1.3 * cm]
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    return table


def build_history_report(
    *,
    repository_url: str,
    analyses: list[dict],
    linguagens: list[str] | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """`analyses`: lista cronológica de `{id, concluida_em, measurements, status_conformidade_geral}`."""
    generated_at = generated_at or datetime.now(UTC)
    analyses = [{**a, "measurements": _ordered(a["measurements"])} for a in analyses]
    first, last = analyses[0], analyses[-1]
    period = (
        format_date(first["concluida_em"])
        if len(analyses) == 1
        else f"{format_date(first['concluida_em'])} a {format_date(last['concluida_em'])}"
    )
    meta = [
        ("Repositório", escape(repository_url)),
        ("Linguagens detectadas", escape(", ".join(linguagens)) if linguagens else "—"),
        ("Análises incluídas", f"{len(analyses)} (concluídas)"),
        ("Período", period),
    ]
    latest_status = last.get("status_conformidade_geral")
    previous = analyses[-2] if len(analyses) >= 2 else None

    story: list = [*_title_block("HISTÓRICO COMPLETO", repository_url, meta)]
    if latest_status:
        story.append(_p("Situação mais recente", "h3"))
        story += _verdict_card(
            latest_status,
            last["measurements"],
            _index(previous["measurements"]) if previous else None,
            previous["concluida_em"] if previous else None,
        )

    story += [_p("Evolução do índice de conformidade", "h2"), *_index_chart(analyses)]
    if len(analyses) >= 2:
        story += [KeepTogether([_p("Variação por métrica", "h2"), _variation_table(analyses)]), Spacer(1, 0.1 * cm)]
        story.append(
            _p(
                "Variação total compara a primeira e a mais recente análise; a tendência compara as duas mais "
                "recentes (a direção que melhora depende da métrica).",
                "small",
            )
        )
    story += [_p("Evolução de cada métrica", "h2"), _metric_charts(analyses), legend_row(CONTENT_W)]
    story += [_p("Análises incluídas", "h2"), _analyses_matrix(analyses), Spacer(1, 0.1 * cm)]
    story.append(_p("Cores das células indicam o status da métrica naquela análise; valores sem fonte aparecem como —.", "small"))

    if latest_status:
        story += _summary_section(last["measurements"], latest_status)
    story += [*_technical_sheet(last["measurements"]), KeepTogether([*_how_to_read(), *_references()])]
    return _render(
        story,
        title=f"Histórico de Conformidade — {_repo_label(repository_url)}",
        repo_label=_repo_label(repository_url),
        document_label="Laudo de Conformidade — Histórico",
        generated_at=generated_at,
    )


__all__ = ["build_history_report", "build_single_analysis_report"]
