"""M4-C2 sourcegen tests (decision 0026) — pure, offline (no PG).

Pins the staging contract: per-Athenaeum site layout (book dirs + one
conf.py), deterministic output, E1/E2 edge rulings, fail-loud exports,
docname rules (`index` → `index-p` leaf mangle), unrestricted nesting
(0023) as parent pages, and MyST-conditional conf.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.sphinx.sourcegen import (
    EmptySiteError,
    SitePlan,
    SnapshotNode,
    StagedBook,
    StagingError,
    plan_site,
    snapshot_nodes,
)


def nov(node_id: str, slug: str, kind: str = "folio") -> dict[str, Any]:
    return {
        "id": node_id,
        "parent_id": None,
        "kind": kind,
        "slug": slug,
        "title": slug,
        "tiptap": None,
    }


def body_doc(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(blocks)}


def para_doc(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def folio(slug: str, body: dict[str, Any] | None = None) -> SnapshotNode:
    return SnapshotNode(
        id=slug, kind="folio", slug=slug, title=slug.title(), tiptap=body
    )


def chapter(
    slug: str,
    children: tuple[SnapshotNode, ...] = (),
    body: dict[str, Any] | None = None,
    title: str | None = None,
) -> SnapshotNode:
    return SnapshotNode(
        id=slug,
        kind="chapter",
        slug=slug,
        title=title if title is not None else slug.title(),
        tiptap=body,
        children=children,
    )


def book(slug: str, nodes: tuple[SnapshotNode, ...], fmt: str = "rst") -> StagedBook:
    return StagedBook(slug=slug, title=slug.title(), source_format=fmt, nodes=nodes)


def test_empty_books_refused() -> None:
    with pytest.raises(EmptySiteError, match="no grimoires to build"):
        plan_site("Empty", [])


def test_simple_site_layout_and_index() -> None:
    site = plan_site("Athanor", [book("letters", (folio("one", para_doc("hello")),))])
    files = site.files
    assert set(files) == {
        "conf.py",
        "index.rst",
        "letters/index.rst",
        "letters/one.rst",
    }
    assert "project = 'Athanor'" in files["conf.py"]
    assert "   Letters <letters/index>" in files["index.rst"]
    # the folio page carries its exported body
    assert "hello" in files["letters/one.rst"]
    assert "   One <letters/one>" in files["letters/index.rst"]


def test_empty_book_skipped_with_note() -> None:
    site = plan_site(
        "Mixed",
        [
            book("void", (chapter("shell", ()),)),
            book("live", (folio("doc", para_doc("kept")),)),
        ],
    )
    assert site.notes == (
        "skipped empty grimoire 'void' ('Void') — no folio documents",
    )
    assert not any(name.startswith("void/") for name in site.files)
    assert "<void/index>" not in site.files["index.rst"]
    assert "Live <live/index>" in site.files["index.rst"]
    assert "kept" in site.files["live/doc.rst"]


def test_all_empty_books_refused() -> None:
    with pytest.raises(EmptySiteError, match="no publishable grimoires"):
        plan_site("Hollow", [book("a", (chapter("c", ()),))])


def test_myst_conf_and_md_pages() -> None:
    site = plan_site(
        "Mystic", [book("grimoire", (folio("p1", para_doc("myst body")),), fmt="myst")]
    )
    assert 'extensions = ["myst_parser"]' in site.files["conf.py"]
    assert '".md": "myst"' in site.files["conf.py"]
    assert (
        'source_suffix = {".rst": "restructuredtext", ".md": "myst"}'
        in site.files["conf.py"]
    )
    assert "grimoire/p1.md" in site.files
    # master documents are always RST toctree containers
    assert "grimoire/index.rst" in site.files
    assert "index.rst" in site.files


def test_rst_only_conf_has_no_myst() -> None:
    site = plan_site("Classic", [book("b", (folio("f", para_doc("x")),))])
    conf = site.files["conf.py"]
    assert "myst_parser" not in conf
    assert '".md"' not in conf
    assert "html_theme = " in conf  # interim placeholder present (C3 swaps curated)
    assert "html_theme = 'alabaster'" in conf


def test_unrestricted_nesting_parent_pages() -> None:
    # chapters contain folios; a folio may itself parent (0023 nesting)
    branch = SnapshotNode(
        id="branch",
        kind="folio",
        slug="branch",
        title="Branch",
        tiptap=para_doc("branch body"),
        children=(folio("inner", para_doc("inner body")),),
    )
    deep = chapter(
        "ambient",
        (
            folio("leaf", para_doc("leaf body")),
            branch,
        ),
    )
    site = plan_site(
        "Nest",
        [book("tree", (chapter("spells", (deep,)),))],
    )
    files = site.files
    # container chapter page = toctree only (no body) with path quals
    assert "tree/spells/ambient.rst" in files
    assert "   Leaf <tree/spells/ambient/leaf>" in files["tree/spells/ambient.rst"]
    # folio-with-children page: body + child toctree in ONE file
    branch_page = files["tree/spells/ambient/branch.rst"]
    assert "branch body" in branch_page
    assert "   Inner <tree/spells/ambient/branch/inner>" in branch_page
    assert "inner body" in files["tree/spells/ambient/branch/inner.rst"]
    # nothing published for contentless shells
    assert "tree/index.rst" in files


def test_leaf_index_slug_mangles() -> None:
    site = plan_site("Mangle", [book("b", (folio("index", para_doc("hit")),))])
    assert "b/index-p.rst" in site.files
    assert "b/index.rst" in site.files  # master doc untouched by the mangle
    assert "hit" in site.files["b/index-p.rst"]


def test_contentless_shell_not_published() -> None:
    site = plan_site(
        "Shell",
        [
            book(
                "s",
                (
                    chapter("empty-shelf", ()),
                    folio("kept", para_doc("kept")),
                ),
            )
        ],
    )
    assert "s/empty-shelf.rst" not in site.files
    assert "s/kept.rst" in site.files


def test_deterministic_output() -> None:
    books = [
        book("zeta", (folio("f", para_doc("z")),)),
        book("alpha", (chapter("c", (folio("g", para_doc("a")),)),)),
    ]
    first = plan_site("Same", books)
    second = plan_site("Same", books)
    assert first == second


def test_title_sanitized_in_toctree() -> None:
    poison = SnapshotNode(
        id="p", kind="folio", slug="p", title="A<B>C", tiptap=para_doc("x")
    )
    site = plan_site("T", [book("t", (poison,))])
    assert "   A«B»C <t/p>" in site.files["t/index.rst"]
    assert "<A<B>C" not in site.files["t/index.rst"]


def test_staging_error_fail_loud() -> None:
    # heading level skip is fail-loud on export (0017 matrix) — the build
    # must record failed, not guess (stored JSON is canonical but not
    # pre-validated for export shape).
    bad = body_doc(
        {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "H1"}],
        },
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "H3"}],
        },
    )
    with pytest.raises(StagingError, match="folio 'flip': Heading level skip"):
        plan_site("Broken", [book("b", (folio("flip", bad),))])


def test_snapshot_nodes_folds_rows_and_order() -> None:
    rows = [
        {**nov("r1", "root-one"), "parent_id": None},
        {**nov("c2", "child-two"), "parent_id": "r2", "kind": "chapter"},
        {**nov("r2", "root-two"), "parent_id": None, "kind": "chapter"},
        {**nov("c1", "child-one"), "parent_id": "r2"},
    ]
    tree = snapshot_nodes(rows)
    assert [n.slug for n in tree] == ["root-one", "root-two"]
    two = tree[1]
    assert two.kind == "chapter"
    assert [c.slug for c in two.children] == ["child-two", "child-one"]
    assert two.children[1].tiptap is None
    assert two.children[1].kind == "folio"


def test_plan_returns_siteplan_dataclass() -> None:
    site = plan_site("Type", [book("b", (folio("f", para_doc("x")),))])
    assert isinstance(site, SitePlan)
    assert isinstance(site.notes, tuple)
    assert site.notes == ()
