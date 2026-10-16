"""Authentication + per-project RBAC (decision 0005/0010, Q22).

- Passwords: Argon2id via argon2-cffi (never MD5/SHA/bcrypt downgrade).
- Tokens: short-lived access JWT + rotating refresh JWT (PyJWT, HS256).
  Cookies (HttpOnly/Secure/SameSite) are set at the router layer (M3); this
  module mints/verifies token strings only.
- Server-side refresh-reuse detection needs a token store (schema addition) —
  parked as an owner question for M2; rotation here is stateless.
- Non-members get HTTP 404 (not 403) so project existence is not leaked (IDOR).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Membership

_ph = PasswordHasher()  # Argon2id defaults (OWASP-recommended parameters)
_bearer = HTTPBearer(auto_error=False)

ACCESS_MINUTES = 15
REFRESH_DAYS = 7


class AuthError(Exception):
    """Invalid, expired, or wrong-typed token."""


def get_secret() -> str:
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY is not set — refusing to mint tokens.")
    return secret


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return _ph.verify(stored_hash, plain)
    except VerifyMismatchError:
        return False


def _mint(user_id: uuid.UUID, secret: str, kind: str, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": kind,
            "iat": now,
            "exp": now + lifetime,
        },
        secret,
        algorithm="HS256",
    )


def create_token_pair(user_id: uuid.UUID, secret: str) -> tuple[str, str]:
    """Return (access, refresh). Refresh rotation = mint a fresh pair from a valid refresh."""
    return (
        _mint(user_id, secret, "access", timedelta(minutes=ACCESS_MINUTES)),
        _mint(user_id, secret, "refresh", timedelta(days=REFRESH_DAYS)),
    )


def decode_token(token: str, secret: str, expected_type: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "type", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Token rejected: {exc}") from exc
    if payload.get("type") != expected_type:
        raise AuthError(f"Wrong token type (need {expected_type}).")
    try:
        return uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise AuthError("Token subject is not a UUID.") from exc


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> uuid.UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    try:
        return decode_token(credentials.credentials, get_secret(), "access")
    except (AuthError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


async def require_membership(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> str:
    """Return the member's role, or raise 404 (hides project existence from outsiders)."""
    role = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == user_id, Membership.project_id == project_id
        )
    )
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return str(role)


async def get_session_user(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> tuple[AsyncSession, uuid.UUID]:
    return session, user_id
