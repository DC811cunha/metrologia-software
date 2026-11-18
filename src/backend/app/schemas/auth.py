import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator

# O bcrypt só considera os primeiros 72 BYTES da senha (a v5 recusa mais que isso).
MAX_PASSWORD_BYTES = 72


def _validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"A senha deve ter no máximo {MAX_PASSWORD_BYTES} bytes (UTF-8)")
    return value


def _normalize_email(value: str) -> str:
    """E-mails são comparados sem distinção de caixa: "Pessoa@Example.com" e "pessoa@example.com" são a
    mesma conta (a parte local tecnicamente distingue caixa, mas nenhum provedor relevante o faz)."""
    return value.strip().lower()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    _check_password_bytes = field_validator("password")(_validate_password_bytes)
    _normalize_email = field_validator("email")(_normalize_email)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    _normalize_email = field_validator("email")(_normalize_email)


class LoginResponse(BaseModel):
    """O refresh token vai apenas no cookie HttpOnly — nunca no corpo da resposta, onde um
    XSS, proxy ou log o exporia e anularia o benefício do HttpOnly."""

    access_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    _normalize_email = field_validator("email")(_normalize_email)


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

    _check_password_bytes = field_validator("new_password")(_validate_password_bytes)
