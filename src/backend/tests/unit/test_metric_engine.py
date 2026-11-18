from app.analysis import metric_engine
from app.analysis.metric_engine import (
    RepoMetrics,
    analyze_js_ts_file,
    analyze_python_file,
    compute_maintainability_index,
)

PYTHON_SOURCE = """
def simple(a):
    return a + 1


def branching(a, b):
    if a > b:
        return a - b
    else:
        return b - a
"""

JS_SOURCE = """
function simple(a) {
  return a + 1;
}

function branching(a, b) {
  if (a > b) {
    return a - b;
  } else {
    return b - a;
  }
}
"""

TS_SOURCE = """
function withTernary(a: number, b: number): number {
  return a > b ? a - b : b - a;
}
"""


class TestComputeMaintainabilityIndex:
    def test_returns_100_when_halstead_volume_is_zero(self):
        assert compute_maintainability_index(0, 5, 10) == 100.0

    def test_returns_value_within_0_and_100(self):
        mi = compute_maintainability_index(100, 5, 20)
        assert 0.0 <= mi <= 100.0

    def test_higher_complexity_lowers_index(self):
        low_complexity = compute_maintainability_index(100, 2, 20)
        high_complexity = compute_maintainability_index(100, 20, 20)
        assert high_complexity < low_complexity


class TestAnalyzePythonFile:
    def test_extracts_per_function_complexity_and_loc(self):
        metrics = RepoMetrics()
        analyze_python_file(PYTHON_SOURCE, metrics)

        assert len(metrics.function_complexities) == 2
        # 'branching' tem um ponto de decisão (if/else) -> CC = 2; 'simple' não tem -> CC = 1
        assert sorted(metrics.function_complexities) == [1.0, 2.0]
        assert len(metrics.function_loc) == 2
        assert all(loc > 0 for loc in metrics.function_loc)

    def test_records_one_maintainability_index_per_file(self):
        metrics = RepoMetrics()
        analyze_python_file(PYTHON_SOURCE, metrics)
        assert len(metrics.file_maintainability_index) == 1
        assert 0.0 <= metrics.file_maintainability_index[0] <= 100.0


class TestAnalyzeJsTsFile:
    def test_extracts_per_function_complexity_and_loc(self):
        metrics = RepoMetrics()
        analyze_js_ts_file(JS_SOURCE, ".js", metrics)

        assert len(metrics.function_complexities) == 2
        assert sorted(metrics.function_complexities) == [1.0, 2.0]
        assert all(loc > 0 for loc in metrics.function_loc)

    def test_counts_ternary_as_decision_point(self):
        metrics = RepoMetrics()
        analyze_js_ts_file(TS_SOURCE, ".ts", metrics)

        assert metrics.function_complexities == [2.0]

    def test_records_one_maintainability_index_per_file(self):
        metrics = RepoMetrics()
        analyze_js_ts_file(JS_SOURCE, ".js", metrics)
        assert len(metrics.file_maintainability_index) == 1
        assert 0.0 <= metrics.file_maintainability_index[0] <= 100.0


class TestWeightedMaintainabilityIndex:
    """A média do MI pesa cada arquivo pelas suas linhas (ADR-015): arquivos minúsculos (MI ~100) não podem
    puxar para cima a média de um repositório cujo código está em poucos arquivos grandes."""

    def _repo(self, tmp_path):
        small = "\n".join(f"def f{i}():\n    return {i}" for i in range(2))
        large = "\n".join(
            f"def g{i}(x):\n    if x > {i}:\n        return x * {i} + len(str(x))\n    return sum(range({i}))" for i in range(60)
        )
        (tmp_path / "small.py").write_text(small, encoding="utf-8")
        (tmp_path / "large.py").write_text(large, encoding="utf-8")
        return metric_engine.analyze_repository(tmp_path, ["python"])

    def test_weighted_average_sits_close_to_the_large_file(self, tmp_path):
        metrics = self._repo(tmp_path)
        small_mi, large_mi = sorted(metrics.file_maintainability_index, reverse=True)
        plain = (small_mi + large_mi) / 2

        assert metrics.avg_maintainability_index < plain
        assert abs(metrics.avg_maintainability_index - large_mi) < abs(plain - large_mi)

    def test_each_file_contributes_its_sloc_as_weight(self, tmp_path):
        metrics = self._repo(tmp_path)

        assert len(metrics.file_sloc) == len(metrics.file_maintainability_index) == 2
        assert all(weight >= 1 for weight in metrics.file_sloc)

    def test_equal_weights_give_the_plain_average(self):
        metrics = metric_engine.RepoMetrics(file_maintainability_index=[40.0, 60.0], file_sloc=[10.0, 10.0])

        assert metrics.avg_maintainability_index == 50.0

    def test_falls_back_to_the_plain_average_without_weights(self):
        metrics = metric_engine.RepoMetrics(file_maintainability_index=[40.0, 60.0])

        assert metrics.avg_maintainability_index == 50.0

    def test_javascript_files_are_weighted_too(self, tmp_path):
        (tmp_path / "a.js").write_text("function a() { return 1; }\n", encoding="utf-8")
        (tmp_path / "b.js").write_text(
            "\n".join(f"function b{i}(x) {{ if (x > {i}) {{ return x * {i}; }} return {i}; }}" for i in range(40)),
            encoding="utf-8",
        )

        metrics = metric_engine.analyze_repository(tmp_path, ["javascript"])

        assert len(metrics.file_sloc) == 2
        assert metrics.avg_maintainability_index is not None
