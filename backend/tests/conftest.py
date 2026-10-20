"""Shared fixtures. Live-DB tests skip unless DATABASE_URL is set (CI provides PG18).

When DATABASE_URL IS set, the schema is migrated to head ONCE at conftest
import — alphabetical pytest file order must not decide whether earlier
files (test_auth_api.py < test_migration.py) see a migrated DB (M3 C2 lesson).
"""

from __future__ import annotations

import os

import pytest

LIVE_DB_URL = os.environ.get("DATABASE_URL", "")

needs_db = pytest.mark.skipif(
    not LIVE_DB_URL.startswith("postgresql+asyncpg://"),
    reason="DATABASE_URL (postgresql+asyncpg://) not set — needs live PG18",
)

REDIS_TEST_URL = os.environ.get("REDIS_URL", "")

needs_redis = pytest.mark.skipif(
    not REDIS_TEST_URL.startswith("redis://"),
    reason="REDIS_URL (redis://) not set — needs live Redis",
)


def _migrate_if_live() -> None:
    if not LIVE_DB_URL.startswith("postgresql+asyncpg://"):
        return
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(ini.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", LIVE_DB_URL)
    command.upgrade(cfg, "head")


_migrate_if_live()


@pytest.fixture(autouse=True)
def _fresh_app_loops() -> None:
    """One event loop per test: decouple cached app↔Redis clients from dead loops."""
    from app import db, limiter

    db.reset_engine()
    limiter.reset_client()


async def app_teardown() -> None:
    """Dispose app-cached async clients on the owning loop (tests call before exit)."""
    from app import db, limiter

    await db.dispose_engine()
    await limiter.dispose_client()
