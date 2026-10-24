# Changelog 2026-10-23 — M4 theme second feedback batch (0029 pass + 0030 fonts + 0031)

## What landed in the theme this round

Batch #2 of the owner's preview rulings, applied on top of the
already-verified 0029 code pass and 0030 typography:

- **Fluid reading width** — `--sd-col-wide` deleted; the article fills
  the paper area (search page, general index, pager, credit decapped
  with it) at any viewport.
- **Search dialog, RTD-style, every page** — panel field or `Ctrl+K`
  opens a dark-chrome dialog over the engine's build-emitted index;
  hits grouped by folio with matched-heading rows + highlighted
  snippets and a grimoire chip on each row's bottom; ↑/↓/Enter/Esc
  keyboard bar; engine `search.html` untouched as fallback. On plain
  `file://` previews snippets degrade to links (disclosed).
- **Inline code + download chips** — icy-green chip pair
  (`--sd-code-inline-*` / `--sd-chip-*`, the AA-tested tip family);
  download references render as green pills with the Tabler download
  glyph (CSS-mask data URI; not in the sprite).
- **Weight-700 headings** across article + engine index pages; h6
  inherits the page ink.
- **Danger re-tints to wine/plum** (`#6E2142` rule, `#F5E9F0` bg,
  `#5C1B36` ink) with the skull glyph; error keeps vermilion.
- **Sticky, collapsible panel** — sidebar sticks with the article
  (`100dvh`), one top-bar toggle swaps the two `layout-sidebar`
  glyph states and persists per device; hidden <900px.
- **Panel semantics** — grimoire rows open the FIRST content-bearing
  folio (never a bare master); staged toctrees go `:hidden:`; the site
  index keeps its visible toctree; chapters render their own content
  (chapters are folios — hierarchy is panel placement).
- **Scrollspy rewrite** — the last heading above the offset stays
  active; click highlights immediately; `IntersectionObserver` gone.
- **Copy button confirms** — icon flips copy→check for ~1.6 s.
- **CI finding (transportation bug) fixed**: sidebar links lost their
  `.html` suffix because `pathto(docname, 1)` means *resource mode* in
  engine 9.1 — the same underlying cause of the preview's "clicking a
  chapter takes me to a page like this" complaint. Now
  `pathto(docname)` (document form), pinned by tests.

## Files touched

- `backend/app/sphinx/theme/scriptorium/layout.html` — sprite 21
  symbols, panel toggle, container macro.
- `backend/app/sphinx/theme/scriptorium/static/scriptorium.css` /
  `scriptorium.js` — full 0031 tranche as above.
- `backend/app/sphinx/sourcegen.py` — hidden toctrees, first-leaf book
  rows, `"container": True`.
- Tests — sidebar rows, hidden-toctree pins (rst + myst), theme-build
  physiology (toggle/glyphs/hrefs/master-page), contrast `_tokens`
  findall-merge + chip pairs. Suite **78 passed / 36 skipped**
  (`-W error`), ruff + `mypy --strict` clean.
- Fixture preview rebuilt (inspection library, + one deeper fourth-rung
  page + console code block) on `0.0.0.0:8321` as preview #4.

## Records

- `docs/decisions/0031-theme-second-feedback.md` (owner rulings +
  CI finding + editor platform facts). Q-EDITOR-1 opened in
  OPEN-QUESTIONS for the editor-phase language-suggestion combobox.
