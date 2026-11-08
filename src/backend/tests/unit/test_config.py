import pytest
from pydantic import ValidationError

from app.core.config import MIN_SECRET_LENGTH, Settings

STRONG_ACCESS = "a" * 40
STRONG_REFRESH = "b" * 40
SAFE_DB = "postgresql://softmeter:uma-senha-forte-xyz@db:5432/softmeter_db"


def production(**overrides) -> Settings:
    values = {
        "environment": "production",
        "jwt_secret": STRONG_ACCESS,
        "jwt_refresh_secret": STRONG_REFRESH,
        "cookie_secure": True,
        "database_url": SAFE_DB,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class TestDevelopment:
    def test_allows_the_default_secrets(self, monkeypatch):
        for name in ("ENVIRONMENT", "JWT_SECRET", "JWT_REFRESH_SECRET", "DATABASE_URL"):
            monkeypatch.delenv(name, raising=False)

        settings = Settings(_env_file=None)

        assert settings.environment == "development"
        assert settings.jwt_secret.startswith("dev_secret")

    def test_allows_short_equal_secrets_and_insecure_cookie(self):
        Settings(_env_file=None, jwt_secret="x", jwt_refresh_secret="x", cookie_secure=False)


class TestProduction:
    def test_accepts_a_safe_configuration(self):
        settings = production()

        assert settings.environment == "production"

    @pytest.mark.parametrize(
        "default_secret",
        [
            "dev_secret_change_in_production_please",
            "dev_secret_change_in_production",
            "TROQUE_PARA_UM_VALOR_SECRETO_EM_PRODUCAO",
        ],
    )
    def test_refuses_default_jwt_secret(self, default_secret):
        with pytest.raises(ValidationError, match="JWT_SECRET está com um valor padrão"):
            production(jwt_secret=default_secret)

    def test_refuses_default_refresh_secret(self):
        with pytest.raises(ValidationError, match="JWT_REFRESH_SECRET está com um valor padrão"):
            production(jwt_refresh_secret="dev_refresh_secret_change_in_production")

    def test_refuses_short_secrets(self):
        with pytest.raises(ValidationError, match=f"ao menos {MIN_SECRET_LENGTH} caracteres"):
            production(jwt_secret="curto")

    def test_refuses_equal_secrets(self):
        with pytest.raises(ValidationError, match="devem ser diferentes"):
            production(jwt_secret=STRONG_ACCESS, jwt_refresh_secret=STRONG_ACCESS)

    def test_refuses_insecure_cookie(self):
        with pytest.raises(ValidationError, match="COOKIE_SECURE"):
            production(cookie_secure=False)

    def test_refuses_default_database_password(self):
        with pytest.raises(ValidationError, match="senha padrão do banco"):
            production(database_url="postgresql://softmeter:softmeter123@db:5432/softmeter_db")

    def test_reports_every_problem_at_once(self):
        with pytest.raises(ValidationError) as error:
            production(jwt_secret="curto", cookie_secure=False)

        message = str(error.value)
        assert "ao menos" in message
        assert "COOKIE_SECURE" in message
