"""Artifact path resolution for serving (decision 0035 C1).

Only files under the configured artifact root are servable. The manifest
is the gate: a build without a valid manifest cannot be published or
served (it would lack the CSP hash inventory).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.models import Build
from app.serving.manifest import read_artifact_manifest
from app.sphinx.runner import build_config


def artifact_root() -> Path:
    return build_config().artifact_root.resolve()


def artifact_dir(build: Build) -> Path | None:
    """Return the build's artifact directory if it is inside the root."""
    if not build.artifact_path:
        return None
    root = artifact_root()
    try:
        path = Path(build.artifact_path).resolve()
        html = (path / "html").resolve()
    except (OSError, RuntimeError):
        return None
    if not path.is_relative_to(root):
        return None
    # A symlinked html/ could otherwise point outside the artifact jail.
    if not html.is_dir() or not html.is_relative_to(root):
        return None
    return path


def servable_artifact(build: Build) -> tuple[Path, dict[str, Any]] | None:
    """Return (html_root, manifest) for a safe, manifest-backed artifact."""
    path = artifact_dir(build)
    if path is None:
        return None
    manifest = read_artifact_manifest(path)
    if manifest is None:
        return None
    return path / "html", manifest


def safe_file(html_root: Path, url_path: str) -> Path | None:
    """Resolve a URL path inside html_root; reject traversal/symlink escapes."""
    relative = url_path.lstrip("/")
    if not relative:
        relative = "index.html"
    if "\x00" in relative:
        return None
    try:
        root = html_root.resolve()
        candidate = (html_root / relative).resolve()
        if not candidate.is_relative_to(root):
            return None
        if candidate.is_dir():
            candidate = (candidate / "index.html").resolve()
            if not candidate.is_relative_to(root):
                return None
    except (OSError, RuntimeError):
        return None
    if not candidate.is_file():
        return None
    return candidate
