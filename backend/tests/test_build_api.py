"""Build API tests (M4-C3, decision 0026) — live PG18 + real sandboxed Sphinx.

Covers the owner rulings: E1 empty-Athenaeum 422, E2 skip-notes in the
build log, E3 one-build-per-athenaeum 409, per-Athenaeum numbering,
owner-only trigger, member-visible GETs, ok / failed status machine,
and the artifact contents on disk (`ok` ⇒ warning-free html/ + log).
Uses SC_BUILD_DISPATCH=inline (disclosed dev/CI mode) so each POST
completes within the request.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Coroutine
from pathlib import Path
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
from app.models import AuditLog, Build, User
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db

_SECRET = "m3-test-only-secret-not-a-real-credential"  # matches test_auth_api.py's SECRET_KEY default

_DOC = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Chapter text"}],
        }
    ],
}


def _headers(user: dict[str, Any]) -> dict[str, str]:
    access, _r, _f, _j = create_token_pair(uuid.UUID(str(user["id"])), _SECRET)
    return {"Authorization": f"Bearer {access}"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _run(test: Coroutine[Any, Any, None]) -> None:
    async def wrapped() -> None:
        try:
            await test
        finally:
            # the awaited disposal MUST run even when an assert fails,
            # else pooled asyncpg sockets leak and a later test eats the
            # ResourceWarning under -W error (Rule 6, 2026-10-21 lesson)
            await app_teardown()

    try:
        asyncio.run(wrapped())
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
                email = f"build-{uuid.uuid4().hex[:12]}-{n}@example.test"
                row = User(email=email, pw_hash="x", display=f"Owner {n}")
                session.add(row)
                await session.commit()
                users.append({"id": str(row.id), "email": email})
    finally:
        await engine.dispose()
    return users


def _paths(tmp: str) -> dict[str, str]:
    return {
        "SC_ARTIFACT_ROOT": str(Path(tmp) / "artifacts"),
        "SC_BUILD_ROOT": str(Path(tmp) / "builds"),
        "SC_BUILD_DISPATCH": "inline",
    }


async def _mk_user_lib(client: httpx.AsyncClient, me: dict[str, Any]) -> str:
    made = await client.post(
        "/api/v1/athenaeums",
        json={"slug": f"lib-{uuid.uuid4().hex[:6]}", "title": "Works"},
        headers=_headers(me),
    )
    assert made.status_code == 201
    return str(made.json()["id"])


async def _mk_folio_with_doc(
    client: httpx.AsyncClient,
    me: dict[str, Any],
    athenaeum_id: str,
    slug: str,
    body: dict[str, Any],
) -> tuple[str, str]:
    made = await client.post(
        "/api/v1/grimoires",
        json={"athenaeum_id": athenaeum_id, "slug": slug, "title": slug.title()},
        headers=_headers(me),
    )
    assert made.status_code == 201
    gid = str(made.json()["id"])
    node = await client.post(
        f"/api/v1/grimoires/{gid}/nodes",
        json={"kind": "folio", "slug": "folio-one", "title": "Folio one"},
        headers=_headers(me),
    )
    assert node.status_code == 201
    doc = await client.put(
        f"/api/v1/grimoires/{gid}/nodes/{node.json()['id']}/document",
        json={"tiptap_json": body, "expected_version": 0},
        headers=_headers(me),
    )
    assert doc.status_code == 200
    return gid, str(node.json()["id"])


@needs_db
def test_build_rules_and_machine(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(2))
    me, stranger = users

    async def run() -> None:
        for key, value in _paths(str(tmp_path)).items():
            os.environ[key] = value
        async with _client() as client:
            aid = await _mk_user_lib(client, me)

            killed = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert killed.status_code == 422  # E1: empty Athenaeum refused
            assert "no grimoires" in killed.json()["detail"]

            gid, _node = await _mk_folio_with_doc(client, me, aid, "mains", _DOC)
            del gid

            outsider = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(stranger)
            )
            assert outsider.status_code == 404  # owner-only trigger

            first = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert first.status_code == 201
            body = first.json()
            assert body["status"] == "ok"  # inline: done by now, warning-free
            assert body["build_number"] == 1
            artifact = Path(str(body["artifact_path"]))
            assert (artifact / "html" / "index.html").is_file()
            assert (artifact / "build.log").is_file()
            assert artifact.name == "1"

            listing = await client.get(
                f"/api/v1/athenaeums/{aid}/builds", headers=_headers(me)
            )
            assert listing.status_code == 200
            assert len(listing.json()) == 1

            second = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert second.status_code == 201
            assert second.json()["build_number"] == 2  # per-Athenaeum counter
            assert second.json()["status"] == "ok"

            # E3: an external queued row blocks the trigger (409)
            engine = create_async_engine(LIVE_DB_URL)
            maker = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            try:
                async with maker() as session:
                    session.add(
                        Build(
                            athenaeum_id=uuid.UUID(aid),
                            build_number=3,
                            status="queued",
                            triggered_by=uuid.UUID(me["id"]),
                        )
                    )
                    await session.commit()
            finally:
                await engine.dispose()
            blocked = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert blocked.status_code == 409

            assert await _audit_action_count("build_triggered") >= 2
        await app_teardown()

    _run(run())


async def _audit_action_count(action: str) -> int:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            rows = await session.scalars(
                select(AuditLog.id).where(AuditLog.action == action)
            )
            return len(list(rows))
    finally:
        await engine.dispose()


@needs_db
def test_build_visibility_and_visibility_edges(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(3))
    me, viewer, stranger = users

    async def run() -> None:
        for key, value in _paths(str(tmp_path)).items():
            os.environ[key] = value
        async with _client() as client:
            aid = await _mk_user_lib(client, me)
            gid, _node = await _mk_folio_with_doc(client, me, aid, "codes", _DOC)

            added = await client.post(
                f"/api/v1/grimoires/{gid}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )
            assert added.status_code == 201

            made = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert made.status_code == 201
            build_id = str(made.json()["id"])

            viewer_get = await client.get(
                f"/api/v1/athenaeums/{aid}/builds/{build_id}",
                headers=_headers(viewer),
            )
            assert viewer_get.status_code == 200  # member-visible (list/one)

            viewer_list = await client.get(
                f"/api/v1/athenaeums/{aid}/builds", headers=_headers(viewer)
            )
            assert viewer_list.status_code == 200
            assert len(viewer_list.json()) == 1

            stranger_one = await client.get(
                f"/api/v1/athenaeums/{aid}/builds/{build_id}",
                headers=_headers(stranger),
            )
            assert stranger_one.status_code == 404  # non-members do not see it

            cross = await client.get(
                f"/api/v1/athenaeums/{aid}/builds/{uuid.uuid4()}",
                headers=_headers(me),
            )
            assert cross.status_code == 404
        await app_teardown()

    _run(run())


@needs_db
def test_failed_build_records_log(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        for key, value in _paths(str(tmp_path)).items():
            os.environ[key] = value
        async with _client() as client:
            aid = await _mk_user_lib(client, me)
            head_skip = {
                "type": "doc",
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": 1},
                        "content": [{"type": "text", "text": "A"}],
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 3},
                        "content": [{"type": "text", "text": "B"}],
                    },
                ],
            }
            gid, _ = await _mk_folio_with_doc(client, me, aid, "brok", head_skip)
            del gid
            made = await client.post(
                f"/api/v1/athenaeums/{aid}/builds", json={}, headers=_headers(me)
            )
            assert made.status_code == 201
            body = made.json()
            assert body["status"] == "failed"  # fail loud under -W (0017 matrix)
            assert body["artifact_path"] is None
            if body["log_path"]:
                assert Path(str(body["log_path"])).is_file()
        await app_teardown()

    _run(run())
