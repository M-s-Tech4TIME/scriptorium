"""Execute Full backup export/restore jobs (0039 C1).

Celery and inline dispatch share this entry point, exactly like builds:
one implementation, two schedulers. Each run creates and disposes its own
engine so a worker loop never shares the app's cached pool.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.audit import add_audit
from app.backup.archive import remove_tree, unlink_quiet
from app.backup.export import archive_name, export_archive_sync
from app.backup.manifest import BackupError, backup_root, download_ttl
from app.backup.restore import restore_archive_sync
from app.db import get_database_url
from app.models import Athenaeum, BackupJob


async def _execute_export(job_id: uuid.UUID) -> None:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            job = await session.get(BackupJob, job_id)
            if job is None or job.kind != "export" or job.status != "queued":
                return
            job.status = "running"
            job.started_at = datetime.now(UTC)
            await session.commit()

            destination: Path | None = None
            try:
                if job.athenaeum_id is None:
                    raise BackupError("Backup job has no source Athenaeum.")
                athenaeum = await session.get(Athenaeum, job.athenaeum_id)
                if athenaeum is None:
                    raise BackupError("Backup source Athenaeum no longer exists.")
                root = backup_root() / "jobs"
                root.mkdir(parents=True, exist_ok=True)
                destination = root / (
                    f"{job.id.hex}-"
                    f"{archive_name(athenaeum.public_slug, job.mode, job.format)}"
                )
                result = await asyncio.to_thread(
                    export_archive_sync,
                    str(athenaeum.id),
                    job.mode,
                    job.format,
                    str(destination),
                )
                job.path = str(result.path)
                job.size_bytes = result.size_bytes
                job.sha256 = result.sha256
                job.expires_at = datetime.now(UTC) + download_ttl()
                job.status = "ok"
                job.finished_at = datetime.now(UTC)
                add_audit(
                    session,
                    actor=job.requested_by,
                    action="backup_exported",
                    meta={
                        "job_id": str(job.id),
                        "athenaeum_id": str(athenaeum.id),
                        "mode": job.mode,
                        "format": job.format,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - job boundary records any failure
                if destination is not None:
                    unlink_quiet(destination)
                job.status = "failed"
                job.error = str(exc)[:2000]
                job.finished_at = datetime.now(UTC)
                add_audit(
                    session,
                    actor=job.requested_by,
                    action="backup_export_failed",
                    meta={
                        "job_id": str(job.id),
                        "athenaeum_id": (
                            str(job.athenaeum_id)
                            if job.athenaeum_id is not None
                            else None
                        ),
                        "mode": job.mode,
                        "format": job.format,
                    },
                )
            await session.commit()
    finally:
        await engine.dispose()


async def _execute_restore(job_id: uuid.UUID) -> None:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            job = await session.get(BackupJob, job_id)
            if job is None or job.kind != "restore" or job.status != "queued":
                return
            job.status = "running"
            job.started_at = datetime.now(UTC)
            await session.commit()

            archive = Path(job.path) if job.path else None
            workdir = backup_root() / "tmp" / f"restore-{job.id.hex}"
            try:
                if archive is None or job.requested_by is None:
                    raise BackupError("Restore job has no archive or importer.")
                result = await asyncio.to_thread(
                    restore_archive_sync,
                    str(archive),
                    str(job.requested_by),
                    str(workdir),
                )
                job.result_athenaeum_id = result.athenaeum_id
                job.status = "ok"
                job.finished_at = datetime.now(UTC)
            except Exception as exc:  # noqa: BLE001 - job boundary records any failure
                job.status = "failed"
                job.error = str(exc)[:2000]
                job.finished_at = datetime.now(UTC)
                add_audit(
                    session,
                    actor=job.requested_by,
                    action="backup_restore_failed",
                    meta={
                        "job_id": str(job.id),
                        "mode": job.mode,
                        "format": job.format,
                    },
                )
            finally:
                if archive is not None:
                    unlink_quiet(archive)
                job.path = None
                remove_tree(workdir)
            await session.commit()
    finally:
        await engine.dispose()


def execute_export_sync(job_id: str) -> None:
    asyncio.run(_execute_export(uuid.UUID(job_id)))


def execute_restore_sync(job_id: str) -> None:
    asyncio.run(_execute_restore(uuid.UUID(job_id)))
