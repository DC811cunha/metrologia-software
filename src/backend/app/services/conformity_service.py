"""Classifica cada métrica medida contra o catálogo e calcula o índice agregado de
conformidade da Análise (data-model.md, spec.md linha 243).

A spec define os cortes do índice agregado (≥90 Conforme, 70–89 Condicional, <70
Não-Conforme) mas não a fórmula de pontuação por métrica; adotamos uma pontuação
simples e documentada — Conforme=100, Condicional=50, Não-Conforme=0, média sobre as
métricas com status diferente de "Não disponível" (que são excluídas, nunca contam
como Não-Conforme — regra explícita do data-model.md para `cobertura_testes`).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.analysis.metrics_catalog import METRICS_CATALOG, ConformityStatus, get_metric

_SCORE_BY_STATUS: dict[ConformityStatus, float] = {
    ConformityStatus.CONFORME: 100.0,
    ConformityStatus.CONDICIONAL: 50.0,
    ConformityStatus.NAO_CONFORME: 0.0,
}


@dataclass(frozen=True)
class MeasurementResult:
    metrica_chave: str
    valor_medido: float | None
    status_conformidade: ConformityStatus


def classify_measurements(values_by_metric: dict[str, float | None]) -> list[MeasurementResult]:
    """Classifica cada valor medido contra os limites do catálogo (uma Medição por
    métrica do catálogo — data-model.md exige as 6)."""
    results = []
    for chave in METRICS_CATALOG:
        valor = values_by_metric.get(chave)
        metric = get_metric(chave)
        status = metric.classificar(valor)
        results.append(MeasurementResult(chave, valor, status))
    return results


def calculate_overall_status(measurements: list[MeasurementResult]) -> ConformityStatus:
    """Índice agregado: média dos scores por status, excluindo "Não disponível"."""
    scores = [
        _SCORE_BY_STATUS[m.status_conformidade]
        for m in measurements
        if m.status_conformidade in _SCORE_BY_STATUS
    ]
    if not scores:
        return ConformityStatus.NAO_CONFORME

    index = sum(scores) / len(scores)
    if index >= 90:
        return ConformityStatus.CONFORME
    if index >= 70:
        return ConformityStatus.CONDICIONAL
    return ConformityStatus.NAO_CONFORME
