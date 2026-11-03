"""Backup format constants, limits, and manifest validation (0039)."""

from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import Any

BACKUP_FORMAT = "scriptorium-backup@1"
MANIFEST_NAME = "manifest.json"
DATA_NAME = "data.json"

MODES = ("editorial", "full")
FORMATS = ("zip", "tar.gz")
KINDS = ("export", "restore")
STATUSES = ("queued", "running", "ok", "failed")

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class BackupError(RuntimeError):
    """The archive or requested backup operation is invalid."""


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive, got {value}.")
    return value


def max_archive_bytes() -> int:
    return _int_env("SC_BACKUP_MAX_ARCHIVE_BYTES", 8 * 1024**3)


def max_expanded_bytes() -> int:
    return _int_env("SC_BACKUP_MAX_EXPANDED_BYTES", 16 * 1024**3)


def max_entry_bytes() -> int:
    return _int_env("SC_BACKUP_MAX_ENTRY_BYTES", 512 * 1024**2)


def max_entries() -> int:
    return _int_env("SC_BACKUP_MAX_ENTRIES", 200_000)


def download_ttl() -> timedelta:
    return timedelta(seconds=_int_env("SC_BACKUP_DOWNLOAD_TTL_SECONDS", 15 * 60))


def backup_root() -> Path:
    return Path(os.environ.get("SC_BACKUP_ROOT", "/var/lib/scriptorium/backups"))


def safe_relpath(name: str) -> str:
    """Validate a payload path; reject absolute, traversal, and odd forms."""
    if not name or "\x00" in name or "\\" in name:
        raise BackupError(f"Unsafe archive path: {name!r}.")
    if name.startswith("/"):
        raise BackupError(f"Absolute archive path: {name!r}.")
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name:
        raise BackupError(f"Non-canonical archive path: {name!r}.")
    if any(part in ("", ".", "..") for part in path.parts):
        raise BackupError(f"Unsafe archive path: {name!r}.")
    return name


def validate_manifest(raw: Any) -> dict[str, Any]:
    """Structurally validate the archive manifest (the integrity contract)."""
    if not isinstance(raw, dict):
        raise BackupError("Backup manifest is not an object.")
    if raw.get("format") != BACKUP_FORMAT:
        raise BackupError("Unsupported backup format.")
    if raw.get("mode") not in MODES:
        raise BackupError("Backup mode is invalid.")
    if raw.get("archive") not in FORMATS:
        raise BackupError("Backup container is invalid.")
    source = raw.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("athenaeum_id"), str):
        raise BackupError("Backup source metadata is invalid.")
    counts = raw.get("counts")
    if not isinstance(counts, dict) or not all(
        isinstance(value, int) and value >= 0 for value in counts.values()
    ):
        raise BackupError("Backup counts are invalid.")
    files = raw.get("files")
    if not isinstance(files, dict):
        raise BackupError("Backup file inventory is invalid.")
    if MANIFEST_NAME in files:
        raise BackupError("Backup inventory must not list the manifest itself.")
    for name, entry in files.items():
        if not isinstance(name, str):
            raise BackupError("Backup inventory has a non-string path.")
        safe_relpath(name)
        if not isinstance(entry, dict):
            raise BackupError(f"Inventory entry for {name!r} is invalid.")
        sha = entry.get("sha256")
        size = entry.get("bytes")
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            raise BackupError(f"Inventory hash for {name!r} is invalid.")
        if not isinstance(size, int) or size < 0:
            raise BackupError(f"Inventory size for {name!r} is invalid.")
    return raw
