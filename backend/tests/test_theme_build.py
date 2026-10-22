"""M4-C3.5 theme regression tests (decisions 0027/0028) — offline but real.

The runner test executes the actual sandboxed build (subprocess, `-W`,
RLIMITs, whitelisted env) with the test interpreter as build python —
no DB, no network. It pins the artifact physiology:

- the own from-scratch theme (no parent-theme leakage in `_static`),
- vendored engine JS (byte-identical to the pinned engine, 0027),
- engine-generated `pygments.css` from the custom style module (0028 ②A),
- the pinned search DOM contract (0028), genindex, sidebar tree.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

import sphinx

from app.sphinx.runner import RunnerConfigError, _materialize, run_build
from app.sphinx.sourcegen import SitePlan, SnapshotNode, StagedBook, plan_site


def para(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def code_doc() -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [
                    {"type": "text", "text": "def flame(x):\n    return x + 1\n"}
                ],
            }
        ],
    }


def _plan() -> SitePlan:
    letters = StagedBook(
        slug="letters",
        title="Letters",
        source_format="rst",
        nodes=(
            SnapshotNode(
                id="one", kind="folio", slug="one", title="One", tiptap=code_doc()
            ),
        ),
        category_label="Correspondence",
    )
    inquiry = StagedBook(
        slug="inquiry",
        title="Inquiry",
        source_format="myst",
        nodes=(
            SnapshotNode(
                id="hd",
                kind="folio",
                slug="hd",
                title="Hypothesis",
                tiptap=para("claims"),
            ),
        ),
        category_label=None,
    )
    return plan_site("Athos", [letters, inquiry])


def test_materialize_stages_theme_style_and_engine_js(tmp_path: Path) -> None:
    """The staged workspace carries the theme, the style module, vendored JS."""
    ws = tmp_path / "ws"
    _materialize(ws, _plan(), Path(sys.executable))

    theme = ws / "theme" / "scriptorium"
    for name in (
        "theme.conf",
        "layout.html",
        "page.html",
        "search.html",
        "genindex.html",
    ):
        assert (theme / name).is_file()
    static = theme / "static"
    assert (static / "scriptorium.css").is_file()
    assert (static / "scriptorium.js").is_file()

    # Pygments style module beside conf.py (`scriptorium_style.ScriptoriumStyle`)
    style = ws / "scriptorium_style.py"
    assert style.is_file()
    assert "class ScriptoriumStyle" in style.read_text()

    # vendored engine assets: byte-identical to the build interpreter's engine
    engine_static = (
        Path(sphinx.__file__).resolve().parent / "themes" / "basic" / "static"
    )
    for name in (
        "doctools.js",
        "searchtools.js",
        "sphinx_highlight.js",
        "documentation_options.js.jinja",
        "language_data.js.jinja",
    ):
        assert (static / name).read_bytes() == (engine_static / name).read_bytes()


def test_materialize_engine_missing_fail_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrong/absent engine location fails loud (contracts bump together)."""
    plan = _plan()

    fake = tmp_path / "fakepy"
    fake.write_text("#!/bin/sh\necho /tmp/opencode/theme-test/nowhere\n")
    fake.chmod(0o755)
    with pytest.raises(RunnerConfigError, match="is missing"):
        _materialize(tmp_path / "ws", plan, fake)

    broken = tmp_path / "brokenpy"
    broken.write_text("#!/bin/sh\necho cannot import >&2\nexit 3\n")
    broken.chmod(0o755)
    with pytest.raises(RunnerConfigError, match="cannot import Sphinx"):
        _materialize(tmp_path / "ws2", plan, broken)


def test_run_build_theme_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline-but-real: one sandboxed build; the artifact physiology."""
    monkeypatch.setenv("SC_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SC_BUILD_ROOT", str(tmp_path / "builds"))

    outcome = run_build(_plan(), uuid.uuid4(), uuid.uuid4(), 1)
    assert outcome.ok, (
        Path(outcome.log_path).read_text() if outcome.log_path else outcome
    )

    artifact = Path(str(outcome.artifact_path)) / "html"
    static = artifact / "_static"

    # own theme + engine-emitted assets; no parent CSS sneaks in
    assert {p.name for p in static.glob("*")} == {
        "scriptorium.css",
        "scriptorium.js",
        "doctools.js",
        "searchtools.js",
        "sphinx_highlight.js",
        "documentation_options.js",  # rendered from the vendored .jinja
        "language_data.js",  # rendered from the vendored .jinja
        "base-stemmer.js",  # emitted by the search module
        "english-stemmer.js",
        "pygments.css",
    }
    options_js = (static / "documentation_options.js").read_text()
    assert "DOCUMENTATION_OPTIONS" in options_js
    assert "NAVIGATION_WITH_KEYS: false" in options_js
    pygments_css = (static / "pygments.css").read_text()
    assert "var(--sd-syn-kw,#4FB39A)" in pygments_css
    assert "var(--sd-syn-com,#7E9486)" in pygments_css
    assert "italic" in pygments_css

    # index renders the shell: topbar, tree, sprite markers, our assets
    index = (artifact / "index.html").read_text()
    assert 'data-content_root="' in index
    assert 'class="sd-sidebar"' in index
    assert 'class="sd-cat-label">Correspondence<' in index  # ruled exception B
    assert 'href="#sd-i-book"' in index
    assert '<use href="#sd-i-file-text"' in index
    assert "_static/scriptorium.css" in index
    assert "_static/scriptorium.js" in index
    assert "genindex.html" in index

    # engine auto-scripts reach every page through the asset list
    assert "_static/doctools.js" in index
    assert "_static/documentation_options.js" in index
    assert "_static/sphinx_highlight.js" in index

    # a content page: role="main" article, aligned trail, highlight spans
    page = (artifact / "letters" / "one.html").read_text()
    assert 'role="main"' in page
    assert 'class="sd-article"' in page
    assert "sd-trail-parent" in page  # breadcrumb chain carries the book
    assert 'class="k"' in page  # custom style spans (keyword role)
    assert 'class="nf"' in page  # function role
    assert "<details" in page  # collapsible sidebar tree

    # myst book coexists: md page served through myst_parser
    assert (artifact / "inquiry" / "hd.html").is_file()
    myst = (artifact / "inquiry" / "hd.html").read_text()
    assert 'role="main"' in myst
    assert "claims" in myst

    # search page: pinned DOM contract (0028) + script wiring
    search = (artifact / "search.html").read_text()
    for marker in (
        'name="q"',
        'id="search-results"',
        'id="search-progress"',
        "_static/searchtools.js",
        "_static/language_data.js",
    ):
        assert marker in search
    assert 'searchindex.js" defer="defer"' in search  # root-relative, deferred
    assert (artifact / "searchindex.js").is_file()

    # generated index is plain HTML
    gen = (artifact / "genindex.html").read_text()
    assert "Index" in gen
    assert "sd-genindex" in gen

    # ok ⇒ workspace removed, log stored in the artifact
    builds_root = tmp_path / "builds"
    assert not any(builds_root.iterdir())
    assert (Path(str(outcome.artifact_path)) / "build.log").is_file()
