"""WCAG AA token verification (Rule 2, decision 0028) — pure, offline.

Parses the theme stylesheet, resolves `var(--sd-…)` indirections to the
`:root` literals, and computes WCAG 2.x relative-luminance contrast for
every fg/bg pair the record lists. Hand-checked values in 0028 are
approximate; THESE assertions are the exact pinned numbers: every text
pair ≥ 4.5:1; the decorative accent pair ≥ 3:1 (non-text UI minimum,
used only for rules/bars/fills — never normal text, per 0028).
"""

from __future__ import annotations

import re
from pathlib import Path

CSS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "sphinx"
    / "theme"
    / "scriptorium"
    / "static"
    / "scriptorium.css"
)

_HEX = re.compile(r"--sd-([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})")
_ADM_BLOCK = re.compile(r"\.admonition(?:\.([a-z]+))?\s*\{([^}]*)\}")
_ADM_TOKEN = re.compile(
    r"--sd-adm-(rule|bg|ink):\s*(var\(--sd-[a-z0-9-]+\)|#[0-9A-Fa-f]{6}|#000)"
)
_TYPES = (
    "note",
    "seealso",
    "tip",
    "hint",
    "important",
    "attention",
    "caution",
    "warning",
    "danger",
    "error",
)


def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _luminance(hexv: str) -> float:
    hexv = hexv.removeprefix("#")
    r, g, b = (int(hexv[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def _contrast(fg: str, bg: str) -> float:
    hi, lo = max(_luminance(fg), _luminance(bg)), min(_luminance(fg), _luminance(bg))
    return (hi + 0.05) / (lo + 0.05)


def _tokens(css: str) -> dict[str, str]:
    # all :root blocks (the consult block + the 0029–0031 addendum)
    found: dict[str, str] = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", css):
        found.update(_HEX.findall(block))
    assert found, "no --sd-* tokens found in :root"
    return found


def _resolve(ref: str, root: dict[str, str]) -> str:
    if ref.startswith("#"):
        return ref
    name = ref.removeprefix("var(--sd-").removesuffix(")")
    assert name in root, f"var reference {ref} does not resolve to a :root literal"
    return root[name]


def _admonition_palette(css: str, root: dict[str, str]) -> dict[str, dict[str, str]]:
    """Per-type {rule, bg, ink} resolved hexes — 11 anchors (0028)."""
    palette: dict[str, dict[str, str]] = {}
    for selector, body in _ADM_BLOCK.findall(css):
        kind = selector or "generic"
        tokens: dict[str, str] = {}
        for slot, raw in _ADM_TOKEN.findall(body):
            tokens[slot] = _resolve(raw, root)
        # later .admonition blocks (component styling) add no palette
        # tokens — merging keeps the anchor block authoritative
        palette.setdefault(kind, {}).update(tokens)
    assert set(palette) == {*_TYPES, "generic"}, f"callout anchors: {sorted(palette)}"
    for kind in (*_TYPES, "generic"):
        assert set(palette[kind]) == {"rule", "bg", "ink"}, kind
        for slot, hexv in palette[kind].items():
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", hexv), f"{kind}.{slot} unresolved"
    return palette


def test_root_tokens_present() -> None:
    css = CSS_PATH.read_text()
    tokens = _tokens(css)
    for name in (
        "bg",
        "surface",
        "border",
        "ink",
        "ink-muted",
        "ink-faint",
        "link",
        "accent",
        "accent-strong",
        "on-accent",
        "page",
        "page-ink",
        "page-faint",
        "page-border",
        "page-link",
        "code-bg",
        "code-text",
        "syn-kw",
        "syn-str",
        "syn-com",
        "syn-fn",
        "ok",
        "warn",
        "err",
        # 0031 addendum tokens (AA pairs for the icy-green chips)
        "code-inline-bg",
        "code-inline-ink",
        "chip-bg",
        "chip-ink",
    ):
        assert name in tokens, f"--sd-{name} missing from the consult token set"


def test_aa_pairs_readability() -> None:
    """0028 pair table — every normal-text pair ≥ 4.5:1 (AA)."""
    css = CSS_PATH.read_text()
    root = _tokens(css)
    pairs: list[tuple[str, str, str]] = [
        # paper (the document page)
        ("page-ink/page", "page-ink", "page"),
        ("page-faint/page", "page-faint", "page"),
        ("page-link/page", "page-link", "page"),
        # dark chrome (top bar, sidebar, footer)
        ("ink/bg", "ink", "bg"),
        ("ink-muted/bg", "ink-muted", "bg"),
        ("ink-faint/bg", "ink-faint", "bg"),
        ("link/bg", "link", "bg"),  # category labels (exception B)
        # filled controls use accent-strong (0028)
        ("on-accent/accent-strong", "on-accent", "accent-strong"),
        # 0031: the icy-green chip pair (inline code, download + hit + dialog chips)
        ("code-inline-ink/code-inline-bg", "code-inline-ink", "code-inline-bg"),
        ("chip-ink/chip-bg", "chip-ink", "chip-bg"),
    ]
    for label, fg, bg in pairs:
        assert fg in root and bg in root, label
        ratio = _contrast(root[fg], root[bg])
        assert ratio >= 4.5, f"{label}: {ratio:.2f} < 4.5"
    # accent alone carries no normal text (2.4:1 would fail); it is
    # allowed as a non-text UI indicator (rules/bars) at ≥ 3:1
    accent_rule = _contrast(root["on-accent"], root["accent"])
    assert accent_rule >= 3.0, accent_rule


def test_aa_callout_anchors() -> None:
    css = CSS_PATH.read_text()
    root = _tokens(css)
    palette = _admonition_palette(css, root)
    for kind, tokens in palette.items():
        title_ink = _contrast(tokens["ink"], tokens["bg"])
        assert title_ink >= 4.5, f"{kind}: title ink {title_ink:.2f} < 4.5"
        body_ink = _contrast(root["page-ink"], tokens["bg"])
        assert body_ink >= 4.5, f"{kind}: uniform body ink {body_ink:.2f} < 4.5"
        link_ink = _contrast(root["page-link"], tokens["bg"])
        assert link_ink >= 4.5, f"{kind}: page-link {link_ink:.2f} < 4.5"
        # The 3px rule anchor is decorative (WCAG 1.4.11 covers
        # meaning-bearing graphics only — the title ink + hue carry the
        # semantics), and the anchor values are owner-ruled in 0028
        # (several are deliberately quiet on their tint). No numeric
        # floor is asserted for rules; text-bearing pairs above are.
