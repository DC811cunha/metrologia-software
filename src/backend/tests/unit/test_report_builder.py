import io
from datetime import datetime, timezone

from pypdf import PdfReader

from app.analysis.metrics_catalog import METRICS_CATALOG
from app.services.report_service import build_history_report, build_single_analysis_report

MEASUREMENTS = [
    {"metrica_chave": "complexidade_ciclomatica", "valor_medido": 5, "status_conformidade": "Conforme"},
    {"metrica_chave": "loc", "valor_medido": 20, "status_conformidade": "Conforme"},
    {"metrica_chave": "indice_manutenibilidade", "valor_medido": 80, "status_conformidade": "Conforme"},
    {"metrica_chave": "cobertura_testes", "valor_medido": None, "status_conformidade": "Não disponível"},
    {"metrica_chave": "acoplamento", "valor_medido": 0.3, "status_conformidade": "Conforme"},
    {"metrica_chave": "score_duplicacao", "valor_medido": 2, "status_conformidade": "Conforme"},
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
        )
        assert pdf_bytes.startswith(b"%PDF")

    def test_includes_formula_source_and_limits_for_every_metric(self):
        pdf_bytes = build_single_analysis_report(
            repository_url="https://github.com/octocat/Hello-World",
            analysis_id="analysis-1",
            concluida_em=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            measurements=MEASUREMENTS,
        )
        text = _extract_text(pdf_bytes)

        for metric in METRICS_CATALOG.values():
            assert metric.nome in text
            assert str(metric.limite_nominal) in text
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
        )
        text = _extract_text(pdf_bytes)
        assert "Não disponível" in text


class TestBuildHistoryReport:
    def test_produces_valid_pdf_with_one_section_per_analysis(self):
        analyses = [
            {
                "id": "analysis-1",
                "concluida_em": datetime(2026, 6, 1, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS,
            },
            {
                "id": "analysis-2",
                "concluida_em": datetime(2026, 6, 15, tzinfo=timezone.utc),
                "measurements": MEASUREMENTS,
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
