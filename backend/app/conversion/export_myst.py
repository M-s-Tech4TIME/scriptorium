"""TipTap JSON → MyST/CommonMark writer (decision 0017, Q-M2-3).

Plain CommonMark with fenced code blocks; strike/underline are not parsed by
myst-parser 5.1.0 as ``~~``/custom markup, so they are emitted as inline raw
HTML (``<s>…</s>`` / ``<u>…</u>``) which survives MyST import as raw html
nodes the importer maps back to marks (0017). Unlike RST, code may coexist
with strike/underline on one run (code span + tags are siblings).
"""

from __future__ import annotations

import re
import textwrap

from .import_doc import ConversionError
from .tiptap import Node

# CommonMark ASCII punctuation may be backslash-escaped.
_ESC = str.maketrans({c: "\\" + c for c in "\\`*_~[]<#"})

_ENUMERATOR = re.compile(r"^(\d+)([.)])( |$)")


def _escape(text: str) -> str:
    return text.translate(_ESC)


def _href_safe(href: str) -> str:
    return href.replace("(", "\\(").replace(")", "\\)")


def _code_span(text: str) -> str:
    # Restores code content whose BOTH edges are spaces: CommonMark strips a
    # single space per side in that case, so pad one extra space per side.
    core = (
        " " + text + " "
        if text.startswith(" ") and text.endswith(" ") and len(text) >= 1
        else text
    )
    runs = re.findall(r"`+", core)
    delim = "`" * (max((len(r) for r in runs), default=0) + 1)
    if core.startswith("`") or core.endswith("`"):
        return f"{delim} {core} {delim}"  # code spans strip one edge-space pair
    return f"{delim}{core}{delim}"


def _guard(line: str) -> str:
    """Escape line starts that would re-parse as structure (CommonMark)."""
    if not line:
        return line
    if re.fullmatch(r"[-=*_=]+", line):
        return "\\" + line  # setext underline / thematic break lookalikes
    c = line[0]
    if c == "#":
        return "\\" + line  # ATX heading trigger (even "#tag")
    if line.startswith(("> ", "- ", "+ ", "* ")):
        return "\\" + line
    m = _ENUMERATOR.match(line)
    if m:
        return m.group(1) + "\\" + line[len(m.group(1)) :]  # ordered "5." / "5)"
    m2 = re.match(r"^\(\d+\) ", line)
    if m2:
        return "\\(" + line[1:]
    return line


def _render_run(text: str, marks: list[Node]) -> str:
    present = {str(m.get("type")) for m in marks}
    href = next(
        (
            str(m.get("attrs", {}).get("href", ""))
            for m in marks
            if m.get("type") == "link"
        ),
        None,
    )
    edges = text != text.strip(" ")

    if "code" in present:
        # Code spans keep single-side edge spaces; both-side edge spaces are
        # restored by padding one extra space per side (CommonMark strips a
        # single space per side when BOTH edges are spaces).
        s = _code_span(text)
    else:
        s = _escape(text)
    # <s>/<u> raw tags preserve edge spaces naturally (no escape tricks).
    if "strike" in present:
        s = f"<s>{s}</s>"
    if "underline" in present:
        s = f"<u>{s}</u>"
    if href is not None:
        s = f"[{s}]({_href_safe(href)})"
    # Asterisk delimiters reject edge spaces (`**\ x**` renders a literal
    # backslash in CommonMark) — fall back to <strong>/<em> HTML tags.
    if "italic" in present:
        s = f"<em>{s}</em>" if edges else f"*{s}*"
    if "bold" in present:
        s = f"<strong>{s}</strong>" if edges else f"**{s}**"
    return s


def _inline_lines(nodes_list: list[Node]) -> list[str]:
    """Render inline nodes into hardBreak-separated lines (no markers)."""
    runs: list[tuple[str, list[Node]]] = []
    for node in nodes_list:
        if node.get("type") == "hardBreak":
            runs.append(("\n", []))
            continue
        if node.get("type") != "text":
            raise ConversionError(f"Unsupported inline node {node.get('type')!r}.")
        marks = node.get("marks") or []
        if runs and runs[-1][1] == marks:
            runs[-1] = (runs[-1][0] + str(node.get("text", "")), marks)
        else:
            runs.append((str(node.get("text", "")), marks))
    lines: list[str] = []
    current: list[str] = []
    for text, marks in runs:
        segments = text.split("\n")
        for idx, segment in enumerate(segments):
            if idx:
                lines.append("".join(current))
                current = []
            if segment:
                current.append(_render_run(segment, marks))
    lines.append("".join(current))
    while lines and not lines[-1]:  # trailing hardBreak
        lines.pop()
    return lines


def _blocks_str(blocks: list[Node], indent: str) -> str:
    parts: list[str] = []
    for block in blocks:
        rendered = _block_str(block, indent)
        if rendered.strip():
            parts.append(rendered)
    return "\n\n".join(parts)


def _block_str(node: Node, indent: str) -> str:
    kind = node.get("type")
    content = node.get("content") or []
    if kind == "paragraph":
        lines = [_guard(line) for line in _inline_lines(content)]
        if len(lines) > 1:  # CommonMark hard break: backslash at each line end
            body = "\\\n".join(lines)
        else:
            body = lines[0] if lines else ""
        return "\n".join(indent + line for line in body.split("\n"))
    if kind == "heading":
        return _heading(node, indent)
    if kind == "codeBlock":
        return _code_block(node, indent)
    if kind == "bulletList":
        return _list(node, indent, ordered=False)
    if kind == "orderedList":
        return _list(node, indent, ordered=True)
    if kind == "blockquote":
        inner = _blocks_str(content, indent + "    ")
        return "\n".join(
            (indent + "> " + line.lstrip()) if line else (indent + ">")
            for line in textwrap.indent(inner, indent).split("\n")
        )
    if kind == "horizontalRule":
        return indent + "---"
    if kind == "image":
        return _image(node, indent)
    raise ConversionError(f"Unsupported block node {kind!r} for MyST export.")


def _image(node: Node, indent: str) -> str:
    attrs = node.get("attrs") or {}
    src = str(attrs.get("src") or "").strip()
    if not src:
        raise ConversionError("Image node has no src.")
    if "\n" in src or "\r" in src or " " in src:
        raise ConversionError("Image src must be a single URL without spaces.")
    alt = " ".join(str(attrs.get("alt") or "").split()).replace("]", "\\]")
    title = " ".join(str(attrs.get("title") or "").split()).replace('"', '\\"')
    suffix = f' "{title}"' if title else ""
    return f"{indent}![{alt}]({src}{suffix})"


def _heading(node: Node, indent: str) -> str:
    attrs = node.get("attrs") or {}
    level = min(max(int(attrs.get("level", 1)), 1), 6)
    # hardBreaks in a heading flatten into the title text (documented in 0017).
    text = "".join(_inline_lines(node.get("content") or []))
    return indent + "#" * level + " " + text


def _code_block(node: Node, indent: str) -> str:
    text = ""
    for child in node.get("content") or []:
        if child.get("type") == "text":
            text += str(child.get("text", ""))
    lang = str((node.get("attrs") or {}).get("language") or "")
    runs = re.findall(r"```+", text)
    fence = "`" * (max((len(r) for r in runs), default=0) + 3)
    body = textwrap.indent(text.rstrip("\n"), indent)
    return f"{indent}{fence}{lang}\n{body}\n{indent}{fence}"


def _list(node: Node, indent: str, *, ordered: bool) -> str:
    start = int((node.get("attrs") or {}).get("start", 1) or 1)
    chunks: list[str] = []
    for offset, item in enumerate(node.get("content") or []):
        if item.get("type") != "listItem":
            raise ConversionError(f"Expected listItem, got {item.get('type')!r}.")
        marker = f"{start + offset}. " if ordered else "- "
        pad = " " * len(marker)
        inner = _blocks_str(item.get("content") or [], indent + pad)
        lines = inner.split("\n") if inner else [indent + pad]
        first = indent + marker + lines[0].lstrip()
        chunks.append("\n".join([first, *lines[1:]]))
    return "\n\n".join(chunks)


def _scan_heading_skips(blocks: list[Node], last: list[int]) -> None:
    """docutils assigns heading hierarchy from token order (with subtitle
    collapse and skip warnings) — level skips cannot survive reimport, so
    fail loud (decision 0017)."""
    for block in blocks:
        if block.get("type") == "heading":
            level = int((block.get("attrs") or {}).get("level", 1))
            if level > last[0] + 1:
                raise ConversionError(
                    f"Heading level skip: {level} follows {last[0]}; docutils "
                    "builds levels sequentially (decision 0017 fail-loud)."
                )
            last[0] = level
        for sub in block.get("content") or []:
            if isinstance(sub, dict) and sub.get("type") in PARAGRAPHISH:
                _scan_heading_skips([sub], last)
        if block.get("type") in ("bulletList", "orderedList"):
            for item in block.get("content") or []:
                _scan_heading_skips(item.get("content") or [], last)


PARAGRAPHISH = {"paragraph", "blockquote", "bulletList", "orderedList"}


def export_myst(doc: Node, *, base_level: int = 0) -> str:
    """Render a canonical TipTap doc → MyST (CommonMark).

    `base_level` mirrors `export_rst`: the staged page title is level 1,
    so body headings may start at h2; standalone exports keep 0.
    """
    if doc.get("type") != "doc":
        raise ConversionError("Expected a doc node at the root.")
    last: list[int] = [base_level]
    _scan_heading_skips(doc.get("content") or [], last)
    return _blocks_str(doc.get("content") or [], "") + "\n"
