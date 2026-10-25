"""Custom-CSS sandbox for published artifacts (decision 0035 E2).

The owner may skin a published site through the platform, never by editing
generated files. Custom CSS is therefore an *input* that must be constrained:

- **Namespaced:** every selector is rewritten under
  ``html[data-sd-athenaeum]`` so the stylesheet can only affect the
  published artifact that carries the marker. ``:root``/``html`` become the
  marked root; ``body``/classes become descendants.
- **No network:** ``url()``, ``image-set()``, ``data:``, ``@import`` and
  every other at-rule are rejected. This prevents remote images/fonts,
  tracking pixels, and CSS-based exfiltration.
- **No script-ish CSS:** ``expression()``, ``behavior`` and
  ``-moz-binding`` are rejected; custom JavaScript is never accepted.
- **No overlay escape hatch:** ``position: fixed`` is rejected because a
  scoped rule could otherwise cover the whole page.
- **Bounded:** 64 KiB of UTF-8, flat rules only (no nesting/at-rules), no
  backslash escapes (the classic ``u\\72l()`` obfuscation route).

The validator is deliberately conservative. It returns normalized CSS; the
build writes that normalized form into the immutable artifact.
"""

from __future__ import annotations

import hashlib
import re

MAX_CUSTOM_CSS_BYTES = 64 * 1024

_SCOPE = "html[data-sd-athenaeum]"

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_FIXED_RE = re.compile(r"position\s*:\s*fixed\b", re.IGNORECASE)

# Tokens that can fetch a resource, run legacy script, or escape the
# stylesheet context. The checks run on comment-stripped, lower-cased text.
_FORBIDDEN_TOKENS = (
    "url",
    "image(",
    "image-set",
    "cross-fade",
    "element(",
    "paint(",
    "expression",
    "javascript:",
    "vbscript:",
    "data:",
    "behavior:",
    "-moz-binding",
    "binding:",
    "@",
    "\\",
    "<",
)


class CustomCssError(ValueError):
    """The submitted custom CSS is outside the E2 sandbox."""


def _split_selectors(selector_text: str) -> list[str]:
    """Split a selector list on top-level commas (parentheses/brackets aware)."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    start = 0
    for index, char in enumerate(selector_text):
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
            if depth < 0:
                raise CustomCssError("Unbalanced selector parentheses.")
        elif char == "," and depth == 0:
            parts.append(selector_text[start:index].strip())
            start = index + 1
    if quote is not None or depth != 0:
        raise CustomCssError("Unbalanced selector quote/parenthesis.")
    parts.append(selector_text[start:].strip())
    if any(not part for part in parts):
        raise CustomCssError("Empty selector in selector list.")
    return parts


def _prefix_selector(selector: str) -> str:
    """Rewrite one selector under the published-site namespace."""
    cleaned = " ".join(selector.split())
    if not cleaned:
        raise CustomCssError("Empty selector.")
    if cleaned.startswith(_SCOPE):
        return cleaned
    if cleaned == ":root":
        return _SCOPE
    if cleaned.startswith(":root"):
        # :root.foo / :root > body — the root itself, then the remainder.
        return _SCOPE + cleaned[len(":root") :]
    if cleaned == "html":
        return _SCOPE
    if cleaned.startswith("html") and (len(cleaned) == 4 or cleaned[4] in " .[>+~:#"):
        return _SCOPE + cleaned[4:]
    return f"{_SCOPE} {cleaned}"


def sanitize_custom_css(raw: str) -> str:
    """Validate and normalize owner custom CSS; raise CustomCssError on refusal."""
    if not raw.strip():
        return ""
    if "\x00" in raw:
        raise CustomCssError("NUL bytes are not allowed in custom CSS.")
    try:
        encoded = raw.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CustomCssError("Custom CSS must be valid UTF-8.") from exc
    if len(encoded) > MAX_CUSTOM_CSS_BYTES:
        raise CustomCssError(
            f"Custom CSS is too large ({len(encoded)} bytes; "
            f"max {MAX_CUSTOM_CSS_BYTES})."
        )

    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _COMMENT_RE.sub("", text)
    if "/*" in text:
        raise CustomCssError("Unterminated CSS comment.")

    lowered = text.lower()
    for token in _FORBIDDEN_TOKENS:
        if token in lowered:
            raise CustomCssError(f"Custom CSS may not contain {token!r}.")
    if _FIXED_RE.search(text):
        raise CustomCssError("Custom CSS may not use position: fixed.")

    rules: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        if text[index] == "}":
            raise CustomCssError("Unexpected closing brace.")
        brace = text.find("{", index)
        if brace < 0:
            raise CustomCssError("Trailing text outside a CSS rule.")
        selector_text = text[index:brace].strip()
        if not selector_text:
            raise CustomCssError("CSS rule has no selector.")
        if "}" in selector_text:
            raise CustomCssError("Unexpected closing brace in selector.")
        close = text.find("}", brace + 1)
        if close < 0:
            raise CustomCssError("Unterminated CSS rule.")
        body = text[brace + 1 : close]
        if "{" in body:
            raise CustomCssError("Nested CSS rules are not supported.")
        if "}" in body:
            raise CustomCssError("Unexpected closing brace in declarations.")
        if not body.strip():
            raise CustomCssError("CSS rule has an empty declaration block.")
        if ":" not in body:
            raise CustomCssError("CSS rule has no declarations.")
        selectors = _split_selectors(selector_text)
        prefixed = ", ".join(_prefix_selector(part) for part in selectors)
        rules.append(f"{prefixed} {{{body.strip()}}}")
        index = close + 1

    if not rules:
        raise CustomCssError("Custom CSS contains no rules.")

    header = (
        "/* Scriptorium custom CSS — published artifact only (0035 E2).\n"
        "   Namespaced under html[data-sd-athenaeum]; no URL/import/JS. */"
    )
    normalized = header + "\n" + "\n".join(rules) + "\n"
    if len(normalized.encode("utf-8")) > MAX_CUSTOM_CSS_BYTES:
        raise CustomCssError("Normalized custom CSS exceeds the 64 KiB sandbox limit.")
    return normalized


def custom_css_sha256(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
