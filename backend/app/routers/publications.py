"""Publication pointers (decision 0035 A2) — owner-selected stable/latest.

Builds are immutable numbered snapshots. Publishing does not copy or mutate
an artifact; it points one or both channels at an existing ``ok`` build and
records the build's first-publication history. A build that was ever
published remains addressable by its numbered URL, so old stable links and
rollback targets survive later publications.

Routes are owner-only; foreign Athenaeums are the uniform 404.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id
from app.db import get_session
from app.models import Athenaeum, Build, PublicName
from app.serving.access import own_athenaeum
from app.serving.artifacts import servable_artifact

router = APIRouter(prefix="/api/v1/athenaeums", tags=["publications"])

Channel = Literal["latest", "stable", "both"]


class PublishIn(BaseModel):
    build_id: uuid.UUID
    channel: Channel = "both"


def _build_body(build: Build, athenaeum: Athenaeum) -> dict[str, object]:
    return {
        "build_id": str(build.id),
        "build_number": build.build_number,
        "status": build.status,
        "published_at": (
            build.published_at.isoformat()
            if isinstance(build.published_at, datetime)
            else None
        ),
        "published_by": str(build.published_by) if build.published_by else None,
        "url": f"/a/{athenaeum.public_slug}/b/{build.build_number}/",
    }


async def _pointer(
    session: AsyncSession, athenaeum: Athenaeum, build_id: uuid.UUID | None
) -> Build | None:
    if build_id is None:
        return None
    build = await session.get(Build, build_id)
    if build is None or build.athenaeum_id != athenaeum.id:
        return None
    return build


async def _publication_body(
    session: AsyncSession, athenaeum: Athenaeum
) -> dict[str, object]:
    latest = await _pointer(session, athenaeum, athenaeum.latest_build_id)
    stable = await _pointer(session, athenaeum, athenaeum.stable_build_id)
    aliases = await session.scalars(
        select(PublicName)
        .where(
            PublicName.athenaeum_id == athenaeum.id,
            PublicName.is_current.is_(False),
        )
        .order_by(PublicName.created_at, PublicName.slug)
    )
    return {
        "athenaeum_id": str(athenaeum.id),
        "public_slug": athenaeum.public_slug,
        "public_aliases": [
            {
                "slug": alias.slug,
                "retired_at": (
                    alias.retired_at.isoformat()
                    if isinstance(alias.retired_at, datetime)
                    else None
                ),
            }
            for alias in aliases
        ],
        "is_public": athenaeum.is_public,
        "latest": _build_body(latest, athenaeum) if latest else None,
        "stable": _build_body(stable, athenaeum) if stable else None,
        "latest_url": f"/a/{athenaeum.public_slug}/latest/",
        "stable_url": f"/a/{athenaeum.public_slug}/stable/",
    }


@router.get("/{athenaeum_id}/publication")
async def get_publication(
    athenaeum_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    athenaeum = await own_athenaeum(session, athenaeum_id, user_id)
    return await _publication_body(session, athenaeum)


@router.post("/{athenaeum_id}/publish")
async def publish_build(
    athenaeum_id: uuid.UUID,
    body: PublishIn,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    athenaeum = await own_athenaeum(session, athenaeum_id, user_id)
    build = await session.get(Build, body.build_id)
    if build is None or build.athenaeum_id != athenaeum.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Build not found."
        )
    if build.status != "ok" or servable_artifact(build) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a successful, manifest-backed build can be published.",
        )

    channels = ["latest", "stable"] if body.channel == "both" else [body.channel]
    if build.published_at is None:
        build.published_at = datetime.now(UTC)
        build.published_by = user_id
    if "latest" in channels:
        athenaeum.latest_build_id = build.id
    if "stable" in channels:
        athenaeum.stable_build_id = build.id
    add_audit(
        session,
        actor=user_id,
        action="build_published",
        meta={
            "athenaeum_id": str(athenaeum.id),
            "build_id": str(build.id),
            "build_number": build.build_number,
            "channels": channels,
        },
    )
    await session.commit()
    return await _publication_body(session, athenaeum)


@router.delete("/{athenaeum_id}/publish", status_code=status.HTTP_204_NO_CONTENT)
async def unpublish_build(
    athenaeum_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    channel: Channel = "both",
) -> Response:
    athenaeum = await own_athenaeum(session, athenaeum_id, user_id)
    channels = ["latest", "stable"] if channel == "both" else [channel]
    if "latest" in channels:
        athenaeum.latest_build_id = None
    if "stable" in channels:
        athenaeum.stable_build_id = None
    add_audit(
        session,
        actor=user_id,
        action="build_unpublished",
        meta={"athenaeum_id": str(athenaeum.id), "channels": channels},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
