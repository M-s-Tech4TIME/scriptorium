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

Theme (0027/0028): `THEME_BASE = "scriptorium"` — the Scriptorium
theme, materialized per build from `backend/app/sphinx/theme/`. The
staged conf carries `html_theme_path = ["theme"]`,
`pygments_style = "scriptorium_style.ScriptoriumStyle"` (the custom
Pygments style module lives beside conf.py once the runner copies it
in), and — when any page is published — `html_context =
{'sidebar_categories': …}`, the visual-only sidebar tree (categories
are order-only grouping labels, not toctree levels). Every sidebar
docname is produced by the same publishable-only traversal the staged
pages use, so the sidebar can never reference a page the build did not
write.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.conversion.import_doc import ConversionError
from app.conversion.export_myst import export_myst
from app.conversion.export_rst import export_rst

THEME_BASE = "scriptorium"
PYGMENTS_STYLE = "scriptorium_style.ScriptoriumStyle"

_SIDEBAR_ICONS = {"book": "book", "node": "file-text"}


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
    category_label: str | None = None  # visual grouping only (0028)


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


def _conf_py(title: str, myst: bool, sidebar_categories: list[dict[str, Any]]) -> str:
    extensions = '["myst_parser"]' if myst else "[]"
    suffix = (
        '{".rst": "restructuredtext", ".md": "myst"}'
        if myst
        else '{".rst": "restructuredtext"}'
    )
    # Materialized layout: conf.py + scriptorium_style.py at the
    # workspace root, the copied theme at ./theme/scriptorium (0027).
    # html_context accepts dict values only — the sidebar tree rides
    # under the `sidebar_categories` key (0028).
    context: dict[str, Any] = {"sidebar_categories": sidebar_categories}
    return "\n".join(
        [
            "# Auto-generated by Scriptorium sourcegen (decision 0026).",
            "# Do not edit: this file is materialized fresh for every build.",
            "from pathlib import Path",
            "import sys",
            "sys.path.insert(0, str(Path(__file__).resolve().parent))",
            f"project = {title!r}",
            'master_doc = "index"',
            'exclude_patterns = ["_build"]',
            f"extensions = {extensions}",
            f"source_suffix = {suffix}",
            f"html_theme = {THEME_BASE!r}",
            'html_theme_path = ["theme"]',
            f"pygments_style = {PYGMENTS_STYLE!r}",
            "html_static_path = []",
            f"html_context = {context!r}",
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
) -> tuple[str, dict[str, Any]]:
    """Materialize one page; recurse into publishable children first.

    Returns the docname plus its sidebar-tree row (children are the
    published, visited child rows — same traversal as the staged pages).
    """
    docname = f"{book.slug}/{'/'.join(parents + (_leaf(node.slug),))}"
    child_entries: list[tuple[str, str]] = []
    child_rows: list[dict[str, Any]] = []
    for child in node.children:
        if _publishable(child):
            child_docname, child_row = _emit_page(
                book, child, parents + (node.slug,), files
            )
            child_entries.append((child.title, child_docname))
            child_rows.append(child_row)

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

    row: dict[str, Any] = {
        "title": node.title,
        "docname": docname,
        "branch": docname + "/",
        "icon": _SIDEBAR_ICONS["node"],
        "children": child_rows,
    }
    return docname, row


def _sidebar_rows(
    pairs: Sequence[tuple["StagedBook", dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Group the per-book sidebar rows under their category labels.

    Categories are order-only visual grouping (0020/0028): labels come
    in first-seen order; the unlabeled bucket stays last. Only books
    that actually published pages appear (0026 E2 skips the rest).
    """
    labeled: list[dict[str, Any]] = []
    unlabeled: dict[str, Any] = {"label": None, "books": []}
    for book, row in pairs:
        if book.category_label is None:
            unlabeled["books"].append(row)
            continue
        for group in labeled:
            if group["label"] == book.category_label:
                group["books"].append(row)
                break
        else:
            labeled.append({"label": book.category_label, "books": [row]})
    groups = [*labeled]
    if unlabeled["books"]:
        groups.append(unlabeled)
    return groups


def plan_site(title: str, books: Sequence[StagedBook]) -> SitePlan:
    """Plan the whole one-site build for an Athenaeum snapshot.

    Returns the file map. The sidebar tree (html_context) is built from
    the same single traversal: `_emit_page` returns each published
    page's row, so the sidebar can never reference a page the build did
    not write.
    """
    if not books:
        raise EmptySiteError("Athenaeum has no grimoires to build.")

    files: dict[str, str] = {}
    notes: list[str] = []
    sidebar_pairs: list[tuple[StagedBook, dict[str, Any]]] = []
    site_entries: list[tuple[str, str]] = []

    for book in books:
        entries: list[tuple[str, str]] = []
        root_rows: list[dict[str, Any]] = []
        for root in book.nodes:
            if _publishable(root):
                docname, row = _emit_page(book, root, (), files)
                entries.append((root.title, docname))
                root_rows.append(row)
        if not entries:
            notes.append(
                f"skipped empty grimoire '{book.slug}' ('{book.title}') "
                "— no folio documents"
            )
            continue  # 0026 E2: no sidebar presence at all
        master = f"{book.slug}/index"
        files[f"{master}.rst"] = _join_page(
            [_title_block(book.title, "rst"), _toctree(entries)]
        )
        site_entries.append((book.title, master))
        sidebar_pairs.append(
            (
                book,
                {
                    "title": book.title,
                    "docname": master,
                    "branch": f"{book.slug}/",
                    "icon": _SIDEBAR_ICONS["book"],
                    "children": root_rows,
                },
            )
        )

    if not site_entries:
        raise EmptySiteError("Athenaeum has no publishable grimoires (all empty).")

    sidebar = _sidebar_rows(sidebar_pairs)
    files["conf.py"] = _conf_py(
        title, any(book.source_format == "myst" for book in books), sidebar
    )
    files["index.rst"] = _toctree(site_entries)
    return SitePlan(files=files, notes=tuple(notes))
