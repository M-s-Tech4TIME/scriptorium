"""TipTap JSON → reStructuredText writer (decision 0017, Q-M2-1=A).

Nesting order (docutils constraints): strong/emphasis/reference parse their
contents, while inline literals (``code``) and custom roles
(``strike``/``underline``) are raw containers. Therefore a run carrying
{code} plus {strike|underline}, or both roles at once, is unrepresentable in
plain RST and the writer raises ConversionError (fail-loud — 0017).

Line-start guards escape characters that would otherwise be re-parsed as
structure (lists, directives, section bars, enumerators).
"""

from __future__ import annotations

import re
import textwrap

from docutils.utils import column_width

from .import_doc import ConversionError
from .tiptap import Node

_LEVEL_CHARS = {1: "=", 2: "-", 3: "~", 4: "^", 5: '"', 6: "+"}

# Characters that start/continue inline markup — escaped everywhere in text.
_ESC = str.maketrans({c: "\\" + c for c in "\\`*_|:~"})

_ENUMERATOR = re.compile(r"^(\d+)([.)])( |$)")
_PUNCT_BAR = re.compile(r"[=\-~^\"+_]{4,}")

_ROLES = ("strike", "underline")


def _escape(text: str) -> str:
    return text.translate(_ESC)


def _guard(line: str) -> str:
    """Escape characters that could make a paragraph line re-parse as structure."""
    if not line:
        return line
    if _PUNCT_BAR.fullmatch(line):
        return "\\" + line  # section bar / single-line transition lookalike
    if line.startswith(".."):
        return "\\" + line  # directive/comment
    if line.startswith(("* ", "- ", "+ ")) or line in ("*", "-", "+"):
        return "\\" + line  # bullet markers
    if line.startswith("#"):
        return "\\" + line  # RST comment trigger
    m = _ENUMERATOR.match(line)
    if m:
        return m.group(1) + "\\" + line[len(m.group(1)) :]  # "5." enumerator
    m2 = re.match(r"^\(\d+\) ", line)
    if m2:
        return "\\(" + line[1:]  # enumerator (1)
    return line


def _href_safe(href: str) -> str:
    return href.replace("\\", "\\\\").replace("<", "\\<").replace(">", "\\>")


def _literal(text: str) -> str:
    """Inline literal: raw content, backtick-safe delimiters, no escapes.

    docutils inline literals use DOUBLE backticks (single backtick is
    interpreted text / title_reference).
    """
    runs = re.findall(r"`+", text)
    delim = "`" * (max((len(r) for r in runs), default=0) + 2)
    if text.startswith("`") or text.endswith("`"):
        return f"{delim} {text} {delim}"  # docutils strips one edge-space pair
    return f"{delim}{text}{delim}"


def _render_run(text: str, marks: list[Node], roles: set[str]) -> str:
    types = [str(m.get("type")) for m in marks]
    present = set(types)
    href = next(
        (
            str(m.get("attrs", {}).get("href", ""))
            for m in marks
            if m.get("type") == "link"
        ),
        None,
    )
    # Probe-verified docutils 0.22.4 constraints (decision 0017, fail-loud):
    # strong/emphasis content is parsed for NOTHING (roles, literals, nested
    # markup all stay literal), same-char delimiters cannot nest, and
    # references may not nest inside anything. One mark — or a bare link —
    # per run, no combinations.
    if len(present) > 1:
        raise ConversionError(
            f"RST cannot represent combined inline marks {sorted(present)} on "
            "one run (docutils inline markup does not nest; decision 0017 "
            "fail-loud policy)."
        )

    # docutils inline markup cannot carry edge spaces: `` ` x` `` literals are
    # rejected outright, and escaped spaces inside strong/roles are consumed
    # (`**\ x**` parses but yields "x" — space lost). Fail loud instead.
    if (present or href is not None) and text != text.strip(" "):
        raise ConversionError(
            "RST cannot preserve edge spaces inside marked/link runs "
            "(docutils inline markup rules; decision 0017 fail-loud policy)."
        )

    s = _escape(text)
    if "code" in present:
        s = _literal(text)  # raw content — no escape processing inside literals
    elif "strike" in present:
        roles.add("strike")
        s = f":strike:`{s}`"
    elif "underline" in present:
        roles.add("underline")
        s = f":underline:`{s}`"
    if href is not None:
        s = f"`{s} <{_href_safe(href)}>`__"
    if "italic" in present:
        s = f"*{s}*"
    if "bold" in present:
        s = f"**{s}**"
    return s


def _inline_lines(nodes_list: list[Node], roles: set[str]) -> list[str]:
    """Render inline nodes into hardBreak-separated lines (no markers).

    Adjacent runs with identical marks are merged first.
    """
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
                current.append(_render_run(segment, marks, roles))
    lines.append("".join(current))
    while lines and not lines[-1]:  # trailing hardBreak
        lines.pop()
    return lines


def _paragraph_lines(content: list[Node], indent: str, roles: set[str]) -> list[str]:
    lines = [_guard(line) for line in _inline_lines(content, roles)]
    if not lines:
        return [indent]
    if len(lines) > 1:  # hardBreaks → docutils line-block (verbatim lines)
        body = textwrap.indent("\n".join(lines), indent + "    ")
        return [indent + ".. line-block::", "", body]
    return [indent + lines[0]]


def _blocks_str(blocks: list[Node], indent: str, roles: set[str]) -> str:
    parts: list[str] = []
    for block in blocks:
        rendered = _block_str(block, indent, roles)
        if rendered.strip():
            parts.append(rendered)
    return "\n\n".join(parts)


def _block_str(node: Node, indent: str, roles: set[str]) -> str:
    kind = node.get("type")
    content = node.get("content") or []
    if kind == "paragraph":
        return "\n".join(_paragraph_lines(content, indent, roles))
    if kind == "heading":
        return "\n".join(_heading(node, indent, roles))
    if kind == "codeBlock":
        return _code_block(node, indent)
    if kind == "bulletList":
        return _list(node, indent, roles, ordered=False)
    if kind == "orderedList":
        return _list(node, indent, roles, ordered=True)
    if kind == "blockquote":
        # Any indented block after a blank line is a docutils block quote.
        return _blocks_str(content, indent + "    ", roles)
    if kind == "horizontalRule":
        return indent + "----"
    if kind == "image":
        return _image(node, indent)
    raise ConversionError(f"Unsupported block node {kind!r} for RST export.")


def _image(node: Node, indent: str) -> str:
    attrs = node.get("attrs") or {}
    src = str(attrs.get("src") or "").strip()
    if not src:
        raise ConversionError("Image node has no src.")
    if "\n" in src or "\r" in src or " " in src:
        raise ConversionError("Image src must be a single URL without spaces.")

    def clean(value: object) -> str:
        return " ".join(str(value or "").split())

    lines = [indent + f".. image:: {src}"]
    alt = clean(attrs.get("alt"))
    if alt:
        lines.append(indent + f"   :alt: {alt}")
    title = clean(attrs.get("title"))
    if title:
        lines.append(indent + f"   :title: {title}")
    return "\n".join(lines)


def _heading(node: Node, indent: str, roles: set[str]) -> list[str]:
    attrs = node.get("attrs") or {}
    level = min(max(int(attrs.get("level", 1)), 1), 6)
    # hardBreaks in a heading flatten into the title text (documented in 0017).
    text = "".join(_inline_lines(node.get("content") or [], roles))
    bar_char = _LEVEL_CHARS[level]
    bar = bar_char * max(column_width(text), 1)
    lines = [indent + text, indent + bar]
    if level == 1:
        lines.insert(0, indent + bar)
    return lines


def _code_block(node: Node, indent: str) -> str:
    text = ""
    for child in node.get("content") or []:
        if child.get("type") == "text":
            text += str(child.get("text", ""))
    lang = (node.get("attrs") or {}).get("language")
    code_lines = text.split("\n")
    while code_lines and not code_lines[-1]:
        code_lines.pop()
    while code_lines and not code_lines[0]:
        code_lines.pop(0)
    if not code_lines:
        code_lines = [""]
    common = min(
        (len(line) - len(line.lstrip()) for line in code_lines if line.strip()),
        default=0,
    )
    if common:
        code_lines = [line[common:] for line in code_lines]
    body = textwrap.indent("\n".join(code_lines), indent + "    ")
    head = indent + (f".. code:: {lang}" if lang else "::")
    return f"{head}\n\n{body}"


def _list(node: Node, indent: str, roles: set[str], *, ordered: bool) -> str:
    start = int((node.get("attrs") or {}).get("start", 1) or 1)
    chunks: list[str] = []
    for offset, item in enumerate(node.get("content") or []):
        if item.get("type") != "listItem":
            raise ConversionError(f"Expected listItem, got {item.get('type')!r}.")
        marker = f"{start + offset}. " if ordered else "- "
        pad = " " * len(marker)
        inner = _blocks_str(item.get("content") or [], indent + pad, roles)
        lines = inner.split("\n") if inner else [""]
        first = indent + marker + lines[0].lstrip()
        chunks.append("\n".join([first, *lines[1:]]))
    return "\n\n".join(chunks)


def _scan_heading_skips(blocks: list[Node], last: list[int]) -> None:
    """docutils derives levels from style-introduction order — level skips
    (e.g. h1 → h3) cannot survive reimport, so fail loud (0017)."""
    for block in blocks:
        if block.get("type") == "heading":
            level = int((block.get("attrs") or {}).get("level", 1))
            if level > last[0] + 1:
                raise ConversionError(
                    f"Heading level skip: {level} follows {last[0]}; docutils "
                    "builds levels sequentially (decision 0017 fail-loud)."
                )
            last[0] = level
        for key in ("content",):
            for sub in block.get(key) or []:
                if isinstance(sub, dict) and sub.get("type") in PARAGRAPHISH:
                    _scan_heading_skips([sub], last)
        if block.get("type") in ("bulletList", "orderedList"):
            for item in block.get("content") or []:
                _scan_heading_skips(item.get("content") or [], last)


PARAGRAPHISH = {"paragraph", "blockquote", "bulletList", "orderedList"}


def export_rst(doc: Node, *, base_level: int = 0) -> str:
    """Render a canonical TipTap doc → reStructuredText.

    `base_level` is the heading level the surrounding staging context has
    already introduced (sourcegen prepends the page title as level 1, so a
    body may legitimately start at h2). Standalone exports keep the 0017
    default (0): a first heading above h1 is still a fail-loud skip.
    """
    if doc.get("type") != "doc":
        raise ConversionError("Expected a doc node at the root.")
    roles: set[str] = set()
    last: list[int] = [base_level]
    _scan_heading_skips(doc.get("content") or [], last)
    body = _blocks_str(doc.get("content") or [], "", roles)
    if roles:
        prelude = "\n".join(f".. role:: {role}" for role in _ROLES if role in roles)
        body = f"{prelude}\n\n{body}"
    return body + "\n"
