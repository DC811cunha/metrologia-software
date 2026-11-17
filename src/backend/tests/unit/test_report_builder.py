import io
from datetime import datetime, timezone

from pypdf import PdfReader

from app.analysis.metrics_catalog import METRICS_CATALOG
from app.services.report_service import build_history_report, build_single_analysis_report
from app.services.report_theme import format_limit

MEASUREMENTS = [
    {"metrica_chave": "complexidade_ciclomatica", "valor_medido": 5, "status_conformidade": "Conforme"},
    {"metrica_chave": "loc", "valor_medido": 20, "status_conformidade": "Conforme"},
    {"metrica_chave": "indice_manutenibilidade", "valor_medido": 80, "status_conformidade": "Conforme"},
    {"metrica_chave": "cobertura_testes", "valor_medido": None, "status_conformidade": "Não disponível"},
    {"metrica_chave": "acoplamento", "valor_medido": 0.3, "status_conformidade": "Conforme"},
    {"metrica_chave": "score_duplicacao", "valor_medido": 2, "status_conformidade": "Conforme"},
]

MEASUREMENTS_WITH_ISSUE = [
    {"metrica_chave": "complexidade_ciclomatica", "valor_medido": 5, "status_conformidade": "Conforme"},
    {"metrica_chave": "loc", "valor_medido": 20, "status_conformidade": "Conforme"},
    {"metrica_chave": "indice_manutenibilidade", "valor_medido": 80, "status_conformidade": "Conforme"},
    {"metrica_chave": "cobertura_testes", "valor_medido": None, "status_conformidade": "Não disponível"},
    {"metrica_chave": "acoplamento", "valor_medido": 0.3, "status_conformidade": "Conforme"},
    {
        "metrica_chave": "score_duplicacao",
        "valor_medido": 49.7,
        "status_conformidade": "Não-Conforme",
    },
]


def _extract_text(pdf_bytes: bytes) -> str:
    """Extrai o texto e normaliza espaços — o PDF quebra linha em pontos de wrap
    da tabela, o que não deve ser confundido com ausência do texto."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return " ".join(raw.split())


class TestBuildSingleAnalysisReport:
    def test_produces_valid_pdf_bytes(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
            overall_status="Conforme",
        )
        assert pdf_bytes.startswith(b"%PDF")

    def test_includes_formula_source_and_limits_for_every_metric(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
            overall_status="Conforme",
        )
        text = _extract_text(pdf_bytes)

        for metric in METRICS_CATALOG.values():
            assert metric.nome in text
            assert format_limit(metric.limite_nominal) in text
            # Primeira palavra da fonte bibliográfica (ex.: autor) — um único token curto
            # tem baixíssima chance de ser quebrado pelo word-wrap da tabela, ao
            # contrário de truncar a frase em um ponto arbitrário.
            first_word = metric.fonte_bibliografica.split()[0].rstrip(",.")
            assert first_word in text

    def test_marks_unavailable_metric_explicitly(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
            overall_status="Conforme",
        )
        text = _extract_text(pdf_bytes)
        assert "Não disponível" in text

    def test_summary_lists_conformant_metrics_as_strengths(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
            overall_status="Conforme",
        )
        text = _extract_text(pdf_bytes)
        assert "Resumo da análise" in text
        assert "Pontos fortes" in text
        # Nada fora do limite nesta amostra — a seção de atenção não deve aparecer.
        assert "Pontos de atenção" not in text

    def test_summary_flags_out_of_limit_metric_with_insight(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS_WITH_ISSUE,
            overall_status="Condicional",
        )
        text = _extract_text(pdf_bytes)
        assert "Pontos de atenção" in text
        assert "Score de Duplicação" in text
        # A implicação prática da métrica específica precisa estar presente, não só o nome.
        assert "custo de manutenção" in text
        assert "Índice agregado" in text


class TestBuildHistoryReport:
    def test_produces_valid_pdf_with_one_section_per_analysis(self):
        analyses = [
            {
                "id": "analysis-1",
                "concluida_em": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS,
                "status_conformidade_geral": "Conforme",
            },
            {
                "id": "analysis-2",
                "concluida_em": datetime(2026, 6, 15, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS,
                "status_conformidade_geral": "Conforme",
            },
        ]
        pdf_bytes = build_history_report(
            repository_url="https://github.com/octocat/Hello-World", analyses=analyses
        )
        text = _extract_text(pdf_bytes)

        assert pdf_bytes.startswith(b"%PDF")
        assert "analysis-1" in text
        assert "analysis-2" in text
        assert "Tend" in text  # "Tendência"

    def test_includes_summary_for_most_recent_analysis(self):
        analyses = [
            {
                "id": "analysis-1",
                "concluida_em": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS,
                "status_conformidade_geral": "Conforme",
            },
            {
                "id": "analysis-2",
                "concluida_em": datetime(2026, 6, 15, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS_WITH_ISSUE,
                "status_conformidade_geral": "Condicional",
            },
        ]
        pdf_bytes = build_history_report(
            repository_url="https://github.com/octocat/Hello-World", analyses=analyses
        )
        text = _extract_text(pdf_bytes)
        assert "Resumo da análise" in text
        assert "Pontos de atenção" in text


class TestScopeNote:
    """O usuário precisa saber que testes e arquivos gerados não entram nas métricas (ADR-011)."""

    def test_single_report_states_the_measurement_scope(self):
        pdf = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="a-1",
            concluida_em=datetime(2026, 6, 1, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
            overall_status="Conforme",
        )

        text = _extract_text(pdf)

        assert "Escopo da medição" in text
        assert "Arquivos de teste, dependências e arquivos gerados" in text

    def test_history_report_states_the_measurement_scope(self):
        pdf = build_history_report(
            repository_url="https://github.com/octocat/Hello-World",
            analyses=[
                {
                    "id": "a-1",
                    "concluida_em": datetime(2026, 6, 1, tzinfo=timezone.utc),
                    "measurements": MEASUREMENTS,
                    "status_conformidade_geral": "Conforme",
                }
            ],
        )

        assert "Escopo da medição" in _extract_text(pdf)


MEASUREMENTS_PREVIOUS = [
    {"metrica_chave": "complexidade_ciclomatica", "valor_medido": 8, "status_conformidade": "Conforme"},
    {"metrica_chave": "loc", "valor_medido": 20, "status_conformidade": "Conforme"},
    {"metrica_chave": "indice_manutenibilidade", "valor_medido": 80, "status_conformidade": "Conforme"},
    {"metrica_chave": "cobertura_testes", "valor_medido": None, "status_conformidade": "Não disponível"},
    {"metrica_chave": "acoplamento", "valor_medido": 0.3, "status_conformidade": "Conforme"},
    {"metrica_chave": "score_duplicacao", "valor_medido": 30.12345, "status_conformidade": "Não-Conforme"},
]
MEASUREMENTS_CURRENT = [
    {"metrica_chave": "complexidade_ciclomatica", "valor_medido": 5, "status_conformidade": "Conforme"},
    {"metrica_chave": "loc", "valor_medido": 20, "status_conformidade": "Conforme"},
    {"metrica_chave": "indice_manutenibilidade", "valor_medido": 80, "status_conformidade": "Conforme"},
    {"metrica_chave": "cobertura_testes", "valor_medido": 91.6743, "status_conformidade": "Conforme"},
    {"metrica_chave": "acoplamento", "valor_medido": 0.3, "status_conformidade": "Conforme"},
    {"metrica_chave": "score_duplicacao", "valor_medido": 17.0529, "status_conformidade": "Não-Conforme"},
]


def _single(**overrides) -> str:
    kwargs = dict(
        repository_url="https://github.com/octocat/Hello-World",
        analysis_id="analysis-1",
        concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        measurements=MEASUREMENTS_CURRENT,
        overall_status="Condicional",
    )
    kwargs.update(overrides)
    return _extract_text(build_single_analysis_report(**kwargs))


class TestReportData:
    def test_limits_use_the_right_direction_for_each_metric(self):
        # Regressão: a tabela antiga mostrava "≤ 80 / ≤ 50" para a Cobertura de Testes, em que MAIS é melhor.
        text = _single()

        assert "Conforme ≥ 80 · Condicional ≥ 50 · Não-Conforme < 50" in text  # cobertura
        assert "Conforme ≤ 10 · Condicional ≤ 20 · Não-Conforme > 20" in text  # complexidade

    def test_numbers_use_brazilian_format_and_sensible_precision(self):
        text = _single()

        assert "17,1%" in text  # 17.0529 -> uma casa, vírgula decimal
        assert "91,7%" in text
        assert "17.0529" not in text
        assert "91.6743" not in text

    def test_shows_the_overall_conformity_index_and_counts(self):
        text = _single()

        # 5 Conformes (500) + 1 Não-Conforme (0) = 83,3
        assert "83,3" in text
        assert "ÍNDICE DE CONFORMIDADE" in text

    def test_dates_are_shown_in_brasilia_time(self):
        text = _single()  # 12:00 UTC

        assert "01/06/2026 09:00" in text
        assert "horário de Brasília" in text

    def test_shows_languages_and_repository_name(self):
        text = _single(linguagens=["Python", "TypeScript"])

        assert "Python, TypeScript" in text
        assert "octocat/Hello-World" in text

    def test_compares_with_the_previous_analysis_when_available(self):
        text = _single(
            previous={
                "concluida_em": datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS_PREVIOUS,
                "status_conformidade_geral": "Condicional",
            }
        )

        assert "vs. anterior" in text
        assert "melhorou" in text  # complexidade 8 -> 5 e duplicação 30,1 -> 17,1
        assert "desde a análise de 01/05/2026" in text

    def test_has_no_comparison_column_without_a_previous_analysis(self):
        assert "vs. anterior" not in _single()

    def test_attention_points_say_how_far_each_metric_is_from_conforme(self):
        text = _single()

        assert "Para chegar a Conforme, reduzir de 17,1% para no máximo 5%" in text
        assert "Sugestão:" in text

    def test_pages_are_numbered_with_the_total(self):
        assert "Página 1 de" in _single()

    def test_survives_special_characters_in_the_repository_url(self):
        text = _single(repository_url="https://github.com/octocat/a&b<c>")

        assert "a&b" in text

    def test_measurement_order_from_the_database_does_not_matter(self):
        shuffled = list(reversed(MEASUREMENTS_CURRENT))

        assert _single(measurements=shuffled) == _single(measurements=MEASUREMENTS_CURRENT)

    def test_has_a_references_section_and_a_reading_guide(self):
        text = _single()

        assert "Como ler este laudo" in text
        assert "Referências" in text
        assert "McCabe" in text


class TestHistoryReportCharts:
    ANALYSES = [
        {
            "id": "analysis-1",
            "concluida_em": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "measurements": MEASUREMENTS_PREVIOUS,
            "status_conformidade_geral": "Condicional",
        },
        {
            "id": "analysis-2",
            "concluida_em": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "measurements": MEASUREMENTS_CURRENT,
            "status_conformidade_geral": "Condicional",
        },
    ]

    def _history(self, analyses=None) -> str:
        return _extract_text(
            build_history_report(
                repository_url="https://github.com/octocat/Hello-World",
                analyses=analyses or self.ANALYSES,
                linguagens=["Python"],
            )
        )

    def test_has_overview_evolution_and_variation_sections(self):
        text = self._history()

        assert "Evolução do índice de conformidade" in text
        assert "Evolução de cada métrica" in text
        assert "Variação por métrica" in text
        assert "Primeira análise" in text
        assert "Análises incluídas" in text
        assert "Período" in text

    def test_variation_table_shows_total_change_and_recent_trend(self):
        text = self._history()

        assert "−13,1" in text  # duplicação 30,12 -> 17,05
        assert "Melhorando" in text

    def test_a_single_analysis_has_no_variation_table_but_still_renders(self):
        text = self._history(self.ANALYSES[:1])

        assert "Variação por métrica" not in text
        assert "Evolução do índice de conformidade" in text

    def test_matrix_lists_every_analysis_id_with_its_index(self):
        text = self._history()

        assert "analysis-1" in text and "analysis-2" in text
        assert "83,3" in text
