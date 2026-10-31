"""M4-C2 sourcegen tests (decision 0026) — pure, offline (no PG).

Pins the staging contract: per-Athenaeum site layout (book dirs + one
conf.py), deterministic output, E1/E2 edge rulings, fail-loud exports,
docname rules (`index` → `index-p` leaf mangle), unrestricted nesting
(0023) as parent pages, and MyST-conditional conf.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from typing import Any, cast

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
    assert "   Letters </letters/index>" in files["index.rst"]
    # the folio page carries its exported body
    assert "hello" in files["letters/one.rst"]
    assert "   One </letters/one>" in files["letters/index.rst"]


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
    assert "Live </live/index>" in site.files["index.rst"]
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
    site = plan_site(
        "Classic",
        [book("b", (folio("f", para_doc("x")),))],
        site_credit="Alsechemist",
    )
    conf = site.files["conf.py"]
    assert "myst_parser" not in conf
    assert '".md"' not in conf
    assert "html_theme = 'scriptorium'" in conf  # own theme, no parent (0027)
    assert 'html_theme_path = ["theme"]' in conf
    assert "pygments_style = 'scriptorium_style.ScriptoriumStyle'" in conf
    # 0029: "Last updated on …" is conf-driven (build-date semantics)
    assert 'html_last_updated_fmt = "%B %d, %Y"' in conf
    assert 'html_static_path = ["_static"]' in conf
    # the sidebar tree is always materialized once pages exist
    assert "html_context = {'sidebar_categories': [{" in conf
    # 0029 context: decoration island + the credit holder
    assert "'book_categories': {'b': {'label': '', 'title': 'B'}}" in conf
    assert "'site_credit': 'Alsechemist'" in conf


def test_book_categories_map_labels() -> None:
    """The 0029 island maps each published book to its label/title."""
    site = plan_site(
        "Map",
        [replace(book("a", (folio("f", para_doc("x")),)), category_label="Herbs")],
    )
    conf = site.files["conf.py"]
    assert "'book_categories': {'a': {'label': 'Herbs', 'title': 'A'}}" in conf


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
    assert "   Leaf </tree/spells/ambient/leaf>" in files["tree/spells/ambient.rst"]
    # folio-with-children page: body + child toctree in ONE file
    branch_page = files["tree/spells/ambient/branch.rst"]
    assert "branch body" in branch_page
    assert "   Inner </tree/spells/ambient/branch/inner>" in branch_page
    assert "inner body" in files["tree/spells/ambient/branch/inner.rst"]
    # nothing published for contentless shells
    assert "tree/index.rst" in files


def test_leaf_index_slug_mangles() -> None:
    site = plan_site("Mangle", [book("b", (folio("index", para_doc("hit")),))])
    assert "b/index-p.rst" in site.files
    assert "b/index.rst" in site.files  # master doc untouched by the mangle
    assert "hit" in site.files["b/index-p.rst"]


def _sidebar_context(conf: str) -> list[dict[str, Any]]:
    """Parse the materialized html_context literal (deterministic repr)."""
    line = next(ln for ln in conf.splitlines() if ln.startswith("html_context = "))
    context = ast.literal_eval(line.removeprefix("html_context = "))
    assert isinstance(context, dict)
    return cast("list[dict[str, Any]]", context["sidebar_categories"])


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


def test_sidebar_tree_in_conf_context() -> None:
    """0028: html_context carries the publishable-only sidebar tree."""
    site = plan_site(
        "Nest",
        [
            book(
                "tree",
                (
                    chapter("spells", (folio("leaf", para_doc("leaf")),)),
                    folio("solo", para_doc("solo")),
                ),
            )
        ],
    )
    sidebar = _sidebar_context(site.files["conf.py"])
    assert sidebar == [
        {
            "label": None,  # unlabeled bucket exists but stays unlabeled
            "books": [
                {
                    "title": "Tree",
                    # 0031: clicking the grimoire opens the beginning —
                    # the first published folio with its own body
                    "docname": "tree/spells/leaf",
                    "branch": "tree/",
                    "icon": "book",
                    "container": True,  # never marked current in the panel
                    "children": [
                        {
                            "title": "Spells",  # container page exists (toctree)
                            "docname": "tree/spells",
                            "branch": "tree/spells/",
                            "icon": "file-text",
                            "children": [
                                {
                                    "title": "Leaf",
                                    "docname": "tree/spells/leaf",
                                    "branch": "tree/spells/leaf/",
                                    "icon": "file-text",
                                    "children": [],
                                }
                            ],
                        },
                        {
                            "title": "Solo",
                            "docname": "tree/solo",
                            "branch": "tree/solo/",
                            "icon": "file-text",
                            "children": [],
                        },
                    ],
                }
            ],
        }
    ]


def test_sidebar_grouping_categories_and_unlabeled_last() -> None:
    """First-seen label order; the unlabeled bucket always comes last."""
    a = book("a", (folio("f", para_doc("1")),))
    b = book("b", (folio("f", para_doc("2")),))
    c = book("c", (folio("f", para_doc("3")),))
    site = plan_site(
        "Cats",
        [replace(a, category_label="Herbs"), b, replace(c, category_label="Herbs")],
    )
    sidebar = _sidebar_context(site.files["conf.py"])
    assert [group["label"] for group in sidebar] == ["Herbs", None]
    assert [node["docname"] for group in sidebar for node in group["books"]] == [
        "a/f",
        "c/f",
        "b/f",
    ]


def test_sidebar_skipped_books_absent() -> None:
    """0026 E2: an empty grimoire contributes no row to the tree at all."""
    site = plan_site(
        "Skip",
        [
            book("void", (chapter("shell", ()),)),
            book("live", (folio("doc", para_doc("kept")),)),
        ],
    )
    sidebar = _sidebar_context(site.files["conf.py"])
    assert len(sidebar) == 1
    assert [node["docname"] for node in sidebar[0]["books"]] == ["live/doc"]


def test_hidden_toctrees_first_leaf_and_site_index() -> None:
    """0031 ⑦: staged trees are engine-required but rendering-hidden.

    - grimoire master + chapter toctrees carry `:hidden:` (the page
      renders its own content; the panel is the tree);
    - the sidebar book row points at the FIRST content-bearing folio
      (tree order) — never a bare tree page; the master stays unlinked;
    - the SITE root index keeps its visible toctree (library landing).
    """
    site = plan_site(
        "Orch",
        [
            book(
                "b",
                (
                    chapter("c1", (folio("f1", para_doc("one")),)),
                    folio("f2", para_doc("two")),
                ),
            )
        ],
    )
    files = site.files
    assert "   :hidden:" in files["b/index.rst"]
    assert "   C1 </b/c1>" in files["b/index.rst"]
    chapter_page = files["b/c1.rst"]
    assert "   :hidden:" in chapter_page
    assert "   F1 </b/c1/f1>" in chapter_page
    leaf_page = files["b/c1/f1.rst"]
    assert "one" in leaf_page
    assert ":hidden:" not in leaf_page  # a leaf stages no toctree at all
    site_index = files["index.rst"]
    assert "   B </b/index>" in site_index
    assert ":hidden:" not in site_index

    sidebar = _sidebar_context(files["conf.py"])
    row = sidebar[0]["books"][0]
    assert row["docname"] == "b/c1/f1"  # the beginning, not the master
    assert row["container"] is True


def test_myst_child_toctree_hidden_option() -> None:
    site = plan_site(
        "Mystic2",
        [book("m", (chapter("ch", (folio("f", para_doc("body")),)),), fmt="myst")],
    )
    chapter_md = site.files["m/ch.md"]
    assert "```{toctree}" in chapter_md
    assert "   :hidden:" in chapter_md
    assert "F </m/ch/f>" in chapter_md


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
    assert "   A«B»C </t/p>" in site.files["t/index.rst"]
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


def test_body_subheadings_stage_under_the_generated_title() -> None:
    """0032 finding: a page body may start at h2.

    sourcegen prepends the page title as level 1, so an authored h2 is a
    legal child section, not a heading-level skip. The writer therefore
    validates from the staging context (base_level=1) while standalone
    exports keep the 0017 default.
    """
    body = body_doc(
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "The Forge"}],
        },
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "The furnace breathes."}],
        },
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Anvil Notes"}],
        },
    )
    rst_site = plan_site("T", [book("b", (folio("p", body),))])
    rst = rst_site.files["b/p.rst"]
    assert "P\n=\n" in rst  # generated page title (level 1)
    assert "The Forge\n---------\n" in rst  # authored h2 is legal
    assert "Anvil Notes\n~~~~~~~~~~~\n" in rst  # authored h3 nests below

    myst_book = StagedBook(
        slug="m",
        title="M",
        source_format="myst",
        nodes=(SnapshotNode(id="p", kind="folio", slug="p", title="P", tiptap=body),),
    )
    myst = plan_site("T", [myst_book]).files["m/p.md"]
    assert "# P\n" in myst
    assert "## The Forge\n" in myst
    assert "### Anvil Notes\n" in myst


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
