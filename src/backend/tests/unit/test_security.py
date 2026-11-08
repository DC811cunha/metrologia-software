import uuid

import pytest

import jwt

from app.core.config import settings
from app.core.security import (
    InvalidTokenError,
    equalize_login_timing,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    password = "super-secret-123"
    hashed = hash_password(password)
    assert hashed != password


def test_verify_password_accepts_correct_password():
    password = "super-secret-123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("super-secret-123")
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    claims = decode_access_token(token)
    assert claims.user_id == user_id
    assert claims.version == 0


def test_refresh_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    claims = decode_refresh_token(token)
    assert claims.user_id == user_id
    assert claims.version == 0


def test_access_token_rejected_by_refresh_decoder():
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id)
    with pytest.raises(InvalidTokenError):
        decode_refresh_token(access_token)


def test_invalid_token_raises():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-valid-token")


def test_verify_password_returns_false_instead_of_raising_for_over_72_bytes():
    hashed = hash_password("super-secret-123")
    assert verify_password("x" * 100, hashed) is False


def test_tokens_carry_the_session_version():
    user_id = uuid.uuid4()
    assert decode_access_token(create_access_token(user_id, token_version=3)).version == 3
    assert decode_refresh_token(create_refresh_token(user_id, token_version=5)).version == 5


def test_token_without_version_claim_is_treated_as_version_zero():
    user_id = uuid.uuid4()
    legacy = jwt.encode({"sub": str(user_id), "type": "access"}, settings.jwt_secret, algorithm="HS256")
    assert decode_access_token(legacy).version == 0


def test_equalize_login_timing_never_raises_even_for_long_passwords():
    equalize_login_timing("short-password")
    equalize_login_timing("x" * 200)
