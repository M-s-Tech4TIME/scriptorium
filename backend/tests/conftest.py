"""Shared fixtures. Live-DB tests skip unless DATABASE_URL is set (CI provides PG18)."""

from __future__ import annotations

import os

import pytest

LIVE_DB_URL = os.environ.get("DATABASE_URL", "")

needs_db = pytest.mark.skipif(
    not LIVE_DB_URL.startswith("postgresql+asyncpg://"),
    reason="DATABASE_URL (postgresql+asyncpg://) not set — needs live PG18",
)
