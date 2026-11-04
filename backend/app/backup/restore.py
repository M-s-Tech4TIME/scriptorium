"""Validate and restore one backup archive (0039 D1/E1).

The archive is untrusted input. This module validates the manifest, every
relational row, and the exact payload inventory before it writes anything.
Files are then staged under fresh UUIDs and the database import runs in one
transaction. A failed restore cleans the staged files and leaves no new
Athenaeum.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.audit import add_audit
from app.backup.archive import extract_archive, load_data, remove_tree, unlink_quiet
from app.backup.manifest import BackupError
from app.db import get_database_url
from app.media import (
    MAX_MEDIA_BYTES,
    MEDIA_TYPES,
    get_media_root,
    media_url,
    sniff_image,
    storage_relpath,
)
from app.models import (
    Athenaeum,
    Build,
    Document,
    DocumentHistory,
    Grimoire,
    GrimoireCategory,
    MediaAsset,
    Membership,
    Node,
    PublicName,
)
from app.serving.css import MAX_CUSTOM_CSS_BYTES, CustomCssError, sanitize_custom_css
from app.serving.manifest import MANIFEST_NAME, read_artifact_manifest
from app.serving.names import (
    PUBLIC_NAME_RE,
    PUBLIC_NAMES_LOCK,
    RESERVED_PUBLIC_SLUGS,
)
from app.sphinx.runner import build_config

_MEDIA_URL_RE = re.compile(
    r"/_static/media/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})\.(?P<ext>png|jpe?g|gif|webp|avif)"
)
_MEDIA_TEXT_RE = re.compile(
    r"/_static/media/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})\.(?:png|jpe?g|gif|webp|avif)"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SLUG_RE = re.compile(r"[a-z0-9-]+")
_COUNT_KEYS = (
    "categories",
    "grimoires",
    "nodes",
    "documents",
    "document_history",
    "media",
    "builds",
)
_TOP_LEVEL_KEYS = {
    "athenaeum",
    "public_names",
    "categories",
    "grimoires",
    "nodes",
    "documents",
    "document_history",
    "media",
    "builds",
    "pointers",
}


@dataclass(frozen=True)
class RestoreResult:
    athenaeum_id: uuid.UUID
    title: str
    public_slug: str
    mode: str
    warnings: list[str]
    counts: dict[str, int]


@dataclass
class _Plan:
    mode: str
    source: dict[str, Any]
    athenaeum: dict[str, Any]
    public_names: list[dict[str, Any]]
    categories: list[dict[str, Any]]
    grimoires: list[dict[str, Any]]
    nodes: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    history: list[dict[str, Any]]
    media: list[dict[str, Any]]
    builds: list[dict[str, Any]]
    latest: int | None
    stable: int | None
    counts: dict[str, int]


@dataclass(frozen=True)
class _MediaStage:
    row: dict[str, Any]
    new_id: uuid.UUID
    storage_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _BuildStage:
    row: dict[str, Any]
    new_id: uuid.UUID
    artifact_path: str | None
    log_path: str | None


@dataclass
class _Staged:
    media: list[_MediaStage] = field(default_factory=list)
    builds: list[_BuildStage] = field(default_factory=list)
    media_paths: list[Path] = field(default_factory=list)
    artifact_dirs: list[Path] = field(default_factory=list)
    log_paths: list[Path] = field(default_factory=list)


def _as_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BackupError(f"{label} must be an object.")
    return cast(dict[str, Any], value)


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise BackupError(f"{label} must be a list.")
    return value


def _dict_list(value: Any, label: str) -> list[dict[str, Any]]:
    return [
        _as_dict(item, f"{label}[{index}]")
        for index, item in enumerate(_as_list(value, label))
    ]


def _text(
    value: Any,
    label: str,
    *,
    max_len: int | None = None,
    empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise BackupError(f"{label} must be a string.")
    if "\x00" in value:
        raise BackupError(f"{label} contains a NUL byte.")
    if not empty and not value:
        raise BackupError(f"{label} may not be empty.")
    if max_len is not None and len(value) > max_len:
        raise BackupError(f"{label} is longer than {max_len} characters.")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise BackupError(f"{label} must be a boolean.")
    return value


def _int(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BackupError(f"{label} must be an integer.")
    if value < minimum:
        raise BackupError(f"{label} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise BackupError(f"{label} must be at most {maximum}.")
    return value


def _uuid(value: Any, label: str) -> uuid.UUID:
    if not isinstance(value, str):
        raise BackupError(f"{label} must be a UUID string.")
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise BackupError(f"{label} is not a valid UUID.") from exc


def _timestamp(value: Any, label: str, *, required: bool = True) -> datetime | None:
    if value is None:
        if required:
            raise BackupError(f"{label} is required.")
        return None
    if not isinstance(value, str):
        raise BackupError(f"{label} must be an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise BackupError(f"{label} is not a valid ISO timestamp.") from exc
    if parsed.tzinfo is None:
        raise BackupError(f"{label} must include a timezone.")
    return parsed


def _slug(value: Any, label: str, *, max_len: int) -> str:
    slug = _text(value, label, max_len=max_len)
    if not _SLUG_RE.fullmatch(slug):
        raise BackupError(f"{label} must match [a-z0-9-]+.")
    return slug


def _image_srcs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        if node.get("type") == "image":
            attrs = node.get("attrs")
            if not isinstance(attrs, dict) or not isinstance(attrs.get("src"), str):
                raise BackupError("A document image has no valid src attribute.")
            yield attrs["src"]
        for value in node.values():
            yield from _image_srcs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _image_srcs(value)


def _rewrite_json(value: Any, url_by_id: dict[uuid.UUID, str]) -> Any:
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            if key == "src" and isinstance(item, str):
                match = _MEDIA_URL_RE.fullmatch(item)
                if match is not None:
                    result[key] = url_by_id[uuid.UUID(match.group("id"))]
                    continue
            result[key] = _rewrite_json(item, url_by_id)
        return result
    if isinstance(value, list):
        return [_rewrite_json(item, url_by_id) for item in value]
    return value


def _rewrite_text(value: str, url_by_id: dict[uuid.UUID, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        return url_by_id[uuid.UUID(match.group("id"))]

    return _MEDIA_TEXT_RE.sub(replace, value)


def _node_levels(nodes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Return parent-first levels; reject cycles and unreachable nodes."""
    by_parent: dict[uuid.UUID | None, list[dict[str, Any]]] = {}
    for row in nodes:
        by_parent.setdefault(row["parent_id"], []).append(row)
    levels: list[list[dict[str, Any]]] = []
    frontier: list[uuid.UUID | None] = [None]
    seen = 0
    while frontier:
        level: list[dict[str, Any]] = []
        next_frontier: list[uuid.UUID | None] = []
        for parent_id in frontier:
            for row in by_parent.get(parent_id, []):
                level.append(row)
                next_frontier.append(row["id"])
        if not level:
            break
        levels.append(level)
        seen += len(level)
        frontier = next_frontier
    if seen != len(nodes):
        raise BackupError("Node hierarchy contains a cycle or orphan.")
    return levels


def _validate_inventory(manifest: dict[str, Any], plan: _Plan) -> None:
    inventory = set(manifest["files"])
    expected = {"data.json"}
    for row in plan.media:
        expected.add(f"media/{row['storage_path']}")
    for row in plan.builds:
        number = row["build_number"]
        prefix = f"artifacts/{number}/"
        if row["artifact"]:
            artifact_files = {name for name in inventory if name.startswith(prefix)}
            required = {f"{prefix}html/index.html", f"{prefix}manifest.json"}
            if not required <= artifact_files:
                raise BackupError(
                    f"Build #{number} is missing its artifact or manifest."
                )
            expected |= artifact_files
        elif any(name.startswith(prefix) for name in inventory):
            raise BackupError(f"Build #{number} has unexpected artifact files.")
        log_name = f"logs/{number}.log"
        if row["log"]:
            if log_name not in inventory:
                raise BackupError(f"Build #{number} is missing its log.")
            expected.add(log_name)
        elif any(name.startswith(f"logs/{number}.") for name in inventory):
            raise BackupError(f"Build #{number} has an unexpected log.")
    missing = expected - inventory
    extra = inventory - expected
    if missing or extra:
        raise BackupError(
            "Backup payload does not match data.json"
            + (f" (missing {len(missing)})" if missing else "")
            + (f" (unexpected {len(extra)})" if extra else "")
            + "."
        )


def _parse_plan(manifest: dict[str, Any], data: dict[str, Any]) -> _Plan:
    if set(data) != _TOP_LEVEL_KEYS:
        raise BackupError("Backup data.json has an unexpected shape.")
    mode = manifest["mode"]

    raw_athenaeum = _as_dict(data["athenaeum"], "athenaeum")
    title = _text(raw_athenaeum.get("title"), "athenaeum.title", max_len=200)
    athenaeum_slug = _slug(raw_athenaeum.get("slug"), "athenaeum.slug", max_len=120)
    public_slug = _slug(
        raw_athenaeum.get("public_slug"), "athenaeum.public_slug", max_len=160
    )
    is_public = _bool(raw_athenaeum.get("is_public"), "athenaeum.is_public")
    raw_css = _text(
        raw_athenaeum.get("custom_css"),
        "athenaeum.custom_css",
        max_len=MAX_CUSTOM_CSS_BYTES,
        empty=True,
    )
    try:
        custom_css = sanitize_custom_css(raw_css)
    except CustomCssError as exc:
        raise BackupError(f"Backup custom CSS is invalid: {exc}") from exc
    athenaeum_created = _timestamp(
        raw_athenaeum.get("created_at"), "athenaeum.created_at"
    )
    athenaeum = {
        "title": title,
        "slug": athenaeum_slug,
        "public_slug": public_slug,
        "is_public": is_public,
        "custom_css": custom_css,
        "created_at": athenaeum_created,
    }

    public_names: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, row in enumerate(_dict_list(data["public_names"], "public_names")):
        name = _slug(row.get("slug"), f"public_names[{index}].slug", max_len=160)
        if name in seen_names:
            raise BackupError("Backup public names contain a duplicate.")
        seen_names.add(name)
        current = _bool(row.get("is_current"), f"public_names[{index}].is_current")
        created = _timestamp(row.get("created_at"), f"public_names[{index}].created_at")
        retired = _timestamp(
            row.get("retired_at"),
            f"public_names[{index}].retired_at",
            required=False,
        )
        if not current and retired is None:
            raise BackupError("A public-name alias has no retirement time.")
        public_names.append(
            {
                "slug": name,
                "is_current": current,
                "created_at": created,
                "retired_at": retired,
            }
        )
    current_names = [row for row in public_names if row["is_current"]]
    if len(current_names) != 1 or current_names[0]["slug"] != public_slug:
        raise BackupError("Backup public-name registry does not match its site.")

    categories: list[dict[str, Any]] = []
    category_ids: set[uuid.UUID] = set()
    category_names: set[str] = set()
    for index, row in enumerate(_dict_list(data["categories"], "categories")):
        category_id = _uuid(row.get("id"), f"categories[{index}].id")
        if category_id in category_ids:
            raise BackupError("Backup categories contain a duplicate id.")
        category_ids.add(category_id)
        name = _text(row.get("name"), f"categories[{index}].name", max_len=120)
        if name in category_names:
            raise BackupError("Backup categories contain a duplicate name.")
        category_names.add(name)
        categories.append(
            {
                "id": category_id,
                "name": name,
                "position": _int(row.get("position"), f"categories[{index}].position"),
                "created_at": _timestamp(
                    row.get("created_at"), f"categories[{index}].created_at"
                ),
            }
        )

    grimoires: list[dict[str, Any]] = []
    grimoire_ids: set[uuid.UUID] = set()
    grimoire_slugs: set[str] = set()
    for index, row in enumerate(_dict_list(data["grimoires"], "grimoires")):
        grimoire_id = _uuid(row.get("id"), f"grimoires[{index}].id")
        if grimoire_id in grimoire_ids:
            raise BackupError("Backup grimoires contain a duplicate id.")
        grimoire_ids.add(grimoire_id)
        slug = _slug(row.get("slug"), f"grimoires[{index}].slug", max_len=120)
        if slug in grimoire_slugs:
            raise BackupError("Backup grimoires contain a duplicate slug.")
        grimoire_slugs.add(slug)
        raw_category_id = row.get("category_id")
        parsed_category: uuid.UUID | None = None
        if raw_category_id is not None:
            parsed_category = _uuid(raw_category_id, f"grimoires[{index}].category_id")
            if parsed_category not in category_ids:
                raise BackupError("A grimoire references an unknown category.")
        source_format = _text(
            row.get("source_format"), f"grimoires[{index}].source_format"
        )
        if source_format not in ("rst", "myst"):
            raise BackupError("A grimoire has an invalid source format.")
        grimoires.append(
            {
                "id": grimoire_id,
                "category_id": parsed_category,
                "slug": slug,
                "title": _text(
                    row.get("title"), f"grimoires[{index}].title", max_len=200
                ),
                "source_format": source_format,
                "theme": _text(
                    row.get("theme"), f"grimoires[{index}].theme", max_len=80
                ),
                "created_at": _timestamp(
                    row.get("created_at"), f"grimoires[{index}].created_at"
                ),
            }
        )

    nodes: list[dict[str, Any]] = []
    node_ids: set[uuid.UUID] = set()
    sibling_slugs: set[tuple[uuid.UUID, uuid.UUID | None, str]] = set()
    for index, row in enumerate(_dict_list(data["nodes"], "nodes")):
        node_id = _uuid(row.get("id"), f"nodes[{index}].id")
        if node_id in node_ids:
            raise BackupError("Backup nodes contain a duplicate id.")
        node_ids.add(node_id)
        grimoire_id = _uuid(row.get("grimoire_id"), f"nodes[{index}].grimoire_id")
        if grimoire_id not in grimoire_ids:
            raise BackupError("A node references an unknown grimoire.")
        parent_value = row.get("parent_id")
        parent_id: uuid.UUID | None = None
        if parent_value is not None:
            parent_id = _uuid(parent_value, f"nodes[{index}].parent_id")
            if parent_id == node_id:
                raise BackupError("A node cannot be its own parent.")
        kind = _text(row.get("kind"), f"nodes[{index}].kind")
        if kind not in ("chapter", "folio"):
            raise BackupError("A node has an invalid kind.")
        slug = _slug(row.get("slug"), f"nodes[{index}].slug", max_len=160)
        sibling_key = (grimoire_id, parent_id, slug)
        if sibling_key in sibling_slugs:
            raise BackupError("Backup nodes contain duplicate sibling slugs.")
        sibling_slugs.add(sibling_key)
        nodes.append(
            {
                "id": node_id,
                "grimoire_id": grimoire_id,
                "parent_id": parent_id,
                "kind": kind,
                "title": _text(row.get("title"), f"nodes[{index}].title", max_len=200),
                "slug": slug,
                "position": _int(row.get("position"), f"nodes[{index}].position"),
            }
        )
    for row in nodes:
        if row["parent_id"] is not None:
            parent = next(
                (item for item in nodes if item["id"] == row["parent_id"]), None
            )
            if parent is None or parent["grimoire_id"] != row["grimoire_id"]:
                raise BackupError("A node references a parent in another tree.")
    _node_levels(nodes)

    documents: list[dict[str, Any]] = []
    document_ids: set[uuid.UUID] = set()
    documented_nodes: set[uuid.UUID] = set()
    for index, row in enumerate(_dict_list(data["documents"], "documents")):
        document_id = _uuid(row.get("id"), f"documents[{index}].id")
        if document_id in document_ids:
            raise BackupError("Backup documents contain a duplicate id.")
        document_ids.add(document_id)
        node_id = _uuid(row.get("node_id"), f"documents[{index}].node_id")
        if node_id not in node_ids:
            raise BackupError("A document references an unknown node.")
        if node_id in documented_nodes:
            raise BackupError("A node has more than one document.")
        documented_nodes.add(node_id)
        source_format = _text(
            row.get("source_format"), f"documents[{index}].source_format"
        )
        if source_format not in ("rst", "myst"):
            raise BackupError("A document has an invalid source format.")
        documents.append(
            {
                "id": document_id,
                "node_id": node_id,
                "tiptap_json": _as_dict(
                    row.get("tiptap_json"), f"documents[{index}].tiptap_json"
                ),
                "source_text": _text(
                    row.get("source_text"),
                    f"documents[{index}].source_text",
                    empty=True,
                ),
                "source_format": source_format,
                "version": _int(
                    row.get("version"), f"documents[{index}].version", minimum=1
                ),
                "updated_at": _timestamp(
                    row.get("updated_at"), f"documents[{index}].updated_at"
                ),
            }
        )

    history: list[dict[str, Any]] = []
    history_ids: set[uuid.UUID] = set()
    history_versions: set[tuple[uuid.UUID, int]] = set()
    for index, row in enumerate(
        _dict_list(data["document_history"], "document_history")
    ):
        history_id = _uuid(row.get("id"), f"document_history[{index}].id")
        if history_id in history_ids:
            raise BackupError("Backup history contains a duplicate id.")
        history_ids.add(history_id)
        document_id = _uuid(
            row.get("document_id"), f"document_history[{index}].document_id"
        )
        if document_id not in document_ids:
            raise BackupError("History references an unknown document.")
        version = _int(
            row.get("version"),
            f"document_history[{index}].version",
            minimum=1,
        )
        if (document_id, version) in history_versions:
            raise BackupError("Backup history contains a duplicate version.")
        history_versions.add((document_id, version))
        history.append(
            {
                "id": history_id,
                "document_id": document_id,
                "version": version,
                "tiptap_json": _as_dict(
                    row.get("tiptap_json"),
                    f"document_history[{index}].tiptap_json",
                ),
                "source_text": _text(
                    row.get("source_text"),
                    f"document_history[{index}].source_text",
                    empty=True,
                ),
                "at": _timestamp(row.get("at"), f"document_history[{index}].at"),
            }
        )

    media: list[dict[str, Any]] = []
    media_ids: set[uuid.UUID] = set()
    media_paths: set[str] = set()
    for index, row in enumerate(_dict_list(data["media"], "media")):
        media_id = _uuid(row.get("id"), f"media[{index}].id")
        if media_id in media_ids:
            raise BackupError("Backup media contains a duplicate id.")
        media_ids.add(media_id)
        grimoire_id = _uuid(row.get("grimoire_id"), f"media[{index}].grimoire_id")
        if grimoire_id not in grimoire_ids:
            raise BackupError("Media references an unknown grimoire.")
        content_type = _text(row.get("content_type"), f"media[{index}].content_type")
        if content_type not in MEDIA_TYPES:
            raise BackupError("Backup media has an unsupported content type.")
        extension = MEDIA_TYPES[content_type]
        storage_path = _text(
            row.get("storage_path"),
            f"media[{index}].storage_path",
            max_len=500,
        )
        expected_path = f"{media_id.hex[:2]}/{media_id}.{extension}"
        if storage_path != expected_path:
            raise BackupError("Backup media storage path is not canonical.")
        if storage_path in media_paths:
            raise BackupError("Backup media contains a duplicate storage path.")
        media_paths.add(storage_path)
        size_bytes = _int(
            row.get("size_bytes"),
            f"media[{index}].size_bytes",
            maximum=MAX_MEDIA_BYTES,
        )
        digest = _text(row.get("sha256"), f"media[{index}].sha256", max_len=64)
        if not _SHA256_RE.fullmatch(digest):
            raise BackupError("Backup media has an invalid SHA-256.")
        media.append(
            {
                "id": media_id,
                "grimoire_id": grimoire_id,
                "filename": _text(
                    row.get("filename"),
                    f"media[{index}].filename",
                    max_len=255,
                ),
                "content_type": content_type,
                "size_bytes": size_bytes,
                "sha256": digest,
                "storage_path": storage_path,
                "created_at": _timestamp(
                    row.get("created_at"), f"media[{index}].created_at"
                ),
            }
        )

    media_by_id = {row["id"]: row for row in media}
    for label, rows in (("document", documents), ("history", history)):
        for row in rows:
            for src in _image_srcs(row["tiptap_json"]):
                match = _MEDIA_URL_RE.fullmatch(src)
                if match is None:
                    raise BackupError(f"A {label} image is not a canonical media URL.")
                asset = media_by_id.get(uuid.UUID(match.group("id")))
                if asset is None:
                    raise BackupError(f"A {label} references missing media.")
                extension = match.group("ext").lower()
                if extension == "jpeg":
                    extension = "jpg"
                if extension != MEDIA_TYPES[asset["content_type"]]:
                    raise BackupError(
                        f"A {label} image extension does not match its asset."
                    )
            for match in _MEDIA_TEXT_RE.finditer(row["source_text"]):
                if uuid.UUID(match.group("id")) not in media_by_id:
                    raise BackupError(f"A {label} source references missing media.")

    builds: list[dict[str, Any]] = []
    build_ids: set[uuid.UUID] = set()
    build_numbers: set[int] = set()
    builds_by_number: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(_dict_list(data["builds"], "builds")):
        build_id = _uuid(row.get("id"), f"builds[{index}].id")
        if build_id in build_ids:
            raise BackupError("Backup builds contain a duplicate id.")
        build_ids.add(build_id)
        number = _int(
            row.get("build_number"),
            f"builds[{index}].build_number",
            minimum=1,
            maximum=2_000_000_000,
        )
        if number in build_numbers:
            raise BackupError("Backup builds contain a duplicate number.")
        build_numbers.add(number)
        status = _text(row.get("status"), f"builds[{index}].status")
        if status not in ("ok", "failed"):
            raise BackupError("Backup contains a non-terminal build.")
        artifact = _bool(row.get("artifact"), f"builds[{index}].artifact")
        log = _bool(row.get("log"), f"builds[{index}].log")
        published = _timestamp(
            row.get("published_at"),
            f"builds[{index}].published_at",
            required=False,
        )
        if status == "ok" and not artifact:
            raise BackupError("A successful build has no artifact.")
        if status == "failed" and (artifact or published is not None):
            raise BackupError("A failed build cannot have an artifact or publish.")
        if mode == "editorial":
            if status != "ok" or published is None:
                raise BackupError(
                    "Editorial backups may only contain published successful builds."
                )
            if log:
                raise BackupError("Editorial backups cannot contain build logs.")
        parsed = {
            "id": build_id,
            "build_number": number,
            "status": status,
            "started": _timestamp(
                row.get("started"), f"builds[{index}].started", required=False
            ),
            "finished": _timestamp(
                row.get("finished"), f"builds[{index}].finished", required=False
            ),
            "published_at": published,
            "artifact": artifact,
            "log": log,
        }
        builds.append(parsed)
        builds_by_number[number] = parsed

    raw_pointers = _as_dict(data["pointers"], "pointers")
    latest = _optional_build_number(
        raw_pointers.get("latest_build_number"), "pointers.latest_build_number"
    )
    stable = _optional_build_number(
        raw_pointers.get("stable_build_number"), "pointers.stable_build_number"
    )
    for pointer in (latest, stable):
        if pointer is None:
            continue
        target = builds_by_number.get(pointer)
        if target is None:
            raise BackupError("A publication pointer is not in the backup.")
        if target["status"] != "ok":
            raise BackupError("A publication pointer targets a failed build.")

    counts = {
        key: _int(manifest["counts"].get(key), f"counts.{key}") for key in _COUNT_KEYS
    }
    actual = {
        "categories": len(categories),
        "grimoires": len(grimoires),
        "nodes": len(nodes),
        "documents": len(documents),
        "document_history": len(history),
        "media": len(media),
        "builds": len(builds),
    }
    if counts != actual:
        raise BackupError("Backup counts do not match its rows.")

    source = _as_dict(manifest["source"], "source")
    plan = _Plan(
        mode=mode,
        source=source,
        athenaeum=athenaeum,
        public_names=public_names,
        categories=categories,
        grimoires=grimoires,
        nodes=nodes,
        documents=documents,
        history=history,
        media=media,
        builds=builds,
        latest=latest,
        stable=stable,
        counts=counts,
    )
    _validate_inventory(manifest, plan)
    return plan


def _optional_build_number(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return _int(value, label, minimum=1, maximum=2_000_000_000)


def _suffix(base: str, limit: int) -> str:
    suffix = f"-{uuid.uuid4().hex[:8]}"
    return f"{base[: limit - len(suffix)]}{suffix}"


async def _live_public_slug(session: AsyncSession, candidate: str) -> bool:
    taken = await session.scalar(
        select(Athenaeum.id).where(Athenaeum.public_slug == candidate)
    )
    return taken is not None


async def _claimable_name(
    session: AsyncSession, candidate: str, importer_id: uuid.UUID
) -> bool:
    if candidate in RESERVED_PUBLIC_SLUGS or not PUBLIC_NAME_RE.fullmatch(candidate):
        return False
    if await _live_public_slug(session, candidate):
        return False
    row = await session.get(PublicName, candidate)
    if row is None:
        return True
    return row.athenaeum_id is None and row.owner_id == importer_id


async def _allocate_public_name(
    session: AsyncSession,
    importer_id: uuid.UUID,
    desired: str,
    *,
    strict: bool = False,
) -> str:
    if strict:
        if await _claimable_name(session, desired, importer_id):
            return desired
        raise BackupError(
            f"Public name '{desired}' is not free for this restore "
            "(strict move mode; no automatic suffix)."
        )
    candidate = desired
    for _ in range(8):
        if await _claimable_name(session, candidate, importer_id):
            return candidate
        candidate = _suffix(desired, 160)
    raise BackupError("Could not allocate a free public name for the restore.")


async def _validate_strict_names(
    session: AsyncSession, importer_id: uuid.UUID, plan: _Plan
) -> None:
    """Fail before staging any file when a move would change a public URL."""
    desired = {plan.athenaeum["public_slug"]}
    desired.update(row["slug"] for row in plan.public_names)
    for name in sorted(desired):
        if not await _claimable_name(session, name, importer_id):
            raise BackupError(
                f"Public name '{name}' conflicts with existing data; "
                "strict move restore refuses to rename it."
            )


async def _write_public_name(
    session: AsyncSession,
    *,
    slug: str,
    athenaeum_id: uuid.UUID,
    importer_id: uuid.UUID,
    current: bool,
    created_at: datetime | None,
    retired_at: datetime | None,
) -> None:
    row = await session.get(PublicName, slug)
    if row is None:
        session.add(
            PublicName(
                slug=slug,
                athenaeum_id=athenaeum_id,
                owner_id=importer_id,
                is_current=current,
                created_at=created_at,
                retired_at=retired_at,
            )
        )
        return
    row.athenaeum_id = athenaeum_id
    row.owner_id = importer_id
    row.is_current = current
    row.retired_at = retired_at


async def _unique_editor_slug(
    session: AsyncSession, importer_id: uuid.UUID, base: str
) -> str:
    candidate = base
    for _ in range(8):
        taken = await session.scalar(
            select(Athenaeum.id).where(
                Athenaeum.owner_id == importer_id,
                Athenaeum.slug == candidate,
            )
        )
        if taken is None:
            return candidate
        candidate = _suffix(base, 120)
    raise BackupError("Could not allocate an editor slug for the restore.")


async def _unique_grimoire_slug(session: AsyncSession, base: str) -> str:
    candidate = base
    for _ in range(8):
        taken = await session.scalar(
            select(Grimoire.id).where(Grimoire.slug == candidate)
        )
        if taken is None:
            return candidate
        candidate = _suffix(base, 120)
    raise BackupError("Could not allocate a grimoire slug for the restore.")


def _stage_media(plan: _Plan, extracted: Path, staged: _Staged) -> dict[uuid.UUID, str]:
    root = get_media_root()
    url_by_id: dict[uuid.UUID, str] = {}
    for row in plan.media:
        old_id: uuid.UUID = row["id"]
        content_type: str = row["content_type"]
        extension = MEDIA_TYPES[content_type]
        new_id = uuid.uuid4()
        storage_path = storage_relpath(new_id, extension)
        source = extracted / "media" / row["storage_path"]
        if not source.is_file():
            raise BackupError("Backup media payload is missing.")
        target = root / storage_path
        target.parent.mkdir(parents=True, exist_ok=True)
        staged.media_paths.append(target)
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as src, target.open("wb") as out:
            while chunk := src.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                out.write(chunk)
        if size != row["size_bytes"] or digest.hexdigest() != row["sha256"]:
            raise BackupError("Backup media bytes do not match their row.")
        with target.open("rb") as head:
            sniffed = sniff_image(head.read(32))
        if sniffed is None or sniffed[0] != content_type:
            raise BackupError("Backup media bytes do not match their content type.")
        staged.media.append(
            _MediaStage(
                row=row,
                new_id=new_id,
                storage_path=storage_path,
                size_bytes=size,
                sha256=digest.hexdigest(),
            )
        )
        url_by_id[old_id] = media_url(new_id, extension)
    return url_by_id


def _stage_builds(
    plan: _Plan, extracted: Path, new_athenaeum_id: uuid.UUID, staged: _Staged
) -> None:
    cfg = build_config()
    for row in plan.builds:
        number: int = row["build_number"]
        new_id = uuid.uuid4()
        artifact_path: str | None = None
        log_path: str | None = None
        if row["artifact"]:
            source = extracted / "artifacts" / str(number)
            if not source.is_dir():
                raise BackupError(f"Build #{number} artifact payload is missing.")
            target = cfg.artifact_root / str(new_athenaeum_id) / str(number)
            target.parent.mkdir(parents=True, exist_ok=True)
            staged.artifact_dirs.append(target)
            shutil.copytree(source, target)
            artifact_manifest = read_artifact_manifest(target)
            if artifact_manifest is None:
                raise BackupError(f"Build #{number} artifact has no valid manifest.")
            if artifact_manifest.get("build_number") != number:
                raise BackupError(
                    f"Build #{number} artifact manifest has the wrong number."
                )
            artifact_manifest["athenaeum_id"] = str(new_athenaeum_id)
            (target / MANIFEST_NAME).write_text(
                json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            artifact_path = str(target)
        if row["log"]:
            source = extracted / "logs" / f"{number}.log"
            if not source.is_file():
                raise BackupError(f"Build #{number} log payload is missing.")
            target = cfg.build_root / str(new_id) / "build.log"
            target.parent.mkdir(parents=True, exist_ok=True)
            staged.log_paths.append(target)
            shutil.copyfile(source, target)
            log_path = str(target)
        staged.builds.append(
            _BuildStage(
                row=row,
                new_id=new_id,
                artifact_path=artifact_path,
                log_path=log_path,
            )
        )


def _cleanup_staged(staged: _Staged) -> None:
    for path in staged.media_paths:
        unlink_quiet(path)
    for path in staged.log_paths:
        unlink_quiet(path)
        try:
            path.parent.rmdir()
        except OSError:
            pass
    for path in staged.artifact_dirs:
        remove_tree(path)


async def _import_plan(
    session: AsyncSession,
    importer_id: uuid.UUID,
    plan: _Plan,
    new_athenaeum_id: uuid.UUID,
    staged: _Staged,
    url_by_id: dict[uuid.UUID, str],
    warnings: list[str],
    *,
    strict_names: bool = False,
) -> str:
    await session.execute(select(func.pg_advisory_xact_lock(PUBLIC_NAMES_LOCK)))

    editor_slug = await _unique_editor_slug(
        session, importer_id, plan.athenaeum["slug"]
    )
    public_slug = await _allocate_public_name(
        session,
        importer_id,
        plan.athenaeum["public_slug"],
        strict=strict_names,
    )
    athenaeum = Athenaeum(
        id=new_athenaeum_id,
        owner_id=importer_id,
        slug=editor_slug,
        public_slug=public_slug,
        title=plan.athenaeum["title"],
        is_public=plan.athenaeum["is_public"],
        custom_css=plan.athenaeum["custom_css"],
        created_at=plan.athenaeum["created_at"],
    )
    session.add(athenaeum)
    await session.flush()
    await _write_public_name(
        session,
        slug=public_slug,
        athenaeum_id=new_athenaeum_id,
        importer_id=importer_id,
        current=True,
        created_at=plan.athenaeum["created_at"],
        retired_at=None,
    )

    category_map: dict[uuid.UUID, uuid.UUID] = {}
    for row in plan.categories:
        new_id = uuid.uuid4()
        category_map[row["id"]] = new_id
        session.add(
            GrimoireCategory(
                id=new_id,
                athenaeum_id=new_athenaeum_id,
                name=row["name"],
                position=row["position"],
                created_at=row["created_at"],
            )
        )
    await session.flush()

    grimoire_map: dict[uuid.UUID, uuid.UUID] = {}
    for row in plan.grimoires:
        new_id = uuid.uuid4()
        grimoire_map[row["id"]] = new_id
        slug = await _unique_grimoire_slug(session, row["slug"])
        session.add(
            Grimoire(
                id=new_id,
                athenaeum_id=new_athenaeum_id,
                category_id=category_map.get(row["category_id"]),
                slug=slug,
                title=row["title"],
                source_format=row["source_format"],
                theme=row["theme"],
                created_by=None,
                created_at=row["created_at"],
            )
        )
        session.add(Membership(user_id=importer_id, grimoire_id=new_id, role="owner"))
    await session.flush()

    node_map: dict[uuid.UUID, uuid.UUID] = {
        row["id"]: uuid.uuid4() for row in plan.nodes
    }
    for level in _node_levels(plan.nodes):
        for row in level:
            parent = (
                node_map[row["parent_id"]] if row["parent_id"] is not None else None
            )
            session.add(
                Node(
                    id=node_map[row["id"]],
                    grimoire_id=grimoire_map[row["grimoire_id"]],
                    parent_id=parent,
                    kind=row["kind"],
                    title=row["title"],
                    slug=row["slug"],
                    position=row["position"],
                )
            )
        await session.flush()

    document_map: dict[uuid.UUID, uuid.UUID] = {}
    for row in plan.documents:
        new_id = uuid.uuid4()
        document_map[row["id"]] = new_id
        session.add(
            Document(
                id=new_id,
                node_id=node_map[row["node_id"]],
                tiptap_json=_rewrite_json(row["tiptap_json"], url_by_id),
                source_text=_rewrite_text(row["source_text"], url_by_id),
                source_format=row["source_format"],
                version=row["version"],
                updated_by=None,
                updated_at=row["updated_at"],
            )
        )
    await session.flush()

    for row in plan.history:
        session.add(
            DocumentHistory(
                id=uuid.uuid4(),
                document_id=document_map[row["document_id"]],
                version=row["version"],
                tiptap_json=_rewrite_json(row["tiptap_json"], url_by_id),
                source_text=_rewrite_text(row["source_text"], url_by_id),
                author=None,
                at=row["at"],
            )
        )
    await session.flush()

    for stage in staged.media:
        row = stage.row
        session.add(
            MediaAsset(
                id=stage.new_id,
                grimoire_id=grimoire_map[row["grimoire_id"]],
                filename=row["filename"],
                content_type=row["content_type"],
                size_bytes=stage.size_bytes,
                sha256=stage.sha256,
                storage_path=stage.storage_path,
                created_by=None,
                created_at=row["created_at"],
            )
        )
    await session.flush()

    build_map: dict[int, uuid.UUID] = {}
    for build_stage in staged.builds:
        row = build_stage.row
        build_map[row["build_number"]] = build_stage.new_id
        session.add(
            Build(
                id=build_stage.new_id,
                athenaeum_id=new_athenaeum_id,
                build_number=row["build_number"],
                status=row["status"],
                triggered_by=None,
                started=row["started"],
                finished=row["finished"],
                log_path=build_stage.log_path,
                artifact_path=build_stage.artifact_path,
                published_at=row["published_at"],
                published_by=None,
            )
        )
    await session.flush()
    athenaeum.latest_build_id = (
        build_map[plan.latest] if plan.latest is not None else None
    )
    athenaeum.stable_build_id = (
        build_map[plan.stable] if plan.stable is not None else None
    )
    await session.flush()

    for row in plan.public_names:
        if row["is_current"]:
            continue
        if row["slug"] == public_slug:
            continue
        if not await _claimable_name(session, row["slug"], importer_id):
            if strict_names:
                raise BackupError(
                    f"Public name alias '{row['slug']}' conflicts with existing "
                    "data; strict move restore refuses to drop it."
                )
            warnings.append(
                f"Public name alias '{row['slug']}' was skipped because "
                "it belongs to another site."
            )
            continue
        await _write_public_name(
            session,
            slug=row["slug"],
            athenaeum_id=new_athenaeum_id,
            importer_id=importer_id,
            current=False,
            created_at=row["created_at"],
            retired_at=row["retired_at"],
        )
    await session.flush()

    add_audit(
        session,
        actor=importer_id,
        action="backup_restored",
        meta={
            "athenaeum_id": str(new_athenaeum_id),
            "source_athenaeum_id": plan.source.get("athenaeum_id"),
            "mode": plan.mode,
            "counts": plan.counts,
            "warnings": warnings,
        },
    )
    return public_slug


async def restore_archive(
    session: AsyncSession,
    importer_id: uuid.UUID,
    archive_path: Path,
    workdir: Path,
    *,
    strict_names: bool = False,
) -> RestoreResult:
    extracted = workdir / "extracted"
    remove_tree(extracted)
    workdir.mkdir(parents=True, exist_ok=True)
    staged = _Staged()
    try:
        manifest = extract_archive(archive_path, extracted)
        data = load_data(extracted)
        plan = _parse_plan(manifest, data)
        if strict_names:
            await _validate_strict_names(session, importer_id, plan)
        new_athenaeum_id = uuid.uuid4()
        url_by_id = _stage_media(plan, extracted, staged)
        _stage_builds(plan, extracted, new_athenaeum_id, staged)
        warnings: list[str] = []
        try:
            public_slug = await _import_plan(
                session,
                importer_id,
                plan,
                new_athenaeum_id,
                staged,
                url_by_id,
                warnings,
                strict_names=strict_names,
            )
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise BackupError(
                "Restore conflicted with existing data; retry the import."
            ) from exc
        except Exception:
            await session.rollback()
            raise
        return RestoreResult(
            athenaeum_id=new_athenaeum_id,
            title=plan.athenaeum["title"],
            public_slug=public_slug,
            mode=plan.mode,
            warnings=warnings,
            counts=plan.counts,
        )
    except Exception:
        _cleanup_staged(staged)
        raise
    finally:
        remove_tree(extracted)


async def _restore(
    archive_path: Path,
    importer_id: uuid.UUID,
    workdir: Path,
    *,
    strict_names: bool = False,
) -> RestoreResult:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            return await restore_archive(
                session,
                importer_id,
                archive_path,
                workdir,
                strict_names=strict_names,
            )
    finally:
        await engine.dispose()


def restore_archive_sync(
    archive_path: str,
    importer_id: str,
    workdir: str,
    *,
    strict_names: bool = False,
) -> RestoreResult:
    return asyncio.run(
        _restore(
            Path(archive_path),
            uuid.UUID(importer_id),
            Path(workdir),
            strict_names=strict_names,
        )
    )
