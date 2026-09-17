"""Envio de e-mail transacional de recuperação de senha via Resend (ADR-005).

Sem `settings.resend_api_key` configurada, o link é apenas registrado no log do
backend em vez de enviado — nunca bloqueia o fluxo de "esqueci minha senha", e
mantém o endpoint utilizável em desenvolvimento sem nenhuma conta externa.
Qualquer erro de rede/API também é apenas logado: o endpoint sempre responde
com a mesma mensagem genérica, para não revelar se um e-mail existe.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


def _render_html(reset_link: str) -> str:
    return (
        "<p>Você solicitou a recuperação de senha no SoftMeter.</p>"
        f'<p><a href="{reset_link}">Clique aqui para redefinir sua senha</a></p>'
        f"<p>Esse link expira em {settings.password_reset_token_expires_minutes} minutos. "
        "Se você não solicitou isso, ignore este e-mail.</p>"
    )


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY não configurado — link de recuperação de senha para %s: %s",
            to_email,
            reset_link,
        )
        return

    try:
        response = httpx.post(
            _RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from,
                "to": [to_email],
                "subject": "Recuperação de senha — SoftMeter",
                "html": _render_html(reset_link),
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Falha ao enviar e-mail de recuperação de senha via Resend para %s", to_email)
