import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import oauth2_scheme
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    equalize_login_timing,
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
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.services.password_reset_service import hash_token
from app.workers.auth_tasks import request_password_reset_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "Se este e-mail estiver cadastrado, você receberá um link de recuperação em instantes."
)


REFRESH_COOKIE_NAME = "softmeter_refresh_token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_refresh_expires_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _issue_session(user: User, response: Response) -> LoginResponse:
    _set_refresh_cookie(response, create_refresh_token(user.id, user.token_version))
    return LoginResponse(access_token=create_access_token(user.id, user.token_version))


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=LoginResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado") from exc
    db.refresh(user)

    return _issue_session(user, response)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        # Sem isto, e-mail inexistente responderia na hora e e-mail cadastrado levaria o custo
        # do bcrypt — diferença de tempo que revela quais contas existem.
        equalize_login_timing(payload.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    return _issue_session(user, response)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ausente")
    try:
        claims = decode_refresh_token(refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc

    user = db.get(User, claims.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    if user.token_version != claims.version:
        # Sessão encerrada (reset de senha ou logout) depois que este token foi emitido.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão encerrada")

    return AccessTokenResponse(access_token=create_access_token(user.id, user.token_version))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """Sempre responde a mesma mensagem genérica e NÃO consulta o banco: só enfileira o pedido, e o worker
    decide se a conta existe, grava o token e envia o e-mail (ver `services/password_reset_service.py`).

    Se o endpoint fizesse esse trabalho, o caminho de e-mail cadastrado (gravar no banco + publicar na fila)
    seria mensuravelmente mais lento que o de e-mail inexistente — um side-channel de timing que revelaria quais
    e-mails têm conta mesmo com a mensagem de resposta idêntica (medido: ~174 ms × ~151 ms). Agora os dois
    caminhos fazem exatamente a mesma coisa. Se a fila estiver fora do ar o erro é só registrado: devolver 5xx
    revelaria o estado do sistema, não o da conta, mas a resposta tem de ser igual para todos."""
    try:
        request_password_reset_task.delay(payload.email)
    except Exception:
        logger.exception("Não foi possível enfileirar o pedido de recuperação de senha")
    return ForgotPasswordResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_token(payload.token)
    reset_token = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    )

    if reset_token is None or reset_token.usado_em is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado"
        )

    now = datetime.now(UTC)
    expira_em = reset_token.expira_em
    if expira_em.tzinfo is None:
        # SQLite não preserva timezone-awareness em DateTime(timezone=True):
        # o valor volta naive, mas foi gravado em UTC — normaliza antes de comparar.
        expira_em = expira_em.replace(tzinfo=UTC)
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
    # Quem tinha acesso à conta antes do reset (ex.: sessão roubada) perde as sessões ativas. A expressão SQL
    # (`token_version + 1`, e não ler-e-somar em Python) evita perder um incremento se dois pedidos coincidirem.
    user.token_version = User.token_version + 1
    reset_token.usado_em = now
    db.commit()


def _session_owner(db: Session, refresh_token: str | None, access_token: str | None) -> User | None:
    """Dono da sessão apresentada, ou None se não há sessão vigente.

    O cookie do refresh token vem primeiro: ele é justamente o que precisa ser revogado e está presente
    mesmo quando o access token (15 min) já expirou — o caso mais comum de logout. O access token fica
    como alternativa. Só vale uma sessão VIGENTE: um token de versão antiga (já revogado, ou anterior a
    um reset de senha) não identifica ninguém, para não derrubar a sessão nova de um login posterior.
    """
    candidates = (
        (refresh_token, decode_refresh_token),
        (access_token, decode_access_token),
    )
    for token, decode in candidates:
        if not token:
            continue
        try:
            claims = decode(token)
        except InvalidTokenError:
            continue
        user = db.get(User, claims.user_id)
        if user is not None and user.token_version == claims.version:
            return user
    return None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    access_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> None:
    """Encerra a sessão no servidor (não só apaga o cookie): incrementar a versão invalida o refresh
    token mesmo que uma cópia dele tenha vazado, e o access token também. Efeito: sai de todos os
    dispositivos.

    Idempotente: responde 204 e apaga o cookie mesmo sem sessão válida (token ausente, expirado ou já
    revogado), em vez de falhar com 401 — antes, um logout depois de 15 min parado devolvia 401 sem
    revogar nada e deixava a sessão aberta por 7 dias. Não é CSRF-ável: o cookie é SameSite=Lax e não
    acompanha um POST vindo de outro site.
    """
    user = _session_owner(db, refresh_token, access_token)
    if user is not None:
        user.token_version = User.token_version + 1  # atômico no banco
        db.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
