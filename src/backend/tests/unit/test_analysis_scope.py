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


class TestAmbiguousDirectoriesAreJudgedByContext:
    """`build/`, `dist/`, `out/`, `target/`, `coverage/` e `env/` podem ser saída/ambiente OU código autoral
    (um `src/build/` de uma ferramenta de build). Só saem da medição com evidência de que são saída."""

    @pytest.mark.parametrize("directory", ["build", "dist", "out", "target", "coverage"])
    def test_output_directory_at_the_repository_root_is_ignored(self, tmp_path, directory):
        write(tmp_path, "app.py")
        write(tmp_path, f"{directory}/generated.py")

        assert names(tmp_path, {".py"}) == ["app.py"]

    @pytest.mark.parametrize("manifest", ["package.json", "pyproject.toml", "pom.xml", "Cargo.toml"])
    def test_output_directory_next_to_a_project_manifest_is_ignored(self, tmp_path, manifest):
        write(tmp_path, "frontend/src/app.py")
        write(tmp_path, f"frontend/{manifest}", "{}")
        write(tmp_path, "frontend/build/bundle_helper.py")
        write(tmp_path, "frontend/dist/out.py")

        assert names(tmp_path, {".py"}) == ["frontend/src/app.py"]

    def test_a_package_named_build_inside_the_source_tree_is_measured(self, tmp_path):
        # Regressão: o nome "build" era podado em qualquer profundidade e sumia com o pacote de uma ferramenta.
        write(tmp_path, "pyproject.toml", "[project]\n")
        write(tmp_path, "src/tool/build/compiler.py", "def compile():\n    return 1\n")
        write(tmp_path, "src/tool/cli.py", "def main():\n    return 1\n")

        assert names(tmp_path, {".py"}) == ["src/tool/build/compiler.py", "src/tool/cli.py"]

    def test_env_is_ignored_only_when_it_is_a_virtual_environment(self, tmp_path):
        write(tmp_path, "app.py")
        write(tmp_path, "venv_like/pyvenv.cfg", "home = /usr/bin\n")
        write(tmp_path, "env/pyvenv.cfg", "home = /usr/bin\n")
        write(tmp_path, "env/bin/activate_this.py")
        write(tmp_path, "settings/env/config.py")  # `env` de configuração, sem pyvenv.cfg

        assert names(tmp_path, {".py"}) == ["app.py", "settings/env/config.py"]


class TestGeneratedAndVendoredFiles:
    @pytest.mark.parametrize(
        "directory",
        [".next", ".nuxt", "out", "target", "site-packages", "bower_components", "migrations", "node_modules", "vendor"],
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


class TestRepositoryWithNothingToMeasure:
    """Regressão: sem nenhuma função (só constantes, Python 2, configuração) a média por função não existe,
    e a análise falhava mais adiante com "Métrica 'complexidade_ciclomatica' não permite valor ausente"."""

    def test_constants_only_python_package_explains_the_problem(self, tmp_path):
        write(tmp_path, "pkg/__init__.py", "VERSION = '1.0'\n")
        write(tmp_path, "pkg/consts.py", "A = 1\nB = 2\n")

        with pytest.raises(NoAnalyzableSourceError, match="nenhuma função ou método"):
            metric_engine.analyze_repository(tmp_path, ["python"])

    def test_python_2_only_repository_says_the_files_could_not_be_parsed(self, tmp_path):
        write(tmp_path, "legacy.py", "print 'olá'\n")

        with pytest.raises(NoAnalyzableSourceError, match="pôde ser interpretado"):
            metric_engine.analyze_repository(tmp_path, ["python"])

    def test_a_single_unparseable_file_does_not_stop_the_analysis(self, tmp_path):
        write(tmp_path, "legacy.py", "print 'olá'\n")
        write(tmp_path, "ok.py", "def f(x):\n    return x\n")

        metrics = metric_engine.analyze_repository(tmp_path, ["python"])

        assert metrics.avg_complexity == 1.0

    def test_javascript_without_functions_explains_the_problem(self, tmp_path):
        write(tmp_path, "config.js", "module.exports = { port: 3000 };\n")

        with pytest.raises(NoAnalyzableSourceError, match="nenhuma função ou método"):
            metric_engine.analyze_repository(tmp_path, ["javascript"])


class TestMalformedCoverageFromThirdParties:
    def test_malformed_lcov_lines_are_ignored_instead_of_crashing(self, tmp_path):
        write(tmp_path, "lcov.info", "SF:a.js\nLF:\nLH:abc\nLF:10\nLH:5\nend_of_record\n")

        assert read_coverage_percentage(tmp_path) == 50.0

    def test_lcov_without_valid_totals_is_unavailable(self, tmp_path):
        write(tmp_path, "lcov.info", "LF:\nLH:3\n")

        assert read_coverage_percentage(tmp_path) is None

    def test_inconsistent_lcov_is_unavailable(self, tmp_path):
        write(tmp_path, "lcov.info", "LF:10\nLH:50\n")  # mais linhas cobertas que linhas totais

        assert read_coverage_percentage(tmp_path) is None

    def test_a_coverage_goal_in_prose_is_not_a_measurement(self, tmp_path):
        write(tmp_path, "README.md", "# Projeto\n\nMeta: test coverage 100% obrigatório nos módulos novos.\n")

        assert read_coverage_percentage(tmp_path) is None

    def test_a_textual_badge_line_still_counts(self, tmp_path):
        write(tmp_path, "README.md", "# Projeto\n\n![Coverage: 87%](https://example.com/badge.svg)\n")

        assert read_coverage_percentage(tmp_path) == 87.0


class TestPrunedAndDeterministicScan:
    """`rglob` percorria node_modules inteiro só para descartar cada arquivo depois, e devolvia os arquivos na
    ordem do sistema de arquivos."""

    def test_does_not_descend_into_ignored_or_test_directories(self, tmp_path, monkeypatch):
        import os

        write(tmp_path, "src/app.py")
        write(tmp_path, "node_modules/pkg/deep/index.js")
        write(tmp_path, "tests/test_a.py")
        write(tmp_path, ".venv/lib/x.py")
        visited: list[str] = []
        real_walk = os.walk

        def spying_walk(top, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
                visited.append(Path(dirpath).relative_to(tmp_path).as_posix())
                yield dirpath, dirnames, filenames

        monkeypatch.setattr(metric_engine.os, "walk", spying_walk)

        found = names(tmp_path, {".py", ".js"})

        assert found == ["src/app.py"]
        assert not any(part.startswith(("node_modules", "tests", ".venv")) for part in visited), visited

    def test_returns_files_in_alphabetical_order(self, tmp_path):
        for name in ("z.py", "a/b.py", "a/a.py", "m/x.py", "b.py"):
            write(tmp_path, name)

        listed = [path.relative_to(tmp_path).as_posix() for path in iter_source_files(tmp_path, {".py"})]

        # Arquivos da pasta atual primeiro (ordem alfabética), depois cada subpasta, também em ordem alfabética.
        assert listed == ["b.py", "z.py", "a/a.py", "a/b.py", "m/x.py"]

    def test_coverage_search_does_not_descend_into_third_party_directories(self, tmp_path, monkeypatch):
        import os

        from app.analysis import coverage_reader

        write(tmp_path, "node_modules/pkg/coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.99"></coverage>')
        write(tmp_path, "coverage.xml", '<?xml version="1.0"?><coverage line-rate="0.5"></coverage>')
        visited: list[str] = []
        real_walk = os.walk

        def spying_walk(top, *args, **kwargs):
            for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
                visited.append(dirpath)
                yield dirpath, dirnames, filenames

        monkeypatch.setattr(coverage_reader.os, "walk", spying_walk)

        assert read_coverage_percentage(tmp_path) == 50.0
        assert not any("node_modules" in v for v in visited)
