"""Motor de Complexidade Ciclomática, LOC e Índice de Manutenibilidade.

Radon para Python (research.md item 3); tree-sitter para JavaScript/TypeScript,
aplicando a mesma fórmula documentada no catálogo de métricas (`data-model.md`) para
garantir consistência entre linguagens (Constituição, Princípio V).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from radon.complexity import cc_visit
from radon.metrics import h_visit
from radon.raw import analyze as radon_analyze
from tree_sitter import Language, Node, Parser
import tree_sitter_javascript as ts_javascript
import tree_sitter_typescript as ts_typescript

PYTHON_EXTENSIONS = {".py"}
JAVASCRIPT_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
TYPESCRIPT_EXTENSIONS = {".ts", ".tsx"}

IGNORED_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "vendor",
    ".tox",
    "coverage",
}

FUNCTION_NODE_TYPES = {
    "function_declaration",
    "function_expression",
    "function",
    "arrow_function",
    "method_definition",
    "generator_function",
    "generator_function_declaration",
}

# Pontos de decisão contados para Complexidade Ciclomática (McCabe), seguindo a mesma
# convenção usada por ferramentas de análise estática JS consolidadas (ex.: escomplex):
# if/for/while/case (exceto default)/catch/ternário, somados aos operadores de
# curto-circuito `&&`/`||` (cada um introduz um caminho de execução adicional).
DECISION_NODE_TYPES = {
    "if_statement",
    "for_statement",
    "for_in_statement",
    "for_of_statement",
    "while_statement",
    "do_statement",
    "switch_case",
    "catch_clause",
    "ternary_expression",
}
SHORT_CIRCUIT_OPERATORS = {"&&", "||", "??"}

# Classificação de tokens-folha para o Volume de Halstead (HV = (N1+N2)*log2(n1+n2)):
# operadores = palavras-chave/pontuação com significado sintático; operandos =
# identificadores e literais. Aproximação documentada — não pretende paridade exata
# com ferramentas Halstead nativas de JS, apenas uma definição interna consistente.
_OPERAND_LEAF_TYPES = {
    "identifier",
    "property_identifier",
    "shorthand_property_identifier",
    "shorthand_property_identifier_pattern",
    "private_property_identifier",
    "number",
    "string_fragment",
    "regex_pattern",
    "true",
    "false",
    "null",
    "undefined",
    "this",
}


@dataclass
class RepoMetrics:
    function_complexities: list[float] = field(default_factory=list)
    function_loc: list[float] = field(default_factory=list)
    file_maintainability_index: list[float] = field(default_factory=list)

    def _average(self, values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    @property
    def avg_complexity(self) -> float | None:
        return self._average(self.function_complexities)

    @property
    def avg_loc(self) -> float | None:
        return self._average(self.function_loc)

    @property
    def avg_maintainability_index(self) -> float | None:
        return self._average(self.file_maintainability_index)


def compute_maintainability_index(halstead_volume: float, complexity: float, sloc: float) -> float:
    """MI = 171 − 5.2·ln(HV) − 0.23·CC − 16.2·ln(LOC), normalizado 0–100 (data-model.md)."""
    if halstead_volume <= 0 or sloc <= 0:
        return 100.0
    raw_mi = (
        171
        - 5.2 * math.log(halstead_volume)
        - 0.23 * complexity
        - 16.2 * math.log(sloc)
    )
    return min(max(0.0, raw_mi * 100 / 171.0), 100.0)


def iter_source_files(root: Path, extensions: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in extensions:
            continue
        if IGNORED_DIR_NAMES & set(path.relative_to(root).parts[:-1]):
            continue
        files.append(path)
    return files


def analyze_python_file(code: str, metrics: RepoMetrics) -> None:
    lines = code.splitlines()
    blocks = cc_visit(code)
    for block in blocks:
        metrics.function_complexities.append(float(block.complexity))
        snippet = "\n".join(lines[block.lineno - 1 : block.endline])
        metrics.function_loc.append(float(radon_analyze(snippet).sloc))

    raw = radon_analyze(code)
    halstead_volume = h_visit(code).total.volume
    total_complexity = sum(block.complexity for block in blocks) or 1.0
    sloc = raw.lloc or raw.sloc or 1
    metrics.file_maintainability_index.append(
        compute_maintainability_index(halstead_volume, total_complexity, sloc)
    )


_JS_LANGUAGE = Language(ts_javascript.language())
_TS_LANGUAGE = Language(ts_typescript.language_typescript())
_TSX_LANGUAGE = Language(ts_typescript.language_tsx())


def parser_for(extension: str) -> Parser:
    if extension == ".tsx":
        return Parser(_TSX_LANGUAGE)
    if extension == ".ts":
        return Parser(_TS_LANGUAGE)
    return Parser(_JS_LANGUAGE)


def walk_tree(node: Node):
    yield node
    for child in node.children:
        yield from walk_tree(child)


def _count_decision_points(node: Node, *, is_root: bool = True) -> int:
    """Conta pontos de decisão no subtree de `node`, sem descer em funções aninhadas
    (cada função aninhada é contada separadamente como seu próprio bloco)."""
    if not is_root and node.is_named and node.type in FUNCTION_NODE_TYPES:
        return 0

    count = 0
    if node.type in DECISION_NODE_TYPES:
        count += 1
    elif node.type == "binary_expression":
        if any(c.type in SHORT_CIRCUIT_OPERATORS for c in node.children):
            count += 1

    for child in node.children:
        count += _count_decision_points(child, is_root=False)
    return count


def _function_nodes(root: Node) -> list[Node]:
    return [node for node in walk_tree(root) if node.is_named and node.type in FUNCTION_NODE_TYPES]


def _non_blank_non_comment_line_count(text: str) -> int:
    count = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        count += 1
    return count or 1


def analyze_js_ts_file(code: str, extension: str, metrics: RepoMetrics) -> None:
    code_bytes = code.encode("utf-8")
    parser = parser_for(extension)
    tree = parser.parse(code_bytes)
    root = tree.root_node

    function_nodes = _function_nodes(root)
    for func in function_nodes:
        complexity = 1 + _count_decision_points(func)
        metrics.function_complexities.append(float(complexity))
        snippet = code_bytes[func.start_byte : func.end_byte].decode("utf-8")
        metrics.function_loc.append(float(_non_blank_non_comment_line_count(snippet)))

    total_complexity = (
        sum(1 + _count_decision_points(f) for f in function_nodes)
        if function_nodes
        else 1 + _count_decision_points(root)
    )

    operator_tokens: list[str] = []
    operand_tokens: list[str] = []
    for node in walk_tree(root):
        if node.children:
            continue  # apenas tokens-folha
        text = code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
        if not text.strip():
            continue
        if node.type in _OPERAND_LEAF_TYPES:
            operand_tokens.append(text)
        else:
            operator_tokens.append(node.type)

    n1, n2 = len(set(operator_tokens)), len(set(operand_tokens))
    big_n1, big_n2 = len(operator_tokens), len(operand_tokens)
    vocabulary = n1 + n2
    halstead_volume = (big_n1 + big_n2) * math.log2(vocabulary) if vocabulary > 0 else 0.0

    sloc = _non_blank_non_comment_line_count(code)
    metrics.file_maintainability_index.append(
        compute_maintainability_index(halstead_volume, total_complexity, sloc)
    )


def analyze_repository(root: Path, languages: list[str]) -> RepoMetrics:
    metrics = RepoMetrics()

    if "python" in languages:
        for path in iter_source_files(root, PYTHON_EXTENSIONS):
            try:
                analyze_python_file(path.read_text(encoding="utf-8", errors="ignore"), metrics)
            except SyntaxError:
                continue

    js_ts_extensions: set[str] = set()
    if "javascript" in languages:
        js_ts_extensions |= JAVASCRIPT_EXTENSIONS
    if "typescript" in languages:
        js_ts_extensions |= TYPESCRIPT_EXTENSIONS
    for path in iter_source_files(root, js_ts_extensions):
        analyze_js_ts_file(path.read_text(encoding="utf-8", errors="ignore"), path.suffix, metrics)

    return metrics
