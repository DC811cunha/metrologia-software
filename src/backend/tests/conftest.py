import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
