"""Media upload/read endpoints (V1 images + GIF).

Uploads use a raw request body (no multipart dependency): the browser sends
the file bytes with its declared content type, and the server decides the
real type from magic bytes. Every read re-checks grimoire membership, so a
media URL is never a public capability.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_id, require_membership
from app.db import get_session
from app.media import (
    MAX_MEDIA_BYTES,
    MEDIA_TYPES,
    get_media_root,
    media_file,
    media_url,
    sniff_image,
    storage_relpath,
)
from app.models import MediaAsset

router = APIRouter(prefix="/api/v1", tags=["media"])

_FILENAME_RE = re.compile(r"[^\w.\- ()\[\]]+")


def _body(asset: MediaAsset) -> dict[str, object]:
    return {
        "id": str(asset.id),
        "grimoire_id": str(asset.grimoire_id),
        "filename": asset.filename,
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
        "sha256": asset.sha256,
        "url": media_url(asset.id, MEDIA_TYPES[asset.content_type]),
        "content_url": f"/api/v1/media/{asset.id}/content",
        "created_at": asset.created_at.isoformat(),
    }


async def _editor_membership(
    grimoire_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> None:
    role = await require_membership(grimoire_id, user_id, session)
    if role not in ("owner", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor role required.",
        )


@router.post(
    "/grimoires/{grimoire_id}/media",
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    grimoire_id: uuid.UUID,
    request: Request,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    filename: str = Query(default="upload", max_length=255),
) -> dict[str, object]:
    await _editor_membership(grimoire_id, user_id, session)

    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            if int(declared) > MAX_MEDIA_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Media is limited to {MAX_MEDIA_BYTES} bytes.",
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Content-Length.",
            ) from exc
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_MEDIA_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Media is limited to {MAX_MEDIA_BYTES} bytes.",
            )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Empty upload.",
        )
    payload = bytes(data)
    sniffed = sniff_image(payload)
    if sniffed is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="V1 media supports PNG, JPEG, GIF, WebP, and AVIF only.",
        )
    content_type, extension = sniffed

    asset_id = uuid.uuid4()
    relpath = storage_relpath(asset_id, extension)
    path = get_media_root() / relpath
    await anyio.to_thread.run_sync(_write_atomic, path, payload)

    safe_name = (
        _FILENAME_RE.sub("_", Path(filename).name).strip() or f"image.{extension}"
    )
    asset = MediaAsset(
        id=asset_id,
        grimoire_id=grimoire_id,
        filename=safe_name[:255],
        content_type=content_type,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        storage_path=relpath,
        created_by=user_id,
    )
    session.add(asset)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await anyio.to_thread.run_sync(path.unlink, True)
        raise
    return _body(asset)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)


@router.get("/grimoires/{grimoire_id}/media")
async def list_media(
    grimoire_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, object]]:
    await require_membership(grimoire_id, user_id, session)
    assets = await session.scalars(
        select(MediaAsset)
        .where(MediaAsset.grimoire_id == grimoire_id)
        .order_by(MediaAsset.created_at.desc())
    )
    return [_body(asset) for asset in assets]


@router.get("/media/{asset_id}/content")
async def read_media(
    asset_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found."
        )
    await require_membership(asset.grimoire_id, user_id, session)
    path = media_file(asset)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media file missing."
        )
    return FileResponse(
        path,
        media_type=asset.content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "ETag": f'"{asset.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
