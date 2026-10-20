"""RBAC/IDOR tests against live PG18 (runs in CI via postgres:18 service).

Member of a grimoire passes; any non-member (including random UUIDs) gets
the same 404 — grimoire existence is never leaked.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import require_membership
from app.models import Grimoire, Membership, User
from tests.conftest import LIVE_DB_URL, needs_db


@needs_db
def test_member_passes_nonmember_404s() -> None:
    import asyncio

    asyncio.run(_scenario())


async def _scenario() -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = create_async_engine(LIVE_DB_URL)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with maker() as session:
            tag = uuid.uuid4().hex[:8]
            me = User(email=f"owner-{tag}@example.test", pw_hash="x", display="Owner")
            stranger = User(
                email=f"stranger-{tag}@example.test", pw_hash="x", display="Stranger"
            )
            grimoire = Grimoire(
                slug=f"secret-grimoire-{tag}", title="Secret", created_by=None
            )
            session.add_all([me, stranger, grimoire])
            await session.flush()
            session.add(
                Membership(user_id=me.id, grimoire_id=grimoire.id, role="owner")
            )
            await session.commit()

            assert await require_membership(grimoire.id, me.id, session) == "owner"

            with pytest.raises(HTTPException) as exc:
                await require_membership(grimoire.id, stranger.id, session)
            assert exc.value.status_code == 404

            with pytest.raises(HTTPException) as exc2:
                await require_membership(uuid.uuid4(), uuid.uuid4(), session)
            assert exc2.value.status_code == 404
    finally:
        await engine.dispose()
