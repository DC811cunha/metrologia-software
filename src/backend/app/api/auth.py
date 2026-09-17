import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "Se este e-mail estiver cadastrado, você receberá um link de recuperação em instantes."
)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

REFRESH_COOKIE_NAME = "softmeter_refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenPairResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado") from exc
    db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")
    try:
        user_id = decode_refresh_token(refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Sempre responde com a mesma mensagem genérica — não revela se o e-mail
    está cadastrado (evita enumeração de contas)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        return ForgotPasswordResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            usuario_id=user.id,
            token_hash=_hash_token(raw_token),
            expira_em=datetime.now(timezone.utc)
            + timedelta(minutes=settings.password_reset_token_expires_minutes),
        )
    )
    db.commit()

    reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    send_password_reset_email(user.email, reset_link)

    return ForgotPasswordResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    token_hash = _hash_token(payload.token)
    reset_token = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    )

    if reset_token is None or reset_token.usado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado"
        )

    now = datetime.now(timezone.utc)
    expira_em = reset_token.expira_em
    if expira_em.tzinfo is None:
        # SQLite não preserva timezone-awareness em DateTime(timezone=True):
        # o valor volta naive, mas foi gravado em UTC — normaliza antes de comparar.
        expira_em = expira_em.replace(tzinfo=timezone.utc)
    if expira_em < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado"
        )

    user = db.get(User, reset_token.usuario_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado"
        )

    user.password_hash = hash_password(payload.new_password)
    reset_token.usado_em = now
    db.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, _: User = Depends(get_current_user)) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
