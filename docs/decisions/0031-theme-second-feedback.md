# Decision 0031 — theme, second feedback batch: fluid width, search dialog, chips, danger, panel & scrollspy

Status: accepted · 2026-10-23 · Owner: alsechemist (batch #2 rulings delivered
in review chat of the M4-C3.5 preview #3 artifact)

**Amended 2026-10-23/24 by decision 0032** (batch #3): the search
dialog/page mechanics below are superseded by the first-party unified
search (on-demand sectioning, phrase-first ranking, all-word highlight,
full-page takeover); the inline-code bg is now `#D8E7DD` (was
`#EAF1EB`); content headings are weight 800 (was 700); the single
top-bar panel toggle is split into a collapse control beside the search
field and an expand control at the top-bar far left; the scrollspy also
includes the page-title entry and measures directly on scroll. The
history below is preserved; 0032 is the current contract.

## Rulings (all batch #2, owner-confirmed)

1. **Fluid reading width** — the article fills the paper area to the rail
   with a small gap at ANY viewport. The `--sd-col-wide` cap is removed
   entirely (search page, general index, pager and credit keep the same
   decap). Long measure at ultrawide is readaidability cost the owner
   accepts for the "space is there, use it" call — disclosed here.
2. **Search dialog, RTD-style on every page** (superseded by 0032:
   `search.html` is now the first-party full page; the engine renderer
   is retired; the mechanics below describe the batch-#2 implementation
   only):
   - field + bottom-of-screen placement as a floating dark-chrome
     surface; opens from the panel search field (click or submit),
     from anywhere via `Ctrl+K` / `⌘+K`;
   - results **grouped by folio**: a scope header row per folio
     (icon + page title), then per-row items — the matched heading and a
     highlighted snippet — each row's bottom reference is a
     **grimoire chip** (book icon + grimoire title, icy-green pill) so
     items are distinguishable across grimoires;
   - keyboard bar in the footer: ↑/↓ to move, Enter to select,
     `esc` to close; a link to the full engine results page rides along;
   - mechanics: one script still — the dialog loads ONLY the engine's
     build-emitted `language_data.js` (self-contained: stopwords + English
     stemmer; note `splitQuery` lives in searchtools.js in 9.1 → the
     dialog splits with the engine's own default word class inlined) and
     `searchindex.js`, captured with a `Search.setIndex` shim (the real
     `Search` object is never clobbered and searchtools.js stays unloaded
     on document pages). Scoring mirrors the engine: title-term exact
     (weighted) > term exact > partial (word length > 2), AND-semantics
     for multi-word queries, `-` exclusion honored. Snippets/deep anchors
     resolve by same-origin page retrieval (cached); on a plain `file://`
     preview they degrade to folio/heading links without snippets
     (disclosed).
3. **Inline code + download chips** — inline ``code`` renders as the
   icy-green chip pair (bg `#EAF1EB` → **0032: `#D8E7DD`**, ink
   `#2E5C43` — the AA-tested tip
   family; tokens `--sd-code-inline-bg/ink`), borderless. Download
   references (the engine's `a.reference.download`) render as a green
   pill with the Tabler download glyph (CSS mask; the glyph is a data
   URI, NOT in the sprite). Same getters for the dialog/hit grimoire
   chips (`--sd-chip-bg/ink`).
4. **Headings carry weight 700** — all article h1–h6 + search/general
   index h1; h6 keeps the page ink (no more grey runt). **0032 raised
   this to 800.**
5. **Danger ≠ error** — danger re-tints to the wine/plum family (rule
   `#6E2142`, bg `#F5E9F0`, ink `#5C1B36`) and takes the **skull**
   glyph (CSS-mask data URI, out of the sprite); error keeps vermilion.
6. **Book rows open the beginning** — in the panel, a grimoire row
   points at its first content-bearing folio in tree order (contentless
   containers are transparent); the master stays reachable only via the
   landing's visible site toctree + pager, and the panel tree becomes
   the *only* semantics-bearing location of hierarchy. Sidebar rows now
   carry a `"container": True` flag (never marked current), staged
   toctrees go `:hidden:` (engine required, rendering hidden), and the
   site index keeps its visible toctree (disclosed: the landing lists
   grimoires explicitly).
7. **Chapters are folios** — every chapter renders its own content
   page; hierarchy is *panel placement* only. Staging keeps the builder
   paragraph per container page (publishing will hold authored chapter
   bodies; same content clause as grimoire masters).
8. **Sticky, collapsible panel** — the sidebar sticks with the article
   (sticky top-0, `100dvh`, internal scroll); one top-bar toggle
   (Tabler `layout-sidebar-left-collapse`/`…-expand` glyphs, owner's
   two-glyph image) animates the grid column away and persists per
   device (`localStorage` `sd-panel-open`; private-mode degrade
   disclosed); the toggle hides <900px where the drawer owns mobile.
   **0032 split this into two controls:** collapse beside the panel
   search field, expand at the top-bar far left.
9. **Scrollspy rewrite (On-This-Page)** — the LAST heading above the
   viewport offset stays active while its section is being read (None →
   first instead of jumping to the section's END); rAF-scheduled, click
   sets active immediately, `IntersectionObserver` removed (letterboxed
   anchor accuracy). The rail itself unchanged. **0032 adds the
   page-title entry, measures directly on scroll (no rAF), and
   activates the final heading at the exact page bottom.**
10. **Copy button confirms with the check** — icon swaps copy→check for
    ~1.6 s on success (both sprites present), then reverts.

## Effects

- `static/scriptorium.css`: `--sd-col-wide` deleted; sticky/off panel
  states + toggle button; fluid `article/searchpage/genindex/pager/
  credit`; weights; inline-code + chip tokens; download pill;
  wine danger + skull mask; hit chip styles; full dialog surface
  (backdrop, panel, rows, items, marks, chip, footer, count/state,
  `body.sd-dlg-lock` scroll lock); mobile sweep (360–2560) unchanged
  where owned by old rules, touch-sized drawer label at 900.
- `static/scriptorium.js`: full rewrite per the record — copy-check,
  panel toggle + persistence, scrollspy rewrite, engine-page hit
  decoration trimmed to chip + heading chain (page title dropped — the
  engine's title link already carries it), and the search dialog
  (index loader, engine rule mirror, item/snippet resolve, render,
  keyboard, triggers).
- `layout.html`: sprite 17 → 21 symbols (+ `sd-i-skull`, `sd-i-check`,
  the two `sd-i-panel-*` glyphs), panel toggle button, "Contents" label
  retained, boot comment updated.
- `sourcegen.py`: `_toctree(..., hidden)`, `_first_reading_docname`,
  book rows first-leaf + `"container": True`, masters/child trees
  `:hidden:`, site index still visible.
- **CI finding fixed in passing**: `pathto(docname, 1)` was
  *resource-mode* in engine 9.1 (the second positional is `resource`,
  not a relative flag) and silently emitted suffix-less sidebar links
  — this was the "why does clicking a chapter take me to a page like
  this" complaint's real transportation bug. Sidebar linking now uses
  `pathto(docname)` (document suffix form) and is pinned by tests.
- Tests: sidebar rows (first-leaf + container flag), hidden-toctree
  pins (rst + myst), theme-build physiology (toggle, glyphs, sidebar
  href, master page renders no list), contrast `_tokens` merges ALL
  `:root` blocks and pins the chip pairs. Suite: **78 passed / 36
  skipped**, `-W error`, ruff + `mypy --strict` clean.
- `NOTICE`: no change (Tabler subset sentence covers the new glyphs).
- Editor platform facts recorded, not themed (batch #2 observations):
  folio display names are independent of the page title (the artifact
  always shows build-time titles); the code-block language label is a
  user-defined field with suggestions — research parked as Q-EDITOR-1.

## Editor platform facts (for the record)

- The code-block language suggestion set (research parked as Q-EDITOR-1,
  recommendation: an accessible combobox seeded from the vendored
  Pygments lexer names — display label + lexer alias stored separately)
  belongs to the EDITOR phase, not the theme.
