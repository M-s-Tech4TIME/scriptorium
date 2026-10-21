"""Athenaeum routes (M3.5, decision 0020) — the native library layer.

Ownership: every endpoint is owner-scoped; a foreign Athenaeum id is a
uniform 404 (IDOR rule). Sharing stays grimoire-level (Q-M3-12=A).
Delete refuses 409 while the Athenaeum still holds grimoires (Q-M3-11=A).
Slug is renamable (0021): per-owner uniqueness still applies.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id
from app.db import get_session
from app.models import Athenaeum, Grimoire, GrimoireCategory

router = APIRouter(prefix="/api/v1/athenaeums", tags=["athenaeums"])

_SLUG_RE = re.compile(r"[a-z0-9-]+")


class AthenaeumIn(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)


class AthenaeumPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=120)


def _check_slug(slug: str) -> str:
    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Slug must match [a-z0-9-]+.",
        )
    return slug


async def _own_athenaeum(
    athenaeum_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> Athenaeum:
    row = await session.get(Athenaeum, athenaeum_id)
    if row is None or row.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athenaeum not found.",
        )
    return row


def _body(row: Athenaeum) -> dict[str, object]:
    return {
        "id": str(row.id),
        "owner_id": str(row.owner_id),
        "slug": row.slug,
        "title": row.title,
    }


def _grimoire_lite(row: Grimoire) -> dict[str, object]:
    return {
        "id": str(row.id),
        "slug": row.slug,
        "title": row.title,
        "source_format": row.source_format,
        "theme": row.theme,
        "category_id": str(row.category_id) if row.category_id else None,
    }


@router.get("")
async def list_athenaeums(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    rows = await session.scalars(
        select(Athenaeum)
        .where(Athenaeum.owner_id == user_id)
        .order_by(Athenaeum.created_at)
    )
    return [_body(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_athenaeum(
    body: AthenaeumIn,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    _check_slug(body.slug)
    taken = await session.scalar(
        select(Athenaeum.id).where(
            Athenaeum.owner_id == user_id, Athenaeum.slug == body.slug
        )
    )
    if taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already exists."
        )
    row = Athenaeum(
        owner_id=user_id,
        slug=body.slug,
        title=body.title,
    )
    session.add(row)
    await session.flush()
    add_audit(
        session,
        actor=user_id,
        action="athenaeum_created",
        meta={"athenaeum_id": str(row.id), "slug": row.slug},
    )
    await session.commit()
    return _body(row)


@router.get("/{athenaeum_id}")
async def get_athenaeum(
    athenaeum_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return _body(await _own_athenaeum(athenaeum_id, user_id, session))


@router.patch("/{athenaeum_id}")
async def patch_athenaeum(
    athenaeum_id: uuid.UUID,
    body: AthenaeumPatch,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    row = await _own_athenaeum(athenaeum_id, user_id, session)
    provided = body.model_fields_set
    changes: dict[str, str] = {}
    if "title" in provided:
        if body.title is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="title is required — athenaeums cannot be unnamed.",
            )
        if body.title != row.title:
            row.title = body.title
            changes["title"] = body.title
    if "slug" in provided:
        if body.slug is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="slug is required — athenaeums cannot float.",
            )
        _check_slug(body.slug)
        if body.slug != row.slug:
            taken = await session.scalar(
                select(Athenaeum.id).where(
                    Athenaeum.owner_id == user_id,
                    Athenaeum.slug == body.slug,
                    Athenaeum.id != row.id,
                )
            )
            if taken is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Slug already exists."
                )
            row.slug = body.slug
            changes["slug"] = body.slug
    add_audit(
        session,
        actor=user_id,
        action="athenaeum_patched",
        meta={"athenaeum_id": str(row.id), "changes": changes},
    )
    await session.commit()
    return _body(row)


@router.delete("/{athenaeum_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athenaeum(
    athenaeum_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> Response:
    row = await _own_athenaeum(athenaeum_id, user_id, session)
    held = await session.scalar(
        select(func.count())
        .select_from(Grimoire)
        .where(Grimoire.athenaeum_id == athenaeum_id)
    )
    if held:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Athenaeum still holds grimoires; move or delete them first.",
        )
    await session.delete(row)
    add_audit(
        session,
        actor=user_id,
        action="athenaeum_deleted",
        meta={"athenaeum_id": str(athenaeum_id), "slug": row.slug},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{athenaeum_id}/sidebar")
async def get_sidebar(
    athenaeum_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """One call for the sidebar: categories → grimoires + uncategorized (Q-M3-13)."""
    row = await _own_athenaeum(athenaeum_id, user_id, session)
    categories = await session.scalars(
        select(GrimoireCategory)
        .where(GrimoireCategory.athenaeum_id == athenaeum_id)
        .order_by(GrimoireCategory.position, GrimoireCategory.created_at)
    )
    grimoires = await session.scalars(
        select(Grimoire)
        .where(Grimoire.athenaeum_id == athenaeum_id)
        .order_by(Grimoire.title)
    )
    lit_rows = [_grimoire_lite(g) for g in grimoires]
    sections = []
    drawer = [g for g in lit_rows if g["category_id"] is None]  # uncategorized bucket
    for category in categories:
        sections.append(
            {
                "id": str(category.id),
                "name": category.name,
                "position": category.position,
                "grimoires": [
                    g for g in lit_rows if g["category_id"] == str(category.id)
                ],
            }
        )
    return {
        "id": str(row.id),
        "slug": row.slug,
        "title": row.title,
        "categories": sections,
        "uncategorized": drawer,
    }
