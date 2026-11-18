import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import reset_rate_limits
from app.db.session import Base, get_db
from app.main import app

# Banco de dados de teste isolado (SQLite em memória) — mais rápido e portável que exigir
# um Postgres real para cada execução de teste; os tipos usados (Uuid, DateTime) são
# suportados de forma equivalente pelos dois engines.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _enforce_foreign_keys(dbapi_connection, connection_record):
    # O SQLite não aplica chaves estrangeiras por padrão, ao contrário do Postgres de produção:
    # sem isto, uma exclusão que o Postgres recusa (ex.: relatórios apontando para análises)
    # passava nos testes e só estourava com o banco real.
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _no_real_password_reset_queue(monkeypatch):
    """`/forgot-password` enfileira o pedido no Celery; sem isto, os testes publicariam no Redis de verdade (o do
    desenvolvimento, se estiver de pé) ou ficariam esperando um broker. Os testes que precisam do fluxo
    sobrescrevem este `delay` (ver `_fake_email_capture` em test_auth_api.py)."""
    import app.api.auth as auth_module

    monkeypatch.setattr(auth_module.request_password_reset_task, "delay", lambda email: None)


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """O limitador de requisições é um estado global (10 logins/min por IP): sem zerá-lo a cada teste, o
    resultado dependia de quantos logins os testes anteriores já tinham feito no mesmo minuto."""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "super-secret-123"},
    )
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
