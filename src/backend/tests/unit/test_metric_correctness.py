"""Regressões da revisão por pares (issues #92, #93 e #94): a métrica não pode dizer "Conforme"
sem ter medido, nem acusar duplicação em imports/enums, nem contar comentário como código."""

from pathlib import Path

from app.analysis import coupling, duplication, metric_engine
from app.analysis.metrics_catalog import METRICS_CATALOG, ConformityStatus


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestPythonCouplingResolution:
    def test_resolves_imports_when_the_package_is_not_at_the_repository_root(self, tmp_path):
        write(tmp_path, "src/pkg/a.py", "from pkg.b import x\n")
        write(tmp_path, "src/pkg/b.py", "x = 1\n")

        # a depende de b (I=1) e b é dependência de a (I=0): média 0,5. Antes dava 0,0.
        assert coupling.calculate_average_instability(tmp_path, ["python"]) == 0.5

    def test_resolves_absolute_imports_in_the_real_softmeter_layout(self, tmp_path):
        write(tmp_path, "src/backend/app/__init__.py", "")
        write(tmp_path, "src/backend/app/core/__init__.py", "")
        write(tmp_path, "src/backend/app/core/config.py", "settings = 1\n")
        write(tmp_path, "src/backend/app/api/__init__.py", "")
        write(tmp_path, "src/backend/app/api/auth.py", "from app.core.config import settings\n")

        value = coupling.calculate_average_instability(tmp_path, ["python"])

        assert value is not None and value > 0

    def test_ambiguous_suffix_is_ignored_instead_of_guessing(self, tmp_path):
        write(tmp_path, "x/pkg/util.py", "def f(): ...\n")
        write(tmp_path, "y/pkg/util.py", "def f(): ...\n")
        write(tmp_path, "main.py", "from pkg.util import f\n")

        # `pkg.util` existe em dois lugares: nenhuma aresta é criada.
        assert coupling.calculate_average_instability(tmp_path, ["python"]) is None

    def test_a_bare_name_does_not_match_a_nested_module(self, tmp_path):
        write(tmp_path, "pkg/config.py", "x = 1\n")
        write(tmp_path, "main.py", "import config\n")  # `config` externo/outro módulo

        assert coupling.calculate_average_instability(tmp_path, ["python"]) is None

    def test_package_can_be_imported_by_its_bare_name(self, tmp_path):
        write(tmp_path, "src/pkg/__init__.py", "")
        write(tmp_path, "src/main.py", "import pkg\n")

        value = coupling.calculate_average_instability(tmp_path, ["python"])

        assert value == 0.5


class TestCouplingNotAvailable:
    def test_several_modules_and_no_resolved_import_is_not_available(self, tmp_path):
        write(tmp_path, "a.py", "import requests\n")
        write(tmp_path, "b.py", "import json\n")

        assert coupling.calculate_average_instability(tmp_path, ["python"]) is None

    def test_a_single_isolated_module_still_has_zero_coupling(self, tmp_path):
        write(tmp_path, "only.py", "x = 1\n")

        assert coupling.calculate_average_instability(tmp_path, ["python"]) == 0.0

    def test_catalog_classifies_the_missing_value_as_not_available(self):
        definition = METRICS_CATALOG["acoplamento"]

        assert definition.permite_nao_disponivel is True
        assert definition.classificar(None) is ConformityStatus.NAO_DISPONIVEL


class TestTypeScriptAliases:
    TSCONFIG = """{
      // aliases do projeto
      "compilerOptions": {
        "baseUrl": ".",
        "paths": { "@/*": ["src/*"], },   /* vírgula final e comentário */
      },
    }"""

    def test_resolves_the_at_alias_from_tsconfig_with_comments_and_trailing_commas(self, tmp_path):
        write(tmp_path, "tsconfig.json", self.TSCONFIG)
        write(tmp_path, "src/a.ts", "import { b } from '@/b';\nimport { c } from './c';\n")
        write(tmp_path, "src/b.ts", "export const b = 1;\n")
        write(tmp_path, "src/c.ts", "export const c = 1;\n")

        # a->b e a->c: a=1, b=0, c=0 → 0,333. Sem o alias, a->b sumia e dava 0,5.
        assert round(coupling.calculate_average_instability(tmp_path, ["typescript"]) or 0, 3) == 0.333

    def test_resolves_bare_imports_through_base_url(self, tmp_path):
        write(tmp_path, "tsconfig.json", '{"compilerOptions": {"baseUrl": "src"}}')
        write(tmp_path, "src/app.ts", "import { x } from 'lib/util';\n")
        write(tmp_path, "src/lib/util.ts", "export const x = 1;\n")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_uses_the_nearest_tsconfig_in_a_monorepo(self, tmp_path):
        write(tmp_path, "packages/web/tsconfig.json", '{"compilerOptions": {"paths": {"~/*": ["./src/*"]}}}')
        write(tmp_path, "packages/web/src/a.ts", "import { b } from '~/b';\n")
        write(tmp_path, "packages/web/src/b.ts", "export const b = 1;\n")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5

    def test_external_packages_stay_out_of_the_graph(self, tmp_path):
        write(tmp_path, "tsconfig.json", '{"compilerOptions": {"baseUrl": "."}}')
        write(tmp_path, "src/a.ts", "import React from 'react';\n")
        write(tmp_path, "src/b.ts", "export const b = 1;\n")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) is None

    def test_a_broken_tsconfig_is_ignored_without_crashing(self, tmp_path):
        write(tmp_path, "tsconfig.json", "{ isto não é json")
        write(tmp_path, "src/a.ts", "import { b } from './b';\n")
        write(tmp_path, "src/b.ts", "export const b = 1;\n")

        assert coupling.calculate_average_instability(tmp_path, ["typescript"]) == 0.5


class TestDuplicationFalsePositives:
    def test_a_block_of_distinct_imports_is_not_duplication(self, tmp_path):
        modules = ["os", "sys", "json", "re", "math", "time", "uuid", "enum", "typing", "pathlib", "random", "string"]
        write(tmp_path, "imports.py", "\n".join(f"import {name}" for name in modules) + "\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0

    def test_multiline_and_from_imports_are_ignored(self, tmp_path):
        names = ", ".join(f"name{i}" for i in range(12))
        write(tmp_path, "a.py", f"from package import (\n    {names},\n)\nx = 1\n")
        write(tmp_path, "b.py", f"from package import (\n    {names},\n)\ny = 2\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0

    def test_enum_members_are_not_duplication(self, tmp_path):
        members = "\n".join(f"    C{i} = {i}" for i in range(12))
        write(tmp_path, "enums.py", f"from enum import Enum\n\n\nclass Color(Enum):\n{members}\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0

    def test_a_run_of_identical_asserts_is_not_duplication(self, tmp_path):
        asserts = "\n".join(f"    assert value == {i}" for i in range(12))
        write(tmp_path, "test_x.py", f"def test_it(value):\n{asserts}\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0

    def test_javascript_imports_and_requires_are_ignored(self, tmp_path):
        imports = "\n".join(f"import mod{i} from './mod{i}';" for i in range(10))
        requires = "\n".join(f"const lib{i} = require('lib{i}');" for i in range(10))
        write(tmp_path, "a.js", imports + "\n" + requires + "\n")

        assert duplication.calculate_duplication_score(tmp_path, ["javascript"]) == 0.0

    def test_overlapping_windows_in_one_file_do_not_match_each_other(self, tmp_path):
        # Linhas todas iguais: antes, a janela da linha 1 "duplicava" a da linha 2.
        write(tmp_path, "same.py", "def f(x):\n" + "    x += 1\n" * 10 + "    return x\n")

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 0.0


class TestDuplicationStillDetectsRealCopies:
    BLOCK = (
        "def process(items):\n"
        "    total = 0\n"
        "    for item in items:\n"
        "        if item > 10:\n"
        "            total += item * 2\n"
        "        else:\n"
        "            total -= 1\n"
        "    return total\n"
    )

    def test_a_copied_block_across_files_is_detected(self, tmp_path):
        write(tmp_path, "a.py", self.BLOCK)
        write(tmp_path, "b.py", self.BLOCK.replace("items", "values").replace("item", "v"))

        assert duplication.calculate_duplication_score(tmp_path, ["python"]) == 100.0

    def test_a_block_pasted_twice_in_the_same_file_is_detected(self, tmp_path):
        second = self.BLOCK.replace("process", "process_again")
        write(tmp_path, "one.py", self.BLOCK + "\n" + second)

        value = duplication.calculate_duplication_score(tmp_path, ["python"])

        assert value is not None and value > 50


class TestJavaScriptLoc:
    def loc_of(self, tmp_path, code):
        write(tmp_path, "x.js", code)
        return metric_engine.analyze_repository(tmp_path, ["javascript"]).function_loc

    def test_block_comment_lines_inside_a_function_are_not_code(self, tmp_path):
        code = "function f(a) {\n  /*\n  Este bloco explica\n  o que a função faz\n  */\n  return a + 1;\n}\n"

        assert self.loc_of(tmp_path, code) == [3.0]

    def test_a_line_with_code_after_a_comment_still_counts(self, tmp_path):
        code = "function g(a) {\n  /* nota */ return a * 2;\n}\n"

        assert self.loc_of(tmp_path, code) == [3.0]

    def test_a_continuation_line_starting_with_star_is_code(self, tmp_path):
        code = "function h(a, b) {\n  return a\n    * b;\n}\n"

        assert self.loc_of(tmp_path, code) == [4.0]

    def test_line_comments_and_blank_lines_are_not_counted(self, tmp_path):
        code = "function k() {\n  // explica\n\n  return 1; // trailing\n}\n"

        assert self.loc_of(tmp_path, code) == [3.0]

    def test_multiline_template_literal_counts_every_line(self, tmp_path):
        code = "function t() {\n  return `a\nb\nc`;\n}\n"

        assert self.loc_of(tmp_path, code) == [5.0]


class TestMaintainabilityUsesSloc:
    def test_python_feeds_sloc_not_lloc_to_the_formula(self, monkeypatch):
        captured = {}

        def spy(halstead_volume, complexity, sloc):
            captured["sloc"] = sloc
            return 50.0

        monkeypatch.setattr(metric_engine, "compute_maintainability_index", spy)

        # 3 instruções lógicas na mesma linha física: lloc=3, sloc=1.
        metric_engine.analyze_python_file("a = 1; b = 2; c = 3\n", metric_engine.RepoMetrics())

        assert captured["sloc"] == 1

    def test_javascript_ignores_comment_only_lines_in_the_file_sloc(self, monkeypatch):
        captured = {}

        def spy(halstead_volume, complexity, sloc):
            captured["sloc"] = sloc
            return 50.0

        monkeypatch.setattr(metric_engine, "compute_maintainability_index", spy)

        code = "/*\n bloco\n de comentário\n*/\n// linha\nconst x = 1;\n"
        metric_engine.analyze_js_ts_file(code, ".js", metric_engine.RepoMetrics())

        assert captured["sloc"] == 1
