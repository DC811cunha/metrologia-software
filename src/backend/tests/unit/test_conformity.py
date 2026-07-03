from app.analysis.metrics_catalog import ConformityStatus
from app.services.conformity_service import calculate_overall_status, classify_measurements


ALL_CONFORME_VALUES = {
    "complexidade_ciclomatica": 5,
    "loc": 20,
    "indice_manutenibilidade": 80,
    "cobertura_testes": 90,
    "acoplamento": 0.3,
    "score_duplicacao": 2,
}


class TestClassifyMeasurements:
    def test_returns_one_measurement_per_catalog_metric(self):
        results = classify_measurements(ALL_CONFORME_VALUES)
        assert len(results) == 6
        assert all(r.status_conformidade == ConformityStatus.CONFORME for r in results)

    def test_missing_coverage_is_not_available(self):
        values = {**ALL_CONFORME_VALUES, "cobertura_testes": None}
        results = classify_measurements(values)
        coverage = next(r for r in results if r.metrica_chave == "cobertura_testes")
        assert coverage.status_conformidade == ConformityStatus.NAO_DISPONIVEL
        assert coverage.valor_medido is None

    def test_non_conforme_value_is_classified_correctly(self):
        values = {**ALL_CONFORME_VALUES, "complexidade_ciclomatica": 25}
        results = classify_measurements(values)
        cc = next(r for r in results if r.metrica_chave == "complexidade_ciclomatica")
        assert cc.status_conformidade == ConformityStatus.NAO_CONFORME


class TestCalculateOverallStatus:
    def test_all_conforme_yields_conforme(self):
        measurements = classify_measurements(ALL_CONFORME_VALUES)
        assert calculate_overall_status(measurements) == ConformityStatus.CONFORME

    def test_not_available_coverage_excluded_from_index(self):
        values = {**ALL_CONFORME_VALUES, "cobertura_testes": None}
        measurements = classify_measurements(values)
        # As 5 métricas restantes são todas Conforme -> índice ainda 100, mesmo
        # com cobertura "Não disponível" (regra explícita do data-model.md).
        assert calculate_overall_status(measurements) == ConformityStatus.CONFORME

    def test_mostly_non_conforme_yields_non_conforme(self):
        values = {
            "complexidade_ciclomatica": 25,
            "loc": 70,
            "indice_manutenibilidade": 5,
            "cobertura_testes": 30,
            "acoplamento": 0.9,
            "score_duplicacao": 20,
        }
        measurements = classify_measurements(values)
        assert calculate_overall_status(measurements) == ConformityStatus.NAO_CONFORME

    def test_mixed_results_yield_condicional(self):
        values = {
            "complexidade_ciclomatica": 15,  # condicional
            "loc": 45,  # condicional
            "indice_manutenibilidade": 80,  # conforme
            "cobertura_testes": 90,  # conforme
            "acoplamento": 0.3,  # conforme
            "score_duplicacao": 2,  # conforme
        }
        measurements = classify_measurements(values)
        # scores: 50,50,100,100,100,100 -> media = 83.3 -> condicional
        assert calculate_overall_status(measurements) == ConformityStatus.CONDICIONAL
