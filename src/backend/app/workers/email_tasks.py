from app.core.celery_app import celery_app
from app.services.email_service import send_password_reset_email


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email_task(to_email: str, reset_link: str) -> None:
    send_password_reset_email(to_email, reset_link)
