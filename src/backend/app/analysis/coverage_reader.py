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
from pathlib import Path
from xml.etree import ElementTree

_BADGE_PATTERNS = [
    # Badge shields.io/Codecov/Coveralls, ex.: "coverage-87%25-brightgreen" ou "coverage-87%"
    re.compile(r"coverage[-/](\d+(?:\.\d+)?)%(?:25)?", re.IGNORECASE),
    # Menção textual simples, ex.: "Coverage: 87%" ou "87% coverage"
    re.compile(r"coverage[:\s]+(\d+(?:\.\d+)?)%", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)%\s+coverage", re.IGNORECASE),
]


def _parse_coverage_xml(content: str) -> float | None:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return None
    line_rate = root.get("line-rate")
    if line_rate is None:
        return None
    try:
        return float(line_rate) * 100
    except ValueError:
        return None


def _parse_lcov_info(content: str) -> float | None:
    lines_found = lines_hit = 0
    for line in content.splitlines():
        if line.startswith("LF:"):
            lines_found += int(line.removeprefix("LF:"))
        elif line.startswith("LH:"):
            lines_hit += int(line.removeprefix("LH:"))
    if lines_found == 0:
        return None
    return lines_hit / lines_found * 100


def _find_first(root: Path, filename: str) -> Path | None:
    matches = list(root.rglob(filename))
    return matches[0] if matches else None


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
            for name in archive.namelist():
                lower = name.lower()
                if lower.endswith("coverage.xml"):
                    value = _parse_coverage_xml(archive.read(name).decode("utf-8", errors="ignore"))
                    if value is not None:
                        return value
            for name in archive.namelist():
                if name.lower().endswith("lcov.info"):
                    value = _parse_lcov_info(archive.read(name).decode("utf-8", errors="ignore"))
                    if value is not None:
                        return value
    except zipfile.BadZipFile:
        return None
    return None


def read_coverage_percentage(root: Path) -> float | None:
    coverage_xml = _find_first(root, "coverage.xml")
    if coverage_xml is not None:
        value = _parse_coverage_xml(coverage_xml.read_text(encoding="utf-8", errors="ignore"))
        if value is not None:
            return value

    lcov_info = _find_first(root, "lcov.info")
    if lcov_info is not None:
        value = _parse_lcov_info(lcov_info.read_text(encoding="utf-8", errors="ignore"))
        if value is not None:
            return value

    return _read_readme_badge(root)
