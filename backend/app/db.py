"""DB engine/session helpers. Fails loud without DATABASE_URL (no silent defaults)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_CONFIG_FILE = "/etc/scriptorium/config.env"


def get_database_url() -> str:
    """Return DATABASE_URL from env (or /etc config file). Raise if missing/not-asyncpg."""
    url = os.environ.get("DATABASE_URL")
    if not url and os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip("'\"")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set (env or /etc/scriptorium/config.env). "
            "See docs/onboarding/getting-started.md."
        )
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("DATABASE_URL must use the postgresql+asyncpg:// driver.")
    return url


_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: per-request session (RBAC checks run inside request handlers)."""
    maker = async_sessionmaker(
        get_engine(), expire_on_commit=False, class_=AsyncSession
    )
    async with maker() as session:
        yield session
