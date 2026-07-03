"""Score de Duplicação: detecção de clones Tipo-1/Tipo-2 por shingling de linhas
normalizadas, janela mínima de 6 linhas (research.md item 5).

Cada linha de código significativa (não vazia, não comentário) é normalizada
(identificadores -> `ID`, números -> `NUM`, strings -> `STR`) para que clones Tipo-2
(renomeação de variáveis/literais) ainda sejam detectados. Score = percentual de linhas
que participam de ao menos um bloco de 6+ linhas repetido em outro ponto do repositório
(mesmo arquivo ou arquivo diferente).
"""

from __future__ import annotations

import io
import keyword
import tokenize
from pathlib import Path

from app.analysis.metric_engine import (
    JAVASCRIPT_EXTENSIONS,
    PYTHON_EXTENSIONS,
    TYPESCRIPT_EXTENSIONS,
    iter_source_files,
    parser_for,
    walk_tree,
)

WINDOW_SIZE = 6

_JS_TS_OPERAND_LEAF_TYPES = {
    "identifier",
    "property_identifier",
    "shorthand_property_identifier",
    "private_property_identifier",
    "this",
}
_JS_TS_NUMBER_LEAF_TYPES = {"number"}
_JS_TS_STRING_LEAF_TYPES = {"string_fragment", "regex_pattern"}


def _normalized_lines_python(path: Path) -> dict[int, str]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return {}

    lines: dict[int, list[str]] = {}
    for token in tokens:
        if token.type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            continue
        if token.type == tokenize.COMMENT:
            continue
        text = token.string
        if token.type == tokenize.NAME and not keyword.iskeyword(text):
            normalized = "ID"
        elif token.type == tokenize.NUMBER:
            normalized = "NUM"
        elif token.type == tokenize.STRING:
            normalized = "STR"
        else:
            normalized = text
        lines.setdefault(token.start[0], []).append(normalized)

    return {line: " ".join(parts) for line, parts in lines.items()}


def _normalized_lines_js_ts(path: Path) -> dict[int, str]:
    code = path.read_text(encoding="utf-8", errors="ignore")
    parser = parser_for(path.suffix)
    tree = parser.parse(code.encode("utf-8"))

    lines: dict[int, list[str]] = {}
    for node in walk_tree(tree.root_node):
        if node.children:
            continue
        if node.type == "comment":
            continue
        text = node.text.decode("utf-8", errors="ignore")
        if not text.strip():
            continue
        if node.type in _JS_TS_OPERAND_LEAF_TYPES:
            normalized = "ID"
        elif node.type in _JS_TS_NUMBER_LEAF_TYPES:
            normalized = "NUM"
        elif node.type in _JS_TS_STRING_LEAF_TYPES:
            normalized = "STR"
        else:
            normalized = text
        line = node.start_point[0] + 1
        lines.setdefault(line, []).append(normalized)

    return {line: " ".join(parts) for line, parts in lines.items()}


def calculate_duplication_score(root: Path, languages: list[str]) -> float | None:
    python_files = list(iter_source_files(root, PYTHON_EXTENSIONS)) if "python" in languages else []
    js_ts_extensions: set[str] = set()
    if "javascript" in languages:
        js_ts_extensions |= JAVASCRIPT_EXTENSIONS
    if "typescript" in languages:
        js_ts_extensions |= TYPESCRIPT_EXTENSIONS
    js_ts_files = list(iter_source_files(root, js_ts_extensions)) if js_ts_extensions else []

    all_files = python_files + js_ts_files
    if not all_files:
        return None

    # Por arquivo: lista ordenada de (numero_da_linha, linha_normalizada), apenas linhas
    # com conteúdo (linhas vazias/só-comentário já não geram nenhum token).
    file_lines: dict[Path, list[tuple[int, str]]] = {}
    for path in python_files:
        normalized = _normalized_lines_python(path)
        file_lines[path] = sorted(normalized.items())
    for path in js_ts_files:
        normalized = _normalized_lines_js_ts(path)
        file_lines[path] = sorted(normalized.items())

    total_lines = sum(len(lines) for lines in file_lines.values())
    if total_lines == 0:
        return None

    shingles: dict[tuple[str, ...], list[tuple[Path, tuple[int, ...]]]] = {}
    for path, lines in file_lines.items():
        if len(lines) < WINDOW_SIZE:
            continue
        for start in range(len(lines) - WINDOW_SIZE + 1):
            window = lines[start : start + WINDOW_SIZE]
            key = tuple(text for _, text in window)
            line_numbers = tuple(line for line, _ in window)
            shingles.setdefault(key, []).append((path, line_numbers))

    duplicated: set[tuple[Path, int]] = set()
    for occurrences in shingles.values():
        if len(occurrences) < 2:
            continue
        for path, line_numbers in occurrences:
            duplicated.update((path, line) for line in line_numbers)

    return len(duplicated) / total_lines * 100
