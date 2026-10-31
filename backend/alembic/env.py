"""Alembic environment — async online migrations only.

Offline SQL generation is unsupported (no sync driver installed by design);
`scriptorium-admin migrate` always runs online against PG 18+.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    raise RuntimeError(
        "Offline mode is unsupported; run `scriptorium-admin migrate` online."
    )


def _run_sync(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        section, prefix="sqlalchemy.", poolclass=None
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_run_sync)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
