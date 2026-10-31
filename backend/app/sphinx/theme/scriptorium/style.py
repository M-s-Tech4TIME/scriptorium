"""Scriptorium Pygments highlight style (decision 0028 ②A).

The staged ``conf.py`` wires ``pygments_style =
"scriptorium_style.ScriptoriumStyle"``; Sphinx resolves the dotted form
via ``PygmentsBridge.get_style`` (import module, ``getattr`` class) and
*generates* the artifact's ``pygments.css`` from this class — the token
palette lives here, not in hand-written CSS, per 0028 ②A (builtin-style
duplication rejected).

Color values are ``var(--sd-…, fallback)`` so the consult tokens
(``static/scriptorium.css``) remain the single source of truth; the
literals are the tested fallbacks. Verified against Pygments 2.21:
``var(…)`` tokens parse as valid color values and token groups
inherit down their sub-tokens (all comment/string variants wash over).
``--sd-code-text`` itself is deliberately NOT in this map: unstyled
token classes fall through to the container's text color in our CSS,
so every remaining Pygments class derives from the same four consult
roles (kw verdigris / str brass / com faint italic / fn muted blue).
"""

from __future__ import annotations

from typing import Any, ClassVar

from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    String,
)

_TOKEN_KW = "var(--sd-syn-kw,#4FB39A)"
_TOKEN_STR = "var(--sd-syn-str,#D9B26B)"
_TOKEN_COM = "italic var(--sd-syn-com,#7E9486)"
_TOKEN_FN = "var(--sd-syn-fn,#7FB3E0)"
_TOKEN_ERR = "var(--sd-err,#B5524A)"
_TOKEN_OK = "var(--sd-ok,#6BA87F)"


class ScriptoriumStyle(Style):
    """The four consult roles, applied to the whole token space."""

    background_color = "var(--sd-code-bg,#0F1A15)"
    highlight_color = "var(--sd-surface,#16251E)"  # .hll — never red
    line_number_color = "var(--sd-ink-faint,#7E9486)"
    line_number_background_color = "var(--sd-code-bg,#0F1A15)"

    styles: ClassVar[dict[Any, str]] = {
        Comment: _TOKEN_COM,
        Comment.Preproc: _TOKEN_STR,
        Comment.PreprocFile: _TOKEN_STR,
        Keyword: _TOKEN_KW,
        Keyword.Type: _TOKEN_KW,
        String: _TOKEN_STR,
        Number: _TOKEN_STR,
        Name.Builtin: _TOKEN_FN,
        Name.Function: _TOKEN_FN,
        Name.Class: _TOKEN_FN,
        Name.Exception: _TOKEN_FN,
        Name.Namespace: _TOKEN_FN,
        Name.Decorator: _TOKEN_FN,
        Name.Tag: _TOKEN_KW,
        Name.Attribute: _TOKEN_FN,
        Name.Inserted: _TOKEN_OK,
        Name.Deleted: _TOKEN_ERR,
        Error: _TOKEN_ERR,
        Generic.Heading: _TOKEN_KW,
        Generic.Subheading: _TOKEN_FN,
        Generic.Inserted: _TOKEN_OK,
        Generic.Deleted: _TOKEN_ERR,
        Generic.Error: _TOKEN_ERR,
        Generic.Emph: "italic var(--sd-ink,#E8EFE4)",
        Generic.Strong: "bold var(--sd-ink,#E8EFE4)",
    }
