"""Cobertura é "melhor esforço": tenta o artifact de CI do repositório antes dos
artefatos versionados no código-fonte (ver coverage_reader.py)."""

import io
import zipfile

from app.services.analysis_runner import _read_coverage
from app.services.github_service import GithubService


def _zip_with(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class _FakeGithubService(GithubService):
    """Stub que não faz nenhuma chamada de rede real — só devolve o valor configurado."""

    def __init__(self, artifact_zip: bytes | None) -> None:
        self._artifact_zip = artifact_zip

    def fetch_latest_coverage_artifact_zip(self, owner: str, repo: str) -> bytes | None:
        return self._artifact_zip


class TestReadCoverage:
    def test_prefers_ci_artifact_over_versioned_file(self, tmp_path):
        artifact_zip = _zip_with(
            {"coverage.xml": '<?xml version="1.0"?><coverage line-rate="0.95"></coverage>'}
        )
        # Arquivo versionado no repositório diz uma coisa diferente do artifact —
        # o artifact deve vencer, por ser mais provável de existir na prática.
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.1"></coverage>', encoding="utf-8"
        )

        service = _FakeGithubService(artifact_zip=artifact_zip)
        assert _read_coverage(service, "octocat", "Hello-World", tmp_path) == 95.0

    def test_falls_back_to_versioned_file_when_no_artifact(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.6"></coverage>', encoding="utf-8"
        )

        service = _FakeGithubService(artifact_zip=None)
        assert _read_coverage(service, "octocat", "Hello-World", tmp_path) == 60.0

    def test_falls_back_when_artifact_zip_has_no_relevant_file(self, tmp_path):
        artifact_zip = _zip_with({"build.log": "nothing useful here"})
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0"?><coverage line-rate="0.6"></coverage>', encoding="utf-8"
        )

        service = _FakeGithubService(artifact_zip=artifact_zip)
        assert _read_coverage(service, "octocat", "Hello-World", tmp_path) == 60.0

    def test_returns_none_when_nothing_is_available_anywhere(self, tmp_path):
        service = _FakeGithubService(artifact_zip=None)
        assert _read_coverage(service, "octocat", "Hello-World", tmp_path) is None
