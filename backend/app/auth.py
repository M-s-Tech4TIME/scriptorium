"""Authentication + per-grimoire RBAC (decision 0005/0010, Q22, 0017/0018).

- Passwords: Argon2id via argon2-cffi (never MD5/SHA/bcrypt downgrade).
- Tokens: short-lived access JWT + rotating refresh JWT (PyJWT, HS256, 0017).
  Refresh tokens carry `jti` + `fam` claims and are tracked server-side in the
  `refresh_tokens` table (state only, never token material): reuse detection is
  family-based — presenting an already-rotated or unknown `jti` revokes the
  whole token family and forces re-login.
- Cookies (HttpOnly/Secure/SameSite) are set at the router layer (M3); this
  module mints/verifies token strings and performs rotation state changes.
- Non-members get HTTP 404 (not 403) so grimoire existence is not leaked (IDOR,
  retro-approved 0017).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Membership, RefreshToken

_ph = PasswordHasher()  # Argon2id defaults (OWASP-recommended parameters)
_bearer = HTTPBearer(auto_error=False)

ACCESS_MINUTES = 15
REFRESH_DAYS = 7
ACCESS_COOKIE_NAME = "scriptorium_access"


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


_dummy_hash = _ph.hash("scriptorium-timing-equalizer-no-such-account")


def verify_dummy(plain: str) -> bool:
    """Burn argon2 work when the account does not exist (enumeration guard)."""
    return verify_password(_dummy_hash, plain)


def _mint(
    user_id: uuid.UUID,
    secret: str,
    kind: str,
    lifetime: timedelta,
    extra: dict[str, str] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(user_id),
        "type": kind,
        "iat": now,
        "exp": now + lifetime,
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, secret, algorithm="HS256")


def create_token_pair(
    user_id: uuid.UUID, secret: str, family: uuid.UUID | None = None
) -> tuple[str, str, uuid.UUID, uuid.UUID]:
    """Mint (access, refresh, family, jti).

    Pass an existing `family` to continue a refresh chain; a new family starts
    a login session. The DB row for the refresh insertion is the caller's job
    (route/store code), matching decisions 0010/0017.
    """
    fam = family or uuid.uuid4()
    jti = uuid.uuid4()
    return (
        _mint(user_id, secret, "access", timedelta(minutes=ACCESS_MINUTES)),
        _mint(
            user_id,
            secret,
            "refresh",
            timedelta(days=REFRESH_DAYS),
            {"fam": str(fam), "jti": str(jti)},
        ),
        fam,
        jti,
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


def decode_refresh(token: str, secret: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Return (user_id, family, jti) from a refresh token (requires store claims)."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "type", "exp", "jti", "fam"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Token rejected: {exc}") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Wrong token type (need refresh).")
    try:
        return (
            uuid.UUID(str(payload["sub"])),
            uuid.UUID(str(payload["fam"])),
            uuid.UUID(str(payload["jti"])),
        )
    except ValueError as exc:
        raise AuthError("Refresh claims are not UUIDs.") from exc


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Refresh token rejected — sign in again.",
)


async def revoke_family(session: AsyncSession, family: uuid.UUID, reason: str) -> None:
    """Revoke every live token of `family` (reuse detector / logout)."""
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family == family,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=func.now(), revoked_reason=reason)
    )
    await session.commit()


async def rotate_refresh(
    session: AsyncSession, token: str, secret: str
) -> tuple[str, str]:
    """Validate + rotate a refresh token; return (access, refresh) pair.

    - Unknown or already-presented `jti` (reuse): revoke the whole token
      family, then reject (decision 0017 — family-based detection).
    - Expired: mark the row 'expired', reject.
    - Valid: revoke the row ('rotated'), insert its successor (same family),
      return a fresh pair signed with the same secret.
    """
    user_id, family, jti = decode_refresh(token, secret)
    row = await session.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if row is None:
        # Unknown token (never issued / rotated out of existence in an older
        # chain): only claim info is available — revoke the claimed family.
        await revoke_family(session, family, "reuse")
        raise _UNAUTHORIZED
    if user_id != row.user_id or family != row.family:
        # Forged or cross-account claims: burn the REAL stored family.
        await revoke_family(session, row.family, "reuse")
        raise _UNAUTHORIZED
    now = datetime.now(UTC)
    if row.revoked_at is not None:
        # Token was already used — theft indicator. Burn the entire chain.
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family == row.family,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=func.now(), revoked_reason="reuse")
        )
        await session.commit()
        raise _UNAUTHORIZED
    if row.expires_at <= now:
        row.revoked_at = now
        row.revoked_reason = "expired"
        await session.commit()
        raise _UNAUTHORIZED

    row.revoked_at = now
    row.revoked_reason = "rotated"
    access, refresh, fam, jti = create_token_pair(
        row.user_id, secret, family=row.family
    )
    session.add(
        RefreshToken(
            user_id=row.user_id,
            family=fam,
            jti=jti,
            parent_jti=row.jti,
            expires_at=now + timedelta(days=REFRESH_DAYS),
        )
    )
    await session.commit()
    return access, refresh


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
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


async def get_optional_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> uuid.UUID | None:
    """Best-effort reader identity for the public serving surface.

    The browser cannot attach an Authorization header to a static document
    navigation, so login/refresh also set a short-lived HttpOnly access
    cookie scoped to ``/a``. API routes keep using the bearer dependency.
    Invalid/expired/missing credentials simply mean "anonymous"; private
    sites turn that into the uniform 404 in the serving router.
    """
    candidates: list[str] = []
    if credentials is not None and credentials.scheme.lower() == "bearer":
        candidates.append(credentials.credentials)
    cookie = request.cookies.get(ACCESS_COOKIE_NAME)
    if cookie:
        candidates.append(cookie)
    for token in candidates:
        try:
            return decode_token(token, get_secret(), "access")
        except AuthError, RuntimeError:
            continue
    return None


async def require_membership(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> str:
    """Return the member's role, or raise 404 (hides grimoire existence from outsiders)."""
    role = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == user_id, Membership.grimoire_id == grimoire_id
        )
    )
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return str(role)


async def get_session_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> tuple[AsyncSession, uuid.UUID]:
    return session, user_id
