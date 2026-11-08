"""Escopo dos arquivos analisados e escolha determinística da cobertura (issue #100): só código
autoral de produção entra nas métricas, e a cobertura vem do relatório certo, sempre o mesmo."""

from pathlib import Path

import pytest

from app.analysis import coupling, duplication, metric_engine
from app.analysis.coverage_reader import read_coverage_from_artifact_zip, read_coverage_percentage
from app.analysis.metric_engine import NoAnalyzableSourceError, is_test_file, iter_source_files


def write(root: Path, relative: str, content: str = "x = 1\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def names(root: Path, extensions: set[str]) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in iter_source_files(root, extensions))


class TestGeneratedAndVendoredFiles:
    @pytest.mark.parametrize(
        "directory",
        [".next", ".nuxt", "out", "target", "env", "site-packages", "bower_components", "migrations", "node_modules"],
    )
    def test_ignores_generated_and_third_party_directories(self, tmp_path, directory):
        write(tmp_path, "app.py")
        write(tmp_path, f"{directory}/generated.py")

        assert names(tmp_path, {".py"}) == ["app.py"]

    def test_ignores_minified_bundles_and_type_declarations(self, tmp_path):
        write(tmp_path, "src/app.js", "function f() { return 1; }\n")
        write(tmp_path, "public/bundle.min.js", "function g(){return 2}\n")
        write(tmp_path, "src/types.d.ts", "export declare const x: number;\n")

        assert names(tmp_path, {".js", ".ts"}) == ["src/app.js"]

    def test_ignores_a_minified_file_without_the_min_suffix(self, tmp_path):
        write(tmp_path, "src/app.js", "function f() { return 1; }\n")
        write(tmp_path, "vendor-lib.js", "function a(b){return b+1}" * 400 + "\n")  # 1 linha de ~10 KB

        assert names(tmp_path, {".js"}) == ["src/app.js"]

    def test_a_minified_bundle_does_not_distort_the_repository_average(self, tmp_path):
        write(tmp_path, "src/app.js", "function f(a) {\n  if (a) { return 1; }\n  return 2;\n}\n")
        write(tmp_path, "dist-less/bundle.min.js", ("function g(a){" + "if(a){a++}" * 300 + "return a}") + "\n")

        metrics = metric_engine.analyze_repository(tmp_path, ["javascript"])

        assert metrics.avg_complexity == 2.0


class TestTestFilesAreOutOfTheProductionMetrics:
    @pytest.mark.parametrize(
        "relative",
        [
            "tests/helpers.py",
            "test/unit/a.py",
            "src/__tests__/a.js",
            "spec/a.rb.py",
            "e2e/flow.ts",
            "src/test_models.py",
            "src/models_test.py",
            "conftest.py",
            "src/button.test.tsx",
            "src/button.spec.js",
        ],
    )
    def test_recognises_test_files(self, relative):
        assert is_test_file(Path(relative)) is True

    @pytest.mark.parametrize(
        "relative", ["src/latest.py", "src/contest.py", "src/attestation.py", "testing_utils/a.py", "src/protest.js"]
    )
    def test_does_not_mistake_production_files_for_tests(self, relative):
        assert is_test_file(Path(relative)) is False

    def test_test_files_are_not_measured(self, tmp_path):
        write(tmp_path, "src/app.py")
        write(tmp_path, "tests/test_app.py")
        write(tmp_path, "src/app_test.py")

        assert names(tmp_path, {".py"}) == ["src/app.py"]

    def test_test_modules_no_longer_inflate_the_coupling(self, tmp_path):
        write(tmp_path, "pkg/__init__.py", "")
        write(tmp_path, "pkg/core.py", "x = 1\n")
        write(tmp_path, "pkg/api.py", "from pkg.core import x\n")
        for index in range(5):
            write(tmp_path, f"tests/test_{index}.py", "import pkg\nfrom pkg.api import x\nfrom pkg.core import x\n")

        with_tests_excluded = coupling.calculate_average_instability(tmp_path, ["python"])

        # Só o grafo de produção (api -> core): api I=1, core I=0 → 0,5. Com os 5 módulos de teste (I=1
        # cada) na média, o valor passava de 0,8.
        assert with_tests_excluded == 0.5

    def test_test_code_does_not_count_as_duplication(self, tmp_path):
        block = "\n".join(f"    value_{i} = compute({i}) + helper({i})" for i in range(10))
        write(tmp_path, "tests/test_a.py", f"def test_a():\n{block}\n")
        write(tmp_path, "tests/test_b.py", f"def test_b():\n{block}\n")
        write(tmp_path, "src/app.py", "def run():\n    return 1\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0


class TestNoAnalyzableSource:
    def test_raises_a_clear_error_when_only_tests_and_generated_files_exist(self, tmp_path):
        write(tmp_path, "tests/test_a.py")
        write(tmp_path, "node_modules/lib/index.js")

        with pytest.raises(NoAnalyzableSourceError, match="nenhum arquivo-fonte"):
            metric_engine.analyze_repository(tmp_path, ["python", "javascript"])


XML_BACKEND = '<?xml version="1.0"?><coverage line-rate="0.90" lines-valid="1000" lines-covered="900"></coverage>'
XML_FRONTEND = '<?xml version="1.0"?><coverage line-rate="0.50" lines-valid="200" lines-covered="100"></coverage>'


class TestCoverageSelection:
    def test_ignores_reports_inside_third_party_directories(self, tmp_path):
        write(tmp_path, "node_modules/pkg/coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.99"></coverage>')
        write(tmp_path, "venv/lib/coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.98"></coverage>')
        write(tmp_path, "coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.60"></coverage>')

        assert read_coverage_percentage(tmp_path) == 60.0

    def test_still_reads_lcov_from_the_coverage_directory(self, tmp_path):
        write(tmp_path, "coverage/lcov.info", "LF:100\nLH:80\n")

        assert read_coverage_percentage(tmp_path) == 80.0

    def test_monorepo_reports_are_combined_by_lines_not_by_arbitrary_order(self, tmp_path):
        write(tmp_path, "backend/coverage.xml", XML_BACKEND)
        write(tmp_path, "frontend/coverage.xml", XML_FRONTEND)

        # (900 + 100) / (1000 + 200) = 83,33%
        assert round(read_coverage_percentage(tmp_path) or 0, 2) == 83.33

    def test_the_result_does_not_depend_on_directory_creation_order(self, tmp_path):
        first, second = tmp_path / "one", tmp_path / "two"
        write(first, "frontend/coverage.xml", XML_FRONTEND)
        write(first, "backend/coverage.xml", XML_BACKEND)
        write(second, "backend/coverage.xml", XML_BACKEND)
        write(second, "frontend/coverage.xml", XML_FRONTEND)

        assert read_coverage_percentage(first) == read_coverage_percentage(second)

    def test_without_line_totals_the_shallowest_report_wins_deterministically(self, tmp_path):
        write(tmp_path, "coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.70"></coverage>')
        write(tmp_path, "packages/a/coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.10"></coverage>')

        assert read_coverage_percentage(tmp_path) == 70.0

    def test_lcov_reports_of_a_monorepo_are_summed(self, tmp_path):
        write(tmp_path, "a/lcov.info", "LF:100\nLH:100\n")
        write(tmp_path, "b/lcov.info", "LF:300\nLH:0\n")

        assert read_coverage_percentage(tmp_path) == 25.0

    def test_artifact_zip_with_several_reports_is_combined_too(self):
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("backend/coverage.xml", XML_BACKEND)
            archive.writestr("frontend/coverage.xml", XML_FRONTEND)

        assert round(read_coverage_from_artifact_zip(buffer.getvalue()) or 0, 2) == 83.33
