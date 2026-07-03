"""Acoplamento (Instabilidade de Módulo): I = Ce / (Ce + Ca) (research.md item 4).

`Ce` (acoplamento de saída) é o número de outros módulos do próprio repositório que um
arquivo importa; `Ca` (acoplamento de entrada) é o número de módulos do repositório que
importam aquele arquivo. Apenas imports que resolvem a um arquivo do repositório contam
— dependências externas (bibliotecas de terceiros) não fazem parte do grafo de
acoplamento interno que a métrica mede.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from app.analysis.metric_engine import (
    JAVASCRIPT_EXTENSIONS,
    PYTHON_EXTENSIONS,
    TYPESCRIPT_EXTENSIONS,
    parser_for,
    walk_tree,
    iter_source_files,
)

_RELATIVE_IMPORT_PATTERN = re.compile(r"^\.+")


def _module_key(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    return "/".join(relative.parts)


def _python_module_dotted_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _python_imports(path: Path, root: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return set()

    package_parts = list(path.relative_to(root).with_suffix("").parts[:-1])
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                module = node.module or ""
            else:
                base_parts = package_parts[: len(package_parts) - (node.level - 1)] if node.level > 1 else package_parts
                base = ".".join(base_parts)
                module = f"{base}.{node.module}" if node.module else base
            if module:
                imports.add(module)
            for alias in node.names:
                imports.add(f"{module}.{alias.name}" if module else alias.name)
    return imports


def _resolve_python_import(dotted_name: str, modules_by_dotted_name: dict[str, str]) -> str | None:
    if dotted_name in modules_by_dotted_name:
        return modules_by_dotted_name[dotted_name]
    parent = dotted_name.rsplit(".", 1)[0] if "." in dotted_name else None
    if parent and parent in modules_by_dotted_name:
        return modules_by_dotted_name[parent]
    return None


def _js_ts_import_sources(path: Path) -> set[str]:
    code = path.read_text(encoding="utf-8", errors="ignore")
    parser = parser_for(path.suffix)
    tree = parser.parse(code.encode("utf-8"))

    sources: set[str] = set()
    for node in walk_tree(tree.root_node):
        if not node.is_named:
            continue
        if node.type in ("import_statement", "export_statement"):
            string_node = next((c for c in node.children if c.type == "string"), None)
            if string_node is not None:
                sources.add(string_node.text.decode("utf-8").strip("'\"`"))
        elif node.type == "call_expression":
            function_node = node.child_by_field_name("function")
            if function_node is not None and function_node.text == b"require":
                arguments = node.child_by_field_name("arguments")
                if arguments is not None:
                    string_node = next((c for c in arguments.children if c.type == "string"), None)
                    if string_node is not None:
                        sources.add(string_node.text.decode("utf-8").strip("'\"`"))
    return sources


def _resolve_js_ts_import(source: str, importer: Path, root: Path, modules_by_key: dict[str, str]) -> str | None:
    if not _RELATIVE_IMPORT_PATTERN.match(source):
        return None  # dependência externa (node_modules) — fora do grafo interno

    target = (importer.parent / source).resolve()
    candidates = [target]
    suffixes = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
    candidates += [target.with_suffix(suffix) for suffix in suffixes]
    candidates += [target / f"index{suffix}" for suffix in suffixes]

    for candidate in candidates:
        try:
            key = _module_key(candidate, root)
        except ValueError:
            continue
        if key in modules_by_key:
            return modules_by_key[key]
    return None


def calculate_average_instability(root: Path, languages: list[str]) -> float | None:
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

    modules_by_key = {_module_key(path, root): _module_key(path, root) for path in all_files}
    modules_by_dotted_name = {
        _python_module_dotted_name(path, root): _module_key(path, root) for path in python_files
    }

    efferent: dict[str, set[str]] = {key: set() for key in modules_by_key.values()}

    for path in python_files:
        own_key = _module_key(path, root)
        for dotted_name in _python_imports(path, root):
            target = _resolve_python_import(dotted_name, modules_by_dotted_name)
            if target and target != own_key:
                efferent[own_key].add(target)

    for path in js_ts_files:
        own_key = _module_key(path, root)
        for source in _js_ts_import_sources(path):
            target = _resolve_js_ts_import(source, path, root, modules_by_key)
            if target and target != own_key:
                efferent[own_key].add(target)

    afferent: dict[str, set[str]] = {key: set() for key in modules_by_key.values()}
    for module, targets in efferent.items():
        for target in targets:
            afferent[target].add(module)

    # Módulos sem nenhum acoplamento interno (Ce+Ca=0) são excluídos da média — a métrica
    # do catálogo não permite "Não disponível" (apenas cobertura_testes permite), então um
    # repositório sem nenhuma aresta de acoplamento interno (ex.: um único arquivo isolado)
    # é tratado como instabilidade 0.0 (sem acoplamento = máxima estabilidade).
    instabilities: list[float] = []
    for key in modules_by_key.values():
        ce, ca = len(efferent[key]), len(afferent[key])
        if ce + ca == 0:
            continue
        instabilities.append(ce / (ce + ca))

    return sum(instabilities) / len(instabilities) if instabilities else 0.0
