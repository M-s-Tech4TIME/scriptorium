"""Folio document endpoint tests (M3 C5, decision 0024) — live PG18.

Optimistic concurrency (Q-M3-2=A): PUT carries `expected_version`,
mismatch → 409 with nothing written, every save bumps the version and
appends immutable history. Source cache (Q-M3-3=A): server-derived from
the canonical TipTap JSON via the grimoire's exporter; import-from-source
runs the M2 importer with ConversionError → 422. Reads for any member;
saves need editor/owner.
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
            "content": [{"type": "text", "text": "Hello folio"}],
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
                email = f"doc-{uuid.uuid4().hex[:12]}-{n}@example.test"
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
    source_format: str = "rst",
) -> dict[str, Any]:
    made = await client.post(
        "/api/v1/grimoires",
        json={
            "athenaeum_id": athenaeum_id,
            "slug": slug,
            "title": title,
            "source_format": source_format,
        },
        headers=_headers(user),
    )
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


async def _mk_folio(
    client: httpx.AsyncClient, user: dict[str, Any], grimoire_id: str, slug: str
) -> dict[str, Any]:
    made = await client.post(
        f"/api/v1/grimoires/{grimoire_id}/nodes",
        json={"kind": "folio", "slug": slug, "title": slug.title()},
        headers=_headers(user),
    )
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


@needs_db
def test_document_lifecycle_and_concurrency() -> None:
    users = asyncio.run(_seed_users(3))
    me, viewer, outsider = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "docs")
            g = await _mk_grimoire(client, me, aid, "doc-book", "Doc book")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "first-folio")
            base = f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document"

            empty = await client.get(base, headers=_headers(me))
            assert empty.status_code == 404  # no implicit empty row

            history_empty = await client.get(f"{base}/history", headers=_headers(me))
            assert history_empty.status_code == 404

            outsider_get = await client.get(base, headers=_headers(outsider))
            assert outsider_get.status_code == 404  # IDOR: uniform 404

            first = await client.put(
                base,
                json={"tiptap_json": _DOC, "expected_version": 0},
                headers=_headers(me),
            )
            assert first.status_code == 200
            assert first.json()["version"] == 1
            assert "Hello folio" in first.json()["source_text"]  # server-derived
            assert first.json()["source_format"] == "rst"
            assert first.json()["updated_by"] == me["id"]

            second = await client.put(
                base,
                json={"tiptap_json": _DOC, "expected_version": 1},
                headers=_headers(me),
            )
            assert second.status_code == 200
            assert second.json()["version"] == 2

            conflict = await client.put(
                base,
                json={"tiptap_json": _DOC, "expected_version": 1},
                headers=_headers(me),
            )
            assert conflict.status_code == 409  # stale writer (Q-M3-2=A)
            assert "expected 1" in conflict.json()["detail"]
            assert "current 2" in conflict.json()["detail"]

            history = await client.get(f"{base}/history", headers=_headers(me))
            assert history.status_code == 200
            versions = history.json()["versions"]
            assert [v["version"] for v in versions] == [1, 2]
            assert all(v["author"] == me["id"] for v in versions)
            assert "tiptap_json" not in versions[0]  # metadata list (0024)

            await client.post(
                f"/api/v1/grimoires/{gid}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )
            viewer_get = await client.get(base, headers=_headers(viewer))
            assert viewer_get.status_code == 200  # reads belong to any member
            viewer_put = await client.put(
                base,
                json={"tiptap_json": _DOC, "expected_version": 2},
                headers=_headers(viewer),
            )
            assert viewer_put.status_code == 403  # viewers never save (0024)

            assert await _audit_action("document_saved") >= 2

    _run(run())


@needs_db
def test_document_import_from_source_and_errors() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "import")
            g = await _mk_grimoire(client, me, aid, "import-book", "Import book")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "import-folio")
            base = f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document"

            imported = await client.put(
                base,
                json={
                    "source_text": "Title\n=====\n\npara\n",
                    "expected_version": 0,
                },
                headers=_headers(me),
            )
            assert imported.status_code == 200
            saved = imported.json()
            assert saved["version"] == 1
            assert saved["tiptap_json"]["type"] == "doc"
            headings = [
                child
                for child in saved["tiptap_json"]["content"]
                if child.get("type") == "heading"
            ]
            assert headings  # rst section title became a heading node

            boom = await client.put(
                base,
                json={
                    "source_text": "D\n==\n\n:x-unknown:`y`\n",
                    "expected_version": 1,
                },
                headers=_headers(me),
            )
            assert boom.status_code == 422  # unknown rst role → docutils errors
            assert "docutils" in boom.json()["detail"].lower()

            both = await client.put(
                base,
                json={
                    "tiptap_json": _DOC,
                    "source_text": "Title\n=====\n\npara\n",
                    "expected_version": 1,
                },
                headers=_headers(me),
            )
            assert both.status_code == 422  # exactly one content field

            neither = await client.put(
                base,
                json={"expected_version": 1},
                headers=_headers(me),
            )
            assert neither.status_code == 422

            wrong_shape = await client.put(
                base,
                json={"tiptap_json": {"type": "page"}, "expected_version": 1},
                headers=_headers(me),
            )
            assert wrong_shape.status_code == 422  # canonical shape check (0024)

            oversized = await client.put(
                base,
                json={"source_text": "x" * 1_000_001, "expected_version": 1},
                headers=_headers(me),
            )
            assert oversized.status_code == 422  # trust-boundary cap (Rule 2)

            myst_g = await _mk_grimoire(
                client, me, aid, "myst-book", "Myst book", source_format="myst"
            )
            myst_folio = await _mk_folio(client, me, str(myst_g["id"]), "myst-folio")
            myst_base = (
                f"/api/v1/grimoires/{myst_g['id']}/nodes/{myst_folio['id']}/document"
            )
            myst = await client.put(
                myst_base,
                json={"source_text": "# A\n\nbody\n", "expected_version": 0},
                headers=_headers(me),
            )
            assert myst.status_code == 200
            assert myst.json()["source_format"] == "myst"  # grimoire format wins

            # cross-grimoire addressing: folio of another grimoire via this path
            cross = await _mk_grimoire(client, me, aid, "cross-book", "Cross book")
            cross_folio = await _mk_folio(client, me, str(cross["id"]), "cross-folio")
            cross_get = await client.get(
                f"/api/v1/grimoires/{gid}/nodes/{cross_folio['id']}/document",
                headers=_headers(me),
            )
            assert cross_get.status_code == 404  # node not in this grimoire

            assert await _audit_action("document_saved") >= 2

    _run(run())


@needs_db
def test_document_history_detail_and_restore() -> None:
    users = asyncio.run(_seed_users(2))
    me, outsider = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "history")
            g = await _mk_grimoire(client, me, aid, "history-book", "History book")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "history-folio")
            base = f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document"

            first = await client.put(
                base,
                json={"tiptap_json": _DOC, "expected_version": 0},
                headers=_headers(me),
            )
            assert first.status_code == 200
            second_doc = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Second draft"}],
                    }
                ],
            }
            second = await client.put(
                base,
                json={"tiptap_json": second_doc, "expected_version": 1},
                headers=_headers(me),
            )
            assert second.status_code == 200

            detail = await client.get(f"{base}/history/1", headers=_headers(me))
            assert detail.status_code == 200
            assert detail.json()["version"] == 1
            assert detail.json()["tiptap_json"] == _DOC

            missing = await client.get(f"{base}/history/99", headers=_headers(me))
            assert missing.status_code == 404

            stale = await client.post(
                f"{base}/history/1/restore",
                json={"expected_version": 1},
                headers=_headers(me),
            )
            assert stale.status_code == 409

            restored = await client.post(
                f"{base}/history/1/restore",
                json={"expected_version": 2},
                headers=_headers(me),
            )
            assert restored.status_code == 200
            assert restored.json()["version"] == 3
            assert restored.json()["tiptap_json"] == _DOC

            outsider_get = await client.get(
                f"{base}/history/1", headers=_headers(outsider)
            )
            assert outsider_get.status_code == 404
            outsider_restore = await client.post(
                f"{base}/history/1/restore",
                json={"expected_version": 3},
                headers=_headers(outsider),
            )
            assert outsider_restore.status_code == 404

            history = await client.get(f"{base}/history", headers=_headers(me))
            assert [row["version"] for row in history.json()["versions"]] == [1, 2, 3]
            assert await _audit_action("document_restored") >= 1

    _run(run())
