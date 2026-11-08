"""Rate limiting por IP (e limite de tamanho de corpo) — issue #98.

Dois backends com a mesma interface:
- memória (padrão): janela deslizante por processo, com varredura periódica de chaves
  ociosas para o dicionário não crescer indefinidamente;
- Redis (`RATE_LIMIT_BACKEND=redis`): contador por janela fixa compartilhado entre
  processos/réplicas, que expira sozinho. Se o Redis falhar, cai para a memória.

O IP vem de `request.client.host`. Atrás de um proxy reverso, ele só reflete o cliente real
se o uvicorn confiar no proxy (`--proxy-headers` + `FORWARDED_ALLOW_IPS`, já definidos no
`docker-compose.prod.yml`); confiar em `X-Forwarded-For` direto no código permitiria burlar o limite.
"""

import logging
import math
import re
import time
from collections import deque
from typing import Literal, Protocol

import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

_ANALYSES_PATH = re.compile(r"^/api/v1/repositories/[^/]+/analyses$")
_SWEEP_INTERVAL_S = 60.0


class Rule:
    __slots__ = ("name", "limit", "window_s")

    def __init__(self, name: str, limit: int, window_s: int) -> None:
        self.name = name
        self.limit = limit
        self.window_s = window_s


def rule_for(method: str, path: str) -> Rule | None:
    """Regra aplicável à requisição, ou None se ela não é limitada."""
    if method != "POST":
        return None

    # Sempre ativas: tentativas de login e de recuperação de senha (brute-force, spam de
    # e-mail, enumeração de contas). O reset entra por defesa em profundidade.
    if path in {
        "/api/v1/auth/login",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    }:
        return Rule(path, 10, 60)

    # Só em produção: em desenvolvimento, testes e E2E, criar várias contas e análises em
    # sequência é o fluxo normal e não deve esbarrar no limite.
    if settings.environment != "production":
        return None
    if path == "/api/v1/auth/register":
        return Rule(path, settings.rate_limit_register_per_hour, 3600)
    if path == "/api/v1/auth/refresh":
        return Rule(path, settings.rate_limit_refresh_per_minute, 60)
    if _ANALYSES_PATH.match(path):
        # Cada análise consome a cota do GitHub do sistema inteiro e CPU do servidor.
        return Rule("/api/v1/repositories/*/analyses", settings.rate_limit_analyses_per_hour, 3600)
    return None


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_s: int) -> int | None:
        """Registra uma tentativa. Devolve None se permitida, ou os segundos até liberar."""


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[deque[float], int]] = {}
        self._last_sweep = time.monotonic()

    def __len__(self) -> int:
        return len(self._windows)

    def clear(self) -> None:
        self._windows.clear()

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < _SWEEP_INTERVAL_S:
            return
        self._last_sweep = now
        expired = [
            key
            for key, (window, window_s) in self._windows.items()
            if not window or window[-1] < now - window_s
        ]
        for key in expired:
            del self._windows[key]

    async def hit(self, key: str, limit: int, window_s: int) -> int | None:
        now = time.monotonic()
        self._sweep(now)

        window, _ = self._windows.setdefault(key, (deque(), window_s))
        while window and window[0] < now - window_s:
            window.popleft()
        if len(window) >= limit:
            return max(1, math.ceil(window_s - (now - window[0])))
        window.append(now)
        return None


class RedisRateLimiter:
    """Janela fixa: `INCR` + `EXPIRE` na primeira tentativa de cada janela."""

    def __init__(self, url: str, fallback: MemoryRateLimiter) -> None:
        self._client = redis_asyncio.from_url(url)
        self._fallback = fallback
        self._warned = False

    async def hit(self, key: str, limit: int, window_s: int) -> int | None:
        bucket = int(time.time() // window_s)
        redis_key = f"softmeter:rl:{key}:{bucket}"
        try:
            count = await self._client.incr(redis_key)
            if count == 1:
                await self._client.expire(redis_key, window_s)
        except (RedisError, OSError):
            if not self._warned:
                logger.warning("Redis indisponível para o rate limit — usando limite em memória")
                self._warned = True
            return await self._fallback.hit(key, limit, window_s)

        if count > limit:
            return max(1, window_s - int(time.time() % window_s))
        return None


_memory = MemoryRateLimiter()
_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        backend: Literal["memory", "redis"] = settings.rate_limit_backend
        _limiter = RedisRateLimiter(settings.redis_url, _memory) if backend == "redis" else _memory
    return _limiter


def reset_rate_limits() -> None:
    """Zera o estado e volta ao backend configurado (usado pelos testes)."""
    global _limiter
    _memory.clear()
    _limiter = None
