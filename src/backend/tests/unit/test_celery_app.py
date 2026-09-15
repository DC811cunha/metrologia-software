"""Regressão: importar `app.core.celery_app` precisa efetivamente registrar
`run_analysis` na app Celery, em qualquer processo — não só dentro do bootstrap do
comando `celery worker`.

`Celery.autodiscover_tasks` sem `force=True` apenas conecta um callback ao sinal
`import_modules`, que só é emitido pelo bootstrap do comando `celery worker`; em
qualquer outro processo que importe este módulo (o backend ao chamar `.delay()`, um
teste, um shell), a task nunca era registrada. Sem isso, o worker sobe sem erro mas
rejeita toda análise assíncrona em runtime com "Received unregistered task of type
'run_analysis'", deixando a Análise presa em status "processando" para sempre — nunca
reproduzido pelos testes existentes porque eles chamam `run_analysis_task` diretamente,
sem depender do registro real na app Celery.
"""

from app.core.celery_app import celery_app


def test_run_analysis_task_is_registered() -> None:
    assert "run_analysis" in celery_app.tasks
