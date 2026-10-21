"""Grimoire duplication tests (M3 C6, decision 0025) — live PG18.

Owner rulings: caller-supplied slug with optional auto-derivation
(`-copy`, `-copy-2`, …), owner-only roster (fresh, private copy), head
documents copied as v1 with no history clone, cross-library copies into
any owned Athenaeum, copy-of-copy allowed without lineage tracking.
Duplication itself is owner-only on the source (disclosed micro-default
per D2=A).
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
                email = f"dup-{uuid.uuid4().hex[:12]}-{n}@example.test"
                row = User(email=email, pw_hash="x", display=f"Owner {n}")
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
    theme: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "athenaeum_id": athenaeum_id,
        "slug": slug,
        "title": title,
    }
    if theme is not None:
        payload["theme"] = theme
    made = await client.post("/api/v1/grimoires", json=payload, headers=_headers(user))
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


async def _mk_node(
    client: httpx.AsyncClient,
    user: dict[str, Any],
    grimoire_id: str,
    kind: str,
    slug: str,
    title: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": kind, "slug": slug, "title": title}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    made = await client.post(
        f"/api/v1/grimoires/{grimoire_id}/nodes", json=payload, headers=_headers(user)
    )
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


def _flatten(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for n in nodes:
        flat.append({"kind": n["kind"], "slug": n["slug"], "position": n["position"]})
        flat.extend(_flatten(list(n["children"])))
    return flat


async def _seed_seeded_book(
    client: httpx.AsyncClient, me: dict[str, Any], aid: str, slug: str, title: str
) -> dict[str, Any]:
    """Grimoire with a themed tree, a nested folio, and a saved document."""
    category = await client.post(
        f"/api/v1/athenaeums/{aid}/categories",
        json={"name": "Shelf"},
        headers=_headers(me),
    )
    assert category.status_code == 201
    g = await _mk_grimoire(client, me, aid, slug, title, theme="dark-parchment")
    gid = str(g["id"])
    patched = await client.patch(
        f"/api/v1/grimoires/{gid}",
        json={"category_id": category.json()["id"]},
        headers=_headers(me),
    )
    assert patched.status_code == 200
    chapter = await _mk_node(client, me, gid, "chapter", "part-one", "Part one")
    await _mk_node(
        client, me, gid, "folio", "chapter-folio", "Chapter folio", chapter["id"]
    )
    doc_base = f"/api/v1/grimoires/{gid}/nodes/{chapter['id']}/document"
    first = await client.put(
        doc_base,
        json={"tiptap_json": _DOC, "expected_version": 0},
        headers=_headers(me),
    )
    assert first.status_code == 200
    second = await client.put(
        doc_base,
        json={"tiptap_json": _DOC, "expected_version": 1},
        headers=_headers(me),
    )
    assert second.status_code == 200  # original head is v2
    return g


@needs_db
def test_duplicate_deep_copy_fidelity() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "dup")
            g = await _seed_seeded_book(
                client, me, aid, "original-book", "Original book"
            )
            gid = str(g["id"])
            source_tree = (
                await client.get(f"/api/v1/grimoires/{gid}/tree", headers=_headers(me))
            ).json()
            source_chapter = source_tree["nodes"][0]
            source_doc = await client.get(
                f"/api/v1/grimoires/{gid}/nodes/{source_chapter['id']}/document",
                headers=_headers(me),
            )

            made = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={"slug": "twin-book"},
                headers=_headers(me),
            )
            assert made.status_code == 201
            twin = made.json()
            assert twin["slug"] == "twin-book"
            assert twin["title"] == "Original book (copy)"  # 0025 default suffix
            assert twin["athenaeum_id"] == aid
            assert twin["source_format"] == "rst"
            assert twin["theme"] == "dark-parchment"

            twin_tree = (
                await client.get(
                    f"/api/v1/grimoires/{twin['id']}/tree", headers=_headers(me)
                )
            ).json()
            assert _flatten(twin_tree["nodes"]) == _flatten(source_tree["nodes"])
            assert twin_tree["nodes"][0]["id"] != source_chapter["id"]

            twin_doc = await client.get(
                f"/api/v1/grimoires/{twin['id']}/nodes/{twin_tree['nodes'][0]['id']}/document",
                headers=_headers(me),
            )
            assert twin_doc.status_code == 200
            assert twin_doc.json()["version"] == 1  # head content as v1 (ruling c)
            assert twin_doc.json()["tiptap_json"] == source_doc.json()["tiptap_json"]
            assert twin_doc.json()["source_text"] == source_doc.json()["source_text"]

            twin_history = await client.get(
                f"/api/v1/grimoires/{twin['id']}/nodes/{twin_tree['nodes'][0]['id']}/document/history",
                headers=_headers(me),
            )
            assert [v["version"] for v in twin_history.json()["versions"]] == [1]

            roster = await client.get(
                f"/api/v1/grimoires/{twin['id']}/members", headers=_headers(me)
            )
            members = roster.json()
            assert len(members) == 1  # ruling b: fresh roster
            assert members[0]["role"] == "owner"
            assert members[0]["user_id"] == me["id"]

            still = await client.get(
                f"/api/v1/grimoires/{gid}/nodes/{source_chapter['id']}/document",
                headers=_headers(me),
            )
            assert still.json()["version"] == 2  # source untouched

            assert await _audit_action("grimoire_duplicated") >= 1
        await app_teardown()

    _run(run())


@needs_db
def test_duplicate_rules_and_edges() -> None:
    users = asyncio.run(_seed_users(3))
    me, editor, stranger = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "dup")
            other_lib = await _mk_lib(client, me, "dup")
            g = await _mk_grimoire(client, me, aid, "twin-src", "Twin src")
            gid = str(g["id"])

            auto_one = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={},
                headers=_headers(me),
            )
            assert auto_one.status_code == 201
            assert auto_one.json()["slug"] == "twin-src-copy"
            assert auto_one.json()["title"] == "Twin src (copy)"

            auto_two = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={},
                headers=_headers(me),
            )
            assert auto_two.status_code == 201
            assert auto_two.json()["slug"] == "twin-src-copy-2"

            collision = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={"slug": "twin-src-copy"},
                headers=_headers(me),
            )
            assert collision.status_code == 409

            invalid = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={"slug": "Not Valid!"},
                headers=_headers(me),
            )
            assert invalid.status_code == 422

            cross = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={"athenaeum_id": other_lib, "slug": "cross-twin"},
                headers=_headers(me),
            )
            assert cross.status_code == 201
            assert cross.json()["athenaeum_id"] == other_lib

            foreign_lib = await _mk_lib(client, stranger, "dup")
            foreign_target = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={"athenaeum_id": foreign_lib},
                headers=_headers(me),
            )
            assert foreign_target.status_code == 404  # target you do not own

            outsider = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={},
                headers=_headers(stranger),
            )
            assert outsider.status_code == 404  # IDOR on the source

            await client.post(
                f"/api/v1/grimoires/{gid}/members",
                json={"email": editor["email"], "role": "editor"},
                headers=_headers(me),
            )
            editor_copy = await client.post(
                f"/api/v1/grimoires/{gid}/duplicate",
                json={},
                headers=_headers(editor),
            )
            assert editor_copy.status_code == 403  # owner-only (0025 micro-default)

            copy_of_copy = await client.post(
                f"/api/v1/grimoires/{auto_one.json()['id']}/duplicate",
                json={"slug": "grand-twin"},
                headers=_headers(me),
            )
            assert copy_of_copy.status_code == 201  # ruling e: allowed

            assert await _audit_action("grimoire_duplicated") >= 5
        await app_teardown()

    _run(run())
