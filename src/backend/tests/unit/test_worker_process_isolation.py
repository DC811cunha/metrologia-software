"""Regressão: importar só `app.workers.analysis_tasks` (a superfície real do processo
`celery worker`) precisa deixar todos os mappers SQLAlchemy resolvíveis.

Os modelos usam forward references de string em `relationship()` (`Mapped["User"]`,
`Mapped["Repository"]` etc.), resolvidas apenas quando a classe referenciada já foi
importada nesse processo. Um teste rodando no mesmo processo pytest que já executou
`test_auth_api.py` ou qualquer teste de integração não reproduz o bug — nessas
suítes, `app.main` já importou todos os models antes. Este teste roda um processo
Python isolado, com a mesma superfície de import do worker Celery real, e força a
configuração dos mappers (o que a primeira query real também faria) para garantir
que "app/models/__init__.py" está de fato centralizando o registro.
"""

import subprocess
import sys


def test_worker_import_surface_configures_all_mappers() -> None:
    script = (
        "import app.workers.analysis_tasks\n"
        "from sqlalchemy.orm import configure_mappers\n"
        "configure_mappers()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
