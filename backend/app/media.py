"""Media assets (V1: images/GIF) — storage, sniffing, and reference rules.

Canonical content stores ``/_static/media/{asset_id}.{ext}`` image sources.
That URL is relative to the published site root, so the same markup works
in the editor preview (resolved to the authenticated media endpoint) and
in every Sphinx artifact (the runner copies referenced files into the
staged ``_static`` directory).

No remote assets and no SVG in V1: every image reference must resolve to
a ``media_assets`` row owned by the same grimoire.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MediaAsset

MAX_MEDIA_BYTES = 10 * 1024 * 1024
MEDIA_TYPES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/avif": "avif",
}
_EXT_ALIASES = {"jpeg": "jpg"}
_MEDIA_SRC_RE = re.compile(
    r"^/_static/media/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})\.(?P<ext>png|jpe?g|gif|webp|avif)$"
)


class MediaRefError(ValueError):
    """A document image reference is not a local, owned media asset."""


def get_media_root() -> Path:
    return Path(os.environ.get("SC_MEDIA_ROOT", "/var/lib/scriptorium/media"))


def sniff_image(data: bytes) -> tuple[str, str] | None:
    """Return (content_type, extension) from magic bytes, never the name."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    if len(data) >= 12 and data[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif", "avif"
    return None


def media_url(asset_id: uuid.UUID, extension: str) -> str:
    return f"/_static/media/{asset_id}.{extension}"


def storage_relpath(asset_id: uuid.UUID, extension: str) -> str:
    return f"{asset_id.hex[:2]}/{asset_id}.{extension}"


def media_file(asset: MediaAsset) -> Path:
    """Absolute path for a row; storage_path is generated, never user input."""
    return get_media_root() / asset.storage_path


def _normalized_ext(extension: str) -> str:
    return _EXT_ALIASES.get(extension.lower(), extension.lower())


def _image_srcs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        if node.get("type") == "image":
            attrs = node.get("attrs")
            if isinstance(attrs, dict) and isinstance(attrs.get("src"), str):
                yield attrs["src"]
        for value in node.values():
            yield from _image_srcs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _image_srcs(value)


def referenced_asset_ids(tiptap: Any) -> set[uuid.UUID]:
    """All well-formed media ids referenced by a canonical document."""
    ids: set[uuid.UUID] = set()
    for src in _image_srcs(tiptap):
        match = _MEDIA_SRC_RE.fullmatch(src)
        if match:
            ids.add(uuid.UUID(match.group("id")))
    return ids


async def validate_media_refs(
    tiptap: Any, grimoire_id: uuid.UUID, session: AsyncSession
) -> None:
    """Reject external images and media owned by another grimoire."""
    for src in _image_srcs(tiptap):
        match = _MEDIA_SRC_RE.fullmatch(src)
        if match is None:
            raise MediaRefError(
                "Images must be uploaded to this grimoire; external or "
                f"inline image sources are not allowed: {src!r}."
            )
        asset = await session.get(MediaAsset, uuid.UUID(match.group("id")))
        if asset is None or asset.grimoire_id != grimoire_id:
            raise MediaRefError("Image asset not found in this grimoire.")
        if _normalized_ext(match.group("ext")) != MEDIA_TYPES[asset.content_type]:
            raise MediaRefError("Image source extension does not match its asset.")


async def load_media_files(
    tiptap_documents: list[Any], session: AsyncSession
) -> dict[str, Path]:
    """Map canonical ``/_static/media/...`` URLs to files for a build."""
    ids: set[uuid.UUID] = set()
    for document in tiptap_documents:
        ids.update(referenced_asset_ids(document))
    if not ids:
        return {}
    assets = (
        await session.execute(select(MediaAsset).where(MediaAsset.id.in_(ids)))
    ).scalars()
    by_id = {asset.id: asset for asset in assets}
    missing = ids - by_id.keys()
    if missing:
        raise MediaRefError(
            "Build references missing media assets: "
            + ", ".join(sorted(str(asset_id) for asset_id in missing))
        )
    return {
        media_url(asset.id, MEDIA_TYPES[asset.content_type]): media_file(asset)
        for asset in by_id.values()
    }
