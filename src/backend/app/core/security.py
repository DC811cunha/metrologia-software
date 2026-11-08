import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import NamedTuple

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # bcrypt >= 5 recusa senhas com mais de 72 bytes em vez de truncar: uma senha
        # assim nunca pode ter sido cadastrada (os schemas a rejeitam), então é simplesmente
        # incorreta — tratada como credencial inválida, nunca como erro 500.
        return False


# Calculado na importação (não sob demanda) para que a primeira tentativa com e-mail
# inexistente não pague um custo extra que a distinguiria das seguintes.
_DUMMY_PASSWORD_HASH = hash_password("softmeter-timing-equalizer")


def equalize_login_timing(password: str) -> None:
    """Gasta o mesmo custo de uma verificação real quando o e-mail não existe, para que o
    tempo de resposta do login não revele quais e-mails estão cadastrados."""
    verify_password(password, _DUMMY_PASSWORD_HASH)


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenClaims(NamedTuple):
    user_id: uuid.UUID
    # Versão de sessão do usuário no momento da emissão; tokens com versão diferente da
    # atual (após reset de senha ou logout) são recusados.
    version: int


def _create_token(
    user_id: uuid.UUID,
    token_type: TokenType,
    secret: str,
    expires_delta: timedelta,
    token_version: int,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "ver": token_version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    return _create_token(
        user_id,
        TokenType.ACCESS,
        settings.jwt_secret,
        timedelta(minutes=settings.jwt_access_expires_minutes),
        token_version,
    )


def create_refresh_token(user_id: uuid.UUID, token_version: int = 0) -> str:
    return _create_token(
        user_id,
        TokenType.REFRESH,
        settings.jwt_refresh_secret,
        timedelta(days=settings.jwt_refresh_expires_days),
        token_version,
    )


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> TokenClaims:
    return _decode_token(token, settings.jwt_secret, TokenType.ACCESS)


def decode_refresh_token(token: str) -> TokenClaims:
    return _decode_token(token, settings.jwt_refresh_secret, TokenType.REFRESH)


def _decode_token(token: str, secret: str, expected_type: TokenType) -> TokenClaims:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Token type esperado '{expected_type.value}'")
    try:
        user_id = uuid.UUID(payload["sub"])
        version = int(payload.get("ver", 0))
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Token sem 'sub' válido") from exc
    return TokenClaims(user_id=user_id, version=version)
