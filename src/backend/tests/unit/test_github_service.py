import io
import zipfile

import httpx
import pytest

from app.core.config import settings
from app.services.github_service import (
    GithubService,
    RepositoryAccessError,
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
