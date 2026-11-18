"""Desempenho das listas (sem consulta por item) e cadastro com URL normalizada e sem duplicata por caixa."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

import app.api.repositories as repositories_module
from app.models.analysis import Analysis, AnalysisStatus, Measurement
from app.models.repository import Repository


@pytest.fixture()
def count_queries(db_session):
    """Conta as consultas SQL emitidas dentro do bloco."""

    class Counter:
        n = 0

    counter = Counter()
    bind = db_session.get_bind()

    def before(conn, cursor, statement, *args):
        counter.n += 1

    class Ctx:
        def __enter__(self):
            counter.n = 0
            event.listen(bind, "before_cursor_execute", before)
            return counter

        def __exit__(self, *exc):
            event.remove(bind, "before_cursor_execute", before)

    return Ctx()


def _register(client, auth_headers, monkeypatch, url="https://github.com/octocat/Hello-World"):
    monkeypatch.setattr(repositories_module.GithubService, "fetch_languages", lambda self, o, r: ["python"])
    return client.post("/api/v1/repositories", json={"url": url}, headers=auth_headers)


def _fill(db_session, repository_id: str, analyses: int, status=AnalysisStatus.CONCLUIDA) -> None:
    for _ in range(analyses):
        analysis = Analysis(repositorio_id=uuid.UUID(repository_id), status=status, status_conformidade_geral="Conforme")
        db_session.add(analysis)
        db_session.flush()
        for key in ("loc", "acoplamento", "score_duplicacao"):
            db_session.add(Measurement(analise_id=analysis.id, metrica_chave=key, valor_medido=1, status_conformidade="Conforme"))
    db_session.commit()


class TestHistoryQueryCount:
    def test_history_does_not_query_once_per_analysis(self, client, auth_headers, monkeypatch, db_session, count_queries):
        repository = _register(client, auth_headers, monkeypatch).json()
        _fill(db_session, repository["id"], 30)

        with count_queries as counter:
            response = client.get(f"/api/v1/repositories/{repository['id']}/analyses", headers=auth_headers)

        assert response.status_code == 200
        assert len(response.json()) == 30
        assert all(len(item["medicoes"]) == 3 for item in response.json())
        # Antes: 33 consultas (1 por análise + as fixas). Agora o número independe da quantidade de análises.
        assert counter.n <= 8, counter.n

    def test_metric_series_does_not_query_once_per_analysis(self, client, auth_headers, monkeypatch, db_session, count_queries):
        repository = _register(client, auth_headers, monkeypatch).json()
        _fill(db_session, repository["id"], 30)

        with count_queries as counter:
            response = client.get(
                f"/api/v1/repositories/{repository['id']}/analyses?metrica=loc", headers=auth_headers
            )

        assert len(response.json()["serie"]) == 30
        assert counter.n <= 8, counter.n


class TestRepositoryListQueryCount:
    def test_list_has_a_fixed_number_of_queries_regardless_of_repositories(
        self, client, auth_headers, monkeypatch, db_session, count_queries
    ):
        for name in ("a", "b", "c", "d", "e", "f"):
            created = _register(client, auth_headers, monkeypatch, f"https://github.com/octocat/{name}").json()
            _fill(db_session, created["id"], 2)

        with count_queries as counter:
            response = client.get("/api/v1/repositories", headers=auth_headers)

        assert len(response.json()) == 6
        assert counter.n <= 10, counter.n  # antes: 1 consulta por repositório, além das fixas

    def test_last_attempt_and_last_completed_are_still_correct(self, client, auth_headers, monkeypatch, db_session):
        repository = _register(client, auth_headers, monkeypatch).json()
        _fill(db_session, repository["id"], 2)  # concluídas
        failed = Analysis(
            repositorio_id=uuid.UUID(repository["id"]),
            status=AnalysisStatus.FALHOU,
            solicitada_em=datetime.now(timezone.utc) + timedelta(minutes=1),  # explícito: relógio do Windows tem passo grosso
        )
        db_session.add(failed)
        db_session.commit()

        [item] = client.get("/api/v1/repositories", headers=auth_headers).json()

        assert item["ultima_analise_status"] == "falhou"
        assert item["ultima_analise_id"] == str(failed.id)
        assert item["ultima_concluida_id"] is not None
        assert item["ultima_concluida_id"] != str(failed.id)
        assert item["total_analises"] == 3


class TestRegistrationUrlNormalization:
    @pytest.mark.parametrize(
        "typed",
        [
            "https://github.com/octocat/Hello-World.git",
            "https://github.com/octocat/Hello-World/",
            "http://github.com/octocat/Hello-World",
            "https://github.com/octocat/Hello-World",
        ],
    )
    def test_stores_one_canonical_form(self, client, auth_headers, monkeypatch, typed):
        response = _register(client, auth_headers, monkeypatch, typed)

        assert response.status_code == 201
        assert response.json()["url"] == "https://github.com/octocat/Hello-World"
        assert response.json()["owner_nome"] == "octocat/Hello-World"

    @pytest.mark.parametrize(
        "second",
        [
            "https://github.com/octocat/Hello-World.git",
            "https://github.com/OCTOCAT/hello-world",
            "http://github.com/octocat/Hello-World/",
        ],
    )
    def test_the_same_repository_typed_differently_is_a_duplicate(self, client, auth_headers, monkeypatch, second):
        assert _register(client, auth_headers, monkeypatch).status_code == 201

        response = _register(client, auth_headers, monkeypatch, second)

        assert response.status_code == 409
        assert response.json()["detail"] == "Repositório já cadastrado"

    def test_duplicate_is_detected_before_calling_github(self, client, auth_headers, monkeypatch):
        _register(client, auth_headers, monkeypatch)
        calls: list[str] = []
        monkeypatch.setattr(
            repositories_module.GithubService, "fetch_languages", lambda self, o, r: calls.append(f"{o}/{r}") or ["python"]
        )

        client.post("/api/v1/repositories", json={"url": "https://github.com/octocat/hello-world"}, headers=auth_headers)

        assert calls == []  # não gasta a cota do GitHub

    def test_another_account_may_register_the_same_repository(self, client, auth_headers, monkeypatch):
        _register(client, auth_headers, monkeypatch)
        other = client.post(
            "/api/v1/auth/register", json={"email": "other@example.com", "password": "super-secret-123"}
        ).json()["access_token"]

        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
            headers={"Authorization": f"Bearer {other}"},
        )

        assert response.status_code == 201

    def test_the_database_still_rejects_exact_duplicates(self, db_session, client, auth_headers, monkeypatch):
        created = _register(client, auth_headers, monkeypatch).json()
        owner_id = db_session.get(Repository, uuid.UUID(created["id"])).usuario_id

        from sqlalchemy.exc import IntegrityError

        db_session.add(
            Repository(usuario_id=owner_id, url="https://github.com/octocat/Hello-World", owner_nome="x", linguagens_detectadas=[])
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
