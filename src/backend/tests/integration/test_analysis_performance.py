"""
T069 — Teste de performance: análise síncrona em até 10s p95 (Princípio IV).

Executa N análises em sequência sobre um repositório pequeno sintético e verifica
que o percentil 95 do tempo de execução fica abaixo de 10 segundos.
"""
import statistics
import time
from pathlib import Path

import pytest

import app.api.analyses as analyses_module
import app.api.repositories as repositories_module

SAMPLE_SIZE = 5
P95_LIMIT_SECONDS = 10.0


def _fake_download(self, owner, repo, dest_dir: Path) -> Path:
    root = dest_dir / f"{owner}-{repo}-perf"
    root.mkdir(parents=True)
    # Synthetic Python file with enough content to exercise the full pipeline.
    lines = ["import os", "import sys", ""]
    for i in range(20):
        lines += [
            f"def function_{i}(x, y):",
            f"    if x > {i}:",
            f"        return x + {i}",
            f"    elif y < {i}:",
            f"        return y - {i}",
            "    return 0",
            "",
        ]
    (root / "main.py").write_text("\n".join(lines), encoding="utf-8")
    (root / "helper.py").write_text(
        "from main import function_0\n\ndef helper(a, b):\n    return function_0(a, b)\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture()
def _patched(monkeypatch):
    monkeypatch.setattr(
        repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"]
    )
    monkeypatch.setattr(
        analyses_module.GithubService, "fetch_repo_size_kb", lambda self, o, r: 10
    )
    monkeypatch.setattr(analyses_module.GithubService, "download_and_extract", _fake_download)


class TestAnalysisPerformance:
    def test_sync_analysis_p95_under_10_seconds(self, client, auth_headers, _patched):
        repo = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/perf-user/perf-repo"},
            headers=auth_headers,
        ).json()
        repo_id = repo["id"]

        durations: list[float] = []
        for _ in range(SAMPLE_SIZE):
            start = time.perf_counter()
            response = client.post(
                f"/api/v1/repositories/{repo_id}/analyses", headers=auth_headers
            )
            elapsed = time.perf_counter() - start

            assert response.status_code == 201, f"Análise falhou: {response.json()}"
            assert response.json()["status"] == "concluida"
            durations.append(elapsed)

        durations.sort()
        p95_index = int(len(durations) * 0.95) - 1
        p95 = durations[max(p95_index, len(durations) - 1)]
        mean = statistics.mean(durations)
        max_duration = max(durations)

        print(
            f"\nPerformance: N={SAMPLE_SIZE}, mean={mean:.2f}s, "
            f"max={max_duration:.2f}s, p95={p95:.2f}s"
        )

        assert p95 < P95_LIMIT_SECONDS, (
            f"p95={p95:.2f}s excede o limite de {P95_LIMIT_SECONDS}s "
            f"(durações: {[round(d, 2) for d in durations]})"
        )
