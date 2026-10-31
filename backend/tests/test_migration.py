"""Migration round-trip against live PG18 (runs in CI via postgres:18 service).

Upgrade to head, assert the Q21 tables (incl. `athenaeums`, 0020, and
`public_names`, 0036), downgrade to base, upgrade again (idempotency proof
for `scriptorium-admin migrate`).
"""

from __future__ import annotations

import asyncio

from alembic.config import Config

from app.cli import MIN_SERVER_VERSION_NUM, _server_version_num
from tests.conftest import LIVE_DB_URL, needs_db

EXPECTED_TABLES = {
    "users",
    "memberships",
    "athenaeums",
    "grimoires",
    "grimoire_categories",
    "nodes",
    "documents",
    "document_history",
    "builds",
    "audit_log",
    "refresh_tokens",
    "public_names",
}


def _alembic_cfg() -> Config:
    from pathlib import Path

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(ini.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", LIVE_DB_URL)
    return cfg


@needs_db
def test_server_is_pg18_or_newer() -> None:
    assert asyncio.run(_server_version_num(LIVE_DB_URL)) >= MIN_SERVER_VERSION_NUM


@needs_db
def test_upgrade_downgrade_upgrade_roundtrip() -> None:
    from alembic import command

    cfg = _alembic_cfg()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    assert asyncio.run(_live_tables()) >= EXPECTED_TABLES

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    assert asyncio.run(_live_tables()) >= EXPECTED_TABLES


async def _live_tables() -> set[str]:
    from sqlalchemy import inspect
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(LIVE_DB_URL)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    finally:
        await engine.dispose()


@needs_db
def test_public_names_backfill_from_existing_public_slugs() -> None:
    """0008 must turn every existing canonical public_slug into a current row."""
    import uuid

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from alembic import command

    cfg = _alembic_cfg()
    command.downgrade(cfg, "0007serving")
    owner_id = uuid.uuid4()
    athenaeum_id = uuid.uuid4()
    public_slug = f"backfill-{uuid.uuid4().hex[:10]}"

    async def insert_fixture() -> None:
        engine = create_async_engine(LIVE_DB_URL)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO users (id, email, pw_hash, display) "
                        "VALUES (:id, :email, 'x', 'Backfill')"
                    ),
                    {"id": owner_id, "email": f"{owner_id}@example.test"},
                )
                await conn.execute(
                    text(
                        "INSERT INTO athenaeums "
                        "(id, owner_id, slug, public_slug, title) "
                        "VALUES (:id, :owner_id, :slug, :public_slug, 'Backfill')"
                    ),
                    {
                        "id": athenaeum_id,
                        "owner_id": owner_id,
                        "slug": public_slug,
                        "public_slug": public_slug,
                    },
                )
        finally:
            await engine.dispose()

    async def read_backfill() -> tuple[bool, uuid.UUID | None, object]:
        engine = create_async_engine(LIVE_DB_URL)
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT is_current, athenaeum_id, retired_at "
                            "FROM public_names WHERE slug = :slug"
                        ),
                        {"slug": public_slug},
                    )
                ).one()
                return bool(row[0]), row[1], row[2]
        finally:
            await engine.dispose()

    try:
        asyncio.run(insert_fixture())
        command.upgrade(cfg, "head")
        current, linked_id, retired_at = asyncio.run(read_backfill())
        assert current is True
        assert linked_id == athenaeum_id
        assert retired_at is None
    finally:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
