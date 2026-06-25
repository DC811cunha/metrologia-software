import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
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
    assert decode_access_token(token) == user_id


def test_refresh_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    assert decode_refresh_token(token) == user_id


def test_access_token_rejected_by_refresh_decoder():
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id)
    with pytest.raises(InvalidTokenError):
        decode_refresh_token(access_token)


def test_invalid_token_raises():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-valid-token")
