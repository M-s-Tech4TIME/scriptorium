"""Refresh-token store tests (decision 0017): offline claims + live rotation.

Offline tests cover claim round-trips and strictness. The live test (CI PG18
service) exercises the family-based reuse detector end-to-end: rotate → reuse
→ family burned.
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import (
    REFRESH_DAYS,
    AuthError,
    _mint,
    create_token_pair,
    decode_refresh,
    rotate_refresh,
)
from app.models import RefreshToken, User
from tests.conftest import LIVE_DB_URL, needs_db

SECRET = "test-key-" + secrets.token_hex(24)


def test_decode_refresh_roundtrip() -> None:
    user_id = uuid.uuid4()
    _access, refresh, family, jti = create_token_pair(user_id, SECRET)
    assert decode_refresh(refresh, SECRET) == (user_id, family, jti)


def test_decode_refresh_requires_store_claims() -> None:
    # A refresh token minted without jti/fam (legacy shape) must be rejected.
    token = _mint(uuid.uuid4(), SECRET, "refresh", timedelta(days=1))
    with pytest.raises(AuthError):
        decode_refresh(token, SECRET)


def test_decode_refresh_malformed() -> None:
    _access, _refresh, _fam, jti = create_token_pair(uuid.uuid4(), SECRET)
    with pytest.raises(AuthError):
        decode_refresh(jti.hex, SECRET)  # Not even a JWT — AuthError, not crash


def test_expired_refresh_rejected() -> None:
    token = _mint(
        uuid.uuid4(),
        SECRET,
        "refresh",
        timedelta(seconds=-1),
        extra={"fam": str(uuid.uuid4()), "jti": str(uuid.uuid4())},
    )
    with pytest.raises(AuthError):
        decode_refresh(token, SECRET)


@needs_db
def test_rotation_then_reuse_burns_family() -> None:
    asyncio.run(_reuse_scenario())


@needs_db
def test_unknown_jti_is_reuse() -> None:
    asyncio.run(_unknown_scenario())


async def _engine_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, maker


async def _reuse_scenario() -> None:
    engine, maker = await _engine_session()
    try:
        async with maker() as session:
            tag = uuid.uuid4().hex[:8]
            user = User(email=f"refresh-{tag}@example.test", pw_hash="x", display="T")
            session.add(user)
            await session.commit()

            family = uuid.uuid4()
            _a0, refresh0, fam0, jti0 = create_token_pair(user.id, SECRET, family)
            assert fam0 == family
            session.add(
                RefreshToken(
                    user_id=user.id,
                    family=fam0,
                    jti=jti0,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(days=REFRESH_DAYS),
                )
            )
            await session.commit()

            # Legitimate rotation → successor in the same family.
            _a1, refresh1 = await rotate_refresh(session, refresh0, SECRET)
            _u, fam1, jti1 = decode_refresh(refresh1, SECRET)
            assert fam1 == family and jti1 != jti0
            row0 = await session.scalar(
                select(RefreshToken).where(RefreshToken.jti == jti0)
            )
            assert row0 is not None and row0.revoked_at is not None
            assert row0.revoked_reason == "rotated"

            # REUSE of the already-rotated token → whole family burned.
            with pytest.raises(HTTPException) as exc:
                await rotate_refresh(session, refresh0, SECRET)
            assert exc.value.status_code == 401
            rows = (
                (
                    await session.execute(
                        select(RefreshToken).where(RefreshToken.family == family)
                    )
                )
                .scalars()
                .all()
            )
            assert rows, "tokens must exist"
            assert all(r.revoked_at is not None for r in rows)

            # The successor token is dead too — attacker gains nothing.
            with pytest.raises(HTTPException):
                await rotate_refresh(session, refresh1, SECRET)
    finally:
        await engine.dispose()


async def _unknown_scenario() -> None:
    engine, maker = await _engine_session()
    try:
        async with maker() as session:
            tag = uuid.uuid4().hex[:8]
            user = User(email=f"unknown-{tag}@example.test", pw_hash="x", display="T")
            session.add(user)
            await session.commit()

            # Mint WITHOUT inserting a row: valid signature, unknown jti.
            _a, refresh, family, _jti = create_token_pair(user.id, SECRET)
            with pytest.raises(HTTPException) as exc:
                await rotate_refresh(session, refresh, SECRET)
            assert exc.value.status_code == 401
            rows = (
                (
                    await session.execute(
                        select(RefreshToken).where(RefreshToken.family == family)
                    )
                )
                .scalars()
                .all()
            )
            assert rows == []  # Nothing existed to burn; still a clean 401.
    finally:
        await engine.dispose()
