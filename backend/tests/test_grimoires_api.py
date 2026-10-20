"""Grimoire/category/member endpoint tests (M3 C3 native shape, 0020 stated).

Categories are sections inside an Athenaeum (`/api/v1/athenaeums/{id}/…`);
grimoire create carries an owned `athenaeum_id` (0020 Q-M3-10). Covers
per-athenaeum category lifecycles (dup/reorder/delete→Uncategorized),
grimoire CRUD with slug allowlist + creator-owner membership either way,
member management (owner-only mutations except self-leave), IDOR shape
(uniform 404 for outsiders, 403 for under-roles), one audit row per mutation.
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
from app.models import AuditLog, User
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
                email = f"grimoire-{uuid.uuid4().hex[:12]}-{n}@example.test"
                row = User(email=email, pw_hash="x", display=f"User {n}")
                session.add(row)
                await session.commit()
                users.append({"id": str(row.id), "email": email})
    finally:
        await engine.dispose()
    return users


async def _audit_action(action: str) -> int:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    count: int
    try:
        async with maker() as session:
            rows = await session.scalars(
                select(AuditLog.id).where(AuditLog.action == action)
            )
            count = len(list(rows))
    finally:
        await engine.dispose()
    return count


async def _mk_lib(client: httpx.AsyncClient, user: dict[str, Any], slug: str) -> str:
    made = await client.post(
        "/api/v1/athenaeums",
        json={"slug": f"{slug}-{uuid.uuid4().hex[:6]}", "title": slug.title()},
        headers=_headers(user),
    )
    assert made.status_code == 201
    return str(made.json()["id"])


async def _mk_grimoire(
    client: httpx.AsyncClient,
    user: dict[str, Any],
    athenaeum_id: str,
    slug: str,
    title: str,
    **extra: Any,
) -> dict[str, Any]:
    made = await client.post(
        "/api/v1/grimoires",
        json={"athenaeum_id": athenaeum_id, "slug": slug, "title": title, **extra},
        headers=_headers(user),
    )
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


# ---------------------------------------------------------------- categories


@needs_db
def test_category_lifecycle_dup_reorder_delete_uncategorizes() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid_me = await _mk_lib(client, me, "life")
            aid_stranger = await _mk_lib(client, me, "else")  # second lib of mine

            first = await client.post(
                f"/api/v1/athenaeums/{aid_me}/categories",
                json={"name": "Spells"},
                headers=_headers(me),
            )
            assert first.status_code == 201
            assert first.json()["position"] == 1

            second = await client.post(
                f"/api/v1/athenaeums/{aid_me}/categories",
                json={"name": "Rites"},
                headers=_headers(me),
            )
            assert second.status_code == 201
            first_id, second_id = first.json()["id"], second.json()["id"]

            dup = await client.post(
                f"/api/v1/athenaeums/{aid_me}/categories",
                json={"name": "Spells"},
                headers=_headers(me),
            )
            assert dup.status_code == 409

            listing = await client.get(
                f"/api/v1/athenaeums/{aid_me}/categories", headers=_headers(me)
            )
            assert [c["name"] for c in listing.json()] == ["Spells", "Rites"]

            # insert-displacement reorder: move "Rites" ahead of "Spells"
            moved = await client.patch(
                f"/api/v1/athenaeums/{aid_me}/categories/{second_id}",
                json={"position": 1},
                headers=_headers(me),
            )
            assert moved.status_code == 200
            relisting = await client.get(
                f"/api/v1/athenaeums/{aid_me}/categories", headers=_headers(me)
            )
            assert [c["name"] for c in relisting.json()] == ["Rites", "Spells"]

            rename = await client.patch(
                f"/api/v1/athenaeums/{aid_me}/categories/{second_id}",
                json={"name": "Rituals"},
                headers=_headers(me),
            )
            assert rename.json()["name"] == "Rituals"

            # categories of ANOTHER of my athenaeums are not reachable via this one
            foreign_category = await client.patch(
                f"/api/v1/athenaeums/{aid_stranger}/categories/{first_id}",
                json={"name": "X"},
                headers=_headers(me),
            )
            assert foreign_category.status_code == 404

            # a grimoire in the category, then delete → Uncategorized (same lib)
            created = await _mk_grimoire(
                client, me, aid_me, "cat-test", "Cat test", category_id=first_id
            )
            dropped = await client.delete(
                f"/api/v1/athenaeums/{aid_me}/categories/{first_id}",
                headers=_headers(me),
            )
            assert dropped.status_code == 204
            detail = await client.get(
                f"/api/v1/grimoires/{created['id']}", headers=_headers(me)
            )
            assert detail.json()["category_id"] is None
        await app_teardown()

    _run(run())


# ---------------------------------------------------------------- grimoires


@needs_db
def test_grimoire_create_validation_and_creator_membership() -> None:
    users = asyncio.run(_seed_users(2))
    me, stranger = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "create")
            bad_slug = await client.post(
                "/api/v1/grimoires",
                json={"athenaeum_id": aid, "slug": "Bad Slug!", "title": "x"},
                headers=_headers(me),
            )
            assert bad_slug.status_code == 422

            created = await _mk_grimoire(
                client, me, aid, "research-notes", "Research Notes"
            )
            assert created["role"] == "owner"
            assert created["theme"] == "scriptorium"
            assert created["athenaeum_id"] == aid

            dup = await client.post(
                "/api/v1/grimoires",
                json={"athenaeum_id": aid, "slug": "research-notes", "title": "second"},
                headers=_headers(stranger),
            )
            assert dup.status_code == 409  # slug uniqueness is global

            listing = await client.get("/api/v1/grimoires", headers=_headers(stranger))
            assert listing.json() == []  # outsider sees nothing (IDOR)

            detail = await client.get(
                f"/api/v1/grimoires/{created['id']}", headers=_headers(stranger)
            )
            assert detail.status_code == 404

            assert await _audit_action("grimoire_created") >= 1
        await app_teardown()

    _run(run())


@needs_db
def test_grimoire_patch_owner_only_and_explicit_uncategorize() -> None:
    users = asyncio.run(_seed_users(3))
    me, editor, stranger = users
    gid = {"id": ""}

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "patch")
            created = await _mk_grimoire(client, me, aid, "patch-me", "Patch me")
            gid["id"] = created["id"]

            member = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": editor["email"], "role": "editor"},
                headers=_headers(me),
            )
            assert member.status_code == 201

            category = await client.post(
                f"/api/v1/athenaeums/{aid}/categories",
                json={"name": "P"},
                headers=_headers(me),
            )
            attach = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"category_id": category.json()["id"]},
                headers=_headers(me),
            )
            assert attach.json()["category_id"] == category.json()["id"]
            clear = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"category_id": None},
                headers=_headers(me),
            )
            assert clear.json()["category_id"] is None

            titled = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"title": "Patched title"},
                headers=_headers(me),
            )
            assert titled.json()["title"] == "Patched title"

            editor_patch = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"title": "editor attempt"},
                headers=_headers(editor),
            )
            assert editor_patch.status_code == 403  # member, but not owner

            outsider_patch = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"title": "outsider attempt"},
                headers=_headers(stranger),
            )
            assert outsider_patch.status_code == 404  # IDOR: no existence leak

            foreign_category = await client.patch(
                f"/api/v1/grimoires/{gid['id']}",
                json={"category_id": str(uuid.uuid4())},
                headers=_headers(me),
            )
            assert foreign_category.status_code == 404
            assert await _audit_action("grimoire_patched") >= 2
        await app_teardown()

    _run(run())


# ---------------------------------------------------------------- members


@needs_db
def test_member_flows_owner_only_roles_and_self_leave() -> None:
    users = asyncio.run(_seed_users(4))
    me, viewer, stranger, other_owner = users
    gid = {"id": ""}

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "members")
            created = await _mk_grimoire(client, me, aid, "member-flow", "Member flow")
            gid["id"] = created["id"]

            outsider = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(stranger),
            )
            assert outsider.status_code == 404

            unknown = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": "ghost@example.test", "role": "viewer"},
                headers=_headers(me),
            )
            assert unknown.status_code == 404

            added = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )
            assert added.status_code == 201

            dup = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": viewer["email"], "role": "editor"},
                headers=_headers(me),
            )
            assert dup.status_code == 409

            roster = await client.get(
                f"/api/v1/grimoires/{gid['id']}/members", headers=_headers(viewer)
            )
            assert roster.status_code == 200
            assert len(roster.json()) == 2

            viewer_copy = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": stranger["email"], "role": "viewer"},
                headers=_headers(viewer),
            )
            assert viewer_copy.status_code == 403

            promote = await client.patch(
                f"/api/v1/grimoires/{gid['id']}/members/{viewer['id']}",
                json={"role": "editor"},
                headers=_headers(me),
            )
            assert promote.status_code == 200
            owner_target = await client.patch(
                f"/api/v1/grimoires/{gid['id']}/members/{me['id']}",
                json={"role": "viewer"},
                headers=_headers(me),
            )
            assert owner_target.status_code == 409

            leave = await client.delete(
                f"/api/v1/grimoires/{gid['id']}/members/{viewer['id']}",
                headers=_headers(viewer),
            )
            assert leave.status_code == 204

            owner_self = await client.delete(
                f"/api/v1/grimoires/{gid['id']}/members/{me['id']}",
                headers=_headers(me),
            )
            assert owner_self.status_code == 409

            readd = await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )
            assert readd.status_code == 201
            evict = await client.delete(
                f"/api/v1/grimoires/{gid['id']}/members/{viewer['id']}",
                headers=_headers(me),
            )
            assert evict.status_code == 204

            assert await _audit_action("member_added") >= 2
            assert await _audit_action("member_role_changed") >= 1
            assert await _audit_action("member_removed") >= 2

            other_lib = await _mk_lib(client, other_owner, "others")
            other = await _mk_grimoire(
                client, other_owner, other_lib, "other-owner", "Other owner"
            )
            peek = await client.get(
                f"/api/v1/grimoires/{other['id']}", headers=_headers(me)
            )
            assert peek.status_code == 404
        await app_teardown()

    _run(run())


@needs_db
def test_grimoire_delete_owner_only_and_cascades() -> None:
    users = asyncio.run(_seed_users(3))
    me, viewer, stranger = users
    gid = {"id": ""}

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "delete")
            created = await _mk_grimoire(client, me, aid, "delete-me", "Delete me")
            gid["id"] = created["id"]
            await client.post(
                f"/api/v1/grimoires/{gid['id']}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )

            outsider_del = await client.delete(
                f"/api/v1/grimoires/{gid['id']}", headers=_headers(stranger)
            )
            assert outsider_del.status_code == 404

            viewer_del = await client.delete(
                f"/api/v1/grimoires/{gid['id']}", headers=_headers(viewer)
            )
            assert viewer_del.status_code == 403

            owner_del = await client.delete(
                f"/api/v1/grimoires/{gid['id']}", headers=_headers(me)
            )
            assert owner_del.status_code == 204

            post = await client.get(
                f"/api/v1/grimoires/{gid['id']}", headers=_headers(me)
            )
            assert post.status_code == 404  # membership cascade → 404 again

            roster = await client.get(
                f"/api/v1/grimoires/{gid['id']}/members",
                headers=_headers(viewer),
            )
            assert roster.status_code == 404  # membership gone with the grimoire

            listing = await client.get("/api/v1/grimoires", headers=_headers(viewer))
            assert listing.json() == []
            assert await _audit_action("grimoire_deleted") >= 1
        await app_teardown()

    _run(run())
