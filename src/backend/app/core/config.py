from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://softmeter:softmeter123@localhost:5432/softmeter_db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev_secret_change_in_production_please"
    jwt_refresh_secret: str = "dev_refresh_secret_change_in_production_please"
    jwt_access_expires_minutes: int = 15
    jwt_refresh_expires_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000"]

    github_token: str | None = None
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


settings = Settings()
