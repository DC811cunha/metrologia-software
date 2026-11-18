"""Teto de análises síncronas simultâneas neste processo do servidor.

A análise síncrona roda DENTRO da requisição HTTP (até 300 s) e ocupa uma thread do servidor. Sem teto, algumas
análises lentas ao mesmo tempo esgotariam as threads e a API inteira (login, listas) pararia de responder. Quando
não há vaga, a análise segue pelo caminho assíncrono (fila Celery), que já existe para repositórios grandes: o
usuário recebe `202` e acompanha pelo polling em vez de receber um erro.

O contador vale por processo; com várias réplicas o teto total é `réplicas × limite`.
"""

import threading

from app.core.config import settings


class SyncAnalysisSlots:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0

    @property
    def active(self) -> int:
        return self._active

    def try_acquire(self) -> bool:
        with self._lock:
            if self._active >= settings.max_concurrent_sync_analyses:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)


sync_slots = SyncAnalysisSlots()
