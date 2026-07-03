"""Leitor de artefatos de Cobertura de Testes já publicados no repositório
(research.md item 6) — o SoftMeter não executa a suíte de testes do repositório
analisado, apenas lê relatórios estáticos já existentes.

Ordem de busca: `coverage.xml` (coverage.py/Cobertura) → `lcov.info` (lcov/nyc) →
badge Codecov/Coveralls referenciado no README. Retorna `None` ("Não disponível")
quando nenhum artefato é encontrado.
"""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

_BADGE_PATTERNS = [
    # Badge shields.io/Codecov/Coveralls, ex.: "coverage-87%25-brightgreen" ou "coverage-87%"
    re.compile(r"coverage[-/](\d+(?:\.\d+)?)%(?:25)?", re.IGNORECASE),
    # Menção textual simples, ex.: "Coverage: 87%" ou "87% coverage"
    re.compile(r"coverage[:\s]+(\d+(?:\.\d+)?)%", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)%\s+coverage", re.IGNORECASE),
]


def _find_first(root: Path, filename: str) -> Path | None:
    matches = list(root.rglob(filename))
    return matches[0] if matches else None


def _read_coverage_xml(path: Path) -> float | None:
    try:
        tree = ElementTree.parse(path)
    except ElementTree.ParseError:
        return None
    line_rate = tree.getroot().get("line-rate")
    if line_rate is None:
        return None
    try:
        return float(line_rate) * 100
    except ValueError:
        return None


def _read_lcov_info(path: Path) -> float | None:
    lines_found = lines_hit = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("LF:"):
            lines_found += int(line.removeprefix("LF:"))
        elif line.startswith("LH:"):
            lines_hit += int(line.removeprefix("LH:"))
    if lines_found == 0:
        return None
    return lines_hit / lines_found * 100


def _read_readme_badge(root: Path) -> float | None:
    for name in ("README.md", "readme.md", "Readme.md"):
        path = root / name
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in _BADGE_PATTERNS:
            match = pattern.search(content)
            if match:
                return float(match.group(1))
    return None


def read_coverage_percentage(root: Path) -> float | None:
    coverage_xml = _find_first(root, "coverage.xml")
    if coverage_xml is not None:
        value = _read_coverage_xml(coverage_xml)
        if value is not None:
            return value

    lcov_info = _find_first(root, "lcov.info")
    if lcov_info is not None:
        value = _read_lcov_info(lcov_info)
        if value is not None:
            return value

    return _read_readme_badge(root)
