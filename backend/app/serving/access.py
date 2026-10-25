"""Serving access rules (decision 0035 B3) — owner, member, public."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Athenaeum, Grimoire, Membership


async def own_athenaeum(
    session: AsyncSession, athenaeum_id: uuid.UUID, user_id: uuid.UUID
) -> Athenaeum:
    """Owner-scoped load with the uniform 404 IDOR response."""
    row = await session.get(Athenaeum, athenaeum_id)
    if row is None or row.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athenaeum not found.",
        )
    return row


async def can_read_athenaeum(
    session: AsyncSession,
    athenaeum: Athenaeum,
    user_id: uuid.UUID | None,
) -> bool:
    """Public sites are open; private sites allow the owner or any member."""
    if athenaeum.is_public:
        return True
    if user_id is None:
        return False
    if athenaeum.owner_id == user_id:
        return True
    held = await session.scalar(
        select(Grimoire.id)
        .join(Membership, Membership.grimoire_id == Grimoire.id)
        .where(
            Grimoire.athenaeum_id == athenaeum.id,
            Membership.user_id == user_id,
        )
        .limit(1)
    )
    return held is not None
