"""Serving-phase pure units (decision 0035 E2/C1).

These tests need no database and no Sphinx build: they pin the custom-CSS
sandbox, the artifact manifest/CSP hash inventory, path safety, and the
header/cache contract.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from pathlib import Path

import pytest

from app.models import Build
from app.serving.artifacts import artifact_dir, safe_file
from app.serving.css import (
    MAX_CUSTOM_CSS_BYTES,
    CustomCssError,
    sanitize_custom_css,
)
from app.serving.manifest import (
    MANIFEST_FORMAT,
    ManifestError,
    read_artifact_manifest,
    write_artifact_manifest,
)
from app.serving.security import artifact_headers, content_security_policy


def test_custom_css_is_namespaced_and_normalized() -> None:
    raw = """
    :root { --sd-accent: #123456; }
    body, .sd-sidebar { color: #111; }
    html body { background: var(--sd-paper); }
    .sd-reading-main > p { margin: 1rem; }
    """
    out = sanitize_custom_css(raw)
    assert "html[data-sd-athenaeum] {--sd-accent: #123456;}" in out
    assert (
        "html[data-sd-athenaeum] body, "
        "html[data-sd-athenaeum] .sd-sidebar {color: #111;}"
    ) in out
    assert "html[data-sd-athenaeum] body {background: var(--sd-paper);}" in out
    assert "html[data-sd-athenaeum] .sd-reading-main > p" in out
    assert "@" not in out.split("*/", 1)[1]  # only the explanatory header comment


@pytest.mark.parametrize(
    "raw",
    [
        "@import url('https://evil.example/x.css');",
        ".x { background: url(https://evil.example/pixel); }",
        '.x { background: image("https://evil.example/pixel"); }',
        ".x { background: u\\72l(https://evil.example/pixel); }",
        ".x { width: expression(alert(1)); }",
        ".x { behavior: url(x.htc); }",
        ".x { -moz-binding: url(x.xml#x); }",
        ".x { position: fixed; inset: 0; }",
        ".x { color: red; } </style><script>alert(1)</script>",
        ".x { color: red;",
        ".x { color: red; } .y {",
        ".x { color: red; } trailing",
        ".x { }",
        ".x { color: red; } .y { color: blue; } /* unterminated",
        "body}.sd-shell { color: red; }",
    ],
)
def test_custom_css_rejects_sandbox_escapes(raw: str) -> None:
    with pytest.raises(CustomCssError):
        sanitize_custom_css(raw)


def test_custom_css_size_cap_and_empty_clear() -> None:
    assert sanitize_custom_css("   ") == ""
    with pytest.raises(CustomCssError, match="too large"):
        sanitize_custom_css("a" * (MAX_CUSTOM_CSS_BYTES + 1))
    # Prefixing every selector can grow a near-cap input past the cap; the
    # normalized artifact file is bounded too.
    with pytest.raises(CustomCssError, match="Normalized"):
        sanitize_custom_css("a{color:red}\n" * 3000)


def _manifest_artifact(tmp_path: Path, *, inline_style: bool = False) -> Path:
    artifact = tmp_path / "artifact"
    html = artifact / "html"
    (html / "_static").mkdir(parents=True)
    style = ' style="color:red"' if inline_style else ""
    (html / "index.html").write_text(
        "<!doctype html><html><head>"
        "<script>const a = 1;</script>"
        '<script src="_static/x.js"></script>'
        f"</head><body><p{style}>hi</p></body></html>",
        encoding="utf-8",
    )
    (html / "_static" / "x.js").write_text("console.log(1);\n", encoding="utf-8")
    (html / "_static" / "custom.css").write_text(
        "html[data-sd-athenaeum] {color:red;}\n", encoding="utf-8"
    )
    return artifact


def test_manifest_inventory_and_script_hashes(tmp_path: Path) -> None:
    artifact = _manifest_artifact(tmp_path)
    manifest = write_artifact_manifest(
        artifact,
        athenaeum_id=uuid.uuid4(),
        build_number=7,
        site_id="demo",
    )
    assert manifest["format"] == MANIFEST_FORMAT
    assert manifest["entrypoint"] == "index.html"
    assert "index.html" in manifest["files"]
    assert "_static/x.js" in manifest["files"]
    assert manifest["custom_css"]["path"] == "_static/custom.css"
    expected = "sha256-" + base64.b64encode(
        hashlib.sha256(b"const a = 1;").digest()
    ).decode("ascii")
    assert manifest["csp"]["script_hashes"] == [expected]

    loaded = read_artifact_manifest(artifact)
    assert loaded is not None
    assert loaded["build_number"] == 7
    policy = content_security_policy(loaded)
    assert f"'{expected}'" in policy
    assert "unsafe-inline" not in policy
    assert "style-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy


def test_manifest_refuses_inline_style_and_invalid_manifest(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="inline style"):
        write_artifact_manifest(
            _manifest_artifact(tmp_path, inline_style=True),
            athenaeum_id=uuid.uuid4(),
            build_number=1,
        )

    artifact = _manifest_artifact(tmp_path / "second")
    (artifact / "manifest.json").write_text(
        json.dumps({"format": "wrong"}), encoding="utf-8"
    )
    assert read_artifact_manifest(artifact) is None

    artifact = _manifest_artifact(tmp_path / "third")
    (artifact / "html" / "index.html").write_text(
        "<html><head><style>p{color:red}</style></head></html>",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="<style>"):
        write_artifact_manifest(
            artifact,
            athenaeum_id=uuid.uuid4(),
            build_number=1,
        )

    artifact = _manifest_artifact(tmp_path / "fourth")
    (artifact / "manifest.json").write_text(
        json.dumps(
            {
                "format": MANIFEST_FORMAT,
                "files": {},
                "csp": {"script_hashes": ["not-a-real-hash"]},
            }
        ),
        encoding="utf-8",
    )
    assert read_artifact_manifest(artifact) is None


def test_header_contract_cache_modes() -> None:
    manifest = {"csp": {"script_hashes": ["sha256-abc"]}}
    public = artifact_headers(manifest, immutable=True, private=False)
    assert public["Cache-Control"] == "public, max-age=31536000, immutable"
    assert "script-src 'self' 'sha256-abc'" in public["Content-Security-Policy"]
    assert public["X-Content-Type-Options"] == "nosniff"

    alias = artifact_headers(manifest, immutable=False, private=False)
    assert alias["Cache-Control"] == "no-cache"

    private = artifact_headers(manifest, immutable=True, private=True)
    assert private["Cache-Control"] == "private, no-store"
    assert private["Vary"] == "Cookie"
    assert private["X-Robots-Tag"] == "noindex, nofollow"


def test_safe_file_rejects_traversal_and_serves_index(tmp_path: Path) -> None:
    html = tmp_path / "html"
    (html / "sub").mkdir(parents=True)
    (html / "index.html").write_text("root", encoding="utf-8")
    (html / "sub" / "index.html").write_text("sub", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("no", encoding="utf-8")

    assert safe_file(html, "") == html / "index.html"
    assert safe_file(html, "sub/") == html / "sub" / "index.html"
    assert safe_file(html, "sub") == html / "sub" / "index.html"
    assert safe_file(html, "../secret.txt") is None
    assert safe_file(html, "missing.html") is None


def test_artifact_dir_jails_path_and_symlinked_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "artifacts"
    good = root / "good"
    (good / "html").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "bad").mkdir()
    (root / "bad" / "html").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("SC_ARTIFACT_ROOT", str(root))

    assert artifact_dir(Build(artifact_path=str(good))) == good
    assert artifact_dir(Build(artifact_path=str(outside))) is None
    assert artifact_dir(Build(artifact_path=str(root / "bad"))) is None

    # A directory's index.html is resolved too; a symlinked index cannot
    # escape the html root.
    (good / "html" / "safe").mkdir()
    (good / "html" / "safe" / "index.html").write_text("ok")
    (good / "html" / "escape").mkdir()
    (good / "html" / "escape" / "index.html").symlink_to(outside / "index.html")
    (outside / "index.html").write_text("outside")
    assert safe_file(good / "html", "safe/") == (good / "html" / "safe" / "index.html")
    assert safe_file(good / "html", "escape/") is None
