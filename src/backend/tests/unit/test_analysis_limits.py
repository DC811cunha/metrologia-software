import pytest

from app.analysis import limits, metric_engine
from app.analysis.limits import AnalysisTimeoutError, analysis_deadline, check_deadline
from app.core.config import settings


class TestDeadline:
    def test_is_a_no_op_without_a_deadline(self):
        check_deadline()

    def test_passes_before_the_deadline(self):
        with analysis_deadline(60):
            check_deadline()

    def test_raises_after_the_deadline_with_a_clear_message(self, monkeypatch):
        clock = {"now": 100.0}
        monkeypatch.setattr(limits.time, "monotonic", lambda: clock["now"])

        with analysis_deadline(300):
            clock["now"] += 301
            with pytest.raises(AnalysisTimeoutError, match="300 s"):
                check_deadline()

    def test_deadline_does_not_leak_outside_the_context(self, monkeypatch):
        clock = {"now": 100.0}
        monkeypatch.setattr(limits.time, "monotonic", lambda: clock["now"])
        with analysis_deadline(1):
            pass

        clock["now"] += 1000
        check_deadline()


class TestSourceFileLimits:
    def test_files_above_the_size_cap_are_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "max_source_file_kb", 1)
        (tmp_path / "small.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "huge.py").write_text("x = 1\n" * 1000, encoding="utf-8")

        files = metric_engine.iter_source_files(tmp_path, {".py"})

        assert [path.name for path in files] == ["small.py"]

    def test_file_discovery_honours_the_deadline(self, tmp_path, monkeypatch):
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        clock = {"now": 100.0}
        monkeypatch.setattr(limits.time, "monotonic", lambda: clock["now"])

        with analysis_deadline(10):
            clock["now"] += 11
            with pytest.raises(AnalysisTimeoutError):
                metric_engine.iter_source_files(tmp_path, {".py"})


class TestDeepNesting:
    def test_deeply_nested_javascript_does_not_crash_the_analysis(self, tmp_path):
        depth = 4000
        (tmp_path / "gen.js").write_text(
            "function f() { return " + "(" * depth + "1" + ")" * depth + "; }\n", encoding="utf-8"
        )
        (tmp_path / "ok.js").write_text("function g(a) { if (a) { return 1; } return 2; }\n", encoding="utf-8")

        metrics = metric_engine.analyze_repository(tmp_path, ["javascript"])

        # O arquivo patológico pode ser ignorado, mas a análise segue e mede os demais.
        assert metrics.avg_complexity is not None

    def test_walk_tree_is_iterative_and_visits_every_node_in_preorder(self):
        parser = metric_engine.parser_for(".js")
        tree = parser.parse(b"function f(a) { return a + 1; }")

        types = [node.type for node in metric_engine.walk_tree(tree.root_node)]

        assert types[0] == "program"
        assert "function_declaration" in types
        assert types.index("function_declaration") < types.index("return_statement")
