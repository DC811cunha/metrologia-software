"""Prazo cooperativo da análise (issue #99).

A análise síncrona roda dentro da requisição HTTP e não pode ser interrompida de fora (uma
thread não se mata); por isso os laços por arquivo chamam `check_deadline()` e a análise se
aborta sozinha ao estourar o prazo. No worker Celery, `soft_time_limit`/`time_limit` ficam como
rede de segurança por cima deste prazo.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_deadline: ContextVar[float | None] = ContextVar("analysis_deadline", default=None)
_limit_s: ContextVar[float] = ContextVar("analysis_limit_s", default=0.0)


class AnalysisTimeoutError(Exception):
    """A análise ultrapassou o tempo máximo permitido."""


@contextmanager
def analysis_deadline(seconds: float) -> Iterator[None]:
    deadline_token = _deadline.set(time.monotonic() + seconds)
    limit_token = _limit_s.set(seconds)
    try:
        yield
    finally:
        _deadline.reset(deadline_token)
        _limit_s.reset(limit_token)


def check_deadline() -> None:
    """Aborta a análise se o prazo definido por `analysis_deadline` já passou (no-op sem prazo)."""
    deadline = _deadline.get()
    if deadline is not None and time.monotonic() > deadline:
        raise AnalysisTimeoutError(f"A análise excedeu o tempo máximo de {int(_limit_s.get())} s")
