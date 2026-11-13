"""Erros do GitHub (issues #90 e #91): cota esgotada e indisponibilidade são TEMPORÁRIAS e não podem
virar "repositório inacessível" nem erro 500; só 403/404/451 sem sinal de limite são acesso negado."""

import time

import httpx
import pytest

from app.services.github_service import (
    GithubRateLimitError,
    GithubService,
    GithubUnavailableError,
    RepositoryAccessError,
)


def service_with(handler) -> GithubService:
    return GithubService(
        client=httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    )


def respond(status: int, headers: dict | None = None, json: dict | None = None):
    return lambda request: httpx.Response(status, headers=headers or {}, json=json)


class TestRateLimitIsNotInaccessible:
    def test_primary_limit_is_recognised_by_the_remaining_header(self):
        reset = str(int(time.time()) + 600)
        handler = respond(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset}, {"message": "rate limit exceeded"})

        with pytest.raises(GithubRateLimitError) as error:
            service_with(handler).fetch_repo_size_kb("o", "r")

        assert error.value.retry_after is not None and 595 <= error.value.retry_after <= 600

    def test_secondary_limit_is_recognised_by_retry_after(self):
        handler = respond(403, {"retry-after": "90"}, {"message": "secondary rate limit"})

        with pytest.raises(GithubRateLimitError) as error:
            service_with(handler).fetch_languages("o", "r")

        assert error.value.retry_after == 90

    def test_a_403_whose_message_mentions_the_rate_limit_is_a_limit(self):
        handler = respond(403, {}, {"message": "You have exceeded a secondary rate limit. Please wait."})

        with pytest.raises(GithubRateLimitError):
            service_with(handler).fetch_repo_size_kb("o", "r")

    def test_429_is_a_rate_limit(self):
        with pytest.raises(GithubRateLimitError) as error:
            service_with(respond(429, {"retry-after": "30"})).fetch_repo_size_kb("o", "r")

        assert error.value.retry_after == 30

    def test_without_any_hint_the_wait_is_unknown(self):
        with pytest.raises(GithubRateLimitError) as error:
            service_with(respond(429)).fetch_repo_size_kb("o", "r")

        assert error.value.retry_after is None

    def test_the_limit_is_also_recognised_while_downloading_the_zipball(self, tmp_path):
        handler = respond(403, {"x-ratelimit-remaining": "0"}, {"message": "API rate limit exceeded"})

        with pytest.raises(GithubRateLimitError):
            service_with(handler).download_and_extract("o", "r", tmp_path)


class TestRealAccessDenialStillMeansInaccessible:
    @pytest.mark.parametrize("status", [404, 451])
    def test_missing_or_legally_blocked_repository(self, status):
        with pytest.raises(RepositoryAccessError):
            service_with(respond(status)).fetch_repo_size_kb("o", "r")

    def test_a_plain_403_without_limit_signals_is_access_denied(self):
        with pytest.raises(RepositoryAccessError):
            service_with(respond(403, {}, {"message": "Repository access blocked"})).fetch_repo_size_kb("o", "r")

    def test_the_message_for_the_zipball_says_download(self, tmp_path):
        with pytest.raises(RepositoryAccessError, match="para download"):
            service_with(respond(404)).download_and_extract("o", "r", tmp_path)


class TestNetworkAndServerFailures:
    @pytest.mark.parametrize("status", [500, 502, 503, 504])
    def test_server_errors_are_unavailability(self, status):
        with pytest.raises(GithubUnavailableError, match=str(status)):
            service_with(respond(status)).fetch_repo_size_kb("o", "r")

    def test_an_unexpected_status_is_unavailability_not_a_raw_httpx_error(self):
        with pytest.raises(GithubUnavailableError):
            service_with(respond(418)).fetch_languages("o", "r")

    def test_timeout_is_unavailability(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout", request=request)

        with pytest.raises(GithubUnavailableError, match="ReadTimeout"):
            service_with(handler).fetch_repo_size_kb("o", "r")

    def test_connection_refused_is_unavailability(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sem rede", request=request)

        with pytest.raises(GithubUnavailableError, match="ConnectError"):
            service_with(handler).fetch_languages("o", "r")

    def test_a_failure_in_the_middle_of_the_zipball_download_is_unavailability(self, tmp_path):
        class Broken(httpx.SyncByteStream):
            def __iter__(self):
                yield b"PK\x03\x04partial"
                raise httpx.ReadError("conexão interrompida")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, stream=Broken())

        with pytest.raises(GithubUnavailableError):
            service_with(handler).download_and_extract("o", "r", tmp_path)

    def test_coverage_artifacts_stay_best_effort_and_never_raise(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "github_token", "fake-token")

        for handler in (respond(503), respond(403, {"x-ratelimit-remaining": "0"})):
            assert service_with(handler).fetch_latest_coverage_artifact_zips("o", "r") == []

        def down(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sem rede", request=request)

        assert service_with(down).fetch_latest_coverage_artifact_zips("o", "r") == []


class TestRenamedOrTransferredRepositories:
    """O GitHub responde 301 para repositórios renomeados/transferidos: o SoftMeter precisa segui-lo,
    em vez de tratar o 301 como "GitHub indisponível" (caso real: Viaje-Mais -> NomadPlan)."""

    def test_follows_a_301_to_the_new_location(self):
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            if request.url.path == "/repos/old-owner/old-name":
                return httpx.Response(301, headers={"location": "https://api.github.com/repositories/123"})
            return httpx.Response(200, json={"size": 4321})

        assert service_with(handler).fetch_repo_size_kb("old-owner", "old-name") == 4321
        assert seen == ["/repos/old-owner/old-name", "/repositories/123"]

    def test_the_languages_endpoint_follows_redirects_too(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/o/old/languages":
                return httpx.Response(301, headers={"location": "https://api.github.com/repositories/9/languages"})
            return httpx.Response(200, json={"Python": 100})

        assert service_with(handler).fetch_languages("o", "old") == ["python"]

    def test_the_zipball_of_a_renamed_repository_downloads(self, tmp_path):
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("repo-abc/main.py", "x = 1\n")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/o/old/zipball/HEAD":
                return httpx.Response(301, headers={"location": "https://api.github.com/repositories/9/zipball/HEAD"})
            if request.url.path == "/repositories/9/zipball/HEAD":
                return httpx.Response(302, headers={"location": "https://codeload.github.com/o/new/legacy.zip/HEAD"})
            return httpx.Response(200, content=buffer.getvalue())

        root = service_with(handler).download_and_extract("o", "old", tmp_path)

        assert (root / "main.py").read_text() == "x = 1\n"

    def test_the_token_is_not_sent_to_another_origin_after_a_redirect(self, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "github_token", "secret-token")
        auth_by_host: dict[str, str | None] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            auth_by_host[request.url.host] = request.headers.get("authorization")
            if request.url.host == "api.github.com":
                return httpx.Response(302, headers={"location": "https://codeload.github.com/zip"})
            return httpx.Response(200, json={"size": 1})

        service_with(handler).fetch_repo_size_kb("o", "r")

        assert auth_by_host["api.github.com"] == "Bearer secret-token"
        assert auth_by_host["codeload.github.com"] is None

    def test_a_redirect_loop_is_unavailability_and_not_a_server_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(301, headers={"location": "https://api.github.com/repos/o/r"})

        with pytest.raises(GithubUnavailableError, match="TooManyRedirects"):
            service_with(handler).fetch_repo_size_kb("o", "r")

    def test_a_404_after_the_redirect_is_still_an_inaccessible_repository(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/repos/o/old":
                return httpx.Response(301, headers={"location": "https://api.github.com/repositories/9"})
            return httpx.Response(404)

        with pytest.raises(RepositoryAccessError):
            service_with(handler).fetch_repo_size_kb("o", "old")
