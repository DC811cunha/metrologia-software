"""Motor de Complexidade Ciclomática, LOC e Índice de Manutenibilidade.

Radon para Python (research.md item 3); tree-sitter para JavaScript/TypeScript,
aplicando a mesma fórmula documentada no catálogo de métricas (`data-model.md`) para
garantir consistência entre linguagens (Constituição, Princípio V).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from radon.complexity import cc_visit
from radon.metrics import h_visit
from radon.raw import analyze as radon_analyze
from tree_sitter import Language, Node, Parser
import tree_sitter_javascript as ts_javascript
import tree_sitter_typescript as ts_typescript

from app.analysis.limits import check_deadline
from app.core.config import settings

PYTHON_EXTENSIONS = {".py"}
JAVASCRIPT_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
TYPESCRIPT_EXTENSIONS = {".ts", ".tsx"}

# Diretórios que nunca são código autoral: dependências, ambientes virtuais, caches e saídas de framework.
IGNORED_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "site-packages",
    "bower_components",
    ".next",
    ".nuxt",
    "vendor",
    ".tox",
    "migrations",
}

# Nomes AMBÍGUOS: costumam ser saída de build (`build/`, `dist/`, `out/`, `target/`, `coverage/`), mas também
# podem ser um pacote de código (`src/build/` de uma ferramenta de build, `app/out/`). Só são podados quando há
# evidência de que são saída: estão na raiz do repositório ou ao lado de um manifesto de projeto. `env/` só é
# podado se for de fato um ambiente virtual (tem `pyvenv.cfg`). Os arquivos gerados que sobrarem ainda são
# filtrados por nome/forma (`*.min.js`, `*.d.ts`, bundles minificados).
OUTPUT_DIR_NAMES = {"dist", "build", "out", "target", "coverage"}
PROJECT_MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "tsconfig.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Cargo.toml",
}

# O SoftMeter mede o código de produção: testes ficam de fora de CC, LOC, MI, acoplamento e
# duplicação (testes repetem estrutura por natureza e, no grafo de imports, só importam — o que
# infla a instabilidade média). A cobertura de testes continua sendo lida normalmente.
TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs", "e2e", "__mocks__"}
_TEST_FILE_INFIXES = (".test.", ".spec.")
# Arquivos gerados: declarações de tipos e bundles minificados.
_GENERATED_SUFFIXES = (".min.js", ".min.mjs", ".min.cjs", ".d.ts", ".d.mts", ".d.cts", ".bundle.js")
_MINIFIED_MIN_BYTES = 2000
_MINIFIED_AVG_LINE_LENGTH = 200


class NoAnalyzableSourceError(Exception):
    """Nenhum arquivo-fonte restou depois de excluir testes, dependências e arquivos gerados."""


def is_test_file(relative: Path) -> bool:
    name = relative.name
    if TEST_DIR_NAMES & set(relative.parts[:-1]):
        return True
    if name == "conftest.py" or (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py"):
        return True
    return any(infix in name for infix in _TEST_FILE_INFIXES)


def _looks_minified(path: Path) -> bool:
    """Heurística de bundle minificado sem o sufixo `.min.`: poucas linhas e muito longas."""
    try:
        if path.stat().st_size < _MINIFIED_MIN_BYTES:
            return False
        with path.open("rb") as handle:
            sample = handle.read(64 * 1024)
    except OSError:
        return False
    return len(sample) / (sample.count(b"\n") + 1) > _MINIFIED_AVG_LINE_LENGTH

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
    # SLOC de cada arquivo (mesma ordem de `file_maintainability_index`): peso da média do MI.
    file_sloc: list[float] = field(default_factory=list)

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
        """Média do MI dos arquivos **ponderada pelas linhas de código** (ADR-015): um arquivo de uma linha
        (um `__init__.py`, uma constante) não pode pesar o mesmo que um módulo de 500 linhas e inflar a média."""
        total_weight = sum(self.file_sloc)
        if len(self.file_sloc) != len(self.file_maintainability_index) or total_weight <= 0:
            return self._average(self.file_maintainability_index)
        weighted = sum(mi * weight for mi, weight in zip(self.file_maintainability_index, self.file_sloc, strict=True))
        return weighted / total_weight


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
    max_bytes = settings.max_source_file_kb * 1024
    # Diretórios de dependências, gerados e de teste são podados ANTES de descer neles (antes, `rglob` percorria
    # `node_modules` inteiro só para descartar cada arquivo depois), e a ordem é alfabética: a mesma em qualquer
    # máquina, sem depender da ordem do sistema de arquivos.
    pruned = IGNORED_DIR_NAMES | TEST_DIR_NAMES
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        check_deadline()
        current = Path(dirpath)
        has_manifest = current == root or any(name in PROJECT_MANIFESTS for name in filenames)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in pruned
            and not (name in OUTPUT_DIR_NAMES and has_manifest)
            and not (name == "env" and (current / name / "pyvenv.cfg").is_file())
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.suffix not in extensions or not path.is_file():
                continue
            relative = path.relative_to(root)
            if is_test_file(relative):
                continue
            if path.name.endswith(_GENERATED_SUFFIXES) or (path.suffix in JAVASCRIPT_EXTENSIONS | TYPESCRIPT_EXTENSIONS and _looks_minified(path)):
                continue
            # Arquivo enorme é quase sempre gerado/minificado/dados: custo alto e valor ~nulo.
            if path.stat().st_size > max_bytes:
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
    # SLOC (e não `lloc`): é a convenção documentada no catálogo e a mesma usada em JS/TS, para
    # que o mesmo código renda o mesmo índice nas duas linguagens (Princípio V).
    sloc = raw.sloc or 1
    metrics.file_maintainability_index.append(
        compute_maintainability_index(halstead_volume, total_complexity, sloc)
    )
    metrics.file_sloc.append(float(sloc))


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
    """Percorre a árvore em pré-ordem de forma iterativa: a versão recursiva estourava o limite de
    recursão do Python em arquivos com aninhamento muito profundo."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


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


def _code_line_count(node: Node) -> int:
    """SLOC de um nó: linhas físicas que contêm ao menos um token que não seja comentário.

    Usa os nós `comment` do tree-sitter em vez de olhar o primeiro caractere da linha: assim
    linhas internas de um comentário de bloco não contam como código, e uma linha como
    `/* nota */ return x;` conta (tem código). Mesma convenção do `sloc` do radon no Python.
    """
    rows: set[int] = set()
    for current in walk_tree(node):
        if current.children or current.type == "comment" or current.start_byte == current.end_byte:
            continue
        rows.update(range(current.start_point[0], current.end_point[0] + 1))
    return len(rows) or 1


def analyze_js_ts_file(code: str, extension: str, metrics: RepoMetrics) -> None:
    code_bytes = code.encode("utf-8")
    parser = parser_for(extension)
    tree = parser.parse(code_bytes)
    root = tree.root_node

    function_nodes = _function_nodes(root)
    for func in function_nodes:
        complexity = 1 + _count_decision_points(func)
        metrics.function_complexities.append(float(complexity))
        metrics.function_loc.append(float(_code_line_count(func)))

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

    sloc = _code_line_count(root)
    metrics.file_maintainability_index.append(
        compute_maintainability_index(halstead_volume, total_complexity, sloc)
    )
    metrics.file_sloc.append(float(sloc))


def analyze_repository(root: Path, languages: list[str]) -> RepoMetrics:
    metrics = RepoMetrics()
    found_files = 0   # arquivos-fonte candidatos (depois de excluir testes, dependências e gerados)
    parsed_files = 0  # os que puderam ser interpretados

    if "python" in languages:
        for path in iter_source_files(root, PYTHON_EXTENSIONS):
            check_deadline()
            found_files += 1
            try:
                analyze_python_file(path.read_text(encoding="utf-8", errors="ignore"), metrics)
            except (SyntaxError, RecursionError, ValueError):
                continue  # ex.: Python 2 ou arquivo corrompido: ignora só este arquivo
            parsed_files += 1

    js_ts_extensions: set[str] = set()
    if "javascript" in languages:
        js_ts_extensions |= JAVASCRIPT_EXTENSIONS
    if "typescript" in languages:
        js_ts_extensions |= TYPESCRIPT_EXTENSIONS
    for path in iter_source_files(root, js_ts_extensions):
        check_deadline()
        found_files += 1
        try:
            analyze_js_ts_file(path.read_text(encoding="utf-8", errors="ignore"), path.suffix, metrics)
        except RecursionError:
            # Expressões aninhadas em excesso: ignora só este arquivo, não a análise inteira.
            continue
        parsed_files += 1

    if found_files == 0:
        raise NoAnalyzableSourceError(
            "nenhum arquivo-fonte restou depois de excluir testes, dependências e arquivos gerados"
        )
    if parsed_files == 0:
        raise NoAnalyzableSourceError(
            "nenhum arquivo-fonte pôde ser interpretado (sintaxe inválida, código Python 2 ou arquivos corrompidos)"
        )
    if not metrics.function_complexities:
        # Complexidade e LOC são médias por função: sem nenhuma função/método a média não existe, e uma
        # métrica sem valor não pode compor o laudo (Princípio V) — melhor dizer isso do que falhar mais adiante.
        raise NoAnalyzableSourceError(
            "nenhuma função ou método encontrado no código de produção (o repositório só tem constantes, "
            "configuração ou declarações), então não há o que medir em complexidade e LOC"
        )
    return metrics
