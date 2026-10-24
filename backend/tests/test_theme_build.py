"""M4-C3.5 theme regression tests (decisions 0027/0028, amended 0029–0032).

The runner test executes the actual sandboxed build (subprocess, `-W`,
RLIMITs, whitelisted env) with the test interpreter as build python —
no DB, no network. It pins the artifact physiology:

- the own from-scratch theme (no parent-theme leakage in `_static`),
- vendored engine JS (byte-identical to the pinned engine, 0027),
- engine-generated `pygments.css` from the custom style module (0028 ②A),
- the first-party search page/dialog contract (0032), genindex, sidebar
  tree, and **every internal link resolves to a real file** (the 0032
  link-integrity crawl — the batch-#1 404/directory-listing class of bug
  can never ship silently again).
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest

import sphinx

from app.sphinx.runner import RunnerConfigError, _materialize, run_build
from app.sphinx.sourcegen import SitePlan, SnapshotNode, StagedBook, plan_site


class _LinkCollector(HTMLParser):
    """Collect every href/src in one artifact page (link-integrity crawl)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.targets.append(value)


class _PagerPlacement(HTMLParser):
    """0034: prove the pager is a child of the article column, not the page."""

    _VOID = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.main_depth: int | None = None
        self.pager_found = False
        self.pager_in_main = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        if "sd-reading-main" in classes:
            self.main_depth = len(self.stack)
        if "sd-pager" in classes:
            self.pager_found = True
            self.pager_in_main = self.main_depth is not None
        if tag not in self._VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if self.main_depth is not None and len(self.stack) == self.main_depth:
            self.main_depth = None


def _broken_internal_links(artifact: Path) -> list[str]:
    """Resolve every artifact-local href/src; return the dangling ones.

    0032 ⑤: the crawler is deliberately dumb and total — any internal
    link that does not land on a FILE fails the build test. That covers
    the old suffix-less grimoire href (404) and a chapter href that the
    dev server answered with a directory listing.
    """
    broken: list[str] = []
    for page in sorted(artifact.rglob("*.html")):
        collector = _LinkCollector()
        collector.feed(page.read_text())
        for raw in collector.targets:
            parts = urlsplit(raw)
            if parts.scheme or parts.netloc or not parts.path:
                continue  # external, mailto:, data:, fragment-only
            target = (page.parent / unquote(parts.path)).resolve()
            if (
                artifact.resolve() not in target.parents
                and target != artifact.resolve()
            ):
                broken.append(
                    f"{page.relative_to(artifact)} -> {raw} (escapes artifact)"
                )
            elif not target.is_file():
                kind = "directory" if target.is_dir() else "missing"
                broken.append(f"{page.relative_to(artifact)} -> {raw} ({kind})")
    return broken


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
    return plan_site("Athos", [letters, inquiry], site_credit="Alsechemist")


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
    fonts = static / "fonts"  # 0030: vendored Inter faces + their OFL text
    assert (fonts / "inter-latin.woff2").is_file()
    assert (fonts / "inter-latin-italic.woff2").is_file()
    assert (fonts / "OFL-Inter.txt").is_file()

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
        "fonts",  # 0030 — vendored Inter woff2 files live under this dir
        "doctools.js",
        "searchtools.js",
        "sphinx_highlight.js",
        "documentation_options.js",  # rendered from the vendored .jinja
        "language_data.js",  # rendered from the vendored .jinja
        "base-stemmer.js",  # emitted by the search module
        "english-stemmer.js",
        "pygments.css",
    }
    fonts = static / "fonts"
    assert {p.name for p in fonts.glob("*")} == {
        "inter-latin.woff2",
        "inter-latin-italic.woff2",
        "OFL-Inter.txt",  # full OFL text vendored beside the faces
    }
    theme_css = (static / "scriptorium.css").read_text()
    assert "@font-face" in theme_css
    assert "fonts/inter-latin.woff2" in theme_css
    assert '--sd-font-body: "Inter", system-ui' in theme_css  # 0030 override
    # 0031/0032 rulings, pinned at the stylesheet level:
    assert "--sd-col-wide" not in theme_css  # fluid width (no column cap)
    assert "font-weight: 800" in theme_css  # content headings (0032 ⑦)
    assert "--sd-code-inline-bg: #D8E7DD" in theme_css  # darker inline (0032 ⑥)
    assert "--sd-adm-rule: #6E2142" in theme_css  # wine/plum danger
    assert "a.reference.download" in theme_css  # the download chip
    assert "sd-dlg" in theme_css  # the search dialog surface
    assert ".sd-reading-main { min-width: 0; }" in theme_css  # 0034 pager column
    assert "html.sd-panel-pending-off .sd-shell" in theme_css  # pre-paint collapse
    assert "top: 50%;" in theme_css and "translate(-50%, -50%)" in theme_css
    assert "sd-res-book" in theme_css  # shared chip, dialog + page (0032 ②)
    theme_js = (static / "scriptorium.js").read_text()
    assert "sd-dlg" in theme_js  # the first-party search dialog (0031 ①)
    assert "sd-dlg-close" in theme_js  # Tabler x close (0032 ⑦)
    assert "sd-i-check" in theme_js  # copy → check success glyph (0031 ②)
    assert "sd-panel-open" in theme_js  # panel collapse persistence
    assert "sd-search-clear" in theme_js  # clear-only control (0032 ④)
    assert 'placeholder="Search the library"' in theme_js  # dialog unchanged (0034)
    assert "languageFromClass" in theme_js  # 0034 outer-wrapper label fix
    assert 'classList.remove("sd-panel-pending-off")' in theme_js  # 0034 follow-up
    assert "search.html?q=" in theme_js or '?q=" + encodeURIComponent' in theme_js
    assert "sd-res-mark" in theme_js  # all-word highlight in both surfaces
    assert 'article.querySelector("h1")' in theme_js  # scrollspy title (0032 ⑨)
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

    # 0029 shell rulings: footer bar gone, Index centered under the
    # search form, the decoration island, and the credit block
    assert "sd-foot" not in index
    assert 'class="sd-side-links"' in index
    assert "&copy; Copyright by Alsechemist." in index
    assert "Last updated on " in index  # html_last_updated_fmt (0029)
    assert ">Compiled by Scriptorium.</span>" in index
    assert 'id="sd-map"' in index
    # 0032 ①: the island is explicitly namespaced and parseable; the
    # pre-fix raw map made every grimoire chip icon-only
    island_match = re.search(
        r'<script type="application/json" id="sd-map">(.*?)</script>', index
    )
    assert island_match is not None
    island = json.loads(island_match.group(1))
    assert island["books"]["letters"] == {
        "label": "Correspondence",
        "title": "Letters",
    }

    # 0032 ④/⑧: own clear control in the panel field (type=text removes
    # the native glyph), the collapse control beside it, and the expand
    # control in the top bar
    assert 'class="sd-side-head"' in index
    assert 'class="sd-search-clear"' in index
    assert 'type="text" name="q"' in index
    assert 'placeholder="Search"' in index  # 0034: panel placeholder only
    assert 'placeholder="Search the library"' not in index
    # 0034 follow-up: the persisted collapse state is applied in <head>,
    # before the shell exists, so the first paint cannot flash expanded.
    assert "sd-panel-pending-off" in index
    assert index.find("sd-panel-pending-off") < index.find("</head>")
    assert index.find("sd-panel-pending-off") < index.find('class="sd-shell"')
    assert '<use href="#sd-i-x">' in index
    assert "sd-panel-collapse" in index
    assert "sd-panel-expand" in index

    # 0031 shell rulings: the reworked sidebar book row — the grimoire
    # row opens the beginning (its first content-bearing folio), never
    # the master; the master stays reachable only off the landing's
    # visible toctree and the pager chain (both engine-native, both
    # outside the panel)
    assert 'href="letters/one.html"' in index  # sidebar book row (first leaf)
    load_angle = index.find("sd-tree")
    assert 'href="letters/one.html"' in index[load_angle:]

    # hidden staged toctrees (0031 ⑦): the master page exists as the
    # hierarchy holder; the tree renders EMPTY in the article (the
    # engine emits an empty wrapper div for hidden toctrees, no links)
    assert (artifact / "letters" / "index.html").is_file()
    page_master = (artifact / "letters" / "index.html").read_text()
    assert "toctree-wrapper" in page_master  # engine keeps an empty holder
    assert "toctree-l1" not in page_master  # …but the list is gone
    assert (
        "<li"
        not in page_master[page_master.find("sd-article") : page_master.find("sd-toc")]
    )
    assert (artifact / "inquiry" / "index.html").is_file()

    # a content page: role="main" article, aligned trail, highlight spans
    page = (artifact / "letters" / "one.html").read_text()
    assert 'role="main"' in page
    assert 'class="sd-article"' in page
    assert "sd-trail-parent" in page  # breadcrumb chain carries the book
    assert 'href="index.html" class="sd-trail-parent"' in page  # 9.1 pathto
    assert 'class="k"' in page  # custom style spans (keyword role)
    assert 'class="nf"' in page  # function role
    assert "<details" in page  # collapsible sidebar tree

    # 0029 reading layout: wide left article + hierarchical On-This-Page
    # rail (engine local toc) + the ruled green Previous/Next pager
    assert 'class="sd-reading"' in page
    assert 'class="sd-reading-main"' in page  # 0034 article column wrapper
    assert 'class="sd-toc"' in page
    assert ">On This Page<" in page
    assert "sd-pager-prev" in page and "sd-pager-next" in page
    assert "<span>Previous</span>" in page  # pager labels are exact (0029)
    assert "<span>Next</span>" in page
    assert 'aria-label="Adjacent pages"' in page
    placement = _PagerPlacement()
    placement.feed(page)
    assert placement.pager_found
    assert placement.pager_in_main, "pager must live in the article column (0034)"

    # myst book coexists: md page served through myst_parser
    assert (artifact / "inquiry" / "hd.html").is_file()
    myst = (artifact / "inquiry" / "hd.html").read_text()
    assert 'role="main"' in myst
    assert "claims" in myst

    # search page: first-party takeover (0032 ②) — same core as the
    # dialog, `?q=` deep link, the engine's result renderer is GONE
    search = (artifact / "search.html").read_text()
    for marker in (
        'name="q"',
        'id="search-results"',
        "sd-searchpage-form",
        "sd-searchpage-lede",
        "_static/language_data.js",
        'id="sd-map"',
        "the whole sentence",
    ):
        assert marker in search
    assert "_static/searchtools.js" not in search
    assert 'id="search-progress"' not in search
    assert 'class="admonition warning"' in search  # no-JS notice survives
    assert 'searchindex.js" defer="defer"' in search  # root-relative, deferred
    assert (artifact / "searchindex.js").is_file()

    # generated index is plain HTML
    gen = (artifact / "genindex.html").read_text()
    assert "Index" in gen
    assert "sd-genindex" in gen

    # 0032 ⑤: every internal href/src in the whole artifact resolves to a
    # real FILE. This is the regression gate for the batch-#1 404/
    # directory-listing class (suffix-less grimoire/chapter hrefs).
    broken = _broken_internal_links(artifact)
    assert not broken, "\n".join(broken)

    # ok ⇒ workspace removed, log stored in the artifact
    builds_root = tmp_path / "builds"
    assert not any(builds_root.iterdir())
    assert (Path(str(outcome.artifact_path)) / "build.log").is_file()
