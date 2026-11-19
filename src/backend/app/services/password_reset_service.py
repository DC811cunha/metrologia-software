"""Pedido de recuperação de senha: gera o token e envia o e-mail — SEMPRE fora da requisição HTTP.

O endpoint `/forgot-password` só enfileira o pedido e responde a mesma mensagem para qualquer e-mail. Quem
consulta o banco, grava o token e envia o e-mail é a task do worker (`workers/auth_tasks.py`), de modo que o
tempo da resposta não depende de a conta existir (medido antes da mudança: ~174 ms com conta × ~151 ms sem —
uma diferença pequena, mas constante, que revelava quais e-mails têm conta).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

_THROTTLE_WINDOW = timedelta(hours=1)


def hash_token(raw_token: str) -> str:
    """O banco guarda só o hash SHA-256: um vazamento dele não permite redefinir a senha de ninguém."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_password_reset(db: Session, email: str) -> bool:
    """Cria o token e envia o link se a conta existir e não estiver no limite. Devolve se enviou.

    Nenhum resultado aqui chega ao usuário: a resposta HTTP já foi dada, igual para todos os e-mails.
    """
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        return False

    now = datetime.now(UTC)
    window_start = now - _THROTTLE_WINDOW
    recent = db.execute(
        select(func.count())
        .select_from(PasswordResetToken)
        .where(PasswordResetToken.usuario_id == user.id, PasswordResetToken.criado_em > window_start)
    ).scalar_one()
    if recent >= settings.password_reset_max_per_hour:
        # Limite por e-mail (além do de 10/min por IP): impede encher a caixa de alguém a partir de vários IPs.
        logger.warning("Recuperação de senha acima do limite por hora para o usuário %s; pedido ignorado", user.id)
        return False

    # Tokens já usados ou vencidos há mais de uma hora não servem mais: limpa ao emitir um novo (a tabela não
    # cresce sem fim). Os da última hora ficam, porque contam para o limite acima.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.usuario_id == user.id,
        PasswordResetToken.criado_em < window_start,
        (PasswordResetToken.usado_em.is_not(None)) | (PasswordResetToken.expira_em < now),
    ).delete(synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            usuario_id=user.id,
            token_hash=hash_token(raw_token),
            expira_em=now + timedelta(minutes=settings.password_reset_token_expires_minutes),
        )
    )
    db.commit()

    send_password_reset_email(user.email, f"{settings.frontend_url}/reset-password?token={raw_token}")
    return True
