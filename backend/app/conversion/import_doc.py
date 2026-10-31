"""Import RST or MyST source → TipTap JSON (`tiptap@1`, decision 0010/0017).

Usage: `import_document(text, source_format="rst" | "myst")`.
Both formats parse into docutils doctrees (MyST via
`myst_parser.parsers.docutils_.Parser`), so one walker imports both.
Fails loudly (ConversionError) on constructs outside the approved set and on
docutils error-level problems (e.g. unknown roles) — deliberate integrity
choice over silent degradation.
"""

from __future__ import annotations

import re
from typing import Any

from docutils import nodes
from docutils.core import publish_doctree
from docutils.nodes import Node as DocutilsNode

from .tiptap import Mark, Node, canon_doc, new_node, new_text

# Aura nodes: parsing machinery, never editor content — safe to drop.
_AURA = (
    nodes.system_message,
    nodes.comment,
    nodes.target,
    nodes.pending,
    nodes.substitution_definition,
)

_WS = re.compile(r"\s+")

_RUN = tuple[str, frozenset[str], str | None]

_HARD_BREAK = "\n"  # run text reserved for hardBreak (real text never has \n)


class ConversionError(Exception):
    """Source (or JSON) uses constructs outside the approved converter set."""


def _parse_doctree(text: str, source_format: str) -> DocutilsNode:
    """Parse source text into a docutils doctree (RST or MyST parser)."""
    overrides: dict[str, Any] = {"report_level": 5, "halt_level": 5}
    if source_format == "myst":
        from myst_parser.parsers.docutils_ import Parser as MystParser

        doctree = publish_doctree(
            text, parser=MystParser(), settings_overrides=overrides
        )
    elif source_format == "rst":
        doctree = publish_doctree(text, settings_overrides=overrides)
    else:
        raise ConversionError(f"Unknown source_format {source_format!r} (rst|myst).")
    for msg in doctree.findall(nodes.system_message):
        try:
            level = int(msg.get("level", 0))
        except TypeError, ValueError:
            level = 0
        if level >= 3:  # error/severe — never silently convert broken source
            raise ConversionError(f"Source has docutils errors: {msg.astext()}")
    return doctree


def _code_language(block: DocutilsNode) -> str | None:
    """docutils stores lang in classes (['code','python']); plain blocks none."""
    classes = [c for c in block.get("classes", []) if c != "code"]
    return classes[0] if classes else None


def _collect_runs(parent: DocutilsNode, marks: tuple[Mark, ...]) -> list[_RUN]:
    """Flatten an inline tree into (text, mark-names, href) runs.

    - docutils strong/emphasis/literal → bold/italic/code marks.
    - references (refuri/refid) → link mark with href.
    - RST custom roles (`.. role:: strike|underline`) arrive as `inline`
      nodes with a matching class; MyST strike/underline arrive as raw HTML
      sibling markers (<s>…</s>). Both are tracked via the `stack` below so
      text between the markers inherits the mark.
    - raw <br /> → _HARD_BREAK run (hardBreak node); myst-parser also emits a
      latex twin raw containing only backslashes — ignored (0017).
    """
    runs: list[_RUN] = []
    stack: list[str] = []

    def visit(node: DocutilsNode, active: frozenset[str], href: str | None) -> None:
        if isinstance(node, nodes.Text):
            text = node.astext()
            if text:
                names = active | frozenset(stack)
                runs.append((_WS.sub(" ", text), frozenset(names), href))
            return
        if isinstance(node, _AURA):
            return
        name = node.__class__.__name__
        if name in ("strong", "bold"):
            _kids(node, active | {"bold"}, href)
        elif name in ("emphasis", "italic"):
            _kids(node, active | {"italic"}, href)
        elif name == "literal":
            _kids(node, active | {"code"}, href)
        elif isinstance(node, nodes.reference):
            target = str(
                node.get("refuri")
                or (f"#{node.get('refid')}" if node.get("refid") else "")
            )
            _kids(node, active, target or None)
        elif isinstance(node, nodes.inline):
            classes = set(node.get("classes", []))
            tag = (
                "strike"
                if "strike" in classes
                else ("underline" if "underline" in classes else None)
            )
            if tag is not None:
                if tag in stack:
                    raise ConversionError("Nested strike/underline containers.")
                stack.append(tag)
                _kids(node, active, href)
                stack.pop()
            else:
                _kids(node, active, href)
        elif isinstance(node, nodes.raw):
            _raw(node, active, href)
        elif isinstance(node, nodes.line):
            for child in node.children:
                visit(child, active, href)
        else:
            raise ConversionError(f"Unsupported inline node <{name}> in source.")

    def _raw(node: DocutilsNode, active: frozenset[str], href: str | None) -> None:
        fmt = str(node.get("format", ""))
        text = node.astext().strip()
        if fmt == "latex" and text.replace("\\", "") == "":
            return  # latex twin of the html <br /> hardbreak — ignore (0017)
        if fmt != "html":
            raise ConversionError(f"Unsupported raw node (format={fmt!r}).")
        if text.startswith("<br"):
            runs.append((_HARD_BREAK, active | frozenset(stack), href))
            return
        tag_map = {
            "<s>": "strike",
            "</s>": "strike",
            "<u>": "underline",
            "</u>": "underline",
            # myst fallback for bold/italic runs with edge spaces — CommonMark
            # asterisk delimiters cannot carry them (0017).
            "<em>": "italic",
            "</em>": "italic",
            "<strong>": "bold",
            "</strong>": "bold",
        }
        tag = tag_map.get(text)
        if tag is not None:
            closer = text.startswith("</")
            if closer:
                if not stack or stack[-1] != tag:
                    raise ConversionError(f"Mismatched {text} closer.")
                stack.pop()
            else:
                if tag in stack:
                    raise ConversionError(f"Nested {text} HTML containers.")
                stack.append(tag)
            return
        raise ConversionError(f"Unsupported raw HTML fragment {text!r}.")

    def _kids(node: DocutilsNode, active: frozenset[str], href: str | None) -> None:
        for child in node.children:
            visit(child, active, href)

    # The root (paragraph / title / line) is a container here — walk children.
    for child in parent.children:
        visit(child, frozenset(m["type"] for m in marks), None)
    if stack:
        raise ConversionError(f"Unclosed inline HTML marker <{stack[-1]}> in source.")
    return runs


def _append_runs(runs: list[_RUN], out: list[Node]) -> None:
    """Emit text / hardBreak nodes from runs, merging only ADJACENT runs.

    Non-adjacent runs must never be reordered — merging by key would move
    later plain runs before interleaved markup. _HARD_BREAK characters inside
    merged text split into hardBreak nodes (real text never contains \n).
    """
    items: list[tuple[frozenset[str], str | None, str]] = []
    for text, names, href in runs:
        if items and items[-1][0] == names and items[-1][1] == href:
            items[-1] = (names, href, items[-1][2] + text)
        else:
            items.append((names, href, text))
    for names, href, merged in items:
        if not merged:
            continue
        mark_list: list[Mark] = [
            {"type": t}
            for t in sorted(names)
            if t in ("bold", "italic", "code", "strike", "underline")
        ]
        if href:
            mark_list.append({"type": "link", "attrs": {"href": href}})
        segments = merged.split(_HARD_BREAK)
        for idx, segment in enumerate(segments):
            if idx:
                out.append(new_node("hardBreak"))
            if segment:
                out.append(new_text(segment, marks=mark_list or None))


class _Importer:
    def blocks(self, parent: DocutilsNode) -> list[Node]:
        out: list[Node] = []
        for child in parent.children:
            out.extend(self._one(child))
        return out

    def _one(self, child: DocutilsNode) -> list[Node]:
        """Convert one block-level child wherever it appears (single path)."""
        if isinstance(child, nodes.section):
            out: list[Node] = []
            self._section(child, out)
            return out
        if isinstance(child, _AURA):
            return []
        if isinstance(child, nodes.title):
            # Single-section doctrees place the title directly under the
            # document (no section wrapper) — emit it as a level-1 heading.
            return [
                new_node(
                    "heading",
                    attrs={"level": 1},
                    content=self._inline(child),
                )
            ]
        if isinstance(child, nodes.subtitle):
            # docutils docinfo convention: an h2 immediately following the
            # h1 title (with no intervening body) becomes the subtitle.
            return [
                new_node(
                    "heading",
                    attrs={"level": 2},
                    content=self._inline(child),
                )
            ]
        if isinstance(child, nodes.paragraph):
            return [self._paragraph(child)]
        if isinstance(child, nodes.literal_block):
            return [self._code_block(child)]
        if isinstance(child, (nodes.bullet_list, nodes.enumerated_list)):
            return [self._list(child)]
        if isinstance(child, nodes.block_quote):
            return [new_node("blockquote", content=self.blocks(child))]
        if isinstance(child, nodes.transition):
            return [new_node("horizontalRule")]
        if isinstance(child, nodes.line_block):
            return [self._line_block(child)]
        raise ConversionError(f"Unsupported block node <{child.__class__.__name__}>.")

    def _section(self, section: DocutilsNode, out: list[Node]) -> None:
        depth = 1
        ancestor = section.parent
        while isinstance(ancestor, nodes.section):
            depth += 1
            ancestor = ancestor.parent
        for child in section.children:
            if isinstance(child, nodes.title):
                level = min(depth, 6)
                out.append(
                    new_node(
                        "heading",
                        attrs={"level": level},
                        content=self._inline(child),
                    )
                )
            else:
                out.extend(self._one(child))

    def _inline(self, parent: DocutilsNode) -> list[Node]:
        out: list[Node] = []
        _append_runs(_collect_runs(parent, ()), out)
        return out

    def _paragraph(self, para: DocutilsNode) -> Node:
        return new_node("paragraph", content=self._inline(para))

    def _code_block(self, block: DocutilsNode) -> Node:
        lang = _code_language(block)
        attrs = {"language": lang} if lang else {}
        return new_node("codeBlock", attrs=attrs, content=[new_text(block.astext())])

    def _list(self, lst: DocutilsNode) -> Node:
        items = [
            new_node("listItem", content=self.blocks(item)) for item in lst.children
        ]
        if isinstance(lst, nodes.enumerated_list):
            start = int(lst.get("start", 1) or 1)
            attrs = {"start": start} if start != 1 else {}
            return new_node("orderedList", attrs=attrs, content=items)
        return new_node("bulletList", content=items)

    def _line_block(self, block: DocutilsNode) -> Node:
        """line_block → paragraph with hardBreak between lines."""
        content: list[Node] = []
        for idx, line in enumerate(block.findall(nodes.line)):
            if idx:
                content.append(new_node("hardBreak"))
            content.extend(self._inline(line))
        return new_node("paragraph", content=content)


def import_document(text: str, source_format: str) -> dict[str, Any]:
    """Parse source text → canonical TipTap doc JSON (`tiptap@1`)."""
    doctree = _parse_doctree(text, source_format)
    importer = _Importer()
    return canon_doc(new_node("doc", content=importer.blocks(doctree)))
