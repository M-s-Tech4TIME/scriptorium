"""ZIP / tar.gz container adapters with strict integrity checking (0039)."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import stat
import tarfile
import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

from app.backup.manifest import (
    BACKUP_FORMAT,
    DATA_NAME,
    MANIFEST_NAME,
    BackupError,
    max_archive_bytes,
    max_entries,
    max_entry_bytes,
    max_expanded_bytes,
    safe_relpath,
    validate_manifest,
)


@dataclass(frozen=True)
class Payload:
    name: str
    path: Path


def detect_format(path: Path) -> str:
    with path.open("rb") as fh:
        head = fh.read(4)
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"\x1f\x8b"):
        return "tar.gz"
    raise BackupError("Unrecognized backup container (expected ZIP or tar.gz).")


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _zip_info(name: str, timestamp: datetime) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=timestamp.timetuple()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def _write_zip(
    destination: Path,
    manifest: dict[str, Any],
    payload: list[Payload],
    timestamp: datetime,
) -> None:
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
        strict_timestamps=False,
    ) as zf:
        for item in sorted(payload, key=lambda value: value.name):
            info = _zip_info(item.name, timestamp)
            with item.path.open("rb") as source, zf.open(info, "w") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        zf.writestr(_zip_info(MANIFEST_NAME, timestamp), manifest_bytes)


def _write_tar(
    destination: Path,
    manifest: dict[str, Any],
    payload: list[Payload],
    timestamp: datetime,
) -> None:
    mtime = int(timestamp.timestamp())
    with (
        destination.open("wb") as raw,
        gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            mtime=mtime,
            compresslevel=6,
        ) as gz,
        tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf,
    ):
        for item in sorted(payload, key=lambda value: value.name):
            info = tarfile.TarInfo(item.name)
            info.size = item.path.stat().st_size
            info.mtime = mtime
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with item.path.open("rb") as source:
                tf.addfile(info, source)
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size = len(manifest_bytes)
        info.mtime = mtime
        info.mode = 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tf.addfile(info, io.BytesIO(manifest_bytes))


def write_archive(
    destination: Path,
    container: str,
    *,
    mode: str,
    source: dict[str, Any],
    counts: dict[str, int],
    payload: list[Payload],
    created_at: datetime | None = None,
) -> tuple[int, str]:
    """Write a deterministic archive and return (size, sha256)."""
    if container not in ("zip", "tar.gz"):
        raise BackupError(f"Unsupported container {container!r}.")
    names = [item.name for item in payload]
    if len(names) != len(set(names)):
        raise BackupError("Duplicate payload path.")
    for name in names:
        safe_relpath(name)
        if name == MANIFEST_NAME:
            raise BackupError("Payload may not replace the manifest.")
    timestamp = created_at or datetime.now(UTC)
    files: dict[str, dict[str, Any]] = {}
    for item in payload:
        digest, size = _sha256_file(item.path)
        files[item.name] = {"sha256": digest, "bytes": size}
    manifest = {
        "format": BACKUP_FORMAT,
        "archive": container,
        "mode": mode,
        "created_at": timestamp.isoformat(),
        "source": source,
        "counts": counts,
        "files": files,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    if container == "zip":
        _write_zip(destination, manifest, payload, timestamp)
    else:
        _write_tar(destination, manifest, payload, timestamp)
    digest, size = _sha256_file(destination)
    return size, digest


def _read_manifest_zip(path: Path) -> bytes:
    with zipfile.ZipFile(path) as zf:
        matches = [info for info in zf.infolist() if info.filename == MANIFEST_NAME]
        if len(matches) != 1:
            raise BackupError("Backup must contain exactly one manifest.json.")
        info = matches[0]
        if info.is_dir() or info.file_size > max_entry_bytes():
            raise BackupError("Backup manifest is invalid.")
        return zf.read(info)


def _read_manifest_tar(path: Path) -> bytes:
    with tarfile.open(path, mode="r:gz") as tf:
        matches = [member for member in tf if member.name == MANIFEST_NAME]
        if len(matches) != 1:
            raise BackupError("Backup must contain exactly one manifest.json.")
        member = matches[0]
        if not member.isfile() or member.size > max_entry_bytes():
            raise BackupError("Backup manifest is invalid.")
        extracted = tf.extractfile(member)
        if extracted is None:
            raise BackupError("Backup manifest is unreadable.")
        return extracted.read()


def read_manifest(path: Path) -> dict[str, Any]:
    container = detect_format(path)
    try:
        raw = (
            _read_manifest_zip(path) if container == "zip" else _read_manifest_tar(path)
        )
    except BackupError:
        raise
    except (
        zipfile.BadZipFile,
        tarfile.TarError,
        gzip.BadGzipFile,
        EOFError,
        zlib.error,
    ) as exc:
        raise BackupError("Backup archive is corrupt or unreadable.") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BackupError("Backup manifest is not valid JSON.") from exc
    manifest = validate_manifest(parsed)
    if manifest["archive"] != container:
        raise BackupError("Backup manifest/container mismatch.")
    return manifest


def _zip_entries(path: Path) -> Iterator[tuple[str, int, IO[bytes]]]:
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            name = info.filename
            if info.is_dir():
                safe_relpath(name.rstrip("/"))
                continue
            if info.flag_bits & 0x1:
                raise BackupError(f"Encrypted archive entry: {name!r}.")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise BackupError(f"Symlink archive entry: {name!r}.")
            safe_relpath(name)
            with zf.open(info) as stream:
                yield name, info.file_size, stream


def _tar_entries(path: Path) -> Iterator[tuple[str, int, IO[bytes]]]:
    with tarfile.open(path, mode="r:gz") as tf:
        for member in tf:
            name = member.name
            if member.isdir():
                safe_relpath(name.rstrip("/"))
                continue
            if member.issym() or member.islnk():
                raise BackupError(f"Link archive entry: {name!r}.")
            if not member.isfile():
                raise BackupError(f"Special archive entry: {name!r}.")
            safe_relpath(name)
            stream = tf.extractfile(member)
            if stream is None:
                raise BackupError(f"Unreadable archive entry: {name!r}.")
            yield name, member.size, stream


def extract_archive(path: Path, destination: Path) -> dict[str, Any]:
    """Validate + extract an archive into an empty directory.

    Every entry is checked against the manifest while it is written; the
    caller gets the validated manifest and can trust ``destination``.
    """
    if path.stat().st_size > max_archive_bytes():
        raise BackupError("Backup archive is too large.")
    manifest = read_manifest(path)
    inventory = manifest["files"]
    if destination.exists() and any(destination.iterdir()):
        raise BackupError("Extraction destination is not empty.")
    destination.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    expanded = 0
    iterator = (
        _zip_entries(path) if manifest["archive"] == "zip" else _tar_entries(path)
    )
    try:
        for entries, (name, declared_size, stream) in enumerate(iterator, start=1):
            if entries > max_entries():
                raise BackupError("Backup contains too many entries.")
            if name in seen:
                raise BackupError(f"Duplicate archive entry: {name!r}.")
            seen.add(name)
            if name == MANIFEST_NAME:
                expected = None
            else:
                expected = inventory.get(name)
                if expected is None:
                    raise BackupError(f"Undeclared archive entry: {name!r}.")
                if declared_size != expected["bytes"]:
                    raise BackupError(f"Size mismatch for {name!r}.")
            if declared_size > max_entry_bytes():
                raise BackupError(f"Entry too large: {name!r}.")
            expanded += declared_size
            if expanded > max_expanded_bytes():
                raise BackupError("Backup expands beyond the allowed limit.")
            target = destination / name
            if target.parent.exists() and not target.parent.is_dir():
                raise BackupError(f"Path conflict in archive: {name!r}.")
            if target.exists() and target.is_dir():
                raise BackupError(f"Path conflict in archive: {name!r}.")
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            written = 0
            with target.open("wb") as out:
                while chunk := stream.read(1024 * 1024):
                    written += len(chunk)
                    if written > declared_size or written > max_entry_bytes():
                        raise BackupError(f"Entry exceeds its declared size: {name!r}.")
                    digest.update(chunk)
                    out.write(chunk)
            if written != declared_size:
                raise BackupError(f"Truncated archive entry: {name!r}.")
            if expected is not None and digest.hexdigest() != expected["sha256"]:
                raise BackupError(f"Hash mismatch for {name!r}.")
    except BackupError:
        raise
    except (
        zipfile.BadZipFile,
        tarfile.TarError,
        gzip.BadGzipFile,
        EOFError,
        zlib.error,
    ) as exc:
        raise BackupError("Backup archive is corrupt or unreadable.") from exc
    missing = set(inventory) - seen
    if missing:
        raise BackupError(
            "Backup is missing declared files: " + ", ".join(sorted(missing)[:5])
        )
    if DATA_NAME not in inventory:
        raise BackupError("Backup has no data.json.")
    return manifest


def load_data(destination: Path) -> dict[str, Any]:
    path = destination / DATA_NAME
    if path.stat().st_size > max_entry_bytes():
        raise BackupError("Backup data.json is too large.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BackupError("Backup data.json is not valid JSON.") from exc
    if not isinstance(raw, dict):
        raise BackupError("Backup data.json is not an object.")
    return raw


def remove_tree(path: Path) -> None:
    """Best-effort removal that never follows symlinks out of the tree."""
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        try:
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass


def unlink_quiet(path: str | os.PathLike[str]) -> None:
    try:
        Path(path).unlink()
    except OSError:
        pass
