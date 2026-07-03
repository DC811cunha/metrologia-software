"""Cálculo de tendência de uma métrica entre as duas análises mais recentes (FR-008, US3).

A spec não define um limiar de "variação insignificante"; adota-se a definição mais
simples e determinística: `estavel` apenas quando os valores são exatamente iguais —
qualquer diferença é classificada como `melhorando`/`piorando` pela direção da métrica
(`Direcao` do catálogo). Retorna `None` quando algum dos dois valores está ausente
("Não disponível"), já que não há base de comparação.
"""

from __future__ import annotations

from app.analysis.metrics_catalog import Direcao, get_metric


def calculate_trend(
    metrica_chave: str, valor_anterior: float | None, valor_atual: float | None
) -> str | None:
    if valor_anterior is None or valor_atual is None:
        return None
    if valor_atual == valor_anterior:
        return "estavel"

    metric = get_metric(metrica_chave)
    if metric.direcao is Direcao.MAIOR_MELHOR:
        return "melhorando" if valor_atual > valor_anterior else "piorando"
    return "melhorando" if valor_atual < valor_anterior else "piorando"
