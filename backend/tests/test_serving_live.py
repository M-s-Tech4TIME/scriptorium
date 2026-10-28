"""Serving-phase API + static-site tests (decision 0035) — live PG18 + Sphinx.

One real site, two builds, both publication channels. Covers:

- public_slug global uniqueness while editor slugs stay per-owner;
- private-by-default visibility, owner/member access (bearer + `/a` cookie),
  and the uniform 404 for outsiders;
- latest/stable pointers, numbered immutable URLs, unpublish/rollback;
- E2 headers/CSP from the manifest, cache policy, no inline style;
- custom CSS as a build-bound external file, namespaced and URL-free;
- path traversal and directory-redirect behavior.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import create_token_pair
from app.main import app
from app.models import AuditLog, Build, Membership, User
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db

_SECRET = "m3-test-only-secret-not-a-real-credential"

_DOC_ONE = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Chapter text"}],
        }
    ],
}
_DOC_TWO = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Second chapter text"}],
        }
    ],
}


def _headers(user: dict[str, Any]) -> dict[str, str]:
    access, _r, _f, _j = create_token_pair(uuid.UUID(str(user["id"])), _SECRET)
    return {"Authorization": f"Bearer {access}"}


def _access(user: dict[str, Any]) -> str:
    access, _r, _f, _j = create_token_pair(uuid.UUID(str(user["id"])), _SECRET)
    return access


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


def _run(test: Coroutine[Any, Any, None]) -> None:
    async def wrapped() -> None:
        try:
            await test
        finally:
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
                email = f"serve-{uuid.uuid4().hex[:12]}-{n}@example.test"
                row = User(email=email, pw_hash="x", display=f"Reader {n}")
                session.add(row)
                await session.commit()
                users.append({"id": str(row.id), "email": email})
    finally:
        await engine.dispose()
    return users


async def _add_member(user_id: str, grimoire_id: str) -> None:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            session.add(
                Membership(
                    user_id=uuid.UUID(user_id),
                    grimoire_id=uuid.UUID(grimoire_id),
                    role="viewer",
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


async def _mk_lib(
    client: httpx.AsyncClient, user: dict[str, Any], slug: str
) -> dict[str, Any]:
    made = await client.post(
        "/api/v1/athenaeums",
        json={"slug": slug, "title": "Works"},
        headers=_headers(user),
    )
    assert made.status_code == 201, made.text
    return cast(dict[str, Any], made.json())


async def _mk_folio(
    client: httpx.AsyncClient, user: dict[str, Any], athenaeum_id: str
) -> tuple[str, str]:
    made = await client.post(
        "/api/v1/grimoires",
        json={
            "athenaeum_id": athenaeum_id,
            "slug": f"book-{uuid.uuid4().hex[:6]}",
            "title": "Book",
        },
        headers=_headers(user),
    )
    assert made.status_code == 201, made.text
    gid = str(made.json()["id"])
    node = await client.post(
        f"/api/v1/grimoires/{gid}/nodes",
        json={"kind": "folio", "slug": "folio-one", "title": "Folio one"},
        headers=_headers(user),
    )
    assert node.status_code == 201, node.text
    node_id = str(node.json()["id"])
    doc = await client.put(
        f"/api/v1/grimoires/{gid}/nodes/{node_id}/document",
        json={"tiptap_json": _DOC_ONE, "expected_version": 0},
        headers=_headers(user),
    )
    assert doc.status_code == 200, doc.text
    return gid, node_id


async def _build(
    client: httpx.AsyncClient, user: dict[str, Any], athenaeum_id: str
) -> dict[str, Any]:
    made = await client.post(
        f"/api/v1/athenaeums/{athenaeum_id}/builds",
        json={},
        headers=_headers(user),
    )
    assert made.status_code == 201, made.text
    body = cast(dict[str, Any], made.json())
    assert body["status"] == "ok", body
    return body


@needs_db
def test_publication_visibility_serving_and_e2(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(3))
    me, member, stranger = users

    async def run() -> None:
        for key, value in {
            "SC_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
            "SC_BUILD_ROOT": str(tmp_path / "builds"),
            "SC_BUILD_DISPATCH": "inline",
        }.items():
            os.environ[key] = value

        async with _client() as client:
            base = f"works-{uuid.uuid4().hex[:8]}"
            lib = await _mk_lib(client, me, base)
            aid = str(lib["id"])
            public_slug = str(lib["public_slug"])
            assert lib["is_public"] is False
            assert public_slug.startswith(base)

            # D1 global public name, while the editor slug stays per-owner.
            other_lib = await _mk_lib(client, stranger, base)
            assert other_lib["slug"] == base
            assert other_lib["public_slug"] != public_slug
            assert str(other_lib["public_slug"]).startswith(base)

            # D1 immutability: editor-side rename never changes the public URL.
            renamed = await client.patch(
                f"/api/v1/athenaeums/{aid}",
                json={"slug": f"{base}-renamed"},
                headers=_headers(me),
            )
            assert renamed.status_code == 200
            assert renamed.json()["slug"] == f"{base}-renamed"
            assert renamed.json()["public_slug"] == public_slug

            gid, node_id = await _mk_folio(client, me, aid)

            # B3 private default: no anonymous view, even before publication.
            private = await client.get(f"/a/{public_slug}/latest/")
            assert private.status_code == 404

            b1 = await _build(client, me, aid)

            # Publication is owner-only and refuses non-servable builds.
            assert (
                await client.post(
                    f"/api/v1/athenaeums/{aid}/publish",
                    json={"build_id": b1["id"]},
                    headers=_headers(stranger),
                )
            ).status_code == 404
            assert (
                await client.post(
                    f"/api/v1/athenaeums/{other_lib['id']}/publish",
                    json={"build_id": b1["id"]},
                    headers=_headers(stranger),
                )
            ).status_code == 404
            empty_artifact = tmp_path / "empty-artifact"
            (empty_artifact / "html").mkdir(parents=True)
            engine = create_async_engine(LIVE_DB_URL)
            maker = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            refused_ids: list[str] = []
            try:
                async with maker() as session:
                    failed = Build(
                        athenaeum_id=uuid.UUID(aid),
                        build_number=90,
                        status="failed",
                        triggered_by=uuid.UUID(me["id"]),
                        artifact_path=b1["artifact_path"],
                    )
                    no_manifest = Build(
                        athenaeum_id=uuid.UUID(aid),
                        build_number=91,
                        status="ok",
                        triggered_by=uuid.UUID(me["id"]),
                        artifact_path=str(empty_artifact),
                    )
                    session.add_all([failed, no_manifest])
                    await session.flush()
                    refused_ids = [str(failed.id), str(no_manifest.id)]
                    await session.commit()
            finally:
                await engine.dispose()
            for build_id in refused_ids:
                refused = await client.post(
                    f"/api/v1/athenaeums/{aid}/publish",
                    json={"build_id": build_id},
                    headers=_headers(me),
                )
                assert refused.status_code == 409, refused.text

            stable = await client.post(
                f"/api/v1/athenaeums/{aid}/publish",
                json={"build_id": b1["id"], "channel": "stable"},
                headers=_headers(me),
            )
            assert stable.status_code == 200, stable.text
            stable_body = stable.json()
            assert stable_body["latest"] is None
            assert stable_body["stable"]["build_number"] == 1

            # Owner can read private content; outsider still sees 404.
            private_root = await client.get(f"/a/{public_slug}/", headers=_headers(me))
            assert private_root.status_code == 307
            assert private_root.headers["cache-control"] == "private, no-store"
            assert private_root.headers["vary"] == "Cookie"
            assert private_root.headers["x-robots-tag"] == "noindex, nofollow"
            owner_view = await client.get(
                f"/a/{public_slug}/stable/", headers=_headers(me)
            )
            assert owner_view.status_code == 200
            assert 'data-sd-athenaeum="' + public_slug + '"' in owner_view.text
            book_dir = next(
                p.name
                for p in (Path(str(b1["artifact_path"])) / "html").iterdir()
                if p.is_dir() and p.name.startswith("book-")
            )
            owner_page = await client.get(
                f"/a/{public_slug}/stable/{book_dir}/folio-one.html",
                headers=_headers(me),
            )
            assert owner_page.status_code == 200
            assert "Chapter text" in owner_page.text
            assert "style=" not in owner_page.text
            csp = owner_page.headers["content-security-policy"]
            assert "script-src 'self'" in csp
            assert "sha256-" in csp
            assert "unsafe-inline" not in csp
            assert "style-src 'self'" in csp
            assert owner_view.headers["cache-control"] == "private, no-store"
            assert owner_view.headers["x-robots-tag"] == "noindex, nofollow"
            assert owner_view.headers["x-scriptorium-build"] == f"{public_slug}/1"

            # Member via the `/a` access cookie (browser navigation path).
            await _add_member(member["id"], gid)
            member_view = await client.get(
                f"/a/{public_slug}/stable/",
                headers={"Cookie": f"scriptorium_access={_access(member)}"},
            )
            assert member_view.status_code == 200
            assert member_view.headers["cache-control"] == "private, no-store"

            outsider = await client.get(
                f"/a/{public_slug}/stable/", headers=_headers(stranger)
            )
            assert outsider.status_code == 404

            # Root follows the available channel.
            root = await client.get(f"/a/{public_slug}/", headers=_headers(me))
            assert root.status_code == 307
            assert root.headers["location"].endswith(f"/a/{public_slug}/stable/")

            # B3 public toggle: anonymous reading becomes possible.
            published = await client.patch(
                f"/api/v1/athenaeums/{aid}",
                json={"is_public": True},
                headers=_headers(me),
            )
            assert published.status_code == 200
            assert published.json()["is_public"] is True
            anon = await client.get(f"/a/{public_slug}/stable/")
            assert anon.status_code == 200
            assert anon.headers["cache-control"] == "no-cache"
            assert "x-robots-tag" not in anon.headers

            # E2 custom CSS is validated now and materialized on the next build.
            bad_css = await client.put(
                f"/api/v1/athenaeums/{aid}/custom-css",
                json={"css": ".x { background: url(https://evil.example/x); }"},
                headers=_headers(me),
            )
            assert bad_css.status_code == 422
            good_css = await client.put(
                f"/api/v1/athenaeums/{aid}/custom-css",
                json={"css": ":root { --sd-accent: #123456; } body { color: #111; }"},
                headers=_headers(me),
            )
            assert good_css.status_code == 200, good_css.text
            assert "html[data-sd-athenaeum]" in good_css.json()["css"]
            fetched_css = await client.get(
                f"/api/v1/athenaeums/{aid}/custom-css", headers=_headers(me)
            )
            assert fetched_css.status_code == 200
            assert fetched_css.json()["css"] == good_css.json()["css"]
            assert (
                await client.get(
                    f"/api/v1/athenaeums/{aid}/custom-css",
                    headers=_headers(stranger),
                )
            ).status_code == 404

            changed = await client.put(
                f"/api/v1/grimoires/{gid}/nodes/{node_id}/document",
                json={"tiptap_json": _DOC_TWO, "expected_version": 1},
                headers=_headers(me),
            )
            assert changed.status_code == 200, changed.text
            b2 = await _build(client, me, aid)
            b2_number = int(b2["build_number"])
            latest = await client.post(
                f"/api/v1/athenaeums/{aid}/publish",
                json={"build_id": b2["id"], "channel": "latest"},
                headers=_headers(me),
            )
            assert latest.status_code == 200, latest.text
            publication = latest.json()
            assert publication["latest"]["build_number"] == b2_number
            assert publication["stable"]["build_number"] == 1

            latest_view = await client.get(f"/a/{public_slug}/latest/")
            assert latest_view.status_code == 200
            assert "_static/custom.css" in latest_view.text
            assert "style=" not in latest_view.text
            assert latest_view.headers["cache-control"] == "no-cache"
            latest_page = await client.get(
                f"/a/{public_slug}/latest/{book_dir}/folio-one.html"
            )
            assert latest_page.status_code == 200
            assert "Second chapter text" in latest_page.text

            # Immutable numbered build keeps the old content/CSS (A2).
            old = await client.get(f"/a/{public_slug}/b/1/")
            assert old.status_code == 200
            assert "_static/custom.css" not in old.text
            assert old.headers["cache-control"] == "public, max-age=31536000, immutable"
            assert old.headers["x-scriptorium-build"] == f"{public_slug}/1"
            old_page = await client.get(
                f"/a/{public_slug}/b/1/{book_dir}/folio-one.html"
            )
            assert old_page.status_code == 200
            assert "Chapter text" in old_page.text

            new = await client.get(f"/a/{public_slug}/b/{b2_number}/")
            assert new.status_code == 200
            assert new.headers["cache-control"] == "public, max-age=31536000, immutable"
            new_page = await client.get(
                f"/a/{public_slug}/b/{b2_number}/{book_dir}/folio-one.html"
            )
            assert new_page.status_code == 200
            assert "Second chapter text" in new_page.text

            # Clearing the input does not mutate the already-published build.
            cleared_css = await client.delete(
                f"/api/v1/athenaeums/{aid}/custom-css", headers=_headers(me)
            )
            assert cleared_css.status_code == 204
            assert (
                await client.get(
                    f"/api/v1/athenaeums/{aid}/custom-css",
                    headers=_headers(me),
                )
            ).json()["css"] == ""

            # Slash-less channel/numbered roots redirect to the canonical URL.
            latest_root = await client.get(f"/a/{public_slug}/latest")
            assert latest_root.status_code == 307
            assert latest_root.headers["location"].endswith(f"/a/{public_slug}/latest/")
            numbered_root = await client.get(f"/a/{public_slug}/b/{b2_number}")
            assert numbered_root.status_code == 307
            assert numbered_root.headers["location"].endswith(
                f"/a/{public_slug}/b/{b2_number}/"
            )

            # Directory redirect + missing/traversal refusals.
            redirected = await client.get(f"/a/{public_slug}/latest/{book_dir}")
            assert redirected.status_code == 307
            assert redirected.headers["location"].endswith(f"/{book_dir}/")
            assert (
                await client.get(f"/a/{public_slug}/latest/missing.html")
            ).status_code == 404
            assert (await client.get(f"/a/{public_slug}/b/nope/")).status_code == 404
            assert (
                await client.get(f"/a/{public_slug}/latest/%2e%2e/%2e%2e/etc/passwd")
            ).status_code == 404

            # A never-published build is not addressable by number.
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
                            status="ok",
                            triggered_by=uuid.UUID(me["id"]),
                            artifact_path=b2["artifact_path"],
                        )
                    )
                    await session.commit()
            finally:
                await engine.dispose()
            assert (await client.get(f"/a/{public_slug}/b/3/")).status_code == 404

            # Unpublish latest: alias dies, numbered build remains; stable wins root.
            gone = await client.delete(
                f"/api/v1/athenaeums/{aid}/publish?channel=latest",
                headers=_headers(me),
            )
            assert gone.status_code == 204
            assert (await client.get(f"/a/{public_slug}/latest/")).status_code == 404
            assert (
                await client.get(f"/a/{public_slug}/b/{b2_number}/")
            ).status_code == 200
            root_again = await client.get(f"/a/{public_slug}/")
            assert root_again.status_code == 307
            assert root_again.headers["location"].endswith(f"/a/{public_slug}/stable/")

            # Owner-only publication surface.
            assert (
                await client.get(
                    f"/api/v1/athenaeums/{aid}/publication",
                    headers=_headers(stranger),
                )
            ).status_code == 404
            pub = await client.get(
                f"/api/v1/athenaeums/{aid}/publication", headers=_headers(me)
            )
            assert pub.status_code == 200
            assert pub.json()["latest"] is None
            assert pub.json()["stable"]["build_number"] == 1

            # Toggle back to private: anonymous 404 again, owner still reads.
            await client.patch(
                f"/api/v1/athenaeums/{aid}",
                json={"is_public": False},
                headers=_headers(me),
            )
            assert (await client.get(f"/a/{public_slug}/stable/")).status_code == 404
            assert (
                await client.get(f"/a/{public_slug}/stable/", headers=_headers(me))
            ).status_code == 200

            # Publish to both channels and verify the both-channel response.
            both = await client.post(
                f"/api/v1/athenaeums/{aid}/publish",
                json={"build_id": b2["id"], "channel": "both"},
                headers=_headers(me),
            )
            assert both.status_code == 200
            assert both.json()["latest"]["build_number"] == b2_number
            assert both.json()["stable"]["build_number"] == b2_number

    _run(run())


@needs_db
def test_public_name_rename_aliases_and_tombstones(tmp_path: Path) -> None:
    """Decision 0036: renames, permanent aliases, and tombstones.

    The artifact is built once before the rename. Every old public name must
    keep working as a 308 alias (after private authorization), preserve the
    path/query, and resolve directly to the current name; deletion leaves a
    permanent tombstone that no site can reclaim.
    """
    users = asyncio.run(_seed_users(3))
    me, member, stranger = users

    async def run() -> None:
        for key, value in {
            "SC_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
            "SC_BUILD_ROOT": str(tmp_path / "builds"),
            "SC_BUILD_DISPATCH": "inline",
        }.items():
            os.environ[key] = value

        async with _client() as client:
            base = f"durable-{uuid.uuid4().hex[:8]}"
            lib = await _mk_lib(client, me, base)
            aid = str(lib["id"])
            original = str(lib["public_slug"])
            assert original.startswith(base)

            gid, _node_id = await _mk_folio(client, me, aid)
            b1 = await _build(client, me, aid)
            number = int(b1["build_number"])
            published = await client.post(
                f"/api/v1/athenaeums/{aid}/publish",
                json={"build_id": b1["id"], "channel": "stable"},
                headers=_headers(me),
            )
            assert published.status_code == 200, published.text
            book_dir = next(
                p.name
                for p in (Path(str(b1["artifact_path"])) / "html").iterdir()
                if p.is_dir() and p.name.startswith("book-")
            )

            # Private alias: authorization happens before the redirect, so
            # an outsider cannot use the old name to discover the site.
            assert (await client.get(f"/a/{original}/")).status_code == 404
            next_slug = f"{base}-next"
            renamed = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": next_slug},
                headers=_headers(me),
            )
            assert renamed.status_code == 200, renamed.text
            assert renamed.json()["public_slug"] == next_slug

            private_alias = await client.get(f"/a/{original}/", headers=_headers(me))
            assert private_alias.status_code == 308
            assert private_alias.headers["location"] == f"/a/{next_slug}/"
            assert private_alias.headers["cache-control"] == "private, no-store"
            assert private_alias.headers["vary"] == "Cookie"
            assert private_alias.headers["x-robots-tag"] == "noindex, nofollow"

            private_page = await client.get(
                f"/a/{original}/stable/{book_dir}/folio-one.html?utm=1",
                headers=_headers(me),
            )
            assert private_page.status_code == 308
            assert private_page.headers["location"] == (
                f"/a/{next_slug}/stable/{book_dir}/folio-one.html?utm=1"
            )

            await _add_member(member["id"], gid)
            member_alias = await client.get(
                f"/a/{original}/stable/", headers=_headers(member)
            )
            assert member_alias.status_code == 308
            assert member_alias.headers["cache-control"] == "private, no-store"
            assert (
                await client.get(f"/a/{original}/stable/", headers=_headers(stranger))
            ).status_code == 404

            publication = await client.get(
                f"/api/v1/athenaeums/{aid}/publication", headers=_headers(me)
            )
            assert publication.status_code == 200
            assert [a["slug"] for a in publication.json()["public_aliases"]] == [
                original
            ]

            # Public alias: 308, no-cache, path/query preserved, no noindex.
            await client.patch(
                f"/api/v1/athenaeums/{aid}",
                json={"is_public": True},
                headers=_headers(me),
            )
            public_alias = await client.get(
                f"/a/{original}/stable/{book_dir}/folio-one.html?utm=1"
            )
            assert public_alias.status_code == 308
            assert public_alias.headers["location"] == (
                f"/a/{next_slug}/stable/{book_dir}/folio-one.html?utm=1"
            )
            assert public_alias.headers["cache-control"] == "no-cache"
            assert "x-robots-tag" not in public_alias.headers

            canonical_page = await client.get(
                f"/a/{next_slug}/stable/{book_dir}/folio-one.html"
            )
            assert canonical_page.status_code == 200
            assert "Chapter text" in canonical_page.text
            assert canonical_page.headers["x-scriptorium-build"] == (
                f"{next_slug}/{number}"
            )
            # The artifact was not rebuilt: its build-time identity is old.
            assert f'data-sd-athenaeum="{original}"' in canonical_page.text

            numbered_alias = await client.get(
                f"/a/{original}/b/{number}/{book_dir}/folio-one.html?x=1"
            )
            assert numbered_alias.status_code == 308
            assert numbered_alias.headers["location"] == (
                f"/a/{next_slug}/b/{number}/{book_dir}/folio-one.html?x=1"
            )
            numbered = await client.get(
                f"/a/{next_slug}/b/{number}/{book_dir}/folio-one.html"
            )
            assert numbered.status_code == 200
            assert numbered.headers["x-scriptorium-build"] == f"{next_slug}/{number}"

            asset_alias = await client.get(
                f"/a/{original}/stable/_static/theme.css?v=1"
            )
            assert asset_alias.status_code == 308
            assert asset_alias.headers["location"] == (
                f"/a/{next_slug}/stable/_static/theme.css?v=1"
            )

            # Aliases flatten: A -> B -> C means A redirects directly to C.
            third_slug = f"{base}-third"
            assert (
                await client.patch(
                    f"/api/v1/athenaeums/{aid}/public-slug",
                    json={"public_slug": third_slug},
                    headers=_headers(me),
                )
            ).status_code == 200
            first_alias = await client.get(f"/a/{original}/")
            second_alias = await client.get(f"/a/{next_slug}/")
            assert first_alias.status_code == 308
            assert second_alias.status_code == 308
            assert first_alias.headers["location"] == f"/a/{third_slug}/"
            assert second_alias.headers["location"] == f"/a/{third_slug}/"

            # Reverting to one of the site's own retired names is allowed.
            reverted = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": original},
                headers=_headers(me),
            )
            assert reverted.status_code == 200, reverted.text
            assert reverted.json()["public_slug"] == original
            assert (await client.get(f"/a/{next_slug}/")).headers[
                "location"
            ] == f"/a/{original}/"
            publication = await client.get(
                f"/api/v1/athenaeums/{aid}/publication", headers=_headers(me)
            )
            assert {a["slug"] for a in publication.json()["public_aliases"]} == {
                next_slug,
                third_slug,
            }

            # A same-name call is a no-op, not a new alias.
            assert (
                await client.patch(
                    f"/api/v1/athenaeums/{aid}/public-slug",
                    json={"public_slug": original},
                    headers=_headers(me),
                )
            ).status_code == 200
            publication = await client.get(
                f"/api/v1/athenaeums/{aid}/publication", headers=_headers(me)
            )
            assert len(publication.json()["public_aliases"]) == 2

            for bad in ("Bad!", "latest", "stable", "b", "_static", "api"):
                response = await client.patch(
                    f"/api/v1/athenaeums/{aid}/public-slug",
                    json={"public_slug": bad},
                    headers=_headers(me),
                )
                assert response.status_code == 422, (bad, response.text)

            # Another site's current name is a clean conflict; owner scoping
            # still hides a foreign Athenaeum behind 404.
            other = await _mk_lib(client, stranger, f"other-{uuid.uuid4().hex[:8]}")
            other_slug = str(other["public_slug"])
            collision = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": other_slug},
                headers=_headers(me),
            )
            assert collision.status_code == 409, collision.text
            assert (
                await client.patch(
                    f"/api/v1/athenaeums/{other['id']}/public-slug",
                    json={"public_slug": f"{base}-stolen"},
                    headers=_headers(me),
                )
            ).status_code == 404

            # Deletion tombstones every name (current and aliases) forever.
            tomb = await _mk_lib(client, me, f"tomb-{uuid.uuid4().hex[:8]}")
            tomb_a = str(tomb["public_slug"])
            tomb_b = f"{tomb_a}-renamed"
            assert (
                await client.patch(
                    f"/api/v1/athenaeums/{tomb['id']}/public-slug",
                    json={"public_slug": tomb_b},
                    headers=_headers(me),
                )
            ).status_code == 200
            assert (
                await client.delete(
                    f"/api/v1/athenaeums/{tomb['id']}", headers=_headers(me)
                )
            ).status_code == 204
            assert (await client.get(f"/a/{tomb_a}/")).status_code == 404
            assert (await client.get(f"/a/{tomb_b}/")).status_code == 404
            blocked = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": tomb_b},
                headers=_headers(me),
            )
            assert blocked.status_code == 409, blocked.text

            replacement = await _mk_lib(client, me, tomb_b)
            assert replacement["public_slug"] != tomb_b

            # Every successful rename wrote exactly one audit row.
            engine = create_async_engine(LIVE_DB_URL)
            maker = async_sessionmaker(
                engine, expire_on_commit=False, class_=AsyncSession
            )
            try:
                async with maker() as session:
                    rows = await session.scalars(
                        select(AuditLog)
                        .where(AuditLog.action == "athenaeum_public_slug_changed")
                        .order_by(AuditLog.id)
                    )
                    changes = [
                        (
                            row.meta.get("old_public_slug"),
                            row.meta.get("public_slug"),
                        )
                        for row in rows
                        if row.meta.get("athenaeum_id") == aid
                    ]
            finally:
                await engine.dispose()
            assert changes == [
                (original, next_slug),
                (next_slug, third_slug),
                (third_slug, original),
            ]

    _run(run())


@needs_db
def test_public_slug_unique_race_is_a_clean_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent public-name collision returns 409, never a 500."""
    users = asyncio.run(_seed_users(2))
    first_user, second_user = users

    async def run() -> None:
        from app.routers import athenaeums as athenaeums_router

        async with _client() as client:
            first = await _mk_lib(client, first_user, f"race-{uuid.uuid4().hex[:10]}")

            async def collide(_session: AsyncSession, _base: str) -> str:
                return str(first["public_slug"])

            monkeypatch.setattr(athenaeums_router, "_public_slug", collide)
            response = await client.post(
                "/api/v1/athenaeums",
                json={
                    "slug": f"race-{uuid.uuid4().hex[:10]}",
                    "title": "Collision",
                },
                headers=_headers(second_user),
            )
            assert response.status_code == 409, response.text

    _run(run())
