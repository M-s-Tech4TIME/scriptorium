"""Auth/session routes (M3, decision 0018 Q-M3-1=A).

Login mints an access token (JSON body) plus a rotating refresh-token cookie
wired to the M2 family store (0017). No open registration — users are seeded
by CLI (Q-M3-1=A). Unknown emails burn a dummy argon2 verification to keep
response timing uniform (no account enumeration). Cookie attributes:
HttpOnly, SameSite=Lax, path=/; Secure comes from SCRIPTORIUM_COOKIE_SECURE
(prod packaging sets it).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import limiter
from app.auth import (
    REFRESH_DAYS,
    AuthError,
    _UNAUTHORIZED,
    create_token_pair,
    decode_refresh,
    get_secret,
    revoke_family,
    rotate_refresh,
    verify_dummy,
    verify_password,
)
from app.db import get_session
from app.models import AuditLog, RefreshToken, User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_NAME = "scriptorium_refresh"


class LoginIn(BaseModel):
    email: str
    password: str


async def _login_failed(peer_ip: str, email_addr: str) -> None:
    """Count a failed login; any limiter outage fails closed (0019: 503)."""
    try:
        await limiter.count_failure(peer_ip, email_addr)
    except limiter.LimiterUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable.",
        ) from exc


def _cookie_secure() -> bool:
    return os.environ.get("SCRIPTORIUM_COOKIE_SECURE", "").lower() in (
        "1",
        "true",
        "on",
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=REFRESH_DAYS * 86400,
        httponly=True,
        samesite="lax",
        path="/",
        secure=_cookie_secure(),
    )


@router.post("/login")
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    secret = get_secret()
    email = body.email.strip().lower()
    peer_ip = request.client.host if request.client else "unknown"
    try:
        if await limiter.usage(peer_ip, email) >= limiter.max_failures():
            retry = await limiter.retry_after(peer_ip, email)
            session.add(AuditLog(action="auth_rate_limited", meta={"ip": peer_ip}))
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Try again later.",
                headers={"Retry-After": str(retry)},
            )
    except limiter.LimiterUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable.",
        ) from exc

    user_id = await session.scalar(select(User.id).where(User.email == email))
    if user_id is None:
        verify_dummy(body.password)  # burn timing, ignore result
        await _login_failed(peer_ip, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )
    stored = await session.scalar(select(User.pw_hash).where(User.id == user_id))
    if stored is None or not verify_password(stored, body.password):
        await _login_failed(peer_ip, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials."
        )
    try:
        await limiter.clear(peer_ip, email)  # success resets the window
    except limiter.LimiterUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login temporarily unavailable.",
        ) from exc
    uid = uuid.UUID(str(user_id))
    access, refresh, fam, jti = create_token_pair(uid, secret)
    session.add(
        RefreshToken(
            user_id=uid,
            family=fam,
            jti=jti,
            parent_jti=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
        )
    )
    await session.commit()
    _set_refresh_cookie(response, refresh)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _UNAUTHORIZED
    try:
        access, rotated = await rotate_refresh(session, token, get_secret())
    except AuthError as exc:
        raise _UNAUTHORIZED from exc
    _set_refresh_cookie(response, rotated)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        try:
            _, family, _ = decode_refresh(token, get_secret())
            await revoke_family(session, family, "logout")
        except (AuthError, RuntimeError):
            pass  # junk/expired cookie — clear it and treat as logged out
    response.delete_cookie(COOKIE_NAME, path="/")
