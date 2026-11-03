"""Backup/restore live tests (decision 0039) — live PG18 + Sphinx + storage.

Covers the owner rulings end to end:

- A1/C1: Editorial export is a synchronous stream; Full export/restore are
  queued jobs whose archive download link is single-use.
- Numbered ``/b/{n}/`` URLs survive a restore exactly (build numbers,
  artifacts, publication pointers).
- E1: a restore always creates a fresh Athenaeum; free or same-owner
  tombstoned public names are reclaimed, conflicts are suffixed, and
  foreign aliases are skipped with a warning recorded in the audit log.
- D1: restored rows are owned by the importer; every user identity in the
  source (created_by/updated_by/triggered_by/published_by) is nulled.
- Media URLs are rewritten to the restored asset ids and the bytes land
  under the restored storage path.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import os
import uuid
import zipfile
from pathlib import Path
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import (
    Athenaeum,
    AuditLog,
    Build,
    Document,
    DocumentHistory,
    Grimoire,
    MediaAsset,
    Membership,
    Node,
    PublicName,
)
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db
from tests.test_document_api import (
    _client,
    _headers,
    _mk_folio,
    _mk_grimoire,
    _mk_lib,
    _run,
    _seed_users,
)

# 1x1 transparent PNG.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAusB9Wl2n3sAAAAASUVORK5CYII="
)


def _paths(tmp_path: Path) -> dict[str, str]:
    return {
        "SC_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
        "SC_BUILD_ROOT": str(tmp_path / "builds"),
        "SC_MEDIA_ROOT": str(tmp_path / "media"),
        "SC_BACKUP_ROOT": str(tmp_path / "backups"),
        "SC_BUILD_DISPATCH": "inline",
        "SC_BACKUP_DISPATCH": "inline",
    }


async def _build(
    client: httpx.AsyncClient, user: dict[str, Any], athenaeum_id: str
) -> dict[str, Any]:
    made = await client.post(
        f"/api/v1/athenaeums/{athenaeum_id}/builds",
        json={},
        headers=_headers(user),
    )
    assert made.status_code == 201, made.text
    return cast(dict[str, Any], made.json())


async def _publish(
    client: httpx.AsyncClient,
    user: dict[str, Any],
    athenaeum_id: str,
    build_id: str,
    channel: str,
) -> None:
    made = await client.post(
        f"/api/v1/athenaeums/{athenaeum_id}/publish",
        json={"build_id": build_id, "channel": channel},
        headers=_headers(user),
    )
    assert made.status_code == 200, made.text


async def _export(
    client: httpx.AsyncClient,
    user: dict[str, Any],
    athenaeum_id: str,
    *,
    mode: str,
    container: str,
) -> dict[str, Any]:
    made = await client.post(
        f"/api/v1/athenaeums/{athenaeum_id}/backups",
        json={"mode": mode, "format": container},
        headers=_headers(user),
    )
    assert made.status_code == 200, made.text
    return {
        "bytes": made.content,
        "sha256": made.headers["x-backup-sha256"],
        "filename": made.headers["content-disposition"],
    }


async def _export_job(
    client: httpx.AsyncClient,
    user: dict[str, Any],
    athenaeum_id: str,
    *,
    mode: str,
    container: str,
) -> dict[str, Any]:
    made = await client.post(
        f"/api/v1/athenaeums/{athenaeum_id}/backups",
        json={"mode": mode, "format": container},
        headers=_headers(user),
    )
    assert made.status_code == 202, made.text
    body = cast(dict[str, Any], made.json())
    if body["status"] in ("queued", "running"):
        body = await _wait_job(client, user, str(body["id"]))
    return body


async def _wait_job(
    client: httpx.AsyncClient, user: dict[str, Any], job_id: str
) -> dict[str, Any]:
    for _ in range(100):
        got = await client.get(f"/api/v1/backup-jobs/{job_id}", headers=_headers(user))
        assert got.status_code == 200, got.text
        body = cast(dict[str, Any], got.json())
        if body["status"] in ("ok", "failed"):
            return body
        await asyncio.sleep(0.05)
    raise AssertionError("backup job did not finish")


async def _db(fn: Any) -> Any:
    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            return await fn(session)
    finally:
        await engine.dispose()


@needs_db
def test_editorial_roundtrip_preserves_site(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        os.environ.update(_paths(tmp_path))
        async with _client() as client:
            aid = await _mk_lib(client, me, "edbk")
            shown = await client.get(f"/api/v1/athenaeums/{aid}", headers=_headers(me))
            original = str(shown.json()["public_slug"])
            renamed = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": f"{original}-next"},
                headers=_headers(me),
            )
            assert renamed.status_code == 200, renamed.text
            current = str(renamed.json()["public_slug"])

            g = await _mk_grimoire(client, me, aid, "book-one", "Book one")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "page-one")
            base = f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document"

            uploaded = await client.post(
                f"/api/v1/grimoires/{gid}/media",
                params={"filename": "dot.png"},
                content=_PNG,
                headers={**_headers(me), "Content-Type": "image/png"},
            )
            assert uploaded.status_code == 201, uploaded.text
            asset = cast(dict[str, Any], uploaded.json())
            old_url = str(asset["url"])

            doc_one = {
                "type": "doc",
                "content": [
                    {
                        "type": "image",
                        "attrs": {"src": old_url, "alt": "dot"},
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Roundtrip"}],
                    },
                ],
            }
            first = await client.put(
                base,
                json={"tiptap_json": doc_one, "expected_version": 0},
                headers=_headers(me),
            )
            assert first.status_code == 200, first.text
            assert old_url in first.json()["source_text"]

            b1 = await _build(client, me, aid)
            assert b1["build_number"] == 1 and b1["status"] == "ok"

            doc_two = {
                "type": "doc",
                "content": [
                    {
                        "type": "image",
                        "attrs": {"src": old_url, "alt": "dot"},
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Roundtrip two"}],
                    },
                ],
            }
            second = await client.put(
                base,
                json={"tiptap_json": doc_two, "expected_version": 1},
                headers=_headers(me),
            )
            assert second.status_code == 200, second.text
            b2 = await _build(client, me, aid)
            assert b2["build_number"] == 2 and b2["status"] == "ok"

            await _publish(client, me, aid, str(b1["id"]), "stable")
            await _publish(client, me, aid, str(b2["id"]), "latest")
            before = await client.get(f"/a/{current}/b/1/", headers=_headers(me))
            assert before.status_code == 200

            exported = await _export(client, me, aid, mode="editorial", container="zip")
            archive = cast(bytes, exported["bytes"])
            assert exported["sha256"] == hashlib.sha256(archive).hexdigest()
            assert ".zip" in str(exported["filename"])

            # Deleting the site leaves permanent tombstones owned by `me`.
            assert (
                await client.delete(f"/api/v1/grimoires/{gid}", headers=_headers(me))
            ).status_code == 204
            assert (
                await client.delete(f"/api/v1/athenaeums/{aid}", headers=_headers(me))
            ).status_code == 204

            restored = await client.post(
                "/api/v1/backups/restore",
                content=archive,
                headers=_headers(me),
            )
            assert restored.status_code == 201, restored.text
            body = cast(dict[str, Any], restored.json())
            assert body["mode"] == "editorial"
            assert body["warnings"] == []
            assert body["public_slug"] == current  # same-owner tombstone reclaimed
            new_aid = str(body["athenaeum_id"])
            assert new_aid != aid

            # Numbered URLs survive exactly on the fresh site.
            for number in (1, 2):
                page = await client.get(
                    f"/a/{current}/b/{number}/", headers=_headers(me)
                )
                assert page.status_code == 200, page.text
            # The retired public name survives as a redirecting alias.
            alias = await client.get(f"/a/{original}/b/1/", headers=_headers(me))
            assert alias.status_code == 308
            assert alias.headers["location"].endswith(f"/a/{current}/b/1/")

            async def inspect(session: AsyncSession) -> dict[str, Any]:
                athenaeum = await session.get(Athenaeum, uuid.UUID(new_aid))
                assert athenaeum is not None
                names = list(
                    (
                        await session.scalars(
                            select(PublicName)
                            .where(PublicName.athenaeum_id == athenaeum.id)
                            .order_by(PublicName.slug)
                        )
                    ).all()
                )
                builds = list(
                    (
                        await session.scalars(
                            select(Build)
                            .where(Build.athenaeum_id == athenaeum.id)
                            .order_by(Build.build_number)
                        )
                    ).all()
                )
                grimoires = list(
                    (
                        await session.scalars(
                            select(Grimoire).where(
                                Grimoire.athenaeum_id == athenaeum.id
                            )
                        )
                    ).all()
                )
                document = await session.scalar(
                    select(Document)
                    .join(Node, Node.id == Document.node_id)
                    .where(Node.grimoire_id == grimoires[0].id)
                )
                media = list(
                    (
                        await session.scalars(
                            select(MediaAsset).where(
                                MediaAsset.grimoire_id == grimoires[0].id
                            )
                        )
                    ).all()
                )
                memberships = list(
                    (
                        await session.scalars(
                            select(Membership).where(
                                Membership.grimoire_id == grimoires[0].id
                            )
                        )
                    ).all()
                )
                audit = await session.scalar(
                    select(AuditLog)
                    .where(AuditLog.action == "backup_restored")
                    .order_by(AuditLog.id.desc())
                    .limit(1)
                )
                assert document is not None
                versions = list(
                    (
                        await session.scalars(
                            select(DocumentHistory.version)
                            .where(DocumentHistory.document_id == document.id)
                            .order_by(DocumentHistory.version)
                        )
                    ).all()
                )
                return {
                    "athenaeum": athenaeum,
                    "names": names,
                    "builds": builds,
                    "grimoires": grimoires,
                    "document": document,
                    "media": media,
                    "memberships": memberships,
                    "audit": audit,
                    "versions": versions,
                }

            state = await _db(inspect)
            athenaeum = state["athenaeum"]
            assert athenaeum.public_slug == current
            assert athenaeum.is_public is False
            assert athenaeum.latest_build_id == state["builds"][1].id
            assert athenaeum.stable_build_id == state["builds"][0].id

            names = state["names"]
            assert {(row.slug, row.is_current) for row in names} == {
                (current, True),
                (original, False),
            }

            builds = state["builds"]
            assert [row.build_number for row in builds] == [1, 2]
            for row in builds:
                assert row.status == "ok"
                assert row.published_at is not None
                assert row.triggered_by is None
                assert row.published_by is None
                assert row.log_path is None
                assert row.artifact_path is not None
                assert str(athenaeum.id) in row.artifact_path

            grimoire = state["grimoires"][0]
            assert grimoire.created_by is None
            assert grimoire.slug == "book-one"
            assert [(m.user_id, m.role) for m in state["memberships"]] == [
                (uuid.UUID(str(me["id"])), "owner")
            ]

            document = state["document"]
            new_media = state["media"]
            assert len(new_media) == 1
            new_url = f"/_static/media/{new_media[0].id}.png"
            assert new_media[0].id != uuid.UUID(str(asset["id"]))
            assert new_url in document.source_text
            assert old_url not in document.source_text
            assert document.updated_by is None
            assert new_url in str(document.tiptap_json)
            assert (tmp_path / "media" / new_media[0].storage_path).is_file()

            assert state["versions"] == [1, 2]

            audit = state["audit"]
            assert audit is not None
            assert audit.actor == uuid.UUID(str(me["id"]))
            assert audit.meta["athenaeum_id"] == new_aid
            assert audit.meta["mode"] == "editorial"
            assert audit.meta["warnings"] == []
            assert audit.meta["counts"]["builds"] == 2

        await app_teardown()

    _run(run())


@needs_db
def test_full_jobs_and_single_use_download(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        os.environ.update(_paths(tmp_path))
        async with _client() as client:
            aid = await _mk_lib(client, me, "fullbk")
            shown = await client.get(f"/api/v1/athenaeums/{aid}", headers=_headers(me))
            original = str(shown.json()["public_slug"])

            g = await _mk_grimoire(client, me, aid, "full-book", "Full book")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "full-page")
            saved = await client.put(
                f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document",
                json={
                    "tiptap_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Full"}],
                            }
                        ],
                    },
                    "expected_version": 0,
                },
                headers=_headers(me),
            )
            assert saved.status_code == 200, saved.text

            good = await _build(client, me, aid)
            assert good["build_number"] == 1 and good["status"] == "ok"
            await _publish(client, me, aid, str(good["id"]), "both")

            # A failed build with its crash log: only Full mode carries it.
            crash = tmp_path / "builds" / uuid.uuid4().hex / "build.log"
            crash.parent.mkdir(parents=True, exist_ok=True)
            crash.write_text(
                "Scriptorium build log (0026) — staging failed\n"
                "E2: every book is empty\n",
                encoding="utf-8",
            )

            async def add_failed_build(session: AsyncSession) -> str:
                row = Build(
                    athenaeum_id=uuid.UUID(aid),
                    build_number=2,
                    status="failed",
                    triggered_by=uuid.UUID(str(me["id"])),
                    log_path=str(crash),
                )
                session.add(row)
                await session.commit()
                return str(row.id)

            await _db(add_failed_build)

            job = await _export_job(client, me, aid, mode="full", container="tar.gz")
            assert job["status"] == "ok", job
            assert job["size_bytes"] > 0
            assert job["sha256"] is not None
            assert job["download_url"] is not None

            download = await client.get(str(job["download_url"]))
            assert download.status_code == 200
            assert download.headers["content-type"] == "application/gzip"
            archive = download.content
            assert hashlib.sha256(archive).hexdigest() == job["sha256"]

            # C1: the signed link is single-use.
            again = await client.get(str(job["download_url"]))
            assert again.status_code == 410
            after = await _wait_job(client, me, str(job["id"]))
            assert after["download_url"] is None
            assert after["downloaded_at"] is not None

            restore = await client.post(
                "/api/v1/backups/restore",
                content=archive,
                headers=_headers(me),
            )
            assert restore.status_code == 202, restore.text
            restore_job = cast(dict[str, Any], restore.json())
            if restore_job["status"] in ("queued", "running"):
                restore_job = await _wait_job(client, me, str(restore_job["id"]))
            assert restore_job["status"] == "ok", restore_job
            new_aid = str(restore_job["result_athenaeum_id"])

            async def inspect(session: AsyncSession) -> dict[str, Any]:
                athenaeum = await session.get(Athenaeum, uuid.UUID(new_aid))
                assert athenaeum is not None
                builds = list(
                    (
                        await session.scalars(
                            select(Build)
                            .where(Build.athenaeum_id == athenaeum.id)
                            .order_by(Build.build_number)
                        )
                    ).all()
                )
                return {"athenaeum": athenaeum, "builds": builds}

            state = await _db(inspect)
            athenaeum = state["athenaeum"]
            # The source site still owns the live name: E1 suffixes the copy.
            assert athenaeum.public_slug != original
            assert athenaeum.public_slug.startswith(original)

            builds = state["builds"]
            assert [(row.build_number, row.status) for row in builds] == [
                (1, "ok"),
                (2, "failed"),
            ]
            assert builds[0].artifact_path is not None
            assert builds[1].artifact_path is None
            assert builds[1].log_path is not None
            log_file = Path(builds[1].log_path)
            assert log_file.is_file()
            assert "Scriptorium build log" in log_file.read_text(encoding="utf-8")

            served = await client.get(
                f"/a/{athenaeum.public_slug}/b/1/", headers=_headers(me)
            )
            assert served.status_code == 200
            assert (
                await client.get(
                    f"/a/{athenaeum.public_slug}/b/2/", headers=_headers(me)
                )
            ).status_code == 404

        await app_teardown()

    _run(run())


@needs_db
def test_restore_alias_collision_warns_and_suffixes(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(2))
    owner, importer = users

    async def run() -> None:
        os.environ.update(_paths(tmp_path))
        async with _client() as client:
            aid = await _mk_lib(client, owner, "aliasbk")
            shown = await client.get(
                f"/api/v1/athenaeums/{aid}", headers=_headers(owner)
            )
            original = str(shown.json()["public_slug"])
            renamed = await client.patch(
                f"/api/v1/athenaeums/{aid}/public-slug",
                json={"public_slug": f"{original}-keep"},
                headers=_headers(owner),
            )
            assert renamed.status_code == 200, renamed.text
            current = str(renamed.json()["public_slug"])

            exported = await _export(
                client, owner, aid, mode="editorial", container="zip"
            )
            archive = cast(bytes, exported["bytes"])

            assert (
                await client.delete(
                    f"/api/v1/athenaeums/{aid}", headers=_headers(owner)
                )
            ).status_code == 204

            restored = await client.post(
                "/api/v1/backups/restore",
                content=archive,
                headers=_headers(importer),
            )
            assert restored.status_code == 201, restored.text
            body = cast(dict[str, Any], restored.json())
            assert body["public_slug"] != current
            assert str(body["public_slug"]).startswith(current)
            assert any(original in warning for warning in body["warnings"]), body
            new_aid = str(body["athenaeum_id"])

            async def inspect(session: AsyncSession) -> dict[str, Any]:
                names = list(
                    (
                        await session.scalars(
                            select(PublicName).where(
                                PublicName.athenaeum_id == uuid.UUID(new_aid)
                            )
                        )
                    ).all()
                )
                tombstones = list(
                    (
                        await session.scalars(
                            select(PublicName).where(PublicName.athenaeum_id.is_(None))
                        )
                    ).all()
                )
                audit = await session.scalar(
                    select(AuditLog)
                    .where(
                        AuditLog.action == "backup_restored",
                        AuditLog.actor == uuid.UUID(str(importer["id"])),
                    )
                    .order_by(AuditLog.id.desc())
                    .limit(1)
                )
                return {
                    "names": names,
                    "tombstones": tombstones,
                    "audit": audit,
                }

            state = await _db(inspect)
            # Only the fresh, suffixed current name: the foreign aliases were
            # skipped, never hijacked.
            assert [(row.slug, row.is_current) for row in state["names"]] == [
                (str(body["public_slug"]), True)
            ]
            tombstone_slugs = {row.slug for row in state["tombstones"]}
            assert {original, current} <= tombstone_slugs
            assert all(
                row.owner_id == uuid.UUID(str(owner["id"]))
                for row in state["tombstones"]
                if row.slug in {original, current}
            )
            audit = state["audit"]
            assert audit is not None
            assert audit.meta["warnings"] == body["warnings"]

        await app_teardown()

    _run(run())


@needs_db
def test_restore_rejects_tampered_archive(tmp_path: Path) -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        os.environ.update(_paths(tmp_path))
        async with _client() as client:
            aid = await _mk_lib(client, me, "badbk")
            exported = await _export(client, me, aid, mode="editorial", container="zip")
            archive = cast(bytes, exported["bytes"])

            # Rewrite data.json without updating the manifest hash. The edit
            # keeps the byte length identical so the hash check (not the size
            # check) is the gate under test.
            source = zipfile.ZipFile(io.BytesIO(archive))
            tampered = io.BytesIO()
            with zipfile.ZipFile(tampered, "w") as out:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "data.json":
                        data = data.replace(b'"title"', b'"tItle"', 1)
                    out.writestr(info, data)
            source.close()

            async def count_sites(session: AsyncSession) -> int:
                rows = await session.scalars(select(Athenaeum.id))
                return len(list(rows))

            before = await _db(count_sites)
            rejected = await client.post(
                "/api/v1/backups/restore",
                content=tampered.getvalue(),
                headers=_headers(me),
            )
            assert rejected.status_code == 422, rejected.text
            assert "Hash mismatch" in rejected.json()["detail"]
            assert await _db(count_sites) == before

        await app_teardown()

    _run(run())
