"""Grimoire tree endpoint tests (M3 C4, decision 0023) — live PG18.

Chapters & Folios under the owner's rulings: any member reads `GET /tree`,
mutations are owner-only (D2=A), delete refuses 409 while a node holds
sub-nodes or a folio document (D1=A), re-parent is same-Grimoire with a
cycle guard, sibling reorder is 1-based insert-displacement, slugs are
renamable per sibling set (0021). Kinds are `chapter|folio` (0022).
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
from app.models import AuditLog, Document, Node, User
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
                email = f"tree-{uuid.uuid4().hex[:12]}-{n}@example.test"
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
) -> dict[str, Any]:
    made = await client.post(
        "/api/v1/grimoires",
        json={"athenaeum_id": athenaeum_id, "slug": slug, "title": title},
        headers=_headers(user),
    )
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


def _tree_slugs(nodes: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for n in nodes:
        found.append(str(n["slug"]))
        found.extend(_tree_slugs(list(n["children"])))
    return found


@needs_db
def test_tree_read_shape_and_access() -> None:
    users = asyncio.run(_seed_users(3))
    me, viewer, outsider = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "tree")
            g = await _mk_grimoire(client, me, aid, "tree-book", "Tree book")
            gid = str(g["id"])

            outsider_tree = await client.get(
                f"/api/v1/grimoires/{gid}/tree", headers=_headers(outsider)
            )
            assert outsider_tree.status_code == 404  # IDOR: no existence leak

            outsider_create = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={"kind": "chapter", "slug": "x", "title": "X"},
                headers=_headers(outsider),
            )
            assert outsider_create.status_code == 404

            viewer_pre = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={"kind": "chapter", "slug": "x", "title": "X"},
                headers=_headers(viewer),
            )
            assert viewer_pre.status_code == 404  # not a member at all

            joined = await client.post(
                f"/api/v1/grimoires/{gid}/members",
                json={"email": viewer["email"], "role": "viewer"},
                headers=_headers(me),
            )
            assert joined.status_code == 201

            viewer_post = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={"kind": "chapter", "slug": "x", "title": "X"},
                headers=_headers(viewer),
            )
            assert viewer_post.status_code == 403  # member under the role (D2=A)

            viewer_tree = await client.get(
                f"/api/v1/grimoires/{gid}/tree", headers=_headers(viewer)
            )
            assert viewer_tree.status_code == 200  # reads belong to any member
            assert viewer_tree.json()["nodes"] == []

            chapter = await _mk_node(client, me, gid, "chapter", "part-one", "Part one")
            folio = await _mk_node(
                client, me, gid, "folio", "intro-folio", "Intro", chapter["id"]
            )
            deep = await _mk_node(
                client, me, gid, "folio", "nested-folio", "Nested", folio["id"]
            )
            _ = deep

            tree = (
                await client.get(f"/api/v1/grimoires/{gid}/tree", headers=_headers(me))
            ).json()
            roots = tree["nodes"]
            assert len(roots) == 1
            top = roots[0]
            assert top["kind"] == "chapter"
            assert _tree_slugs([top]) == ["part-one", "intro-folio", "nested-folio"]
            assert _tree_slugs(list(top["children"])) == [
                "intro-folio",
                "nested-folio",
            ]
            assert top["position"] == 1

            viewer_bad = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{chapter['id']}",
                json={"title": "nope"},
                headers=_headers(viewer),
            )
            assert viewer_bad.status_code == 403

            assert await _audit_action("node_created") >= 3
        await app_teardown()

    _run(run())


@needs_db
def test_node_create_validation() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "create")
            g = await _mk_grimoire(client, me, aid, "kindling", "Kindling")
            gid = str(g["id"])

            chapter = await _mk_node(client, me, gid, "chapter", "one", "Chapter one")
            first_folio = await _mk_node(
                client, me, gid, "folio", "alpha", "Alpha", chapter["id"]
            )
            assert first_folio["position"] == 1  # positions are per sibling set

            dup = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={
                    "kind": "folio",
                    "slug": "alpha",
                    "title": "again",
                    "parent_id": chapter["id"],
                },
                headers=_headers(me),
            )
            assert dup.status_code == 409  # collision inside the same sibling set

            other_chapter = await _mk_node(client, me, gid, "chapter", "two", "Two")
            same_elsewhere = await _mk_node(
                client, me, gid, "folio", "alpha", "Alpha", other_chapter["id"]
            )
            assert same_elsewhere["position"] == 1  # fresh sibling set, same slug ok

            invalid = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={"kind": "folio", "slug": "Bad Slug!", "title": "x"},
                headers=_headers(me),
            )
            assert invalid.status_code == 422

            wrong_kind = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={"kind": "tome", "slug": "tome", "title": "x"},
                headers=_headers(me),
            )
            assert wrong_kind.status_code == 422  # Literal: chapter|folio only

            missing_parent = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={
                    "kind": "folio",
                    "slug": "orphan",
                    "title": "x",
                    "parent_id": str(uuid.uuid4()),
                },
                headers=_headers(me),
            )
            assert missing_parent.status_code == 404

            cross_g = await _mk_grimoire(client, me, aid, "elsewhere-book", "Elsewhere")
            cross_node = await _mk_node(
                client, me, str(cross_g["id"]), "chapter", "cross-ch", "Cross ch"
            )
            foreign = await client.post(
                f"/api/v1/grimoires/{gid}/nodes",
                json={
                    "kind": "folio",
                    "slug": "cross",
                    "title": "x",
                    "parent_id": cross_node["id"],
                },
                headers=_headers(me),
            )
            assert foreign.status_code == 404  # parent of another grimoire
            assert await _audit_action("node_created") >= 4
        await app_teardown()

    _run(run())


@needs_db
def test_node_patch_reorder_reparent_cycle_and_slug() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "patch")
            g = await _mk_grimoire(client, me, aid, "patch-book", "Patch book")
            gid = str(g["id"])

            ch1 = await _mk_node(client, me, gid, "chapter", "ch-one", "One")
            ch2 = await _mk_node(client, me, gid, "chapter", "ch-two", "Two")
            f1 = await _mk_node(client, me, gid, "folio", "alpha", "Alpha", ch1["id"])
            f2 = await _mk_node(client, me, gid, "folio", "bravo", "Bravo", ch1["id"])

            renamed = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f1['id']}",
                json={"slug": "renamed"},
                headers=_headers(me),
            )
            assert renamed.status_code == 200

            dup = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f2['id']}",
                json={"slug": "renamed"},
                headers=_headers(me),
            )
            assert dup.status_code == 409

            freed = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f2['id']}",
                json={"slug": "alpha"},
                headers=_headers(me),
            )
            assert freed.status_code == 200  # released slugs are reusable (0021)

            floated = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f2['id']}",
                json={"slug": None},
                headers=_headers(me),
            )
            assert floated.status_code == 422  # nothing floats (0021)

            moved = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{ch2['id']}",
                json={"position": 1},
                headers=_headers(me),
            )
            assert moved.status_code == 200
            tree = (
                await client.get(f"/api/v1/grimoires/{gid}/tree", headers=_headers(me))
            ).json()
            assert [n["slug"] for n in tree["nodes"]] == ["ch-two", "ch-one"]

            to_root = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f2['id']}",
                json={"parent_id": None},
                headers=_headers(me),
            )
            assert to_root.status_code == 200
            tree = (
                await client.get(f"/api/v1/grimoires/{gid}/tree", headers=_headers(me))
            ).json()
            assert f2["id"] in [n["id"] for n in tree["nodes"]]

            nest = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{f2['id']}",
                json={"parent_id": ch2["id"]},
                headers=_headers(me),
            )
            assert nest.status_code == 200

            grandchild = await _mk_node(
                client, me, gid, "chapter", "ch-three", "Three", ch1["id"]
            )

            self_move = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{ch1['id']}",
                json={"parent_id": ch1["id"]},
                headers=_headers(me),
            )
            assert self_move.status_code == 409  # under itself

            under_descendant = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{ch1['id']}",
                json={"parent_id": grandchild["id"]},
                headers=_headers(me),
            )
            assert under_descendant.status_code == 409  # own subtree (cycle)

            foreign = await client.patch(
                f"/api/v1/grimoires/{gid}/nodes/{ch1['id']}",
                json={"parent_id": str(uuid.uuid4())},
                headers=_headers(me),
            )
            assert foreign.status_code == 404

            assert await _audit_action("node_moved") >= 3
            assert await _audit_action("node_patched") >= 1
        await app_teardown()

    _run(run())


@needs_db
def test_node_delete_refusal_then_success() -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "delete")
            g = await _mk_grimoire(client, me, aid, "delete-book", "Delete book")
            gid = str(g["id"])

            chapter = await _mk_node(client, me, gid, "chapter", "keeper", "Keeper")
            folio = await _mk_node(
                client, me, gid, "folio", "doc-folio", "Doc folio", chapter["id"]
            )
            loose = await _mk_node(client, me, gid, "folio", "loose-folio", "Loose")
            _ = folio  # flavour: the folio stays under `chapter` for the refusal

            denied_children = await client.delete(
                f"/api/v1/grimoires/{gid}/nodes/{chapter['id']}",
                headers=_headers(me),
            )
            assert denied_children.status_code == 409  # still holds the folio (D1=A)

            engine = create_async_engine(LIVE_DB_URL)
            maker = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            try:
                async with maker() as session:
                    node = (
                        await session.scalars(
                            select(Node).where(Node.id == uuid.UUID(loose["id"]))
                        )
                    ).one()
                    session.add(Document(node_id=node.id))
                    await session.commit()
            finally:
                await engine.dispose()

            denied_document = await client.delete(
                f"/api/v1/grimoires/{gid}/nodes/{loose['id']}",
                headers=_headers(me),
            )
            assert denied_document.status_code == 409  # folio holds its document

            engine = create_async_engine(LIVE_DB_URL)
            maker = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            try:
                async with maker() as session:
                    doc = (
                        await session.scalars(
                            select(Document).where(
                                Document.node_id == uuid.UUID(loose["id"])
                            )
                        )
                    ).one()
                    await session.delete(doc)
                    await session.commit()
            finally:
                await engine.dispose()

            emptied = await client.delete(
                f"/api/v1/grimoires/{gid}/nodes/{loose['id']}",
                headers=_headers(me),
            )
            assert emptied.status_code == 204

            tree = (
                await client.get(f"/api/v1/grimoires/{gid}/tree", headers=_headers(me))
            ).json()
            assert "loose-folio" not in _tree_slugs(list(tree["nodes"]))

            assert await _audit_action("node_deleted") >= 1
        await app_teardown()

    _run(run())
