import io
import logging
import zipfile

import httpx
import pytest

from app.core.config import settings
from app.services.github_service import (
    GithubService,
    RepositoryAccessError,
    RepositoryTooLargeError,
    UnsupportedLanguageError,
    parse_repo_url,
)


def _client_with(handler) -> httpx.Client:
    return httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))


class TestParseRepoUrl:
    def test_parses_owner_and_repo(self):
        assert parse_repo_url("https://github.com/octocat/Hello-World") == (
            "octocat",
            "Hello-World",
        )

    def test_strips_trailing_slash_and_git_suffix(self):
        assert parse_repo_url("https://github.com/octocat/Hello-World.git/") == (
            "octocat",
            "Hello-World",
        )

    def test_rejects_invalid_url(self):
        with pytest.raises(ValueError):
            parse_repo_url("https://example.com/not/github")


class TestFetchRepoSizeKb:
    def test_returns_size_in_kb(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"size": 1234})

        service = GithubService(client=_client_with(handler))
        assert service.fetch_repo_size_kb("octocat", "Hello-World") == 1234

    def test_raises_access_error_on_404(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        service = GithubService(client=_client_with(handler))
        with pytest.raises(RepositoryAccessError):
            service.fetch_repo_size_kb("octocat", "missing-repo")


class TestFetchLanguages:
    def test_returns_supported_languages(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"Python": 1000, "HTML": 200})

        service = GithubService(client=_client_with(handler))
        assert service.fetch_languages("octocat", "Hello-World") == ["python"]

    def test_rejects_repository_without_supported_language(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"HTML": 200, "CSS": 100})

        service = GithubService(client=_client_with(handler))
        with pytest.raises(UnsupportedLanguageError):
            service.fetch_languages("octocat", "Hello-World")

    def test_raises_access_error_on_404(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        service = GithubService(client=_client_with(handler))
        with pytest.raises(RepositoryAccessError):
            service.fetch_languages("octocat", "missing-repo")

    def test_raises_access_error_on_403(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403)

        service = GithubService(client=_client_with(handler))
        with pytest.raises(RepositoryAccessError):
            service.fetch_languages("octocat", "private-repo")


class TestDownloadAndExtract:
    def test_extracts_zipball_root_directory(self, tmp_path):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("octocat-Hello-World-abc123/README.md", "# Hello")
            archive.writestr("octocat-Hello-World-abc123/main.py", "print('hi')")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=buffer.getvalue())

        service = GithubService(client=_client_with(handler))
        root = service.download_and_extract("octocat", "Hello-World", tmp_path)

        assert root == tmp_path / "octocat-Hello-World-abc123"
        assert (root / "main.py").read_text() == "print('hi')"

    def test_raises_access_error_when_download_forbidden(self, tmp_path):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        service = GithubService(client=_client_with(handler))
        with pytest.raises(RepositoryAccessError):
            service.download_and_extract("octocat", "missing-repo", tmp_path)


class TestFetchLatestCoverageArtifactZip:
    def test_returns_none_without_token_and_makes_no_request(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", None)

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("não deveria chamar a API sem token configurado")

        service = GithubService(client=_client_with(handler))
        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") is None

    def test_downloads_the_most_recent_non_expired_coverage_artifact(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        zip_bytes = b"PK\x03\x04fake-zip-content"

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/actions/artifacts"):
                return httpx.Response(
                    200,
                    json={
                        "artifacts": [
                            {"id": 1, "name": "build-logs", "expired": False},
                            {"id": 2, "name": "backend-coverage", "expired": True},
                            {"id": 3, "name": "backend-coverage", "expired": False},
                        ]
                    },
                )
            assert request.url.path.endswith("/actions/artifacts/3/zip")
            return httpx.Response(200, content=zip_bytes)

        service = GithubService(client=_client_with(handler))
        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") == zip_bytes

    def test_returns_none_when_no_coverage_artifact_exists(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"artifacts": [{"id": 1, "name": "build-logs", "expired": False}]})

        service = GithubService(client=_client_with(handler))
        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") is None

    def test_returns_none_on_api_error(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        service = GithubService(client=_client_with(handler))
        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") is None


class TestGithubTokenHandling:
    """Token opcional com fallback gracioso: um token inválido não pode piorar o serviço
    em relação a não ter token algum (repositórios públicos funcionam anonimamente)."""

    def test_sends_bearer_token_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "valid-token")
        seen: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers.get("Authorization"))
            return httpx.Response(200, json={"size": 10})

        GithubService(client=_client_with(handler)).fetch_repo_size_kb("octocat", "Hello-World")

        assert seen == ["Bearer valid-token"]

    def test_sends_no_authorization_header_without_token(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", None)
        seen: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers.get("Authorization"))
            return httpx.Response(200, json={"size": 10})

        GithubService(client=_client_with(handler)).fetch_repo_size_kb("octocat", "Hello-World")

        assert seen == [None]

    def test_retries_without_token_when_github_rejects_it(self, monkeypatch, caplog):
        monkeypatch.setattr(settings, "github_token", "expired-secret-token")
        seen: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            auth = request.headers.get("Authorization")
            seen.append(auth)
            if auth:
                return httpx.Response(401, json={"message": "Bad credentials"})
            return httpx.Response(200, json={"Python": 1000})

        service = GithubService(client=_client_with(handler))
        with caplog.at_level(logging.WARNING):
            languages = service.fetch_languages("octocat", "Hello-World")

        assert languages == ["python"]
        assert seen == ["Bearer expired-secret-token", None]
        assert "GITHUB_TOKEN rejeitado" in caplog.text
        assert "expired-secret-token" not in caplog.text

    def test_stops_sending_the_rejected_token_on_later_requests(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "expired-token")
        seen: list[str | None] = []

        def handler(request: httpx.Request) -> httpx.Response:
            auth = request.headers.get("Authorization")
            seen.append(auth)
            if auth:
                return httpx.Response(401)
            return httpx.Response(200, json={"size": 10})

        service = GithubService(client=_client_with(handler))
        service.fetch_repo_size_kb("octocat", "Hello-World")
        service.fetch_repo_size_kb("octocat", "Hello-World")

        assert seen == ["Bearer expired-token", None, None]

    def test_private_repository_still_raises_access_error_after_fallback(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "expired-token")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401 if request.headers.get("Authorization") else 404)

        service = GithubService(client=_client_with(handler))
        with pytest.raises(RepositoryAccessError):
            service.fetch_languages("octocat", "private-repo")

    def test_coverage_artifact_returns_none_when_token_is_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "expired-token")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Bad credentials"})

        service = GithubService(client=_client_with(handler))
        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") is None


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class TestDownloadLimits:
    """Repositório de terceiros é conteúdo não confiável: baixar e extrair tem teto (issue #99)."""

    def test_refuses_a_download_whose_declared_size_is_above_the_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "max_download_mb", 1)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 10, headers={"content-length": str(5 * 1024 * 1024)})

        service = GithubService(client=_client_with(handler))

        with pytest.raises(RepositoryTooLargeError, match="1 MB"):
            service.download_and_extract("octocat", "Hello-World", tmp_path)

    def test_aborts_a_streamed_download_that_outgrows_the_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "max_download_mb", 1)

        def body():
            for _ in range(40):
                yield b"x" * (64 * 1024)  # 2,5 MB sem Content-Length

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body())

        service = GithubService(client=_client_with(handler))

        with pytest.raises(RepositoryTooLargeError):
            service.download_and_extract("octocat", "Hello-World", tmp_path)

    def test_refuses_an_archive_that_expands_beyond_the_cap(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "max_extracted_mb", 1)
        bomb = _zip_bytes({"repo-abc/data.bin": b"\0" * (3 * 1024 * 1024)})  # comprime para poucos KB

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=bomb)

        service = GithubService(client=_client_with(handler))

        with pytest.raises(RepositoryTooLargeError, match="descompactado"):
            service.download_and_extract("octocat", "Hello-World", tmp_path)
        assert not any(tmp_path.iterdir())

    def test_refuses_an_archive_with_too_many_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "max_extracted_files", 3)
        many = _zip_bytes({f"repo-abc/f{index}.py": b"x = 1\n" for index in range(6)})

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=many)

        service = GithubService(client=_client_with(handler))

        with pytest.raises(RepositoryTooLargeError, match="arquivos"):
            service.download_and_extract("octocat", "Hello-World", tmp_path)

    def test_a_normal_archive_still_extracts(self, tmp_path):
        small = _zip_bytes({"repo-abc/main.py": b"x = 1\n"})

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=small)

        service = GithubService(client=_client_with(handler))

        root = service.download_and_extract("octocat", "Hello-World", tmp_path)

        assert (root / "main.py").read_text() == "x = 1\n"

    def test_coverage_artifact_above_the_cap_is_ignored(self, monkeypatch):
        monkeypatch.setattr(settings, "github_token", "fake-token")
        monkeypatch.setattr(settings, "max_artifact_mb", 1)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/actions/artifacts"):
                return httpx.Response(
                    200, json={"artifacts": [{"id": 7, "name": "coverage", "expired": False}]}
                )
            return httpx.Response(200, content=b"x" * (2 * 1024 * 1024))

        service = GithubService(client=_client_with(handler))

        assert service.fetch_latest_coverage_artifact_zip("octocat", "Hello-World") is None
