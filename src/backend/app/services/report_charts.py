"""Elementos gráficos do relatório PDF, desenhados com `reportlab.graphics` (sem imagens externas).

Nada aqui depende de fonte além da Vera já registrada em `report_theme`: setas e marcadores são formas
geométricas, não glifos.
"""

from __future__ import annotations

import math

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm

from app.analysis.metrics_catalog import Direcao, MetricDefinition
from app.services.report_theme import (
    BRAND,
    INK,
    LINE,
    MUTED,
    SCALE,
    STATUS_COLORS,
    WHITE,
    format_limit,
    format_number,
    status_solid_color,
)

_BAND_ALPHA = 0.28


def _soft(color: colors.Color) -> colors.Color:
    """Cor clareada para o fundo das faixas (mistura com branco)."""
    return colors.Color(
        1 - (1 - color.red) * _BAND_ALPHA * 2,
        1 - (1 - color.green) * _BAND_ALPHA * 2,
        1 - (1 - color.blue) * _BAND_ALPHA * 2,
    )


def metric_bands(metric: MetricDefinition, hi: float) -> list[tuple[float, float, str]]:
    """Faixas (início, fim, status) da métrica na escala 0..hi, respeitando o sentido do limite."""
    lo = SCALE[metric.chave][0]
    nominal, superior = metric.limite_nominal, metric.limite_superior_condicional
    if metric.direcao is Direcao.MAIOR_MELHOR:
        return [(lo, superior, "Não-Conforme"), (superior, nominal, "Condicional"), (nominal, hi, "Conforme")]
    return [(lo, nominal, "Conforme"), (nominal, superior, "Condicional"), (superior, hi, "Não-Conforme")]


def scale_for(metric_key: str, values: list[float | None]) -> tuple[float, float]:
    lo, hi = SCALE[metric_key]
    present = [v for v in values if v is not None]
    if present and max(present) > hi:
        step = 5 if hi >= 20 else 0.1
        hi = math.ceil(max(present) / step) * step  # fim de escala "redondo" (ex.: 32,1 -> 35)
    return lo, hi


def band_gauge(metric: MetricDefinition, value: float | None, width: float, height: float = 0.5 * cm) -> Drawing:
    """Barra horizontal com as 3 faixas de especificação e um marcador na posição do valor medido."""
    lo, hi = scale_for(metric.chave, [value])
    label_h = 0.28 * cm
    drawing = Drawing(width, height + label_h)

    def x_of(v: float) -> float:
        return (min(max(v, lo), hi) - lo) / (hi - lo) * width

    for start, end, status in metric_bands(metric, hi):
        x0, x1 = x_of(start), x_of(end)
        drawing.add(Rect(x0, label_h, max(x1 - x0, 0.1), height, fillColor=_soft(status_solid_color(status)), strokeColor=None))

    for limit in (metric.limite_nominal, metric.limite_superior_condicional):
        x = x_of(limit)
        drawing.add(Line(x, label_h, x, label_h + height, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=0.5))
        drawing.add(String(x, 0.02 * cm, format_limit(limit), fontName="Vera", fontSize=5.5, fillColor=MUTED, textAnchor="middle"))

    if value is not None:
        x = x_of(value)
        drawing.add(Rect(x - 0.9, label_h - 0.04 * cm, 1.8, height + 0.08 * cm, fillColor=INK, strokeColor=WHITE, strokeWidth=0.4))
    return drawing


def index_bar(index: float | None, width: float, height: float = 0.5 * cm) -> Drawing:
    """Barra do índice geral (0–100) com as faixas Não-Conforme < 70 ≤ Condicional < 90 ≤ Conforme."""
    label_h = 0.34 * cm
    drawing = Drawing(width, height + label_h)

    def x_of(v: float) -> float:
        return min(max(v, 0), 100) / 100 * width

    for start, end, status in ((0, 70, "Não-Conforme"), (70, 90, "Condicional"), (90, 100, "Conforme")):
        x0, x1 = x_of(start), x_of(end)
        drawing.add(Rect(x0, label_h, x1 - x0, height, fillColor=_soft(status_solid_color(status)), strokeColor=None))
    for tick in (0, 70, 90, 100):
        x = x_of(tick)
        drawing.add(String(x, 0.03 * cm, str(tick), fontName="Vera", fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
    for tick in (70, 90):
        x = x_of(tick)
        drawing.add(Line(x, label_h, x, label_h + height, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=0.5))

    if index is not None:
        x = x_of(index)
        drawing.add(Rect(x - 1.2, label_h - 0.05 * cm, 2.4, height + 0.1 * cm, fillColor=INK, strokeColor=WHITE, strokeWidth=0.5))
    return drawing


def trend_icon(direction: str | None, size: float = 0.34 * cm) -> Drawing:
    """Indicador de tendência desenhado: triângulo para cima (melhorando), para baixo (piorando) ou
    losango achatado (estável); cinza quando não há dados."""
    drawing = Drawing(size, size)
    half = size / 2
    if direction == "melhorando":
        drawing.add(Polygon([0, 0.12 * size, size, 0.12 * size, half, size * 0.9], fillColor=status_solid_color("Conforme"), strokeColor=None))
    elif direction == "piorando":
        drawing.add(Polygon([0, size * 0.88, size, size * 0.88, half, size * 0.1], fillColor=status_solid_color("Não-Conforme"), strokeColor=None))
    elif direction == "estavel":
        drawing.add(Rect(0, half - size * 0.12, size, size * 0.24, fillColor=colors.HexColor("#64748B"), strokeColor=None))
    else:
        drawing.add(Rect(size * 0.25, half - size * 0.06, size * 0.5, size * 0.12, fillColor=colors.HexColor("#CBD5E1"), strokeColor=None))
    return drawing


def _x_labels(labels: list[str], max_labels: int) -> set[int]:
    count = len(labels)
    if count <= max_labels:
        return set(range(count))
    step = (count - 1) / (max_labels - 1)
    return {round(i * step) for i in range(max_labels)}


def line_chart(
    points: list[tuple[str, float | None, str]],
    *,
    width: float,
    height: float,
    y_range: tuple[float, float],
    bands: list[tuple[float, float, str]],
    value_fmt,
    y_ticks: list[float] | None = None,
    title: str | None = None,
    compact: bool = False,
) -> Drawing:
    """Linha com pontos coloridos pelo status daquela análise, sobre faixas de especificação.

    `points`: [(rótulo do eixo x, valor ou None, status)] em ordem cronológica, espaçados igualmente.
    """
    left = 0.9 * cm if not compact else 0.75 * cm
    right = 0.35 * cm
    bottom = 0.65 * cm
    top = 0.5 * cm if title else 0.25 * cm
    plot_w, plot_h = width - left - right, height - bottom - top
    lo, hi = y_range
    drawing = Drawing(width, height)

    def y_of(v: float) -> float:
        return bottom + (min(max(v, lo), hi) - lo) / (hi - lo) * plot_h

    count = len(points)

    def x_of(i: int) -> float:
        if count == 1:
            return left + plot_w / 2
        return left + plot_w * (0.04 + 0.92 * i / (count - 1))

    for start, end, status in bands:
        y0, y1 = y_of(start), y_of(end)
        if y1 - y0 > 0.05:
            drawing.add(Rect(left, y0, plot_w, y1 - y0, fillColor=_soft(status_solid_color(status)), strokeColor=None))
    drawing.add(Rect(left, bottom, plot_w, plot_h, fillColor=None, strokeColor=LINE, strokeWidth=0.5))

    # Marcas do eixo y: por padrão, nos limites de especificação (os valores que importam no laudo).
    # `y_ticks` vem em ordem de prioridade; uma marca muito próxima de outra já escolhida é descartada.
    candidates = y_ticks if y_ticks is not None else [lo + (hi - lo) * i / 4 for i in range(5)]
    kept: list[float] = []
    for candidate in candidates:
        if all(abs(y_of(candidate) - y_of(other)) >= 10 for other in kept):
            kept.append(candidate)
    for value in kept:
        y = y_of(value)
        drawing.add(Line(left, y, left + plot_w, y, strokeColor=colors.Color(1, 1, 1, alpha=0.6), strokeWidth=0.3))
        drawing.add(String(left - 0.12 * cm, y - 2, value_fmt(value), fontName="Vera", fontSize=6, fillColor=MUTED, textAnchor="end"))

    labels = [p[0] for p in points]
    for i in _x_labels(labels, 3 if compact else 6):
        drawing.add(String(x_of(i), bottom - 0.4 * cm, labels[i], fontName="Vera", fontSize=6, fillColor=MUTED, textAnchor="middle"))

    coords = [(x_of(i), y_of(v)) for i, (_, v, _) in enumerate(points) if v is not None]
    if len(coords) >= 2:
        flat = [c for xy in coords for c in xy]
        drawing.add(PolyLine(flat, strokeColor=BRAND, strokeWidth=1.3))
    for i, (_, point_value, status) in enumerate(points):
        if point_value is None:
            continue
        drawing.add(Circle(x_of(i), y_of(point_value), 2.6, fillColor=status_solid_color(status), strokeColor=WHITE, strokeWidth=0.9))

    last = next(((i, v) for i, (_, v, _) in reversed(list(enumerate(points))) if v is not None), None)
    if last is not None and not compact:
        i, v = last
        drawing.add(String(x_of(i), y_of(v) + 0.2 * cm, value_fmt(v), fontName="Vera-Bold", fontSize=7, fillColor=INK, textAnchor="middle"))

    if title:
        drawing.add(String(left, height - 0.34 * cm, title, fontName="Vera-Bold", fontSize=7.5, fillColor=INK))
    return drawing


def legend_row(width: float) -> Drawing:
    """Legenda das cores de status, para acompanhar os gráficos."""
    drawing = Drawing(width, 0.4 * cm)
    x = 0.0
    for status in ("Conforme", "Condicional", "Não-Conforme"):
        drawing.add(Circle(x + 2.5, 0.18 * cm, 2.5, fillColor=STATUS_COLORS[status][2], strokeColor=None))
        drawing.add(String(x + 8, 0.12 * cm, status, fontName="Vera", fontSize=7, fillColor=MUTED))
        x += 2.4 * cm
    return drawing


def format_index(value: float) -> str:
    return format_number(value, 1)
