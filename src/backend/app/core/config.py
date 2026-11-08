from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_LENGTH = 32

# Valores que existem no repositório público (padrões de código, do compose de desenvolvimento e
# do .env.example): quem os usar em produção publica um sistema com tokens forjáveis por qualquer um.
INSECURE_SECRET_DEFAULTS = frozenset(
    {
        "dev_secret_change_in_production_please",
        "dev_refresh_secret_change_in_production_please",
        "dev_secret_change_in_production",
        "dev_refresh_secret_change_in_production",
        "TROQUE_PARA_UM_VALOR_SECRETO_EM_PRODUCAO",
        "TROQUE_PARA_OUTRO_VALOR_SECRETO_EM_PRODUCAO",
    }
)
DEFAULT_DB_PASSWORD = "softmeter123"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Em "production" a aplicação se recusa a iniciar com configuração insegura (ver o validador).
    environment: Literal["development", "production"] = "development"

    database_url: str = "postgresql://softmeter:softmeter123@localhost:5432/softmeter_db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev_secret_change_in_production_please"
    jwt_refresh_secret: str = "dev_refresh_secret_change_in_production_please"
    jwt_access_expires_minutes: int = 15
    jwt_refresh_expires_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    github_token: str | None = None

    # Cookie do refresh token: `Secure` deve ser ligado sempre que a API for servida por HTTPS.
    cookie_secure: bool = False
    # Heurística de orçamento síncrono (research.md item 7): repositórios até este
    # tamanho (KB, conforme reportado pela API do GitHub) são analisados de forma
    # síncrona; acima disso, a análise é despachada para a fila Celery/Redis.
    sync_analysis_size_limit_kb: int = 5000

    reports_dir: str = "generated_reports"

    # Recuperação de senha (ADR-005) — sem resend_api_key configurada, o link de
    # reset é apenas registrado no log do backend em vez de enviado por e-mail;
    # nunca bloqueia o fluxo.
    resend_api_key: str | None = None
    email_from: str = "SoftMeter <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:3000"
    password_reset_token_expires_minutes: int = 60

    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> "Settings":
        if self.environment != "production":
            return self

        problems: list[str] = []
        for name, value in (("JWT_SECRET", self.jwt_secret), ("JWT_REFRESH_SECRET", self.jwt_refresh_secret)):
            if value in INSECURE_SECRET_DEFAULTS:
                problems.append(f"{name} está com um valor padrão do repositório")
            elif len(value) < MIN_SECRET_LENGTH:
                problems.append(f"{name} deve ter ao menos {MIN_SECRET_LENGTH} caracteres")
        if self.jwt_secret == self.jwt_refresh_secret:
            problems.append("JWT_SECRET e JWT_REFRESH_SECRET devem ser diferentes")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE deve ser true (a API precisa ser servida por HTTPS)")
        if DEFAULT_DB_PASSWORD in self.database_url:
            problems.append("DATABASE_URL usa a senha padrão do banco")

        if problems:
            raise ValueError("Configuração insegura para produção: " + "; ".join(problems))
        return self


settings = Settings()
