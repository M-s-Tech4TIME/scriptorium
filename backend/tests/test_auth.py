"""Auth unit tests — offline (hashing + JWT round-trips, no DB).

Keys are generated at runtime (never stored as literals — secret scanners
must stay clean, Rule 6).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

import pytest

from app.auth import (
    AuthError,
    _mint,
    create_token_pair,
    decode_token,
    get_secret,
    hash_password,
    verify_password,
)

SECRET = "unit-test-key-" + secrets.token_hex(24)
WRONG_SECRET = "wrong-key-" + secrets.token_hex(24)


def test_password_roundtrip() -> None:
    stored = hash_password("correct horse")
    assert stored != "correct horse"
    assert verify_password(stored, "correct horse") is True
    assert verify_password(stored, "wrong") is False


def test_token_pair_roundtrip() -> None:
    user_id = uuid.uuid4()
    access, refresh = create_token_pair(user_id, SECRET)
    assert decode_token(access, SECRET, "access") == user_id
    assert decode_token(refresh, SECRET, "refresh") == user_id


def test_wrong_type_rejected() -> None:
    user_id = uuid.uuid4()
    access, _ = create_token_pair(user_id, SECRET)
    with pytest.raises(AuthError):
        decode_token(access, SECRET, "refresh")


def test_expired_rejected() -> None:
    token = _mint(uuid.uuid4(), SECRET, "access", timedelta(seconds=-1))
    with pytest.raises(AuthError):
        decode_token(token, SECRET, "access")


def test_tampered_rejected() -> None:
    user_id = uuid.uuid4()
    access, _ = create_token_pair(user_id, SECRET)
    with pytest.raises(AuthError):
        decode_token(access + "x", SECRET, "access")
    with pytest.raises(AuthError):
        decode_token(access, WRONG_SECRET, "access")


def test_secret_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        get_secret()
