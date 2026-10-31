"""Build executor (M4-C3) — one implementation, two dispatch modes.

`execute_build_sync` is the single entry: the builds router calls it
inside a worker thread when `SC_BUILD_DISPATCH=inline` (dev/CI), and
the Celery task (`app.worker.tasks`) calls it in production. The task's
own engine is created fresh per run and ALWAYS awaited-disposed — the
cached app engine must never cross event loops (2026-10-21 lesson).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db import get_database_url
from app.models import Build
from app.sphinx.loader import load_site_snapshot
from app.sphinx.runner import build_config, run_build
from app.sphinx.sourcegen import plan_site

_ACTIVE = ("queued", "running")


async def _execute_build(build_id: uuid.UUID) -> None:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            build = await session.get(Build, build_id)
            if build is None:
                return  # vanished before us — nothing to run
            if build.status not in _ACTIVE or build.athenaeum_id is None:
                return  # only queued work executes here (E3 discipline)

            build.status = "running"
            build.started = datetime.now(UTC)
            await session.commit()

            log_path: str
            artifact_path: str | None = None
            try:
                athenaeum, books, site_credit, media_files = await load_site_snapshot(
                    session, build.athenaeum_id
                )
                plan = plan_site(
                    athenaeum.title,
                    books,
                    site_credit=site_credit,
                    site_id=athenaeum.public_slug,
                    custom_css=athenaeum.custom_css or None,
                )
                outcome = run_build(
                    plan,
                    build.id,
                    build.athenaeum_id,
                    build.build_number,
                    site_id=athenaeum.public_slug,
                    media=media_files,
                )
                log_path = outcome.log_path if outcome.log_path is not None else ""
                artifact_path = outcome.artifact_path
                build.status = "ok" if outcome.ok else "failed"
            except Exception as exc:  # noqa: BLE001 - build boundary marks any failure
                # staging/plan/runner failures → build failed
                build.status = "failed"
                log_text = (
                    "Scriptorium build log (0026) — staging failed\n"
                    f"{type(exc).__name__}: {exc}\n"
                )
                cfg = build_config()
                crash = cfg.build_root / str(build.id) / "build.log"
                crash.parent.mkdir(parents=True, exist_ok=True)
                crash.write_text(log_text, encoding="utf-8")
                log_path = str(crash)

            build.finished = datetime.now(UTC)
            build.log_path = log_path
            build.artifact_path = artifact_path
            await session.commit()
    finally:
        await engine.dispose()


def execute_build_sync(build_id: str) -> None:
    """Blocking wrapper for thread-pool calls (inline dispatch) and Celery."""
    asyncio.run(_execute_build(uuid.UUID(build_id)))
