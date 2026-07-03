from app.services.trend_service import calculate_trend


class TestCalculateTrend:
    def test_returns_none_when_either_value_is_missing(self):
        assert calculate_trend("cobertura_testes", None, 80) is None
        assert calculate_trend("cobertura_testes", 80, None) is None

    def test_returns_estavel_when_values_are_equal(self):
        assert calculate_trend("complexidade_ciclomatica", 5, 5) == "estavel"

    def test_menor_melhor_metric_improves_when_value_decreases(self):
        assert calculate_trend("complexidade_ciclomatica", 15, 10) == "melhorando"

    def test_menor_melhor_metric_worsens_when_value_increases(self):
        assert calculate_trend("complexidade_ciclomatica", 10, 15) == "piorando"

    def test_maior_melhor_metric_improves_when_value_increases(self):
        assert calculate_trend("cobertura_testes", 70, 85) == "melhorando"

    def test_maior_melhor_metric_worsens_when_value_decreases(self):
        assert calculate_trend("cobertura_testes", 85, 70) == "piorando"
