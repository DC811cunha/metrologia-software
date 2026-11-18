from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.password_reset_service import issue_password_reset


@celery_app.task(name="request_password_reset")
def request_password_reset_task(email: str) -> None:
    """Trata um pedido de recuperação de senha no worker (ver `services/password_reset_service.py`)."""
    db = SessionLocal()
    try:
        issue_password_reset(db, email)
    finally:
        db.close()
