"""Integração com a API pública do GitHub (research.md itens 1-2).

Detecção de linguagem via `GET /repos/{owner}/{repo}/languages` (FR-002) e ingestão de
código-fonte via download do zipball (sem exigir o binário `git` no worker).
"""

import io
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

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

    def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET com `GITHUB_TOKEN` quando configurado e fallback gracioso: se o GitHub
        rejeitar o token (401 — expirado ou revogado), repete a requisição sem
        credenciais e deixa de enviar o token nas chamadas seguintes desta instância.

        Sem isso, um token inválido deixaria o serviço *pior* do que sem token algum —
        repositórios públicos continuam acessíveis anonimamente (60 req/h). Mesmo
        princípio de "fallback gracioso" do ADR-004: configuração opcional nunca
        quebra o fluxo principal.
        """
        if self._token:
            response = self._client.get(
                url, headers={"Authorization": f"Bearer {self._token}"}, **kwargs
            )
            if response.status_code != 401:
                return response
            logger.warning(
                "GITHUB_TOKEN rejeitado pelo GitHub (401: expirado ou revogado) — "
                "seguindo sem autenticação; gere um token novo para restaurar o limite maior."
            )
            self._token = None
        return self._client.get(url, **kwargs)

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

    def download_and_extract(self, owner: str, repo: str, dest_dir: Path) -> Path:
        """Baixa o zipball padrão do repositório e extrai em `dest_dir`.

        Retorna o caminho da pasta raiz extraída (o GitHub empacota tudo sob um único
        diretório `{owner}-{repo}-{sha}/`).
        """
        response = self._get(f"/repos/{owner}/{repo}/zipball/HEAD", follow_redirects=True)
        if response.status_code in (404, 403):
            raise RepositoryAccessError(f"Repositório '{owner}/{repo}' inacessível para download")
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            archive.extractall(dest_dir)
            root_entry = archive.namelist()[0].split("/")[0]
        return dest_dir / root_entry

    def fetch_latest_coverage_artifact_zip(self, owner: str, repo: str) -> bytes | None:
        """Baixa o artifact de cobertura mais recente publicado pelo GitHub Actions do
        repositório (research.md item 6) — o CI de terceiros já rodou os testes; isto
        só lê o resultado, sem executar nada. Sempre "melhor esforço": qualquer falha
        (sem token configurado, API indisponível, nenhum artifact de cobertura,
        artifact expirado) retorna `None` silenciosamente e o chamador cai para os
        métodos que leem artefatos versionados no próprio código-fonte.

        A API de artifacts do GitHub Actions exige autenticação mesmo em
        repositórios públicos — sem `settings.github_token`, a chamada sempre
        falharia, então nem tentamos — e um token rejeitado pelo GitHub (401) também
        resulta em `None`, não em erro.
        """
        if not self._token:
            return None
        try:
            response = self._get(f"/repos/{owner}/{repo}/actions/artifacts", params={"per_page": 100})
            response.raise_for_status()
            artifacts = response.json()["artifacts"]
            match = next(
                (
                    a
                    for a in artifacts
                    if not a["expired"] and "coverage" in a["name"].lower()
                ),
                None,
            )
            if match is None:
                return None
            download = self._get(
                f"/repos/{owner}/{repo}/actions/artifacts/{match['id']}/zip", follow_redirects=True
            )
            download.raise_for_status()
            return download.content
        except httpx.HTTPError:
            return None

    def close(self) -> None:
        self._client.close()
