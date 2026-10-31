"""Media endpoint tests (V1 images/GIF) — live PG18 + local temp storage.

Uploads are authorized by grimoire membership, typed by magic bytes (never
the filename), and document saves reject external/foreign image sources.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from pathlib import Path

import pytest

from tests.conftest import needs_db
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


@needs_db
def test_media_upload_read_and_document_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SC_MEDIA_ROOT", str(tmp_path / "media"))
    users = asyncio.run(_seed_users(2))
    me, outsider = users

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "media")
            g = await _mk_grimoire(client, me, aid, "media-book", "Media book")
            gid = str(g["id"])
            folio = await _mk_folio(client, me, gid, "media-folio")
            base = f"/api/v1/grimoires/{gid}/nodes/{folio['id']}/document"

            uploaded = await client.post(
                f"/api/v1/grimoires/{gid}/media",
                params={"filename": "dot.png"},
                content=_PNG,
                headers={**_headers(me), "Content-Type": "image/png"},
            )
            assert uploaded.status_code == 201
            asset = uploaded.json()
            assert asset["content_type"] == "image/png"
            assert asset["url"].startswith("/_static/media/")
            assert (tmp_path / "media" / asset["id"].replace("-", "")[:2]).is_dir()

            fetched = await client.get(
                f"/api/v1/media/{asset['id']}/content", headers=_headers(me)
            )
            assert fetched.status_code == 200
            assert fetched.headers["content-type"] == "image/png"
            assert fetched.content == _PNG

            outsider_read = await client.get(
                f"/api/v1/media/{asset['id']}/content", headers=_headers(outsider)
            )
            assert outsider_read.status_code == 404

            outsider_upload = await client.post(
                f"/api/v1/grimoires/{gid}/media",
                params={"filename": "dot.png"},
                content=_PNG,
                headers={**_headers(outsider), "Content-Type": "image/png"},
            )
            assert outsider_upload.status_code == 404

            listed = await client.get(
                f"/api/v1/grimoires/{gid}/media", headers=_headers(me)
            )
            assert listed.status_code == 200
            assert [row["id"] for row in listed.json()] == [asset["id"]]

            image_doc = {
                "type": "doc",
                "content": [
                    {
                        "type": "image",
                        "attrs": {
                            "src": asset["url"],
                            "alt": "dot",
                            "title": "A dot",
                        },
                    }
                ],
            }
            saved = await client.put(
                base,
                json={"tiptap_json": image_doc, "expected_version": 0},
                headers=_headers(me),
            )
            assert saved.status_code == 200
            assert asset["url"] in saved.json()["source_text"]
            assert "image::" in saved.json()["source_text"]

            external = await client.put(
                base,
                json={
                    "tiptap_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "image",
                                "attrs": {"src": "https://example.test/x.png"},
                            }
                        ],
                    },
                    "expected_version": 1,
                },
                headers=_headers(me),
            )
            assert external.status_code == 422
            assert "uploaded" in external.json()["detail"].lower()

            not_image = await client.post(
                f"/api/v1/grimoires/{gid}/media",
                params={"filename": "evil.png"},
                content=b"<svg onload=alert(1)>",
                headers={**_headers(me), "Content-Type": "image/png"},
            )
            assert not_image.status_code == 415

    _run(run())


@needs_db
def test_media_rejects_cross_grimoire_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SC_MEDIA_ROOT", str(tmp_path / "media"))
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        async with _client() as client:
            aid = await _mk_lib(client, me, "media2")
            first = await _mk_grimoire(client, me, aid, "first-book", "First")
            second = await _mk_grimoire(client, me, aid, "second-book", "Second")
            folio = await _mk_folio(client, me, str(second["id"]), "page")
            uploaded = await client.post(
                f"/api/v1/grimoires/{first['id']}/media",
                params={"filename": "dot.png"},
                content=_PNG,
                headers={**_headers(me), "Content-Type": "image/png"},
            )
            assert uploaded.status_code == 201
            url = uploaded.json()["url"]

            saved = await client.put(
                f"/api/v1/grimoires/{second['id']}/nodes/{folio['id']}/document",
                json={
                    "tiptap_json": {
                        "type": "doc",
                        "content": [
                            {"type": "image", "attrs": {"src": url, "alt": "x"}}
                        ],
                    },
                    "expected_version": 0,
                },
                headers=_headers(me),
            )
            assert saved.status_code == 422
            assert "not found in this grimoire" in saved.json()["detail"]

            # A malformed UUID-shaped URL must not be accepted either.
            bad = await client.put(
                f"/api/v1/grimoires/{second['id']}/nodes/{folio['id']}/document",
                json={
                    "tiptap_json": {
                        "type": "doc",
                        "content": [
                            {
                                "type": "image",
                                "attrs": {"src": f"/_static/media/{uuid.uuid4()}.png"},
                            }
                        ],
                    },
                    "expected_version": 0,
                },
                headers=_headers(me),
            )
            assert bad.status_code == 422

    _run(run())
