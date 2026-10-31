"""Artifact manifest + CSP hash discovery (decision 0035 E2).

Every successful build ships ``manifest.json`` beside ``html/``:

- format/version, Athenaeum/build identity, generation time;
- a sorted file inventory with SHA-256 hashes;
- the hashes of inline scripts in the generated HTML, so the serving host
  can use a strict ``script-src 'self' 'sha256-…'`` policy without
  weakening it to ``'unsafe-inline'``;
- the custom-CSS path/hash when present.

The manifest is portable: an exported artifact can carry it to nginx,
S3, or any static host as the authoritative header/hash inventory. The
serving router refuses to serve an artifact without a valid manifest.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"
MANIFEST_FORMAT = "scriptorium-artifact@1"

_INLINE_SCRIPT_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_SRC_ATTR_RE = re.compile(r"\bsrc\s*=", re.IGNORECASE)
_STYLE_ATTR_RE = re.compile(r"\sstyle\s*=", re.IGNORECASE)
_EVENT_ATTR_RE = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
_STYLE_TAG_RE = re.compile(r"<style\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_CSP_HASH_RE = re.compile(r"sha256-[A-Za-z0-9+/]{43}=")


class ManifestError(RuntimeError):
    """The artifact cannot be made safe/portable with a valid manifest."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _csp_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def _html_files(html_root: Path) -> list[Path]:
    return sorted(path for path in html_root.rglob("*.html") if path.is_file())


def _inline_script_hashes(html_root: Path) -> list[str]:
    hashes: set[str] = set()
    for page in _html_files(html_root):
        text = page.read_text(encoding="utf-8")
        if _STYLE_TAG_RE.search(text):
            raise ManifestError(
                f"{page.relative_to(html_root)} contains a <style> block; "
                "E2 requires style-src 'self' (external CSS only)."
            )
        for tag in _TAG_RE.finditer(text):
            tag_text = tag.group(0)
            if _STYLE_ATTR_RE.search(tag_text):
                raise ManifestError(
                    f"{page.relative_to(html_root)} contains an inline style "
                    "attribute; E2 requires style-src 'self' (external CSS only)."
                )
            if _EVENT_ATTR_RE.search(tag_text):
                raise ManifestError(
                    f"{page.relative_to(html_root)} contains an inline event "
                    "handler; E2 forbids inline script attributes."
                )
        for match in _INLINE_SCRIPT_RE.finditer(text):
            if _SRC_ATTR_RE.search(match.group("attrs")):
                continue
            body = match.group("body")
            if body.strip():
                hashes.add(_csp_hash(body))
    return sorted(hashes)


def _file_inventory(html_root: Path) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for path in sorted(html_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(html_root).as_posix()
        data = path.read_bytes()
        inventory[relative] = {
            "sha256": _sha256_bytes(data),
            "bytes": len(data),
        }
    return inventory


def write_artifact_manifest(
    artifact_dir: Path,
    *,
    athenaeum_id: uuid.UUID,
    build_number: int,
    site_id: str = "",
) -> dict[str, Any]:
    """Write the manifest for a completed artifact; fail loud on E2 violations."""
    html_root = artifact_dir / "html"
    if not (html_root / "index.html").is_file():
        raise ManifestError(f"{html_root} has no index.html.")

    inventory = _file_inventory(html_root)
    script_hashes = _inline_script_hashes(html_root)
    custom_css_path = html_root / "_static" / "custom.css"
    custom_css: dict[str, Any] | None = None
    if custom_css_path.is_file():
        data = custom_css_path.read_bytes()
        custom_css = {
            "path": "_static/custom.css",
            "sha256": _sha256_bytes(data),
            "bytes": len(data),
        }

    manifest: dict[str, Any] = {
        "format": MANIFEST_FORMAT,
        "generator": "Scriptorium",
        "site_id": site_id,
        "athenaeum_id": str(athenaeum_id),
        "build_number": build_number,
        "created_at": datetime.now(UTC).isoformat(),
        "entrypoint": "index.html",
        "files": inventory,
        "custom_css": custom_css,
        "csp": {"script_hashes": script_hashes},
    }
    target = artifact_dir / MANIFEST_NAME
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def read_artifact_manifest(artifact_dir: Path) -> dict[str, Any] | None:
    """Read/validate the manifest; None means the artifact is not servable."""
    target = artifact_dir / MANIFEST_NAME
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    if raw.get("format") != MANIFEST_FORMAT:
        return None
    if not isinstance(raw.get("files"), dict):
        return None
    csp = raw.get("csp")
    if not isinstance(csp, dict):
        return None
    hashes = csp.get("script_hashes")
    if (
        not isinstance(hashes, list)
        or not all(isinstance(value, str) for value in hashes)
        or not all(_CSP_HASH_RE.fullmatch(value) for value in hashes)
    ):
        return None
    return raw


def manifest_script_hashes(manifest: dict[str, Any]) -> list[str]:
    csp = manifest.get("csp")
    if not isinstance(csp, dict):
        return []
    hashes = csp.get("script_hashes")
    if not isinstance(hashes, list):
        return []
    return [str(value) for value in hashes]
