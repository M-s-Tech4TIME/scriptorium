"""M4-C2 source staging — plan a Sphinx source tree (decision 0026).

One Athenaeum is one site: every grimoire materializes into its own
directory (staging keyed by grimoire id — the runner names the staging
root per build), folios export via the M2 writers, and one conf.py is
generated per Athenaeum.

Design properties the tests pin:

- **Pure:** no DB/session access; the runner slices snapshots and calls
  `plan_site` / `snapshot_nodes`.
- **Deterministic:** identical input → identical files byte-for-byte
  (positions and ties come ordered from the loader).
- **Fail loud:** an unconvertible body raises `StagingError` — the build
  must fail, never ship corrected-guess output.
- **Edge rulings (0026 §Edge rulings):** E1 — no grimoires (or none
  publishable) → `EmptySiteError` → 422 at the trigger endpoint; E2 —
  an empty grimoire is skipped with a note; (E3 — per-Athenaeum
  serialization — is enforced by the runner, not here).

Document bodies export **directly from the stored canonical TipTap**:
the save path canonicalizes (`PUT` → `canon_doc`), so `source_text` is
never consulted — no stale-source artifacts (0026 micro-default).

Docnames: `_slug/<…path slugs>/leaf` inside each book directory. Only
the leaf `<slug>-index` collision is mangled (`index` → `index-p`),
because `index` is otherwise reserved for the book master document.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.conversion.import_doc import ConversionError
from app.conversion.export_myst import export_myst
from app.conversion.export_rst import export_rst

THEME_BASE = (
    "alabaster"  # interim placeholder (0026 mandate 2: curated theme lands in M4-C3)
)


class EmptySiteError(ValueError):
    """The Athenaeum has (effectively) no grimoires to build — 0026 E1 → 422."""


class StagingError(ValueError):
    """Source materialization failed loudly; the build must record `failed`."""


@dataclass(frozen=True)
class SnapshotNode:
    """One node of the ordered tree, with its document body if published.

    Rows arrive per the loader's ordering (position, id — per sibling
    set). `children` preserves that order recursively.
    """

    id: Any
    kind: str
    slug: str
    title: str
    tiptap: dict[str, Any] | None = None
    children: tuple["SnapshotNode", ...] = ()


@dataclass(frozen=True)
class StagedBook:
    """One grimoire snapshot: name/slug/format plus its tree of nodes."""

    slug: str
    title: str
    source_format: str  # 'rst' | 'myst'
    nodes: tuple[SnapshotNode, ...] = ()  # roots, loader-ordered


@dataclass(frozen=True)
class SitePlan:
    """The materializable site: relpath → file text, plus log notes (E2)."""

    files: dict[str, str]
    notes: tuple[str, ...]


def snapshot_nodes(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[SnapshotNode, ...]:
    """Fold flat node rows (any row order; per-parent order preserved) into trees."""
    info: dict[Any, dict[str, Any]] = {}
    links: dict[Any, list[Any]] = {}
    for row in rows:
        info[row["id"]] = {
            "kind": str(row["kind"]),
            "slug": str(row["slug"]),
            "title": str(row["title"]),
            "tiptap": row.get("tiptap"),
            "children": [],
        }
        links.setdefault(row["parent_id"], []).append(row["id"])

    def build(pid: Any) -> tuple[SnapshotNode, ...]:
        return tuple(
            SnapshotNode(
                id=nid,
                kind=info[nid]["kind"],
                slug=info[nid]["slug"],
                title=info[nid]["title"],
                tiptap=info[nid]["tiptap"],
                children=build(nid),
            )
            for nid in links.get(pid, [])
        )

    return build(None)


def _has_content(tiptap: dict[str, Any] | None) -> bool:
    return isinstance(tiptap, dict) and bool(tiptap.get("content"))


def _publishable(node: SnapshotNode) -> bool:
    """A page is published iff it or any descendant carries a document body."""
    return _has_content(node.tiptap) or any(
        _publishable(child) for child in node.children
    )


def _leaf(slug: str) -> str:
    """`index` collides with the book master document at the leaf — mangle."""
    return "index-p" if slug == "index" else slug


def _safe_title(title: str) -> str:
    # Toctree titles are presentation-only; angle brackets would terminate
    # the explicit `Title <ref>` form. Disclosed micro-default (0026).
    return title.replace("<", "«").replace(">", "»").strip()


def _page_body(node: SnapshotNode, book: StagedBook) -> str | None:
    """Export the stored canonical TipTap body (fail loud on feedback)."""
    data = node.tiptap
    if not isinstance(data, dict) or not data.get("content"):
        return None
    try:
        return export_myst(data) if book.source_format == "myst" else export_rst(data)
    except ConversionError as exc:
        raise StagingError(
            f"grimoire '{book.slug}': folio '{node.slug}': {exc}"
        ) from exc


def _toctree(entries: Sequence[tuple[str, str]], source_format: str = "rst") -> str:
    if source_format == "myst":
        # the RST directive is not parsed inside .md pages — MyST uses
        # a fenced nested directive (CI finding).
        lines = ["```{toctree}", "   :maxdepth: 2", ""]
        for title, docname in entries:
            lines.append(f"{_safe_title(title)} </{docname}>")
        return "\n".join([*lines, "```", ""])
    lines = [".. toctree::", "   :maxdepth: 2", ""]
    for title, docname in entries:
        # Absolute (`/prefix`) docnames: toctree references are
        # document-relative without the leading slash, so a nested page
        # entry would resolve against its own directory (CI finding).
        lines.append(f"   {_safe_title(title)} </{docname}>")
    return "\n".join(lines) + "\n"


def _conf_py(title: str, myst: bool) -> str:
    extensions = '["myst_parser"]' if myst else "[]"
    suffix = (
        '{".rst": "restructuredtext", ".md": "myst"}'
        if myst
        else '{".rst": "restructuredtext"}'
    )
    return "\n".join(
        [
            "# Auto-generated by Scriptorium sourcegen (decision 0026).",
            "# Do not edit: this file is materialized fresh for every build.",
            f"project = {title!r}",
            'master_doc = "index"',
            'exclude_patterns = ["_build"]',
            f"extensions = {extensions}",
            f"source_suffix = {suffix}",
            f"html_theme = {THEME_BASE!r}",  # interim; curated theme lands in M4-C3
            "",
        ]
    )


def _join_page(parts: Sequence[str]) -> str:
    return "\n\n".join(part.rstrip("\n") for part in parts) + "\n"


def _title_block(title: str, source_format: str) -> str:
    """Top section title for a staged page.

    Sphinx resolves toctree entries against the TARGET document's own
    section titles — an explicit `Title <ref>` only restyles the target's
    top title, which must exist (CI finding: a page of bare paragraph
    text has no titles and the entry is dropped, failing `-W`). Every
    referenced page therefore carries its node/book title as the first
    section (deterministic, disclosed micro-default). The site root
    index (master_doc) is never a toctree target and stays bare.
    """
    if source_format == "myst":
        return f"# {title}\n"
    return f"{title}\n{'=' * len(title)}\n"


def _emit_page(
    book: StagedBook,
    node: SnapshotNode,
    parents: tuple[str, ...],
    files: dict[str, str],
) -> str:
    """Materialize one page; recurse into publishable children first."""
    docname = f"{book.slug}/{'/'.join(parents + (_leaf(node.slug),))}"
    child_entries: list[tuple[str, str]] = []
    for child in node.children:
        if _publishable(child):
            child_docname = _emit_page(book, child, parents + (node.slug,), files)
            child_entries.append((child.title, child_docname))

    parts: list[str] = [_title_block(node.title, book.source_format)]
    body = _page_body(node, book)
    if body is not None:
        parts.append(body)
    if child_entries:
        parts.append(_toctree(child_entries, book.source_format))
    if not parts:  # _publishable guard makes this unreachable
        raise StagingError(f"grimoire '{book.slug}': '{node.slug}' published empty")

    ext = "md" if book.source_format == "myst" else "rst"
    files[f"{docname}.{ext}"] = _join_page(parts)
    return docname


def _emit_book(
    book: StagedBook, files: dict[str, str], notes: list[str]
) -> tuple[str, str] | None:
    """Materialize one book; return its site-index entry, else None (0026 E2)."""
    entries: list[tuple[str, str]] = []
    for root in book.nodes:
        if _publishable(root):
            entries.append((root.title, _emit_page(book, root, (), files)))
    if not entries:
        notes.append(
            f"skipped empty grimoire '{book.slug}' ('{book.title}') "
            "— no folio documents"
        )
        return None
    master = f"{book.slug}/index"
    # book master is a toctree TARGET (the site index references it) →
    # carries the book title as its top section (see _title_block).
    files[f"{master}.rst"] = _join_page(
        [_title_block(book.title, "rst"), _toctree(entries)]
    )
    return (book.title, master)


def plan_site(title: str, books: Sequence[StagedBook]) -> SitePlan:
    """Plan the whole one-site build for an Athenaeum snapshot."""
    if not books:
        raise EmptySiteError("Athenaeum has no grimoires to build.")

    files: dict[str, str] = {
        "conf.py": _conf_py(title, any(book.source_format == "myst" for book in books))
    }
    notes: list[str] = []
    entries = [
        master
        for master in (_emit_book(book, files, notes) for book in books)
        if master is not None
    ]
    if not entries:
        raise EmptySiteError("Athenaeum has no publishable grimoires (all empty).")

    files["index.rst"] = _toctree(entries)
    return SitePlan(files=files, notes=tuple(notes))
