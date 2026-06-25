import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(user_id: uuid.UUID, token_type: TokenType, secret: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id,
        TokenType.ACCESS,
        settings.jwt_secret,
        timedelta(minutes=settings.jwt_access_expires_minutes),
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        user_id,
        TokenType.REFRESH,
        settings.jwt_refresh_secret,
        timedelta(days=settings.jwt_refresh_expires_days),
    )


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> uuid.UUID:
    return _decode_token(token, settings.jwt_secret, TokenType.ACCESS)


def decode_refresh_token(token: str) -> uuid.UUID:
    return _decode_token(token, settings.jwt_refresh_secret, TokenType.REFRESH)


def _decode_token(token: str, secret: str, expected_type: TokenType) -> uuid.UUID:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Token type esperado '{expected_type.value}'")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token sem 'sub' válido") from exc
