"""Load one Athenaeum into the portable backup data model (0039)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.backup.archive import Payload
from app.backup.manifest import BackupError
from app.media import get_media_root, media_file, referenced_asset_ids
from app.models import (
    Athenaeum,
    Build,
    Document,
    DocumentHistory,
    Grimoire,
    GrimoireCategory,
    MediaAsset,
    Node,
    PublicName,
)
from app.sphinx.runner import build_config


@dataclass
class Snapshot:
    data: dict[str, Any]
    files: list[Payload]
    source: dict[str, Any]
    counts: dict[str, int]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _safe_under(path: Path, root: Path, label: str) -> Path:
    try:
        resolved = path.resolve()
        base = root.resolve()
    except OSError as exc:
        raise BackupError(f"{label} path is unreadable.") from exc
    if not resolved.is_relative_to(base):
        raise BackupError(f"{label} path escapes its configured root.")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _walk_files(root: Path, prefix: str) -> list[Payload]:
    files: list[Payload] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BackupError(f"Symlinked artifact path: {path.name!r}.")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            files.append(Payload(f"{prefix}/{relative}", path))
    return files


def _assert_artifact(path: Path) -> Path:
    if not path.is_dir():
        raise BackupError("A published build artifact is missing.")
    if not (path / "html" / "index.html").is_file():
        raise BackupError("A build artifact has no html/index.html.")
    if not (path / "manifest.json").is_file():
        raise BackupError("A build artifact has no manifest.json.")
    return path


def _safe_log_path(path: Path, artifact_root: Path, build_root: Path) -> Path:
    try:
        resolved = path.resolve()
        artifact_base = artifact_root.resolve()
        build_base = build_root.resolve()
    except OSError as exc:
        raise BackupError("Build log path is unreadable.") from exc
    if not (
        resolved.is_relative_to(artifact_base) or resolved.is_relative_to(build_base)
    ):
        raise BackupError("Build log path escapes its configured roots.")
    return resolved


async def load_snapshot(
    session: AsyncSession, athenaeum_id: uuid.UUID, mode: str
) -> Snapshot:
    if mode not in ("editorial", "full"):
        raise BackupError(f"Unknown backup mode {mode!r}.")
    # One transaction-level view: every SELECT below sees the same data,
    # even while editors keep saving. Must be the first statement.
    await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))

    athenaeum = await session.get(Athenaeum, athenaeum_id)
    if athenaeum is None:
        raise BackupError("Athenaeum not found.")

    names = list(
        (
            await session.scalars(
                select(PublicName)
                .where(PublicName.athenaeum_id == athenaeum_id)
                .order_by(PublicName.created_at, PublicName.slug)
            )
        ).all()
    )
    categories = list(
        (
            await session.scalars(
                select(GrimoireCategory)
                .where(GrimoireCategory.athenaeum_id == athenaeum_id)
                .order_by(GrimoireCategory.position, GrimoireCategory.name)
            )
        ).all()
    )
    grimoires = list(
        (
            await session.scalars(
                select(Grimoire)
                .where(Grimoire.athenaeum_id == athenaeum_id)
                .order_by(Grimoire.created_at, Grimoire.id)
            )
        ).all()
    )
    grimoire_ids = [row.id for row in grimoires]

    nodes: list[Node] = []
    documents: list[Document] = []
    history: list[DocumentHistory] = []
    if grimoire_ids:
        nodes = list(
            (
                await session.scalars(
                    select(Node)
                    .where(Node.grimoire_id.in_(grimoire_ids))
                    .order_by(Node.grimoire_id, Node.position, Node.id)
                )
            ).all()
        )
        node_ids = [row.id for row in nodes]
        if node_ids:
            documents = list(
                (
                    await session.scalars(
                        select(Document)
                        .where(Document.node_id.in_(node_ids))
                        .order_by(Document.id)
                    )
                ).all()
            )
            document_ids = [row.id for row in documents]
            if document_ids:
                history = list(
                    (
                        await session.scalars(
                            select(DocumentHistory)
                            .where(DocumentHistory.document_id.in_(document_ids))
                            .order_by(
                                DocumentHistory.document_id,
                                DocumentHistory.version,
                            )
                        )
                    ).all()
                )

    media = (
        list(
            (
                await session.scalars(
                    select(MediaAsset)
                    .where(MediaAsset.grimoire_id.in_(grimoire_ids))
                    .order_by(MediaAsset.created_at, MediaAsset.id)
                )
            ).all()
        )
        if grimoire_ids
        else []
    )
    media_by_id = {row.id: row for row in media}

    all_builds = list(
        (
            await session.scalars(
                select(Build)
                .where(Build.athenaeum_id == athenaeum_id)
                .order_by(Build.build_number)
            )
        ).all()
    )
    if mode == "editorial":
        builds = [
            row
            for row in all_builds
            if row.status == "ok" and row.published_at is not None
        ]
    else:
        builds = [row for row in all_builds if row.status in ("ok", "failed")]
    included_numbers = {row.build_number for row in builds}

    def _pointer_number(build_id: uuid.UUID | None) -> int | None:
        if build_id is None:
            return None
        build = next((row for row in all_builds if row.id == build_id), None)
        if build is None or build.build_number not in included_numbers:
            raise BackupError("A publication pointer is not part of this backup.")
        return build.build_number

    files: list[Payload] = []
    media_root = get_media_root()
    for asset in media:
        path = _safe_under(media_file(asset), media_root, "Media")
        if not path.is_file():
            raise BackupError(f"Media file is missing for asset {asset.id}.")
        if path.stat().st_size != asset.size_bytes:
            raise BackupError(f"Media size changed for asset {asset.id}.")
        if _sha256_file(path) != asset.sha256:
            raise BackupError(f"Media hash changed for asset {asset.id}.")
        files.append(Payload(f"media/{asset.storage_path}", path))

    cfg = build_config()
    build_rows: list[dict[str, Any]] = []
    for build in builds:
        has_artifact = build.status == "ok"
        has_log = False
        if has_artifact:
            if not build.artifact_path:
                raise BackupError(f"Build #{build.build_number} has no artifact path.")
            artifact = _safe_under(
                Path(build.artifact_path), cfg.artifact_root, "Artifact"
            )
            _assert_artifact(artifact)
            files.extend(_walk_files(artifact, f"artifacts/{build.build_number}"))
        if mode == "full" and build.log_path:
            log = _safe_log_path(
                Path(build.log_path), cfg.artifact_root, cfg.build_root
            )
            if not log.is_file():
                raise BackupError(f"Build #{build.build_number} log is missing.")
            files.append(Payload(f"logs/{build.build_number}.log", log))
            has_log = True
        build_rows.append(
            {
                "id": str(build.id),
                "build_number": build.build_number,
                "status": build.status,
                "started": _iso(build.started),
                "finished": _iso(build.finished),
                "published_at": _iso(build.published_at),
                "artifact": has_artifact,
                "log": has_log,
            }
        )

    for document in documents:
        referenced = referenced_asset_ids(document.tiptap_json)
        missing = referenced - set(media_by_id)
        if missing:
            raise BackupError(
                "A document references media that is not in this library."
            )
    for row in history:
        referenced = referenced_asset_ids(row.tiptap_json)
        missing = referenced - set(media_by_id)
        if missing:
            raise BackupError(
                "Document history references media that is not in this library."
            )

    data: dict[str, Any] = {
        "athenaeum": {
            "slug": athenaeum.slug,
            "public_slug": athenaeum.public_slug,
            "title": athenaeum.title,
            "is_public": athenaeum.is_public,
            "custom_css": athenaeum.custom_css,
            "created_at": _iso(athenaeum.created_at),
        },
        "public_names": [
            {
                "slug": row.slug,
                "is_current": row.is_current,
                "created_at": _iso(row.created_at),
                "retired_at": _iso(row.retired_at),
            }
            for row in names
        ],
        "categories": [
            {
                "id": str(row.id),
                "name": row.name,
                "position": row.position,
                "created_at": _iso(row.created_at),
            }
            for row in categories
        ],
        "grimoires": [
            {
                "id": str(row.id),
                "category_id": str(row.category_id) if row.category_id else None,
                "slug": row.slug,
                "title": row.title,
                "source_format": row.source_format,
                "theme": row.theme,
                "created_at": _iso(row.created_at),
            }
            for row in grimoires
        ],
        "nodes": [
            {
                "id": str(row.id),
                "grimoire_id": str(row.grimoire_id),
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "kind": row.kind,
                "title": row.title,
                "slug": row.slug,
                "position": row.position,
            }
            for row in nodes
        ],
        "documents": [
            {
                "id": str(row.id),
                "node_id": str(row.node_id),
                "tiptap_json": row.tiptap_json,
                "source_text": row.source_text,
                "source_format": row.source_format,
                "version": row.version,
                "updated_at": _iso(row.updated_at),
            }
            for row in documents
        ],
        "document_history": [
            {
                "id": str(row.id),
                "document_id": str(row.document_id),
                "version": row.version,
                "tiptap_json": row.tiptap_json,
                "source_text": row.source_text,
                "at": _iso(row.at),
            }
            for row in history
        ],
        "media": [
            {
                "id": str(row.id),
                "grimoire_id": str(row.grimoire_id),
                "filename": row.filename,
                "content_type": row.content_type,
                "size_bytes": row.size_bytes,
                "sha256": row.sha256,
                "storage_path": row.storage_path,
                "created_at": _iso(row.created_at),
            }
            for row in media
        ],
        "builds": build_rows,
        "pointers": {
            "latest_build_number": _pointer_number(athenaeum.latest_build_id),
            "stable_build_number": _pointer_number(athenaeum.stable_build_id),
        },
    }
    counts = {
        "categories": len(categories),
        "grimoires": len(grimoires),
        "nodes": len(nodes),
        "documents": len(documents),
        "document_history": len(history),
        "media": len(media),
        "builds": len(builds),
    }
    return Snapshot(
        data=data,
        files=files,
        source={
            "athenaeum_id": str(athenaeum.id),
            "title": athenaeum.title,
            "public_slug": athenaeum.public_slug,
            "mode": mode,
        },
        counts=counts,
    )


def dump_data(data: dict[str, Any]) -> bytes:
    """Serialize data.json deterministically."""
    return (
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
