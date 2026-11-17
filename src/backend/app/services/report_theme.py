"""Identidade visual e formatação do relatório PDF (cores, estilos de texto, números).

A paleta acompanha a interface (azul de marca; verde/âmbar/vermelho para Conforme/Condicional/
Não-Conforme) e o status nunca é indicado só por cor: o texto do status sempre acompanha.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.analysis.metrics_catalog import Direcao, MetricDefinition

# Fontes padrão do ReportLab (Helvetica/Times) não embutem um CMap Unicode, então acentuação em
# português é corrompida na extração de texto. Registramos a TTF Bitstream Vera (incluída no pacote
# reportlab) para garantir codificação Unicode correta. Ela não tem setas nem triângulos: os
# indicadores de tendência são desenhados como formas (ver report_charts.py).
_FONTS_DIR = os.path.normpath(os.path.join(os.path.dirname(pdfmetrics.__file__), "..", "fonts"))
pdfmetrics.registerFont(TTFont("Vera", os.path.join(_FONTS_DIR, "Vera.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Bold", os.path.join(_FONTS_DIR, "VeraBd.ttf")))
pdfmetrics.registerFont(TTFont("Vera-Italic", os.path.join(_FONTS_DIR, "VeraIt.ttf")))
pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="Vera-Bold", italic="Vera-Italic", boldItalic="Vera-Bold")

NAVY = colors.HexColor("#0B1B3A")
BRAND = colors.HexColor("#2563EB")
BRAND_SOFT = colors.HexColor("#DBEAFE")
INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
ZEBRA = colors.HexColor("#F8FAFC")
WHITE = colors.white

# status -> (texto, fundo suave, cor sólida)
STATUS_COLORS: dict[str, tuple[colors.Color, colors.Color, colors.Color]] = {
    "Conforme": (colors.HexColor("#15803D"), colors.HexColor("#DCFCE7"), colors.HexColor("#16A34A")),
    "Condicional": (colors.HexColor("#B45309"), colors.HexColor("#FEF3C7"), colors.HexColor("#F59E0B")),
    "Não-Conforme": (colors.HexColor("#B91C1C"), colors.HexColor("#FEE2E2"), colors.HexColor("#DC2626")),
    "Não disponível": (colors.HexColor("#475569"), colors.HexColor("#E2E8F0"), colors.HexColor("#94A3B8")),
}


def status_text_color(status: str) -> colors.Color:
    return STATUS_COLORS.get(status, STATUS_COLORS["Não disponível"])[0]


def status_soft_color(status: str) -> colors.Color:
    return STATUS_COLORS.get(status, STATUS_COLORS["Não disponível"])[1]


def status_solid_color(status: str) -> colors.Color:
    return STATUS_COLORS.get(status, STATUS_COLORS["Não disponível"])[2]


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = dict(fontName="Vera", fontSize=9, leading=12.5, textColor=INK)
    base.update(kwargs)
    return ParagraphStyle(name, **base)


STYLES: dict[str, ParagraphStyle] = {
    "body": _style("body"),
    "small": _style("small", fontSize=8, leading=11, textColor=MUTED),
    "tiny": _style("tiny", fontSize=7, leading=9, textColor=MUTED),
    "h1": _style("h1", fontName="Vera-Bold", fontSize=22, leading=26, textColor=NAVY),
    "h2": _style("h2", fontName="Vera-Bold", fontSize=13, leading=17, textColor=NAVY, spaceBefore=14, spaceAfter=6, keepWithNext=1),
    "h3": _style("h3", fontName="Vera-Bold", fontSize=10, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=3, keepWithNext=1),
    "eyebrow": _style("eyebrow", fontName="Vera-Bold", fontSize=8, leading=10, textColor=BRAND),
    "repo": _style("repo", fontName="Vera-Bold", fontSize=13, leading=17, textColor=BRAND),
    "label": _style("label", fontSize=7.5, leading=10, textColor=MUTED),
    "cell": _style("cell", fontSize=8.5, leading=11),
    "cell_bold": _style("cell_bold", fontName="Vera-Bold", fontSize=8.5, leading=11),
    "cell_center": _style("cell_center", fontSize=8.5, leading=11, alignment=TA_CENTER),
    "cell_right": _style("cell_right", fontSize=8.5, leading=11, alignment=TA_RIGHT),
    "head": _style("head", fontName="Vera-Bold", fontSize=8, leading=10, textColor=WHITE),
    "head_center": _style("head_center", fontName="Vera-Bold", fontSize=8, leading=10, textColor=WHITE, alignment=TA_CENTER),
    "chip": _style("chip", fontName="Vera-Bold", fontSize=8, leading=10, alignment=TA_CENTER),
    "big_number": _style("big_number", fontName="Vera-Bold", fontSize=24, leading=28, textColor=NAVY),
    "big_status": _style("big_status", fontName="Vera-Bold", fontSize=14, leading=18, alignment=TA_CENTER),
    "scope": _style("scope", fontSize=8, leading=11, textColor=colors.HexColor("#475569")),
    "bullet": _style("bullet", leftIndent=10, bulletIndent=0, spaceAfter=2),
}

# Unidade curta exibida ao lado do valor; mesmas unidades do dashboard.
SHORT_UNIT: dict[str, str] = {
    "complexidade_ciclomatica": "cam./função",
    "loc": "linhas/função",
    "indice_manutenibilidade": "pontos",
    "cobertura_testes": "%",
    "acoplamento": "",
    "score_duplicacao": "%",
}

# Casas decimais por métrica (4 casas do banco são ruído em um laudo).
DECIMALS: dict[str, int] = {
    "complexidade_ciclomatica": 1,
    "loc": 1,
    "indice_manutenibilidade": 1,
    "cobertura_testes": 1,
    "acoplamento": 2,
    "score_duplicacao": 1,
}

# Escala do eixo nos medidores (mesmas faixas do dashboard); estendida se o valor passar do fim.
SCALE: dict[str, tuple[float, float]] = {
    "complexidade_ciclomatica": (0, 30),
    "loc": (0, 90),
    "indice_manutenibilidade": (0, 100),
    "cobertura_testes": (0, 100),
    "acoplamento": (0, 1),
    "score_duplicacao": (0, 30),
}

# Fuso de exibição: horário de Brasília (o Brasil não adota horário de verão desde 2019).
_BRT = timezone(timedelta(hours=-3))


def format_number(value: float | int, decimals: int = 2, strip: bool = True) -> str:
    """Formato brasileiro (vírgula decimal). `strip` remove zeros à direita (bom para limites: "5");
    sem ele as casas ficam fixas (bom para valores medidos: "17,0", alinhado com "29,5")."""
    text = f"{value:.{decimals}f}"
    if strip and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_value(metric_key: str, value: float | None, strip: bool = False) -> str:
    if value is None:
        return "—"
    return format_number(value, DECIMALS.get(metric_key, 2), strip=strip)


def format_value_with_unit(metric_key: str, value: float | None, strip: bool = False) -> str:
    if value is None:
        return "—"
    unit = SHORT_UNIT.get(metric_key, "")
    text = format_value(metric_key, value, strip=strip)
    if unit == "%":
        return f"{text}%"
    return f"{text} {unit}" if unit else text


def format_limit(value: float) -> str:
    return format_number(value, 2)


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_BRT).strftime("%d/%m/%Y %H:%M")


def format_date(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_BRT).strftime("%d/%m/%Y")


def limits_text(metric: MetricDefinition) -> str:
    """Faixas de especificação com o sentido correto: menor-é-melhor usa ≤/>; maior-é-melhor, ≥/<."""
    nominal = format_limit(metric.limite_nominal)
    superior = format_limit(metric.limite_superior_condicional)
    if metric.direcao is Direcao.MAIOR_MELHOR:
        return f"Conforme ≥ {nominal} · Condicional ≥ {superior} · Não-Conforme < {superior}"
    return f"Conforme ≤ {nominal} · Condicional ≤ {superior} · Não-Conforme > {superior}"


def short_limits_text(metric: MetricDefinition) -> str:
    nominal = format_limit(metric.limite_nominal)
    superior = format_limit(metric.limite_superior_condicional)
    if metric.direcao is Direcao.MAIOR_MELHOR:
        return f"≥ {nominal} / ≥ {superior}"
    return f"≤ {nominal} / ≤ {superior}"
