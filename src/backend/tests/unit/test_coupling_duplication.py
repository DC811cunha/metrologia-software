from pathlib import Path

from app.analysis.coupling import calculate_average_instability
from app.analysis.duplication import calculate_duplication_score


def _write(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestCalculateAverageInstability:
    def test_python_module_imported_by_others_has_low_instability(self, tmp_path):
        _write(tmp_path, "pkg/core.py", "def helper():\n    return 1\n")
        _write(tmp_path, "pkg/consumer_a.py", "from pkg import core\n\ncore.helper()\n")
        _write(tmp_path, "pkg/consumer_b.py", "from pkg import core\n\ncore.helper()\n")

        average = calculate_average_instability(tmp_path, ["python"])

        assert average is not None
        assert 0.0 <= average <= 1.0

    def test_isolated_file_has_zero_instability(self, tmp_path):
        # Sem nenhuma aresta de acoplamento interno, a métrica não pode ficar "Não
        # disponível" (regra exclusiva de cobertura_testes) — convenciona-se 0.0.
        _write(tmp_path, "standalone.py", "def foo():\n    return 1\n")

        assert calculate_average_instability(tmp_path, ["python"]) == 0.0

    def test_external_imports_do_not_count_as_internal_coupling(self, tmp_path):
        _write(tmp_path, "app.py", "import os\nimport requests\n\nrequests.get('https://example.com')\n")

        assert calculate_average_instability(tmp_path, ["python"]) == 0.0

    def test_javascript_relative_imports_build_coupling_graph(self, tmp_path):
        _write(tmp_path, "src/utils.js", "export function helper() { return 1; }\n")
        _write(
            tmp_path,
            "src/main.js",
            "import { helper } from './utils.js';\nhelper();\n",
        )

        average = calculate_average_instability(tmp_path, ["javascript"])

        assert average is not None
        assert 0.0 <= average <= 1.0

    def test_returns_none_when_no_eligible_files(self, tmp_path):
        assert calculate_average_instability(tmp_path, ["python"]) is None


class TestCalculateDuplicationScore:
    def test_returns_zero_when_no_duplicated_blocks(self, tmp_path):
        _write(
            tmp_path,
            "a.py",
            "\n".join(
                [
                    "def add(a, b):",
                    "    return a + b",
                    "",
                    "def greet(name):",
                    "    print('hello ' + name)",
                    "    return None",
                    "",
                    "class Counter:",
                    "    def __init__(self):",
                    "        self.value = 0",
                    "",
                    "    def increment(self):",
                    "        self.value += 1",
                    "        return self.value",
                ]
            ),
        )

        score = calculate_duplication_score(tmp_path, ["python"])
        assert score == 0.0

    def test_detects_duplicated_block_across_files(self, tmp_path):
        duplicated_block = "\n".join(
            [
                "def process(items):",
                "    total = 0",
                "    for item in items:",
                "        if item > 0:",
                "            total += item",
                "        else:",
                "            total -= item",
                "    return total",
            ]
        )
        _write(tmp_path, "a.py", duplicated_block)
        _write(tmp_path, "b.py", duplicated_block)

        score = calculate_duplication_score(tmp_path, ["python"])
        assert score > 50.0

    def test_returns_none_when_no_eligible_files(self, tmp_path):
        assert calculate_duplication_score(tmp_path, ["python"]) is None
