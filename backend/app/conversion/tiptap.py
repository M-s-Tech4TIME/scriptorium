"""TipTap JSON helpers (tiptap@1, decision 0010/0017).

Minimal typed builders plus `canon_doc`, the canonicalizer that makes
round-trips deterministic: sorted marks, no empty paragraphs, no falsy
attrs (`start` 1, empty language), trailing newlines stripped from code
blocks. Import and export both funnel through these helpers.
"""

from __future__ import annotations

from typing import Any

type Node = dict[str, Any]
type Mark = dict[str, Any]

# Canonical mark order (alphabetical by type; link keeps its attrs).
_MARK_ORDER = ("bold", "code", "italic", "link", "strike", "underline")


def new_node(
    type_: str,
    *,
    attrs: dict[str, Any] | None = None,
    content: list[Node] | None = None,
) -> Node:
    node: Node = {"type": type_}
    if attrs:
        node["attrs"] = attrs
    if content is not None:
        node["content"] = content
    return node


def new_text(text: str, *, marks: list[Mark] | None = None) -> Node:
    node: Node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def _canon_node(node: Node) -> Node | None:
    """Canonicalize one node; return None when the node must be dropped."""
    kind = node.get("type")
    out: Node = {"type": kind}

    attrs = node.get("attrs") or {}
    if kind == "orderedList" and attrs.get("start", 1) == 1:
        attrs = {k: v for k, v in attrs.items() if k != "start"}
    if kind == "codeBlock" and not attrs.get("language"):
        attrs = {k: v for k, v in attrs.items() if k != "language"}
    if attrs:
        out["attrs"] = attrs

    if kind == "text":
        text = node.get("text", "")
        if not text:
            return None
        out["text"] = text
        marks = node.get("marks") or []
        if marks:
            out["marks"] = sorted(
                marks,
                key=lambda m: (
                    _MARK_ORDER.index(m["type"]) if m["type"] in _MARK_ORDER else 99,
                    str(m.get("attrs", "")),
                ),
            )
        return out

    content = node.get("content") or []
    canon_content = [
        c for c in (_canon_node(child) for child in content) if c is not None
    ]
    if kind == "codeBlock":
        text = canon_content[0].get("text", "") if canon_content else ""
        text = text.rstrip("\n")
        canon_content = [new_text(text)] if text else []
    if kind in ("paragraph", "heading") and not canon_content:
        return None
    if (
        kind in ("blockquote", "bulletList", "orderedList", "listItem", "codeBlock")
        and not canon_content
    ):
        return None
    if canon_content:
        out["content"] = canon_content
    return out


def canon_doc(doc: Node) -> Node:
    """Return the canonical form of a TipTap document."""
    canon = _canon_node(doc)
    if canon is None:
        return new_node("doc", content=[])
    return canon
