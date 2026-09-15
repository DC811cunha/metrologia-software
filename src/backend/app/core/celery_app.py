from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "softmeter",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import direto em vez de autodiscover_tasks: sem force=True, o autodiscover só
# dispara no sinal `import_modules` emitido pelo bootstrap do comando `celery worker`
# — em qualquer outro processo que importe este módulo (o backend ao dar .delay(),
# um teste, um shell), a task nunca era registrada. O import direto garante o
# registro em qualquer processo, de forma determinística. Sem isso, o worker sobe
# sem erro mas rejeita toda análise assíncrona em runtime com "Received unregistered
# task of type 'run_analysis'", deixando a Análise presa em "processando" para sempre.
import app.workers.analysis_tasks  # noqa: E402,F401
