"""Migration round-trip against live PG18 (runs in CI via postgres:18 service).

Upgrade to head, assert the 8 Q21 tables, downgrade to base, upgrade again
(idempotency proof for `scriptorium-admin migrate`).
"""

from __future__ import annotations

import asyncio

from alembic.config import Config

from app.cli import MIN_SERVER_VERSION_NUM, _server_version_num
from tests.conftest import LIVE_DB_URL, needs_db

EXPECTED_TABLES = {
    "users",
    "memberships",
    "projects",
    "nodes",
    "documents",
    "document_history",
    "builds",
    "audit_log",
    "refresh_tokens",
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
