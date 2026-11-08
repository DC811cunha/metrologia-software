"""Leitor de artefatos de Cobertura de Testes já publicados (research.md item 6) —
o SoftMeter não executa a suíte de testes do repositório analisado (risco de
execução de código arbitrário de terceiros), apenas lê relatórios estáticos já
existentes, nesta ordem:

1. Artifact de cobertura publicado pelo GitHub Actions do próprio repositório
   (ex.: `backend-coverage`, `frontend-coverage`) — o CI de terceiros já rodou os
   testes; o SoftMeter só baixa o resultado, sem executar nada. Requer
   `settings.github_token` (a API de artifacts exige autenticação mesmo em
   repositórios públicos) e que o artifact ainda não tenha expirado.
2. `coverage.xml` (coverage.py/Cobertura) versionado no repositório.
3. `lcov.info` (lcov/nyc) versionado no repositório.
4. Badge Codecov/Coveralls referenciado no README.

Retorna `None` ("Não disponível") quando nenhuma fonte está acessível — a maioria
dos repositórios públicos não versiona artefato de build nem publica artifact de
cobertura, e isso é esperado, não uma falha.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from app.core.config import settings

_BADGE_PATTERNS = [
    # Badge shields.io/Codecov/Coveralls, ex.: "coverage-87%25-brightgreen" ou "coverage-87%"
    re.compile(r"coverage[-/](\d+(?:\.\d+)?)%(?:25)?", re.IGNORECASE),
    # Menção textual simples, ex.: "Coverage: 87%" ou "87% coverage"
    re.compile(r"coverage[:\s]+(\d+(?:\.\d+)?)%", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)%\s+coverage", re.IGNORECASE),
]


@dataclass(frozen=True)
class _Reading:
    percentage: float
    covered: float | None = None
    total: float | None = None


def _read_coverage_xml(content: str) -> _Reading | None:
    try:
        # defusedxml: o coverage.xml vem de um repositório de terceiros; o parser padrão aceitaria
        # expansão de entidades ("billion laughs") e consumiria CPU/memória sem limite.
        root = ElementTree.fromstring(content)
    except (ParseError, DefusedXmlException):
        return None
    line_rate = root.get("line-rate")
    if line_rate is None:
        return None
    try:
        percentage = float(line_rate) * 100
    except ValueError:
        return None
    try:
        covered, total = float(root.get("lines-covered", "")), float(root.get("lines-valid", ""))
    except ValueError:
        return _Reading(percentage)
    return _Reading(percentage, covered, total) if total > 0 else _Reading(percentage)


def _read_lcov_info(content: str) -> _Reading | None:
    lines_found = lines_hit = 0
    for line in content.splitlines():
        if line.startswith("LF:"):
            lines_found += int(line.removeprefix("LF:"))
        elif line.startswith("LH:"):
            lines_hit += int(line.removeprefix("LH:"))
    if lines_found == 0:
        return None
    return _Reading(lines_hit / lines_found * 100, float(lines_hit), float(lines_found))


def _parse_coverage_xml(content: str) -> float | None:
    reading = _read_coverage_xml(content)
    return reading.percentage if reading else None


def _parse_lcov_info(content: str) -> float | None:
    reading = _read_lcov_info(content)
    return reading.percentage if reading else None


def _combine(readings: list[_Reading]) -> float | None:
    """Monorepo com vários relatórios: soma linhas cobertas e totais (média ponderada). Se algum
    relatório não informa os totais, usa o primeiro (o mais raso — a escolha é determinística)."""
    if not readings:
        return None
    if len(readings) > 1 and all(reading.total for reading in readings):
        total = sum(reading.total or 0 for reading in readings)
        covered = sum(reading.covered or 0 for reading in readings)
        return covered / total * 100
    return readings[0].percentage


def _within_size_cap(size_bytes: int) -> bool:
    return size_bytes <= settings.max_artifact_mb * 1024 * 1024


# Diretórios de dependências/ambientes de terceiros: relatórios de cobertura de dentro deles não são do
# projeto. Lista própria (e não `IGNORED_DIR_NAMES`) porque `coverage/` é justamente onde o `lcov.info` costuma ficar.
_THIRD_PARTY_DIRS = {
    ".git", "node_modules", "bower_components", "__pycache__", ".venv", "venv", "env",
    "site-packages", "vendor", ".tox",
}
_MAX_REPORTS = 20


def _find_all(root: Path, filename: str) -> list[Path]:
    """Relatórios de cobertura do projeto, em ordem estável: caminho mais raso primeiro e depois
    alfabético — nunca a ordem do sistema de arquivos, que variava entre execuções e máquinas."""
    matches = [
        path
        for path in root.rglob(filename)
        if path.is_file() and not _THIRD_PARTY_DIRS & set(path.relative_to(root).parts[:-1])
    ]
    matches.sort(key=lambda path: (len(path.relative_to(root).parts), path.relative_to(root).as_posix()))
    return matches[:_MAX_REPORTS]


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


def read_coverage_from_artifact_zip(zip_bytes: bytes) -> float | None:
    """Procura `coverage.xml`/`lcov.info` dentro de um artifact ZIP já baixado do
    GitHub Actions (ver `GithubService.fetch_latest_coverage_artifact_zip`)."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = sorted(archive.namelist(), key=lambda name: (name.count("/"), name))
            xml_readings = [
                reading
                for name in names
                if name.lower().endswith("coverage.xml") and _within_size_cap(archive.getinfo(name).file_size)
                if (reading := _read_coverage_xml(archive.read(name).decode("utf-8", errors="ignore"))) is not None
            ]
            value = _combine(xml_readings)
            if value is not None:
                return value
            lcov_readings = [
                reading
                for name in names
                if name.lower().endswith("lcov.info") and _within_size_cap(archive.getinfo(name).file_size)
                if (reading := _read_lcov_info(archive.read(name).decode("utf-8", errors="ignore"))) is not None
            ]
            return _combine(lcov_readings)
    except zipfile.BadZipFile:
        return None


def read_coverage_percentage(root: Path) -> float | None:
    xml_readings = [
        reading
        for path in _find_all(root, "coverage.xml")
        if _within_size_cap(path.stat().st_size)
        if (reading := _read_coverage_xml(path.read_text(encoding="utf-8", errors="ignore"))) is not None
    ]
    value = _combine(xml_readings)
    if value is not None:
        return value

    lcov_readings = [
        reading
        for path in _find_all(root, "lcov.info")
        if _within_size_cap(path.stat().st_size)
        if (reading := _read_lcov_info(path.read_text(encoding="utf-8", errors="ignore"))) is not None
    ]
    value = _combine(lcov_readings)
    if value is not None:
        return value

    return _read_readme_badge(root)
