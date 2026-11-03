"""Build one backup archive from a live Athenaeum (0039)."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.backup.archive import Payload, write_archive
from app.backup.manifest import backup_root
from app.backup.snapshot import dump_data, load_snapshot
from app.db import get_database_url


@dataclass
class ExportResult:
    path: Path
    size_bytes: int
    sha256: str


async def _export(
    athenaeum_id: uuid.UUID, mode: str, container: str, destination: Path
) -> ExportResult:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            snapshot = await load_snapshot(session, athenaeum_id, mode)
            data_path = destination.with_suffix(destination.suffix + ".data.json")
            data_path.parent.mkdir(parents=True, exist_ok=True)
            data_path.write_bytes(dump_data(snapshot.data))
            try:
                payload = [Payload("data.json", data_path), *snapshot.files]
                size, digest = write_archive(
                    destination,
                    container,
                    mode=mode,
                    source=snapshot.source,
                    counts=snapshot.counts,
                    payload=payload,
                )
            finally:
                try:
                    data_path.unlink()
                except OSError:
                    pass
    finally:
        await engine.dispose()
    return ExportResult(destination, size, digest)


def export_archive_sync(
    athenaeum_id: str, mode: str, container: str, destination: str
) -> ExportResult:
    return asyncio.run(
        _export(uuid.UUID(athenaeum_id), mode, container, Path(destination))
    )


def archive_name(public_slug: str, mode: str, container: str) -> str:
    from datetime import UTC, datetime

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"scriptorium-{public_slug}-{mode}-{stamp}.{container}"


def temporary_path(container: str) -> Path:
    root = backup_root() / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{uuid.uuid4().hex}.{container}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
