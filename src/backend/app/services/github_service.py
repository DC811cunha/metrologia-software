"""Integração com a API pública do GitHub (research.md itens 1-2).

Detecção de linguagem via `GET /repos/{owner}/{repo}/languages` (FR-002) e ingestão de
código-fonte via download do zipball (sem exigir o binário `git` no worker).
"""

import logging
import re
import tempfile
import zipfile
from pathlib import Path
from typing import IO, Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"

# Linguagens suportadas pelo motor de métricas (FR-002); chaves como reportadas pela API
# `languages` do GitHub, mapeadas para a chave normalizada usada internamente.
SUPPORTED_LANGUAGES = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
}


class GithubServiceError(Exception):
    """Erro base de integração com o GitHub."""


class RepositoryAccessError(GithubServiceError):
    """Repositório inexistente, privado ou inacessível (FR-014)."""


class RepositoryTooLargeError(GithubServiceError):
    """Repositório (ou artifact) acima dos limites de tamanho aceitos para análise (issue #99)."""


class UnsupportedLanguageError(GithubServiceError):
    """Repositório não contém nenhuma linguagem suportada (FR-002)."""


_URL_PATTERN = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$"
)


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extrai `(owner, repo)` de uma URL pública do GitHub."""
    match = _URL_PATTERN.match(url.strip())
    if match is None:
        raise ValueError(f"URL de repositório GitHub inválida: '{url}'")
    return match.group("owner"), match.group("repo")


class GithubService:
    def __init__(self, client: httpx.Client | None = None) -> None:
        # O token vai por requisição (não como header fixo do client) para poder ser
        # descartado quando o GitHub o rejeitar — ver `_get`.
        self._token: str | None = settings.github_token or None
        self._client = client or httpx.Client(
            base_url=GITHUB_API_URL,
            headers={"Accept": "application/vnd.github+json"},
            timeout=10.0,
        )

    def _send(self, url: str, headers: dict[str, str] | None, stream: bool, **kwargs: Any) -> httpx.Response:
        follow_redirects = kwargs.pop("follow_redirects", False)
        request = self._client.build_request("GET", url, headers=headers, params=kwargs.pop("params", None))
        return self._client.send(request, stream=stream, follow_redirects=follow_redirects)

    def _get(self, url: str, *, stream: bool = False, **kwargs: Any) -> httpx.Response:
        """GET com `GITHUB_TOKEN` quando configurado e fallback gracioso: se o GitHub
        rejeitar o token (401 — expirado ou revogado), repete a requisição sem
        credenciais e deixa de enviar o token nas chamadas seguintes desta instância.

        Sem isso, um token inválido deixaria o serviço *pior* do que sem token algum —
        repositórios públicos continuam acessíveis anonimamente (60 req/h). Mesmo
        princípio de "fallback gracioso" do ADR-004: configuração opcional nunca
        quebra o fluxo principal.
        """
        if self._token:
            response = self._send(url, {"Authorization": f"Bearer {self._token}"}, stream, **kwargs)
            if response.status_code != 401:
                return response
            response.close()
            logger.warning(
                "GITHUB_TOKEN rejeitado pelo GitHub (401: expirado ou revogado) — "
                "seguindo sem autenticação; gere um token novo para restaurar o limite maior."
            )
            self._token = None
        return self._send(url, None, stream, **kwargs)

    def fetch_repo_size_kb(self, owner: str, repo: str) -> int:
        """Tamanho do repositório em KB (metadado leve, sem precisar baixar o zipball) —
        usado como heurística de orçamento síncrono/assíncrono (research.md item 7)."""
        response = self._get(f"/repos/{owner}/{repo}")
        if response.status_code in (404, 403):
            raise RepositoryAccessError(f"Repositório '{owner}/{repo}' inacessível")
        response.raise_for_status()
        return int(response.json()["size"])

    def fetch_languages(self, owner: str, repo: str) -> list[str]:
        """Consulta as linguagens do repositório e valida contra FR-002."""
        response = self._get(f"/repos/{owner}/{repo}/languages")
        if response.status_code in (404, 403):
            raise RepositoryAccessError(f"Repositório '{owner}/{repo}' inacessível")
        response.raise_for_status()

        detected = response.json()
        supported = [
            SUPPORTED_LANGUAGES[lang] for lang in detected if lang in SUPPORTED_LANGUAGES
        ]
        if not supported:
            raise UnsupportedLanguageError(
                f"Repositório '{owner}/{repo}' não contém Python, JavaScript ou TypeScript"
            )
        return supported

    def _read_capped(self, response: httpx.Response, max_bytes: int, what: str) -> IO[bytes]:
        """Lê o corpo em streaming para um arquivo temporário (que só vai ao disco se passar de
        8 MB), abortando assim que o teto é ultrapassado — sem carregar tudo em memória."""
        declared = response.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > max_bytes:
            raise RepositoryTooLargeError(f"{what} acima do limite de {max_bytes // (1024 * 1024)} MB")

        buffer = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)  # noqa: SIM115
        total = 0
        try:
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise RepositoryTooLargeError(f"{what} acima do limite de {max_bytes // (1024 * 1024)} MB")
                buffer.write(chunk)
        except BaseException:
            buffer.close()
            raise
        buffer.seek(0)
        return buffer

    def download_and_extract(self, owner: str, repo: str, dest_dir: Path) -> Path:
        """Baixa o zipball padrão do repositório e extrai em `dest_dir`, respeitando limites de
        tamanho baixado, de tamanho descompactado e de número de arquivos (issue #99).

        Retorna o caminho da pasta raiz extraída (o GitHub empacota tudo sob um único
        diretório `{owner}-{repo}-{sha}/`).
        """
        response = self._get(f"/repos/{owner}/{repo}/zipball/HEAD", stream=True, follow_redirects=True)
        try:
            if response.status_code in (404, 403):
                raise RepositoryAccessError(f"Repositório '{owner}/{repo}' inacessível para download")
            response.raise_for_status()
            buffer = self._read_capped(response, settings.max_download_mb * 1024 * 1024, "Download do repositório")
        finally:
            response.close()

        with buffer, zipfile.ZipFile(buffer) as archive:
            entries = archive.infolist()
            if len(entries) > settings.max_extracted_files:
                raise RepositoryTooLargeError(
                    f"Repositório com mais de {settings.max_extracted_files} arquivos"
                )
            if sum(entry.file_size for entry in entries) > settings.max_extracted_mb * 1024 * 1024:
                raise RepositoryTooLargeError(
                    f"Conteúdo descompactado acima do limite de {settings.max_extracted_mb} MB"
                )
            archive.extractall(dest_dir)
            root_entry = archive.namelist()[0].split("/")[0]
        return dest_dir / root_entry

    def fetch_latest_coverage_artifact_zips(self, owner: str, repo: str) -> list[bytes]:
        """Baixa os artifacts de cobertura do run de CI mais recente do repositório (research.md
        item 6) — o CI de terceiros já rodou os testes; isto só lê o resultado, sem executar nada.

        Em monorepos o CI costuma publicar um artifact por parte (ex.: `backend-coverage` e
        `frontend-coverage`) no mesmo run, então são baixados **todos os artifacts de cobertura do
        mesmo run** (até `max_coverage_artifacts`) para o leitor combinar por linhas — pegar só o
        primeiro faria a cobertura depender de qual parte terminou de subir por último.

        Sempre "melhor esforço": sem token, API indisponível, nenhum artifact, artifact expirado ou
        grande demais resultam em lista vazia (ou só nos artifacts que deram certo), e o chamador
        cai para os relatórios versionados no código. A API de artifacts exige autenticação mesmo em
        repositórios públicos, então sem `settings.github_token` nem tentamos; um token rejeitado
        (401) também resulta em lista vazia, não em erro.
        """
        if not self._token:
            return []
        try:
            response = self._get(f"/repos/{owner}/{repo}/actions/artifacts", params={"per_page": 100})
            response.raise_for_status()
            candidates = [
                artifact
                for artifact in response.json()["artifacts"]
                if not artifact["expired"] and "coverage" in artifact["name"].lower()
            ]
        except httpx.HTTPError:
            return []
        if not candidates:
            return []

        # A API lista do mais novo para o mais antigo: o primeiro define o run.
        latest_run = (candidates[0].get("workflow_run") or {}).get("id")
        if latest_run is None:
            selected = candidates[:1]
        else:
            selected = [a for a in candidates if (a.get("workflow_run") or {}).get("id") == latest_run]
        selected = selected[: settings.max_coverage_artifacts]

        zips: list[bytes] = []
        for artifact in selected:
            data = self._download_artifact(owner, repo, artifact["id"])
            if data is not None:
                zips.append(data)
        return zips

    def _download_artifact(self, owner: str, repo: str, artifact_id: int) -> bytes | None:
        try:
            download = self._get(
                f"/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip",
                stream=True,
                follow_redirects=True,
            )
            try:
                download.raise_for_status()
                with self._read_capped(
                    download, settings.max_artifact_mb * 1024 * 1024, "Artifact de cobertura"
                ) as buffer:
                    return buffer.read()
            finally:
                download.close()
        except (httpx.HTTPError, RepositoryTooLargeError):
            return None

    def close(self) -> None:
        self._client.close()
