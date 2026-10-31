"""Sidebar category routes — sections INSIDE an Athenaeum (0020 Q-M3-9=A).

Categories are scoped per-Athenaeum now (0018's per-user categories are
superseded): ownership/resolution flows through the Athenaeum's owner, and
every path hangs under `/api/v1/athenaeums/{athenaeum_id}`. A foreign
Athenaeum or category id is a uniform 404 (IDOR rule). Deleting a category
leaves its grimoires Uncategorized (NULL) inside the same Athenaeum.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id
from app.db import get_session
from app.models import Athenaeum, Grimoire, GrimoireCategory

router = APIRouter(prefix="/api/v1/athenaeums/{athenaeum_id}/categories")


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    position: int | None = Field(default=None, ge=0)


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


async def _own_category(
    athenaeum_id: uuid.UUID,
    category_id: uuid.UUID,
    session: AsyncSession,
) -> GrimoireCategory:
    category = await session.get(GrimoireCategory, category_id)
    if category is None or category.athenaeum_id != athenaeum_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )
    return category


async def compact_positions(athenaeum_id: uuid.UUID, session: AsyncSession) -> None:
    """Re-index an Athenaeum's categories 1..n by position (ties: created_at)."""
    category_ids = await session.scalars(
        select(GrimoireCategory.id)
        .where(GrimoireCategory.athenaeum_id == athenaeum_id)
        .order_by(GrimoireCategory.position, GrimoireCategory.created_at)
    )
    for new_pos, category_id in enumerate(list(category_ids), start=1):
        await session.execute(
            update(GrimoireCategory)
            .where(GrimoireCategory.id == category_id)
            .values(position=new_pos)
        )


@router.get("")
async def list_categories(
    athenaeum_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, object]]:
    await _own_athenaeum(athenaeum_id, user_id, session)
    rows = await session.scalars(
        select(GrimoireCategory)
        .where(GrimoireCategory.athenaeum_id == athenaeum_id)
        .order_by(GrimoireCategory.position, GrimoireCategory.created_at)
    )
    return [
        {"id": str(row.id), "name": row.name, "position": row.position} for row in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    athenaeum_id: uuid.UUID,
    body: CategoryIn,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _own_athenaeum(athenaeum_id, user_id, session)
    dup = await session.scalar(
        select(GrimoireCategory.id).where(
            GrimoireCategory.athenaeum_id == athenaeum_id,
            GrimoireCategory.name == body.name,
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category already exists."
        )
    next_pos = await session.scalar(
        select(func.max(GrimoireCategory.position)).where(
            GrimoireCategory.athenaeum_id == athenaeum_id
        )
    )
    category = GrimoireCategory(
        athenaeum_id=athenaeum_id, name=body.name, position=(next_pos or 0) + 1
    )
    session.add(category)
    add_audit(
        session,
        actor=user_id,
        action="category_created",
        meta={"category_id": str(category.id), "name": category.name},
    )
    await session.commit()
    return {
        "id": str(category.id),
        "name": category.name,
        "position": category.position,
    }


@router.patch("/{category_id}")
async def patch_category(
    athenaeum_id: uuid.UUID,
    category_id: uuid.UUID,
    body: CategoryPatch,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _own_athenaeum(athenaeum_id, user_id, session)
    category = await _own_category(athenaeum_id, category_id, session)
    if body.name is not None and body.name != category.name:
        dup = await session.scalar(
            select(GrimoireCategory.id).where(
                GrimoireCategory.athenaeum_id == athenaeum_id,
                GrimoireCategory.name == body.name,
            )
        )
        if dup is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Category already exists."
            )
        category.name = body.name
    if body.position is not None and body.position != category.position:
        # Insert-displacement reorder: position is a 1-based index into the
        # Athenaeum's current section order (Q-M3-4=A explicit atomic ops).
        current = await session.scalars(
            select(GrimoireCategory.id)
            .where(GrimoireCategory.athenaeum_id == athenaeum_id)
            .order_by(GrimoireCategory.position, GrimoireCategory.created_at)
        )
        order: list[uuid.UUID] = [row for row in current]
        if category.id in order:
            order.remove(category.id)
        index = max(0, min(body.position - 1, len(order)))
        order.insert(index, category.id)
        for new_pos, moved_id in enumerate(order, start=1):
            await session.execute(
                update(GrimoireCategory)
                .where(GrimoireCategory.id == moved_id)
                .values(position=new_pos)
            )
        await session.refresh(category)
    add_audit(
        session,
        actor=user_id,
        action="category_patched",
        meta={
            "category_id": str(category.id),
            "renamed_to": body.name,
            "moved_to": body.position,
        },
    )
    await session.commit()
    return {
        "id": str(category.id),
        "name": category.name,
        "position": category.position,
    }


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    athenaeum_id: uuid.UUID,
    category_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await _own_athenaeum(athenaeum_id, user_id, session)
    category = await _own_category(athenaeum_id, category_id, session)
    touched = await session.scalar(
        select(func.count())
        .select_from(Grimoire)
        .where(Grimoire.category_id == category_id)
    )
    await session.delete(category)
    add_audit(
        session,
        actor=user_id,
        action="category_deleted",
        meta={
            "category_id": str(category_id),
            "grimoires_uncategorized": int(touched or 0),
        },
    )
    await compact_positions(athenaeum_id, session)
    await session.commit()  # grimoires.category_id → NULL (0018 Q-M3-7 SET NULL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
