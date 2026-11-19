"""Pedido de recuperação de senha: o endpoint só enfileira (resposta independente da conta) e o worker decide,
com limite por e-mail e limpeza de tokens antigos."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event

import app.api.auth as auth_module
import app.services.password_reset_service as service_module
import app.workers.auth_tasks as tasks_module
from app.core.config import settings
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.password_reset_service import issue_password_reset

PASSWORD = "super-secret-123"


@pytest.fixture()
def sent_emails(monkeypatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(service_module, "send_password_reset_email", lambda to, link: sent.append((to, link)))
    return sent


def _register(client, email: str) -> None:
    client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})


class TestEndpointDoesNotDependOnTheAccount:
    """Medido antes da mudança: ~174 ms com conta × ~151 ms sem conta (gravar no banco + publicar na fila só
    acontecia para e-mails cadastrados). Agora o endpoint faz o mesmo trabalho nos dois casos."""

    def test_same_response_and_same_work_for_known_and_unknown_emails(self, client, db_session, monkeypatch):
        _register(client, "known@example.com")
        enqueued: list[str] = []
        monkeypatch.setattr(auth_module.request_password_reset_task, "delay", lambda email: enqueued.append(email))
        statements: list[str] = []
        bind = db_session.get_bind()

        def capture(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(bind, "before_cursor_execute", capture)
        try:
            known = client.post("/api/v1/auth/forgot-password", json={"email": "known@example.com"})
            unknown = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
        finally:
            event.remove(bind, "before_cursor_execute", capture)

        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert enqueued == ["known@example.com", "ghost@example.com"]  # os dois caminhos enfileiram
        assert statements == []  # e nenhum toca no banco durante a requisição

    def test_queue_outage_does_not_change_the_response(self, client, monkeypatch, caplog):
        def broker_down(email):
            raise ConnectionError("redis fora do ar")

        monkeypatch.setattr(auth_module.request_password_reset_task, "delay", broker_down)

        response = client.post("/api/v1/auth/forgot-password", json={"email": "any@example.com"})

        assert response.status_code == 200
        assert "receberá um link" in response.json()["message"]
        assert "enfileirar" in caplog.text


class TestWorkerIssuesTheToken:
    def test_known_account_gets_a_token_and_an_email(self, client, db_session, sent_emails):
        _register(client, "known@example.com")

        assert issue_password_reset(db_session, "known@example.com") is True

        assert len(sent_emails) == 1
        to, link = sent_emails[0]
        assert to == "known@example.com"
        assert link.startswith(f"{settings.frontend_url}/reset-password?token=")
        assert db_session.query(PasswordResetToken).count() == 1

    def test_unknown_account_gets_nothing(self, db_session, sent_emails):
        assert issue_password_reset(db_session, "ghost@example.com") is False

        assert sent_emails == []
        assert db_session.query(PasswordResetToken).count() == 0

    def test_the_celery_task_opens_its_own_session_and_closes_it(self, monkeypatch):
        calls: list[tuple] = []

        class FakeSession:
            def close(self):
                calls.append(("close",))

        monkeypatch.setattr(tasks_module, "SessionLocal", lambda: FakeSession())
        monkeypatch.setattr(tasks_module, "issue_password_reset", lambda db, email: calls.append(("issue", email)))

        tasks_module.request_password_reset_task.run("a@example.com")

        assert calls == [("issue", "a@example.com"), ("close",)]


class TestPerEmailThrottle:
    def test_requests_above_the_hourly_limit_are_ignored(self, client, db_session, sent_emails, caplog):
        _register(client, "target@example.com")

        results = [issue_password_reset(db_session, "target@example.com") for _ in range(settings.password_reset_max_per_hour + 2)]

        assert results == [True] * settings.password_reset_max_per_hour + [False, False]
        assert len(sent_emails) == settings.password_reset_max_per_hour
        assert "acima do limite" in caplog.text

    def test_the_limit_is_per_account(self, client, db_session, sent_emails):
        _register(client, "a@example.com")
        _register(client, "b@example.com")
        for _ in range(settings.password_reset_max_per_hour):
            issue_password_reset(db_session, "a@example.com")

        assert issue_password_reset(db_session, "a@example.com") is False
        assert issue_password_reset(db_session, "b@example.com") is True

    def test_tokens_older_than_an_hour_do_not_count(self, client, db_session, sent_emails):
        _register(client, "old@example.com")
        user = db_session.query(User).one()
        long_ago = datetime.now(UTC) - timedelta(hours=2)
        for i in range(settings.password_reset_max_per_hour):
            db_session.add(
                PasswordResetToken(
                    usuario_id=user.id,
                    token_hash=f"{i}" * 64,
                    expira_em=long_ago + timedelta(minutes=60),
                    criado_em=long_ago,
                )
            )
        db_session.commit()

        assert issue_password_reset(db_session, "old@example.com") is True


class TestHousekeeping:
    def test_old_used_and_expired_tokens_are_removed_but_recent_and_valid_ones_stay(self, client, db_session, sent_emails):
        _register(client, "reset@example.com")
        user = db_session.query(User).one()
        now = datetime.now(UTC)
        long_ago = now - timedelta(hours=3)
        db_session.add_all(
            [
                PasswordResetToken(usuario_id=user.id, token_hash="a" * 64, expira_em=long_ago + timedelta(minutes=60), criado_em=long_ago),  # vencido, antigo
                PasswordResetToken(usuario_id=user.id, token_hash="b" * 64, expira_em=now + timedelta(hours=1), usado_em=long_ago, criado_em=long_ago),  # usado, antigo
                PasswordResetToken(usuario_id=user.id, token_hash="c" * 64, expira_em=now + timedelta(hours=1), criado_em=now - timedelta(minutes=5)),  # válido e recente
            ]
        )
        db_session.commit()

        issue_password_reset(db_session, "reset@example.com")

        remaining = {t.token_hash for t in db_session.query(PasswordResetToken).all()}
        assert "a" * 64 not in remaining and "b" * 64 not in remaining
        assert "c" * 64 in remaining  # um link ainda válido não é invalidado por um novo pedido
        assert len(remaining) == 2  # o válido + o novo
