"""Backup container/integrity tests (decision 0039) — no database required."""

from __future__ import annotations

import hashlib
import io
import json
import stat
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.backup.archive import (
    Payload,
    detect_format,
    extract_archive,
    read_manifest,
    write_archive,
)
from app.backup.manifest import (
    BACKUP_FORMAT,
    BackupError,
    max_archive_bytes,
    validate_manifest,
)

_FIXED = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def _manifest(
    files: dict[str, dict[str, object]],
    *,
    container: str = "zip",
    mode: str = "editorial",
) -> dict[str, object]:
    return {
        "format": BACKUP_FORMAT,
        "archive": container,
        "mode": mode,
        "created_at": _FIXED.isoformat(),
        "source": {"athenaeum_id": "00000000-0000-0000-0000-000000000001"},
        "counts": {
            "categories": 0,
            "grimoires": 0,
            "nodes": 0,
            "documents": 0,
            "document_history": 0,
            "media": 0,
            "builds": 0,
        },
        "files": files,
    }


def _entry(data: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _zip_with(path: Path, entries: list[tuple[str, bytes]], manifest: object) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
        zf.writestr("manifest.json", json.dumps(manifest))


def _tar_with(
    path: Path, entries: list[tuple[str, bytes, bytes]], manifest: object
) -> None:
    with tarfile.open(path, "w:gz") as tf:
        for name, kind, data in entries:
            info = tarfile.TarInfo(name)
            if kind == b"symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tf.addfile(info)
                continue
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        manifest_bytes = json.dumps(manifest).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest_bytes)
        tf.addfile(info, io.BytesIO(manifest_bytes))


@pytest.mark.parametrize("container", ["zip", "tar.gz"])
def test_roundtrip_both_containers(tmp_path: Path, container: str) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_bytes(b'{"hello":"world"}\n')
    media_path = tmp_path / "image.png"
    media_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    archive = tmp_path / f"backup.{container}"
    size, digest = write_archive(
        archive,
        container,
        mode="editorial",
        source={"athenaeum_id": "00000000-0000-0000-0000-000000000001"},
        counts={"builds": 0},
        payload=[
            Payload("data.json", data_path),
            Payload("media/aa/image.png", media_path),
        ],
        created_at=_FIXED,
    )
    assert size == archive.stat().st_size
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert detect_format(archive) == container

    manifest = read_manifest(archive)
    assert manifest["mode"] == "editorial"
    assert set(manifest["files"]) == {"data.json", "media/aa/image.png"}

    destination = tmp_path / "out"
    extracted = extract_archive(archive, destination)
    assert extracted["archive"] == container
    assert (destination / "data.json").read_bytes() == data_path.read_bytes()
    assert (destination / "media/aa/image.png").read_bytes() == media_path.read_bytes()


def test_manifest_rejects_unknown_format() -> None:
    with pytest.raises(BackupError, match="Unsupported backup format"):
        validate_manifest({"format": "scriptorium-backup@99"})


def test_manifest_rejects_manifest_in_inventory() -> None:
    with pytest.raises(BackupError, match="manifest itself"):
        validate_manifest(_manifest({"manifest.json": _entry(b"x")}))


def test_manifest_rejects_unsafe_inventory_path() -> None:
    with pytest.raises(BackupError, match="Unsafe archive path"):
        validate_manifest(_manifest({"../escape": _entry(b"x")}))


@pytest.mark.parametrize("name", ["/abs", "a/../../b", "a\\b", "a//b"])
def test_safe_paths_rejected(name: str) -> None:
    with pytest.raises(BackupError):
        validate_manifest(_manifest({name: _entry(b"x")}))


def test_zip_traversal_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)})
    archive = tmp_path / "evil.zip"
    _zip_with(
        archive,
        [("data.json", data), ("../evil.txt", b"nope")],
        manifest,
    )
    with pytest.raises(BackupError, match="Unsafe archive path"):
        extract_archive(archive, tmp_path / "out")


def test_tar_duplicate_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)}, container="tar.gz")
    archive = tmp_path / "dup.tar.gz"
    _tar_with(
        archive,
        [("data.json", b"file", data), ("data.json", b"file", data)],
        manifest,
    )
    with pytest.raises(BackupError, match="Duplicate archive entry"):
        extract_archive(archive, tmp_path / "out")


def test_zip_symlink_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)})
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("data.json", data)
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "/etc/passwd")
        zf.writestr("manifest.json", json.dumps(manifest))
    with pytest.raises(BackupError, match="Symlink archive entry"):
        extract_archive(archive, tmp_path / "out")


def test_tar_symlink_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)}, container="tar.gz")
    archive = tmp_path / "link.tar.gz"
    _tar_with(
        archive,
        [("data.json", b"file", data), ("link", b"symlink", b"")],
        manifest,
    )
    with pytest.raises(BackupError, match="Link archive entry"):
        extract_archive(archive, tmp_path / "out")


def test_tar_absolute_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)}, container="tar.gz")
    archive = tmp_path / "abs.tar.gz"
    _tar_with(
        archive,
        [("data.json", b"file", data), ("/etc/passwd", b"file", b"x")],
        manifest,
    )
    with pytest.raises(BackupError, match="Absolute archive path"):
        extract_archive(archive, tmp_path / "out")


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    manifest = _manifest({"data.json": _entry(b"good")})
    archive = tmp_path / "hash.zip"
    _zip_with(archive, [("data.json", b"evil")], manifest)
    with pytest.raises(BackupError, match="Hash mismatch"):
        extract_archive(archive, tmp_path / "out")


def test_size_mismatch_rejected(tmp_path: Path) -> None:
    manifest = _manifest({"data.json": _entry(b"good")})
    archive = tmp_path / "size.zip"
    _zip_with(archive, [("data.json", b"longer")], manifest)
    with pytest.raises(BackupError, match="Size mismatch"):
        extract_archive(archive, tmp_path / "out")


def test_missing_declared_file_rejected(tmp_path: Path) -> None:
    manifest = _manifest({"data.json": _entry(b"{}"), "media/aa/x.png": _entry(b"x")})
    archive = tmp_path / "missing.zip"
    _zip_with(archive, [("data.json", b"{}")], manifest)
    with pytest.raises(BackupError, match="missing declared files"):
        extract_archive(archive, tmp_path / "out")


def test_archive_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_path = tmp_path / "data.json"
    data_path.write_bytes(b"{}")
    archive = tmp_path / "big.zip"
    write_archive(
        archive,
        "zip",
        mode="editorial",
        source={"athenaeum_id": "00000000-0000-0000-0000-000000000001"},
        counts={"builds": 0},
        payload=[Payload("data.json", data_path)],
        created_at=_FIXED,
    )
    monkeypatch.setenv("SC_BACKUP_MAX_ARCHIVE_BYTES", "1")
    assert max_archive_bytes() == 1
    with pytest.raises(BackupError, match="too large"):
        extract_archive(archive, tmp_path / "out")


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("broken.zip", b"PK\x03\x04not-a-zip"),
        ("broken.tar.gz", b"\x1f\x8bnot-a-gzip"),
    ],
)
def test_corrupt_container_rejected(tmp_path: Path, name: str, data: bytes) -> None:
    archive = tmp_path / name
    archive.write_bytes(data)
    with pytest.raises(BackupError, match="corrupt or unreadable"):
        read_manifest(archive)


@pytest.mark.parametrize(
    "entries",
    [
        [("data.json", b"{}"), ("data.json/child", b"x")],
        [("data.json/child", b"x"), ("data.json", b"{}")],
    ],
)
def test_file_directory_conflict_rejected(
    tmp_path: Path, entries: list[tuple[str, bytes]]
) -> None:
    manifest = _manifest({name: _entry(data) for name, data in entries})
    archive = tmp_path / "conflict.zip"
    _zip_with(archive, entries, manifest)
    with pytest.raises(BackupError, match="Path conflict"):
        extract_archive(archive, tmp_path / "out")


def test_encrypted_zip_entry_rejected(tmp_path: Path) -> None:
    data = b"{}"
    manifest = _manifest({"data.json": _entry(data)})
    archive = tmp_path / "encrypted.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("data.json", data)
        zf.writestr("manifest.json", json.dumps(manifest))
    raw = bytearray(archive.read_bytes())
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        index = raw.find(signature)
        raw[index + offset] |= 1
    archive.write_bytes(raw)
    with pytest.raises(BackupError, match="Encrypted archive entry"):
        extract_archive(archive, tmp_path / "out")
