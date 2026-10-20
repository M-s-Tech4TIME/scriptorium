"""Login rate-limit tests (decision 0019, Q-002=B) — live Redis via CI service.

Env contract: REDIS_URL redis:// (else skipped offline, conftest `needs_redis`);
these tests OWN the Redis keyspace and flush it between cases.

Peer-IP nuance: in-proc ASGITransport presents one fixed scope client
(127.0.0.1), so the HTTP flows exercise the per-email counter against that
shared IP; per-IP/per-email key separation is asserted directly against the
limiter functions (the router itself never trusts a peer header).

Test-only SECRET value — not a real credential.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Coroutine
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import db, limiter
from app.auth import hash_password
from app.main import app
from app.models import User
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db, needs_redis

os.environ.setdefault("SECRET_KEY", "m3-test-only-secret-not-a-real-credential")

_PASSWORD = "correct-horse-battery-staple"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _run(test: Coroutine[Any, Any, None]) -> None:
    asyncio.run(test)
    db.reset_engine()
    limiter.reset_client()


def _flush() -> None:
    """Clean limiter keyspace: each case starts at zero (tests own this Redis)."""

    async def flush() -> None:
        await limiter.get_client().flushdb()
        await limiter.dispose_client()

    asyncio.run(flush())
    limiter.reset_client()


async def _seed_user() -> str:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    email = f"rl-{uuid.uuid4().hex[:12]}@example.test"
    try:
        async with maker() as session:
            session.add(
                User(email=email, pw_hash=hash_password(_PASSWORD), display="RL")
            )
            await session.commit()
    finally:
        await engine.dispose()
    return email


@needs_redis
def test_counters_start_clean_and_keys_separate() -> None:
    _flush()

    async def run() -> None:
        ip_a, ip_b, mail = "10.0.0.1", "10.0.0.2", "someone@example.test"
        assert await limiter.usage(ip_a, mail) == 0
        for _ in range(3):
            await limiter.count_failure(ip_a, mail)
        await limiter.count_failure(ip_b, mail)
        # email counter: 4 (shared), ip_a: 3, ip_b: 1 — tighter binds at 5 → 1 left.
        assert await limiter.usage(ip_a, mail) == 4
        assert await limiter.usage(ip_b, mail) == 4
        assert await limiter.usage(ip_a, "other@example.test") == 3
        # ip_b alone binds at 1 for a fresh email (ip_b: 1, other-mail: 0 → max 1).
        assert await limiter.usage(ip_b, "other@example.test") == 1
        await limiter.dispose_client()

    _run(run())


@needs_db
@needs_redis
def test_five_failures_then_429_with_retry_after() -> None:
    email = asyncio.run(_seed_user())
    _flush()

    async def run() -> None:
        async with _client() as client:
            for _ in range(limiter.max_failures()):
                bad = await client.post(
                    "/api/v1/auth/login", json={"email": email, "password": "nope"}
                )
                assert bad.status_code == 401
            # Even the CORRECT password gets 429: the block precedes verification.
            trip = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            assert trip.status_code == 429
            assert trip.json() == {
                "detail": "Too many failed attempts. Try again later."
            }
            retry = int(trip.headers["Retry-After"])
            assert 0 < retry <= limiter.window_seconds()
        await app_teardown()

    _run(run())


@needs_db
@needs_redis
def test_success_clears_counters_and_reopens_budget() -> None:
    email = asyncio.run(_seed_user())
    _flush()

    async def run() -> None:
        async with _client() as client:
            for _ in range(limiter.max_failures() - 1):
                bad = await client.post(
                    "/api/v1/auth/login", json={"email": email, "password": "nope"}
                )
                assert bad.status_code == 401
            ok = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            assert ok.status_code == 200
            assert await limiter.usage("127.0.0.1", email) == 0
        await app_teardown()

    _run(run())


@needs_db
@needs_redis
def test_limiter_outage_fails_closed() -> None:
    """No REDIS_URL → the login path refuses with 503 (0019 fail-closed)."""
    email = asyncio.run(_seed_user())
    _flush()
    saved = os.environ.pop("REDIS_URL", None)
    limiter.reset_client()

    async def run() -> None:
        async with _client() as client:
            out = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": _PASSWORD}
            )
            assert out.status_code == 503
            assert out.json() == {"detail": "Login temporarily unavailable."}
        await app_teardown()

    try:
        _run(run())
    finally:
        if saved is not None:
            os.environ["REDIS_URL"] = saved
        limiter.reset_client()
