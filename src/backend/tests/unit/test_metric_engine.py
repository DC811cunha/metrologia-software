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
