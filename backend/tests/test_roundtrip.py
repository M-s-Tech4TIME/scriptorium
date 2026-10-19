"""TipTap ↔ RST/MyST conversion tests (decision 0017).

Covers three directions per the probe-verified parser facts:

1. Export/import round trip of the approved node set (Q-M2-1=A), asserting
   JSON equality AND source idempotency across both writers.
2. Fail-loud cases — constructs docutils 0.22.4 cannot represent exactly
   (no inline nesting; edge-space-inline-markup rules) raise ConversionError.
3. Source-side imports (RST/MyST) — including the docutils title/subtitle
   collapse, CJK heading width, and fail-loud unknown roles/tables/images.
"""

from __future__ import annotations

import pytest

from app.conversion.export_myst import export_myst
from app.conversion.export_rst import export_rst
from app.conversion.import_doc import ConversionError, import_document
from app.conversion.tiptap import Mark, Node, canon_doc, new_text

BOTH = ("rst", "myst")


def t(text: str, *marks: str) -> Node:
    """Text node with plain string marks (used by most corpus entries)."""
    ms: list[Mark] = [{"type": m} for m in marks]
    return new_text(text, marks=ms or None)


def p(*content: Node) -> Node:
    return {"type": "paragraph", "content": list(content)}


def hb() -> Node:
    return {"type": "hardBreak"}


def doc(*blocks: Node) -> Node:
    return {"type": "doc", "content": list(blocks)}


def link(href: str) -> Mark:
    return {"type": "link", "attrs": {"href": href}}


def dl(text: str, *marks: str) -> Node:
    """Text node carrying a raw link mark (for link+other-mark combos)."""
    return new_text(
        text, marks=[{"type": m} for m in marks] + [link("https://x.example")]
    )


ROUNDTRIP_CORPUS: list[tuple[str, Node, tuple[str, ...]]] = [
    ("plain", doc(p(t("hello world"))), BOTH),
    (
        "single-marks",
        doc(
            p(
                t("plain "),
                t("bold", "bold"),
                t(" mid "),
                t("italic", "italic"),
                t(" mid "),
                t("code", "code"),
                t(" mid "),
                t("struck", "strike"),
                t(" mid "),
                t("underline", "underline"),
                t(" end"),
            )
        ),
        BOTH,
    ),
    ("bare-link", doc(p(t("go "), dl("there"), t(" back"))), BOTH),
    ("hardbreak-para", doc(p(t("line one"), hb(), t("line "), t("two", "code"))), BOTH),
    (
        "headings",
        doc(
            {"type": "heading", "attrs": {"level": 1}, "content": [t("H one")]},
            p(t("body")),
            {"type": "heading", "attrs": {"level": 2}, "content": [t("H two")]},
            p(t("deeper body")),
            {"type": "heading", "attrs": {"level": 1}, "content": [t("H back")]},
        ),
        BOTH,
    ),
    (
        "lists",
        doc(
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [p(t("alpha"))]},
                    {"type": "listItem", "content": [p(t("beta")), p(t("gamma"))]},
                ],
            },
            {
                "type": "orderedList",
                "attrs": {"start": 5},
                "content": [
                    {"type": "listItem", "content": [p(t("five"))]},
                    {"type": "listItem", "content": [p(t("six"))]},
                ],
            },
        ),
        BOTH,
    ),
    (
        "quote-and-rule",
        doc(
            p(t("before")),
            {"type": "blockquote", "content": [p(t("quoted line"))]},
            p(t("after")),
            {"type": "horizontalRule"},
            p(t("trailing")),
        ),
        BOTH,
    ),
    (
        "nested-quote",
        doc(
            {
                "type": "blockquote",
                "content": [
                    p(t("outer")),
                    {"type": "blockquote", "content": [p(t("inner"))]},
                ],
            }
        ),
        BOTH,
    ),
    (
        "codeblock",
        doc(
            p(t("watch:")),
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [new_text("def f(x):\n    return x\n")],
            },
            {
                "type": "codeBlock",
                "content": [new_text("plain\nlines\n")],
            },
            p(t("done")),
        ),
        BOTH,
    ),
    (
        "item-with-quote",
        doc(
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            p(t("item")),
                            {"type": "blockquote", "content": [p(t("quoted"))]},
                        ],
                    }
                ],
            }
        ),
        BOTH,
    ),
    # MyST-only representable runs (RST fail-loud, see below).
    (
        "bold-italic-run",
        doc(p(t("a "), t("bi", "bold", "italic"), t(" b"))),
        ("myst",),
    ),
    (
        "code-strike-run",
        doc(p(t("m "), t("cs", "code", "strike"), t(" e"))),
        ("myst",),
    ),
    (
        "link-bold-run",
        doc(p(t("go "), dl("there", "bold"), t(" now"))),
        ("myst",),
    ),
    # Edge-space-inside-mark runs: CommonMark code spans preserve single-side
    # spaces, both-side via padding; <s>/<u>/<strong>/<em> carry their own.
    (
        "edge-space-code",
        doc(p(t("a"), t(" x ", "code"), t("b"))),
        ("myst",),
    ),
    (
        "edge-space-bold",
        doc(p(t("a"), t(" x ", "bold"), t("b"))),
        ("myst",),
    ),
    (
        "edge-space-strike",
        doc(p(t("a"), t(" x ", "strike"), t("b"))),
        ("myst",),
    ),
    (
        "cjk-heading",
        doc(
            {"type": "heading", "attrs": {"level": 1}, "content": [t("日本語の見出し")]}
        ),
        BOTH,
    ),
]


@pytest.mark.parametrize("name,json_doc,formats", ROUNDTRIP_CORPUS)
def test_roundtrip_json_and_source_idempotent(
    name: str, json_doc: Node, formats: tuple[str, ...]
) -> None:
    canonical = canon_doc(json_doc)
    for fmt in formats:
        writer = export_rst if fmt == "rst" else export_myst
        source = writer(canonical)
        back = import_document(source, fmt)
        assert back == canonical, f"{name}/{fmt}: JSON round trip diverged"
        assert writer(back) == source, f"{name}/{fmt}: source not idempotent"


FAIL_LOUD: list[tuple[str, Node, str, str]] = [
    # docutils inline markup does not nest: combos on one run are rejected.
    (
        "rst-bold-italic",
        doc(p(t("x", "bold", "italic"))),
        "rst",
        "combined inline marks",
    ),
    (
        "rst-code-strike",
        doc(p(t("x", "code", "strike"))),
        "rst",
        "combined inline marks",
    ),
    (
        "rst-strike-underline",
        doc(p(t("x", "strike", "underline"))),
        "rst",
        "combined inline marks",
    ),
    (
        "rst-link-bold",
        doc(p(dl("x", "bold"))),
        "rst",
        "combined inline marks",
    ),
    # docutils inline markup cannot carry edge spaces (probes: `**\ x**`
    # consumes the space; `` ` x` `` literals are rejected outright).
    ("rst-edge-code", doc(p(t(" x", "code"))), "rst", "edge spaces"),
    ("rst-edge-bold", doc(p(t(" x ", "bold"))), "rst", "edge spaces"),
    # docutils builds heading levels sequentially — skips fail loud.
    (
        "rst-heading-skip",
        doc(
            {"type": "heading", "attrs": {"level": 1}, "content": [t("H one")]},
            {"type": "heading", "attrs": {"level": 3}, "content": [t("H three")]},
        ),
        "rst",
        "Heading level skip",
    ),
    (
        "myst-heading-skip",
        doc(
            {"type": "heading", "attrs": {"level": 1}, "content": [t("H one")]},
            {"type": "heading", "attrs": {"level": 3}, "content": [t("H three")]},
        ),
        "myst",
        "Heading level skip",
    ),
]


@pytest.mark.parametrize("name,json_doc,fmt,fragment", FAIL_LOUD)
def test_fail_loud_rst(name: str, json_doc: Node, fmt: str, fragment: str) -> None:
    with pytest.raises(ConversionError, match=fragment):
        (export_rst if fmt == "rst" else export_myst)(canon_doc(json_doc))


# Writer must refuse unsuitable source constructs, not guess.
FAIL_LOUD_IMPORT: list[tuple[str, str, str]] = [
    ("rst-unknown-role", "D\n==\n\n:x-unknown:`y`\n", "docutils errors"),
    (
        "rst-table",
        "P\n\n+---+---+\n| a | b |\n+---+---+\n",
        "Unsupported block node",
    ),
    ("myst-image", "P ![alt](img.png)\n", "Unsupported inline node"),
    ("myst-unclosed-strike", "P <s>no close\n", "Unclosed inline HTML"),
]


@pytest.mark.parametrize("name,source,fragment", FAIL_LOUD_IMPORT)
def test_fail_loud_import(name: str, source: str, fragment: str) -> None:
    with pytest.raises(ConversionError, match=fragment):
        import_document(source, "rst" if name.startswith("rst") else "myst")


def test_import_rst_no_language_literal_block() -> None:
    got = import_document("Watch::\n\n    x = 1\n", "rst")
    # "Watch::" line keeps its paragraph (colon dropped per RST rules).
    [para, block] = got["content"]
    assert para["type"] == "paragraph"
    assert para["content"] == [{"type": "text", "text": "Watch:"}]
    assert block == {
        "type": "codeBlock",
        "content": [{"type": "text", "text": "x = 1"}],
    }


def test_import_rst_single_section_title_collapse() -> None:
    got = import_document("Title\n=====\n\npara\n", "rst")
    assert got["content"][0]["type"] == "heading"
    assert got["content"][0]["attrs"] == {"level": 1}
    assert got["content"][1]["type"] == "paragraph"


def test_import_myst_adjacent_h2_is_subtitle() -> None:
    got = import_document("# A\n\n## B\n\nbody text\n", "myst")
    kinds = [b["type"] for b in got["content"]]
    assert kinds == ["heading", "heading", "paragraph"]
    assert got["content"][0]["attrs"] == {"level": 1}
    assert got["content"][1]["attrs"] == {"level": 2}


def test_import_rst_nested_markup_stays_literal() -> None:
    # docutils 0.22.4 parses nothing inside strong — the JSON mirrors that.
    got = import_document("**a *b* c**\n", "rst")
    [para] = got["content"]
    assert para["type"] == "paragraph"
    [run] = para["content"]
    assert run == {"type": "text", "text": "a *b* c", "marks": [{"type": "bold"}]}


def test_cjk_heading_bar_width() -> None:
    json_doc = canon_doc(
        doc(
            {"type": "heading", "attrs": {"level": 1}, "content": [t("日本語の見出し")]}
        )
    )
    source = export_rst(json_doc)
    # CJK chars count as 2 columns; level 1 uses overline + underline.
    assert "日本語の見出し\n" + "=" * 14 in source
    assert import_document(source, "rst") == json_doc
