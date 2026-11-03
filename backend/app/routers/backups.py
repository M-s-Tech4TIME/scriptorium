"""Backup export/restore routes (decision 0039).

Editorial exports stream synchronously. Full exports and Full restores are
queued jobs; the owner polls the job and receives an expiring HMAC-signed
download link. Restore accepts a raw archive body, auto-detects ZIP/tar.gz,
and always creates a fresh Athenaeum owned by the caller.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.audit import add_audit
from app.auth import get_current_user_id
from app.backup.archive import remove_tree, unlink_quiet
from app.backup.execute import execute_export_sync, execute_restore_sync
from app.backup.export import archive_name, export_archive_sync, temporary_path
from app.backup.manifest import (
    BackupError,
    backup_root,
    max_archive_bytes,
)
from app.backup.restore import RestoreResult, restore_archive_sync
from app.backup.tokens import make_download_token, verify_download_token
from app.db import get_session
from app.models import BackupJob
from app.serving.access import own_athenaeum

router = APIRouter(prefix="/api/v1", tags=["backups"])


class BackupIn(BaseModel):
    mode: Literal["editorial", "full"] = "editorial"
    format: Literal["zip", "tar.gz"] = "zip"


def dispatch_mode() -> str:
    mode = os.environ.get("SC_BACKUP_DISPATCH", "celery")
    if mode not in ("celery", "inline"):
        raise RuntimeError(
            f"SC_BACKUP_DISPATCH must be 'celery' or 'inline', got {mode!r}."
        )
    return mode


def _dispatch_export(job_id: uuid.UUID) -> None:
    from app.worker.celery_app import get_app

    get_app().send_task("app.worker.tasks.run_backup_export", args=[str(job_id)])


def _dispatch_restore(job_id: uuid.UUID) -> None:
    from app.worker.celery_app import get_app

    get_app().send_task("app.worker.tasks.run_backup_restore", args=[str(job_id)])


def _media_type(container: str) -> str:
    return "application/zip" if container == "zip" else "application/gzip"


def _job_body(job: BackupJob) -> dict[str, object]:
    download_url: str | None = None
    if (
        job.kind == "export"
        and job.status == "ok"
        and job.path
        and job.downloaded_at is None
        and job.expires_at is not None
        and job.expires_at > datetime.now(UTC)
    ):
        token = make_download_token(job.id, job.expires_at)
        download_url = f"/api/v1/backup-jobs/{job.id}/download?token={token}"
    return {
        "id": str(job.id),
        "kind": job.kind,
        "athenaeum_id": str(job.athenaeum_id) if job.athenaeum_id else None,
        "result_athenaeum_id": (
            str(job.result_athenaeum_id) if job.result_athenaeum_id else None
        ),
        "mode": job.mode,
        "format": job.format,
        "status": job.status,
        "size_bytes": job.size_bytes,
        "sha256": job.sha256,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
        "downloaded_at": (job.downloaded_at.isoformat() if job.downloaded_at else None),
        "download_url": download_url,
    }


def _restore_body(result: RestoreResult) -> dict[str, object]:
    return {
        "athenaeum_id": str(result.athenaeum_id),
        "title": result.title,
        "public_slug": result.public_slug,
        "mode": result.mode,
        "warnings": result.warnings,
        "counts": result.counts,
    }


def _sweep_tmp() -> None:
    """Best-effort cleanup of orphaned uploads/extractions older than a day."""
    root = backup_root() / "tmp"
    if not root.is_dir():
        return
    cutoff = time.time() - 24 * 60 * 60
    for path in root.iterdir():
        try:
            if path.stat().st_mtime >= cutoff:
                continue
            if path.is_dir():
                remove_tree(path)
            else:
                path.unlink()
        except OSError:
            continue


def _mark_dispatch_failure(job: BackupJob, exc: Exception) -> None:
    job.status = "failed"
    job.error = f"Worker dispatch failed: {exc}"[:2000]
    job.finished_at = datetime.now(UTC)


@router.post("/athenaeums/{athenaeum_id}/backups")
async def create_backup(
    athenaeum_id: uuid.UUID,
    body: BackupIn,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    athenaeum = await own_athenaeum(session, athenaeum_id, user_id)
    # End the read transaction before a potentially long archive write.
    await session.commit()
    _sweep_tmp()

    if body.mode == "editorial":
        destination = temporary_path(body.format)
        try:
            result = await anyio.to_thread.run_sync(
                export_archive_sync,
                str(athenaeum.id),
                body.mode,
                body.format,
                str(destination),
            )
        except Exception as exc:
            unlink_quiet(destination)
            add_audit(
                session,
                actor=user_id,
                action="backup_export_failed",
                meta={
                    "athenaeum_id": str(athenaeum.id),
                    "mode": body.mode,
                    "format": body.format,
                },
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Backup export failed: {exc}",
            ) from exc
        add_audit(
            session,
            actor=user_id,
            action="backup_exported",
            meta={
                "athenaeum_id": str(athenaeum.id),
                "mode": body.mode,
                "format": body.format,
            },
        )
        await session.commit()
        filename = archive_name(athenaeum.public_slug, body.mode, body.format)
        return FileResponse(
            destination,
            media_type=_media_type(body.format),
            filename=filename,
            headers={
                "X-Backup-SHA256": result.sha256,
                "X-Backup-Size": str(result.size_bytes),
            },
            background=BackgroundTask(unlink_quiet, destination),
        )

    job = BackupJob(
        kind="export",
        athenaeum_id=athenaeum.id,
        requested_by=user_id,
        mode=body.mode,
        format=body.format,
        status="queued",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    try:
        if dispatch_mode() == "inline":
            await anyio.to_thread.run_sync(execute_export_sync, str(job.id))
            await session.refresh(job)
        else:
            _dispatch_export(job.id)
    except Exception as exc:
        _mark_dispatch_failure(job, exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup worker dispatch failed.",
        ) from exc
    return JSONResponse(_job_body(job), status_code=status.HTTP_202_ACCEPTED)


@router.get("/backup-jobs/{job_id}")
async def get_backup_job(
    job_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    job = await session.get(BackupJob, job_id)
    if job is None or job.requested_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup job not found.",
        )
    expired = job.expires_at is not None and job.expires_at <= datetime.now(UTC)
    if job.kind == "export" and job.path and (expired or job.downloaded_at is not None):
        unlink_quiet(job.path)
        job.path = None
        await session.commit()
    return _job_body(job)


@router.get("/backup-jobs/{job_id}/download")
async def download_backup(
    job_id: uuid.UUID,
    token: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    job = await session.get(BackupJob, job_id)
    if job is None or job.kind != "export":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup job not found.",
        )
    if not verify_download_token(job.id, token):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup download link is invalid.",
        )
    if (
        job.status != "ok"
        or job.path is None
        or job.downloaded_at is not None
        or job.expires_at is None
        or job.expires_at <= datetime.now(UTC)
    ):
        if job.path:
            unlink_quiet(job.path)
            job.path = None
            await session.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Backup download link has expired or was already used.",
        )
    path = Path(job.path)
    if not path.is_file():
        job.path = None
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup archive is no longer available.",
        )
    claimed = await session.execute(
        update(BackupJob)
        .where(
            BackupJob.id == job.id,
            BackupJob.downloaded_at.is_(None),
        )
        .values(downloaded_at=datetime.now(UTC), path=None)
        .returning(BackupJob.id)
    )
    if claimed.first() is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Backup download link was already used.",
        )
    await session.commit()
    return FileResponse(
        path,
        media_type=_media_type(job.format),
        filename=path.name,
        background=BackgroundTask(unlink_quiet, path),
    )


@router.post("/backups/restore", status_code=status.HTTP_201_CREATED)
async def restore_backup(
    request: Request,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    _sweep_tmp()
    upload = temporary_path("upload")
    keep_upload = False
    try:
        size = 0
        with upload.open("wb") as out:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_archive_bytes():
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Backup archive exceeds the allowed size.",
                    )
                out.write(chunk)
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Restore request body is empty.",
            )
        from app.backup.archive import read_manifest

        try:
            manifest = read_manifest(upload)
        except BackupError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

        mode = manifest["mode"]
        container = manifest["archive"]
        if mode == "full":
            job = BackupJob(
                kind="restore",
                requested_by=user_id,
                mode=mode,
                format=container,
                status="queued",
                path=str(upload),
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            keep_upload = True
            try:
                if dispatch_mode() == "inline":
                    await anyio.to_thread.run_sync(execute_restore_sync, str(job.id))
                    await session.refresh(job)
                else:
                    _dispatch_restore(job.id)
            except Exception as exc:
                _mark_dispatch_failure(job, exc)
                job.path = None
                await session.commit()
                unlink_quiet(upload)
                keep_upload = False
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Backup worker dispatch failed.",
                ) from exc
            return JSONResponse(_job_body(job), status_code=status.HTTP_202_ACCEPTED)

        workdir = backup_root() / "tmp" / f"restore-{uuid.uuid4().hex}"
        try:
            result = await anyio.to_thread.run_sync(
                restore_archive_sync,
                str(upload),
                str(user_id),
                str(workdir),
            )
        except Exception as exc:
            add_audit(
                session,
                actor=user_id,
                action="backup_restore_failed",
                meta={"mode": mode, "format": container},
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Restore failed: {exc}",
            ) from exc
        finally:
            remove_tree(workdir)
        return JSONResponse(_restore_body(result), status_code=status.HTTP_201_CREATED)
    finally:
        if not keep_upload:
            unlink_quiet(upload)
