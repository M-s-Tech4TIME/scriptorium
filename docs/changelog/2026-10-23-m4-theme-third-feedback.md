# Changelog 2026-10-23 — M4 theme third feedback batch (0032)

Batch #3 of the owner's preview rulings, implemented on top of the
unpushed 0029 + 0030 + 0031 stack. The central change is a **single
first-party search** with sentence-aware semantics; the rest are the
ruled chrome corrections and one staging bug found while exercising the
new fixture.

## Search — one mechanism, two surfaces

- **Architecture A:** the engine's build-emitted `searchindex.js` is the
  candidate pre-filter only. The first-party core plans the query,
  OR-unions up to 10 candidate folios, fetches those pages same-origin
  (cached), splits them into heading-delimited sections, scores the
  sections, and renders progressively. A build-time section index is the
  documented scale upgrade, deliberately deferred.
- **Semantics:** every typed word is kept for the phrase and highlight
  (stopwords included); scoring drops stopwords/numbers (with a
  stopword-only fallback); the whole typed sentence is a punctuation-
  blind phrase with a dominant bonus; coverage, capped frequency, and
  heading hits rank below; only the last token may prefix-match; `-word`
  exclusions still work. Every typed word is marked in the snippet.
- **Rows:** folio header row (file icon + title), heading-chain/snippet
  rows, and a grimoire chip (book icon + name) on every row. The page-
  title-only row is suppressed when it has no body; structural `index`
  pages are excluded; 8 groups × 6 rows caps.
- **Full page takeover:** `search.html` now uses the same core and
  `.sd-res-*` decoration, prefilled from `?q=` and keeping the query in
  history; the engine's `searchtools.js` result renderer and
  `#search-progress` are gone; a `<noscript>` block states that search
  needs JavaScript. `searchtools.js` remains in the vendored `_static`
  set (0027) but no page loads it.
- **Dialog:** centred horizontally and vertically, compact until results
  arrive, then grows to `min(78dvh, 720px)` with an internal scrolling
  body; closes on Esc, backdrop, and a new Tabler **x** header button;
  the full-results link carries the typed query.
- **Panel field:** `type="text"` plus a Tabler **x** clear control that
  clears and refocuses without opening the dialog; the native search
  clear (which bubbled into the dialog trigger) is removed.
- **Island contract fixed:** `#sd-map` is `{"books": {slug: {label,
  title}}}`; the script normalizes the legacy raw map so old artifacts
  still render chips.

## Chrome corrections

- **Content headings weight 800** (article h1–h6 + search/genindex h1);
  UI chrome stays 600.
- **Inline-code bg** deepened to `#D8E7DD` (ink unchanged); AA pair
  re-pinned.
- **Panel controls split:** collapse beside the panel search field;
  expand is the top-bar far-left control, visible only while the panel
  is off, chrome-ink stroke unchanged, hover/active preserved.
- **Scrollspy includes the page title** (`href="#"` → article h1),
  measures directly on scroll (no rAF dependency), recomputes tops, and
  activates the final heading at the exact page bottom.

## Fixes found while exercising the corpus

- **Link integrity gate:** the theme build test now crawls every internal
  `href`/`src` in every artifact page and fails on a missing file, a
  directory, or a path escaping the artifact. This is the permanent
  regression proof for the batch-#1 404/directory-listing class; the
  underlying `pathto(docname, 1)` resource-mode bug was fixed in 0031.
- **h2 staging fix:** `export_rst`/`export_myst` gained
  `base_level: int = 0`; `sourcegen._page_body` passes `base_level=1`
  because it prepends the page title at level 1. Authored bodies may now
  start at h2 (and then h3); standalone exports keep the fail-loud
  default, and an h3 directly under the generated title still fails.

## Files touched

- `backend/app/sphinx/theme/scriptorium/static/scriptorium.js` — search
  core v2, shared dialog/page renderer, progressive render, clear-only
  field, split panel controls, title-aware scrollspy.
- `backend/app/sphinx/theme/scriptorium/static/scriptorium.css` — shared
  results surface, centred dialog, inline token, weight 800, split
  controls, responsive centring.
- `backend/app/sphinx/theme/scriptorium/layout.html` — island shape,
  `sd-i-x`, clear/collapse/expand controls.
- `backend/app/sphinx/theme/scriptorium/search.html` — first-party full
  page + no-JS notice.
- `backend/app/sphinx/theme/scriptorium/page.html` — comment updated
  (role=main is a landmark, not a searchtools summary hook).
- `backend/app/sphinx/runner.py` — comment updated; `searchtools.js`
  remains vendored per 0027 but is unloaded.
- `backend/app/conversion/export_rst.py` /
  `export_myst.py` — `base_level` kwarg.
- `backend/app/sphinx/sourcegen.py` — `base_level=1` for staged bodies.
- Tests — `test_theme_search_js.py` (Node semantic harness),
  `test_theme_build.py` (island parse, chrome/search pins, link crawl),
  `test_sourcegen.py` (h2 body staging), `test_theme_contrast.py` (new
  inline pair). Suite **80 passed / 36 skipped** (`-W error`), ruff +
  `mypy --strict` clean.
- Preview #5 rebuilt (inspection fixture) and served on
  `0.0.0.0:8321`.

## Verification (headless Chrome, preview #5)

- Search page query “Inside the furnace the berserker” → 7 folios /
  12 sections; exact-phrase `Construction` group first; all typed words
  marked including “the”; grimoire chips named; `?q=` prefill and clear
  removing the query.
- Dialog on a content page: dx = dy = 0 against the viewport centre;
  body scrolls (1731/537); 7 groups / 12 rows; full link
  `../../search.html?q=…`; close label correct.
- Clear X clears and leaves the dialog closed; collapse/expand restores
  the panel and persists the state; expand stroke is chrome ink
  (`rgb(169, 187, 175)`), not green.
- Scrollspy: top `#`, deep `#anvil-chorus`, bottom `#cinder-footnote`.
- Inline code computed `rgb(216, 231, 221)` on `rgb(46, 92, 67)`;
  h1/h2 computed weight 800.

## Records

- `docs/decisions/0032-theme-third-feedback.md` (this batch + the h2
  finding + amendments).
- `docs/decisions/0027-own-theme.md` — search-consumer amendment.
- `docs/decisions/0028-theme-design-baseline.md` — search DOM contract
  superseded.
- `docs/decisions/0031-theme-second-feedback.md` — inline/search/weight/
  toggle/scrollspy amendments.
- `docs/technology/sphinx.md` — current search contract + staging fix.
- Brain synced (`CURRENT-STATE`, `HANDOFF`, `TASKS`,
  `DECISIONS-INDEX`, `OPEN-QUESTIONS` unchanged except the index).

## Not in this tranche

- Build-time section index (scale upgrade; owner-approved deferral).
- Removing `searchtools.js` from the vendored asset list (would reopen
  0027; it is inert).
- M4-C4 packaging, serving-phase hooks, dark-mode policy.
