"""Acoplamento (Instabilidade de Módulo): I = Ce / (Ce + Ca) (research.md item 4).

`Ce` (acoplamento de saída) é o número de outros módulos do próprio repositório que um
arquivo importa; `Ca` (acoplamento de entrada) é o número de módulos do repositório que
importam aquele arquivo. Apenas imports que resolvem a um arquivo do repositório contam
— dependências externas (bibliotecas de terceiros) não fazem parte do grafo de
acoplamento interno que a métrica mede.

Resolução de imports (issue #92):
- Python: o nome pontuado do import é casado com o **sufixo** do caminho dos módulos, então
  funciona em qualquer layout (`src/pkg/a.py`, `backend/app/...`), não só quando o pacote está
  na raiz. Se mais de um módulo casar, o import é ignorado (melhor sem aresta que com aresta errada).
- JS/TS: além de imports relativos, lê `paths`/`baseUrl` do `tsconfig.json`/`jsconfig.json`
  mais próximo (aliases como `@/componentes/Botao`). `extends` não é seguido.

Quando nenhum import interno é resolvido em um repositório com mais de um módulo, o valor é
`None` ("Não disponível"): `0.0` seria indistinguível de "falhei em resolver".
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from app.analysis.limits import check_deadline
from app.analysis.metric_engine import (
    JAVASCRIPT_EXTENSIONS,
    PYTHON_EXTENSIONS,
    TYPESCRIPT_EXTENSIONS,
    iter_source_files,
    parser_for,
    walk_tree,
)

_RELATIVE_IMPORT_PATTERN = re.compile(r"^\.+")
_JS_TS_SUFFIXES = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
_MAX_TSCONFIG_BYTES = 256 * 1024

# Comentários (// e /* */) fora de strings, para ler tsconfig.json (que aceita comentários).
_JSON_COMMENT_PATTERN = re.compile(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', re.DOTALL)
_JSON_TRAILING_COMMA_PATTERN = re.compile(r",(\s*[}\]])")


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
    except (SyntaxError, RecursionError, ValueError):
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


@dataclass
class _PythonModuleIndex:
    exact: dict[str, str]  # nome pontuado a partir da raiz do repositório -> chave do módulo
    by_suffix: dict[str, set[str]]  # sufixo pontuado -> chaves dos módulos que o têm

    @classmethod
    def build(cls, python_files: list[Path], root: Path) -> _PythonModuleIndex:
        exact: dict[str, str] = {}
        by_suffix: dict[str, set[str]] = {}
        for path in python_files:
            key = _module_key(path, root)
            dotted = _python_module_dotted_name(path, root)
            exact[dotted] = key
            parts = dotted.split(".")
            for start in range(len(parts)):
                suffix = ".".join(parts[start:])
                # Sufixo de um segmento só vale para pacotes (`__init__.py`): um nome solto como
                # `config` casaria com módulos de qualquer lugar e criaria arestas falsas.
                if "." in suffix or path.name == "__init__.py":
                    by_suffix.setdefault(suffix, set()).add(key)
        return cls(exact, by_suffix)

    def resolve(self, dotted_name: str) -> str | None:
        parent = dotted_name.rsplit(".", 1)[0] if "." in dotted_name else None
        for candidate in (dotted_name, parent):
            if candidate is None:
                continue
            if candidate in self.exact:
                return self.exact[candidate]
            keys = self.by_suffix.get(candidate)
            if keys is not None and len(keys) == 1:
                return next(iter(keys))
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


@dataclass
class _AliasConfig:
    base_dir: Path | None  # diretório de `baseUrl` (imports "nus" são resolvidos a partir dele)
    paths_base: Path  # diretório a partir do qual os destinos de `paths` são resolvidos
    paths: dict[str, list[str]]


class _TsAliases:
    """Localiza e interpreta o `tsconfig.json`/`jsconfig.json` mais próximo de cada arquivo."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache: dict[Path, _AliasConfig | None] = {}

    def config_for(self, importer: Path) -> _AliasConfig | None:
        directory = importer.parent
        visited: list[Path] = []
        result: _AliasConfig | None = None
        while True:
            if directory in self._cache:
                result = self._cache[directory]
                break
            visited.append(directory)
            found = next(
                (directory / name for name in ("tsconfig.json", "jsconfig.json") if (directory / name).is_file()),
                None,
            )
            if found is not None:
                result = self._load(found)
                break
            if directory == self._root or directory == directory.parent:
                break
            directory = directory.parent
        for visited_directory in visited:
            self._cache[visited_directory] = result
        return result

    @staticmethod
    def _load(config_path: Path) -> _AliasConfig | None:
        try:
            if config_path.stat().st_size > _MAX_TSCONFIG_BYTES:
                return None
            text = config_path.read_text(encoding="utf-8", errors="ignore")
            text = _JSON_COMMENT_PATTERN.sub(lambda match: match.group(1) or "", text)
            text = _JSON_TRAILING_COMMA_PATTERN.sub(r"\1", text)
            options = json.loads(text).get("compilerOptions") or {}
        except (OSError, ValueError, AttributeError):
            return None

        base_url = options.get("baseUrl")
        raw_paths = options.get("paths")
        if not isinstance(base_url, str) and not isinstance(raw_paths, dict):
            return None

        config_dir = config_path.parent
        base_dir = Path(os.path.normpath(config_dir / base_url)) if isinstance(base_url, str) else None
        paths: dict[str, list[str]] = {}
        if isinstance(raw_paths, dict):
            for pattern, targets in raw_paths.items():
                if isinstance(pattern, str) and isinstance(targets, list):
                    paths[pattern] = [target for target in targets if isinstance(target, str)]
        return _AliasConfig(base_dir=base_dir, paths_base=base_dir or config_dir, paths=paths)

    @staticmethod
    def targets_for(source: str, config: _AliasConfig) -> list[Path]:
        targets: list[Path] = []
        for pattern, replacements in config.paths.items():
            if "*" in pattern:
                prefix, suffix = pattern.split("*", 1)
                if source.startswith(prefix) and source.endswith(suffix) and len(source) >= len(prefix) + len(suffix):
                    wildcard = source[len(prefix) : len(source) - len(suffix)]
                    targets += [config.paths_base / item.replace("*", wildcard) for item in replacements]
            elif pattern == source:
                targets += [config.paths_base / item for item in replacements]
        if config.base_dir is not None:
            targets.append(config.base_dir / source)
        return [Path(os.path.normpath(target)) for target in targets]


def _match_module(target: Path, root: Path, modules_by_key: dict[str, str]) -> str | None:
    candidates = [target]
    candidates += [target.with_suffix(suffix) for suffix in _JS_TS_SUFFIXES]
    candidates += [target.parent / f"{target.name}{suffix}" for suffix in _JS_TS_SUFFIXES]
    candidates += [target / f"index{suffix}" for suffix in _JS_TS_SUFFIXES]

    for candidate in candidates:
        try:
            key = _module_key(candidate, root)
        except ValueError:
            continue
        if key in modules_by_key:
            return modules_by_key[key]
    return None


def _resolve_js_ts_import(
    source: str, importer: Path, root: Path, modules_by_key: dict[str, str], aliases: _TsAliases
) -> str | None:
    if _RELATIVE_IMPORT_PATTERN.match(source):
        return _match_module(Path(os.path.normpath(importer.parent / source)), root, modules_by_key)

    # Não relativo: pode ser alias do tsconfig/jsconfig; senão é dependência externa (node_modules).
    config = aliases.config_for(importer)
    if config is None:
        return None
    for target in aliases.targets_for(source, config):
        key = _match_module(target, root, modules_by_key)
        if key is not None:
            return key
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
    python_index = _PythonModuleIndex.build(python_files, root)
    aliases = _TsAliases(root)

    efferent: dict[str, set[str]] = {key: set() for key in modules_by_key.values()}

    for path in python_files:
        check_deadline()
        own_key = _module_key(path, root)
        for dotted_name in _python_imports(path, root):
            target = python_index.resolve(dotted_name)
            if target and target != own_key:
                efferent[own_key].add(target)

    for path in js_ts_files:
        check_deadline()
        own_key = _module_key(path, root)
        for source in _js_ts_import_sources(path):
            target = _resolve_js_ts_import(source, path, root, modules_by_key, aliases)
            if target and target != own_key:
                efferent[own_key].add(target)

    afferent: dict[str, set[str]] = {key: set() for key in modules_by_key.values()}
    for module, targets in efferent.items():
        for target in targets:
            afferent[target].add(module)

    # Módulos sem nenhum acoplamento interno (Ce+Ca=0) são excluídos da média.
    instabilities: list[float] = []
    for key in modules_by_key.values():
        ce, ca = len(efferent[key]), len(afferent[key])
        if ce + ca == 0:
            continue
        instabilities.append(ce / (ce + ca))

    if instabilities:
        return sum(instabilities) / len(instabilities)
    # Um único módulo isolado realmente não tem acoplamento interno (0.0). Com vários módulos e
    # nenhuma aresta resolvida, não dá para distinguir "sem acoplamento" de "não consegui
    # resolver os imports": a métrica fica "Não disponível" em vez de um falso "Conforme".
    return 0.0 if len(modules_by_key) == 1 else None
