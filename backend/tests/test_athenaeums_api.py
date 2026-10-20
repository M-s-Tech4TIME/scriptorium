"""Athenaeum (library) endpoint tests (M3.5, decision 0020) — live PG18.

Native hierarchy: user → Athenaeums → categories → grimoires. Covers the
owner-approved set: per-owner slug uniqueness, delete-refusal while holding
grimoires, nested sidebar (Q-M3-13), required-owned athenaeum on grimoire
create, cross-Athenaeum move with audit, foreign ids → uniform 404.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import create_token_pair
from app.main import app
from app.models import User
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db

_SECRET = "m3-test-only-secret-not-a-real-credential"


def _headers(user: dict[str, Any]) -> dict[str, str]:
    access, _r, _f, _j = create_token_pair(uuid.UUID(str(user["id"])), _SECRET)
    return {"Authorization": f"Bearer {access}"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _run(test: Coroutine[Any, Any, None]) -> None:
    try:
        asyncio.run(test)
    finally:
        from app import db, limiter

        db.reset_engine()
        limiter.reset_client()


async def _seed_users(count: int) -> list[dict[str, Any]]:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    users: list[dict[str, Any]] = []
    try:
        async with maker() as session:
            for n in range(count):
                email = f"athen-{uuid.uuid4().hex[:12]}-{n}@example.test"
                row = User(email=email, pw_hash="x", display=f"Owner {n}")
                session.add(row)
                await session.commit()
                users.append({"id": str(row.id), "email": email})
    finally:
        await engine.dispose()
    return users


async def _audit_count(action: str) -> int:
    from app.models import AuditLog

    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    n: int
    try:
        async with maker() as session:
            rows = await session.scalars(
                select(AuditLog.id).where(AuditLog.action == action)
            )
            n = len(list(rows))
    finally:
        await engine.dispose()
    return n


@needs_db
def test_athenaeum_lifecycle_and_per_owner_slugs() -> None:
    users = asyncio.run(_seed_users(2))
    me, other = users

    async def run() -> None:
        async with _client() as client:
            first = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "default", "title": "Default"},
                headers=_headers(me),
            )
            assert first.status_code == 201

            # same slug for a DIFFERENT user is fine (per-owner uniqueness)
            other_default = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "default", "title": "Default"},
                headers=_headers(other),
            )
            assert other_default.status_code == 201

            dup = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "default", "title": "again"},
                headers=_headers(me),
            )
            assert dup.status_code == 409

            bad_slug = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "Not Valid!", "title": "x"},
                headers=_headers(me),
            )
            assert bad_slug.status_code == 422

            listing = await client.get("/api/v1/athenaeums", headers=_headers(me))
            assert [a["slug"] for a in listing.json()] == ["default"]

            aid = first.json()["id"]
            renamed = await client.patch(
                f"/api/v1/athenaeums/{aid}",
                json={"title": "Product One"},
                headers=_headers(me),
            )
            assert renamed.json()["title"] == "Product One"

            foreign = await client.get(
                f"/api/v1/athenaeums/{uuid.uuid4()}", headers=_headers(other)
            )
            assert foreign.status_code == 404

            assert await _audit_count("athenaeum_created") >= 2
        await app_teardown()

    _run(run())


@needs_db
def test_delete_refuses_nonempty_then_allows_after_move() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            lib = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "shelve", "title": "Shelve"},
                headers=_headers(me),
            )
            aid = lib.json()["id"]
            other = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "elsewhere", "title": "Elsewhere"},
                headers=_headers(me),
            )
            other_id = other.json()["id"]

            await client.post(
                "/api/v1/grimoires",
                json={
                    "athenaeum_id": aid,
                    "slug": "grip",
                    "title": "Grip",
                },
                headers=_headers(me),
            )
            denied = await client.delete(
                f"/api/v1/athenaeums/{aid}", headers=_headers(me)
            )
            assert denied.status_code == 409
            assert await _audit_count("athenaeum_deleted") == 0  # nothing happened

            moved = await client.patch(
                f"/api/v1/grimoires/{(await client.get('/api/v1/grimoires', headers=_headers(me))).json()[0]['id']}",
                json={"athenaeum_id": other_id},
                headers=_headers(me),
            )
            assert moved.status_code == 200
            assert await _audit_count("grimoire_moved") >= 1

            now_empty = await client.delete(
                f"/api/v1/athenaeums/{aid}", headers=_headers(me)
            )
            assert now_empty.status_code == 204
            assert await _audit_count("athenaeum_deleted") == 1
        await app_teardown()

    _run(run())


@needs_db
def test_sidebar_nesting_and_uncategorized_bucket() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            lib = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "side", "title": "Side"},
                headers=_headers(me),
            )
            aid = lib.json()["id"]

            saga = await client.post(
                f"/api/v1/athenaeums/{aid}/categories",
                json={"name": "Saga"},
                headers=_headers(me),
            )
            rites = await client.post(
                f"/api/v1/athenaeums/{aid}/categories",
                json={"name": "Rites"},
                headers=_headers(me),
            )
            for name, category in (
                ("in-saga", saga),
                ("in-rites", rites),
                ("loose", None),
            ):
                body: dict[str, Any] = {
                    "athenaeum_id": aid,
                    "slug": name,
                    "title": name.title(),
                }
                if category is not None:
                    body["category_id"] = category.json()["id"]
                made = await client.post(
                    "/api/v1/grimoires", json=body, headers=_headers(me)
                )
                assert made.status_code == 201

            sidebar = await client.get(
                f"/api/v1/athenaeums/{aid}/sidebar", headers=_headers(me)
            )
            data = sidebar.json()
            assert [s["name"] for s in data["categories"]] == ["Saga", "Rites"]
            saga_slugs = [g["slug"] for g in data["categories"][0]["grimoires"]]
            assert saga_slugs == ["in-saga"]
            assert [g["slug"] for g in data["uncategorized"]] == ["loose"]

            foreign = await client.get(
                f"/api/v1/athenaeums/{uuid.uuid4()}/sidebar", headers=_headers(me)
            )
            assert foreign.status_code == 404
        await app_teardown()

    _run(run())


@needs_db
def test_grimoire_scoping_and_move_rejections() -> None:
    users = asyncio.run(_seed_users(2))
    me, stranger = users

    async def run() -> None:
        async with _client() as client:
            lib = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "home", "title": "Home"},
                headers=_headers(me),
            )
            aid = lib.json()["id"]

            missing = await client.post(
                "/api/v1/grimoires",
                json={"slug": "no-home", "title": "No home"},
                headers=_headers(me),
            )
            assert missing.status_code == 422  # pydantic: required field

            foreign_home = await client.post(
                "/api/v1/grimoires",
                json={
                    "athenaeum_id": str(uuid.uuid4()),
                    "slug": "floating",
                    "title": "Floating",
                },
                headers=_headers(me),
            )
            assert foreign_home.status_code == 404

            stranger_home = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "theirs", "title": "Theirs"},
                headers=_headers(stranger),
            )
            theirs = stranger_home.json()["id"]
            tresspass = await client.post(
                "/api/v1/grimoires",
                json={"athenaeum_id": theirs, "slug": "trespass", "title": "T"},
                headers=_headers(me),
            )
            assert tresspass.status_code == 404  # foreign athenaeum

            home_cat = await client.post(
                f"/api/v1/athenaeums/{aid}/categories",
                json={"name": "HomeCat"},
                headers=_headers(me),
            )
            stray_cat = await client.post(
                f"/api/v1/athenaeums/{theirs}/categories",
                json={"name": "StrayCat"},
                headers=_headers(stranger),
            )
            cross = await client.post(
                "/api/v1/grimoires",
                json={
                    "athenaeum_id": aid,
                    "slug": "cross",
                    "title": "Cross",
                    "category_id": stray_cat.json()["id"],
                },
                headers=_headers(me),
            )
            assert cross.status_code == 404  # category of ANOTHER athenaeum

            made = await client.post(
                "/api/v1/grimoires",
                json={
                    "athenaeum_id": aid,
                    "slug": "resident",
                    "title": "Resident",
                    "category_id": home_cat.json()["id"],
                },
                headers=_headers(me),
            )
            gid = made.json()["id"]

            stranger_move = await client.patch(
                f"/api/v1/grimoires/{gid}",
                json={"athenaeum_id": theirs},
                headers=_headers(stranger),
            )
            assert stranger_move.status_code == 404  # not even a member here

            null_target = await client.patch(
                f"/api/v1/grimoires/{gid}",
                json={"athenaeum_id": None},
                headers=_headers(me),
            )
            assert null_target.status_code == 422

            other_lib = await client.post(
                "/api/v1/athenaeums",
                json={"slug": "home2", "title": "Home2"},
                headers=_headers(me),
            )
            move = await client.patch(
                f"/api/v1/grimoires/{gid}",
                json={"athenaeum_id": other_lib.json()["id"]},
                headers=_headers(me),
            )
            assert move.status_code == 200
            assert move.json()["athenaeum_id"] == other_lib.json()["id"]
            assert await _audit_count("grimoire_moved") >= 1
        await app_teardown()

    _run(run())
