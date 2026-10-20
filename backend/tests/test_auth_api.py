"""Auth API endpoint tests (M3 C2, decision 0018/Q-M3-1) — live PG18 via CI service.

Drives app.main's ASGI app in-process through httpx.ASGITransport (no
starlette.testclient — its import raises a deprecation warning that would
violate Rule 6 under -W error). Cookie rotation/reuse-burn flows exercise
the M2 family store end-to-end.

Loop hygiene: each test runs its own asyncio loop; the app's cached
asyncpg engine is disposed ON that loop (db.dispose_engine) before the
loop closes — leaves no unclosed sockets behind (Rule 6, C2 CI lesson).

Test-only SECRET value: fine to hardcode (not a production secret).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Coroutine
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import db
from app.auth import hash_password
from app.main import app
from app.models import User
from tests.conftest import LIVE_DB_URL, needs_db

os.environ.setdefault("SECRET_KEY", "m3-test-only-secret-not-a-real-credential")

_PASSWORD = "correct-horse-battery-staple"
_COOKIE = "scriptorium_refresh"


def _cookie_from(resp: httpx.Response) -> str:
    raw = resp.headers.get_list("set-cookie")
    for header in raw:
        if header.startswith(f"{_COOKIE}="):
            return header.split("=", 1)[1].split(";", 1)[0]
    raise AssertionError(f"no {_COOKIE} cookie in response: {raw}")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _run(test: Coroutine[Any, Any, None]) -> None:
    asyncio.run(test)
    db.reset_engine()


async def _seed_user() -> str:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    email = f"auth-api-{uuid.uuid4().hex[:12]}@example.test"
    try:
        async with maker() as session:
            session.add(
                User(email=email, pw_hash=hash_password(_PASSWORD), display="Auth API")
            )
            await session.commit()
    finally:
        await engine.dispose()
    return email


@needs_db
def test_login_rejects_wrong_password_and_unknown_email() -> None:
    email = asyncio.run(_seed_user())

    async def run() -> None:
        async with _client() as client:
            wrong = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "totally-wrong"},
            )
            assert wrong.status_code == 401
            assert wrong.json() == {"detail": "Invalid credentials."}
            stranger = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"ghost-{uuid.uuid4().hex}@example.test",
                    "password": "x",
                },
            )
            assert stranger.status_code == 401
        await db.dispose_engine()

    _run(run())


@needs_db
def test_login_mint_access_and_rotating_refresh_cookie() -> None:
    email = asyncio.run(_seed_user())

    async def run() -> None:
        async with _client() as client:
            login = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            assert login.status_code == 200
            body = login.json()
            assert body["token_type"] == "bearer"
            assert body["access_token"].count(".") == 2
            first = _cookie_from(login)

            rotated = await client.post(
                "/api/v1/auth/refresh",
                headers={"Cookie": f"{_COOKIE}={first}"},
            )
            assert rotated.status_code == 200
            assert "access_token" in rotated.json()
            second = _cookie_from(rotated)
            assert second != first  # rotation means a fresh token value
        await db.dispose_engine()

    _run(run())


@needs_db
def test_refresh_reuse_burns_family_then_chain() -> None:
    """Presenting a rotated-out cookie is reuse → 401; even the newest token is dead."""
    email = asyncio.run(_seed_user())

    async def run() -> None:
        async with _client() as client:
            login = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            first = _cookie_from(login)
            second = _cookie_from(
                await client.post(
                    "/api/v1/auth/refresh", headers={"Cookie": f"{_COOKIE}={first}"}
                )
            )

            reuse = await client.post(
                "/api/v1/auth/refresh", headers={"Cookie": f"{_COOKIE}={first}"}
            )
            assert reuse.status_code == 401

            # Reuse detection burned the whole family — the newest cookie dies too.
            burned = await client.post(
                "/api/v1/auth/refresh", headers={"Cookie": f"{_COOKIE}={second}"}
            )
            assert burned.status_code == 401
        await db.dispose_engine()

    _run(run())


@needs_db
def test_logout_revokes_family_and_clears_cookie() -> None:
    email = asyncio.run(_seed_user())

    async def run() -> None:
        async with _client() as client:
            login = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            cookie = _cookie_from(login)

            out = await client.post(
                "/api/v1/auth/logout", headers={"Cookie": f"{_COOKIE}={cookie}"}
            )
            assert out.status_code == 204

            dead = await client.post(
                "/api/v1/auth/refresh", headers={"Cookie": f"{_COOKIE}={cookie}"}
            )
            assert dead.status_code == 401
        await db.dispose_engine()

    _run(run())


@needs_db
def test_refresh_without_cookie_is_401() -> None:
    async def run() -> None:
        async with _client() as client:
            bare = await client.post("/api/v1/auth/refresh")
            assert bare.status_code == 401
        await db.dispose_engine()  # no-op here — no request opened a connection

    _run(run())
