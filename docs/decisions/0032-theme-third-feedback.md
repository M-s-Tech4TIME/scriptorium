# Decision 0032 — theme, third feedback batch: one search, weight 800, split toggles, scrollspy title, and the h2 staging fix

Status: accepted · 2026-10-23 (owner batch #3 rulings on the preview #4
artifact) · implemented and verified 2026-10-24

Amends: **0027** (engine-asset/search clause), **0028** (§Search DOM
contract), **0031** (search dialog mechanics, inline-code tint, heading
weight, panel toggle placement, scrollspy). The historical text of those
records stays intact; this record is the current contract where they
conflict.

## Why this batch existed

Preview #4 was functionally complete but the owner's third review found
the search *semantics* wrong, not merely its styling: a multi-word query
behaved like an AND filter over single words, the whole typed sentence
was not ranked first, the full search page still rendered the engine's
page-level hit list, and several chrome details still contradicted the
rulings (modal placement, clear control, heading weight, toggle
placement, scrollspy title). One corpus page also exposed a staging bug:
an authored body that starts at `h2` was rejected as a heading-level
skip even though the staging layer had already emitted the page title at
level 1.

## Owner rulings (batch #3)

1. **Search architecture A — first-party, on-demand sectioning.** The
   artifact keeps the engine's build-emitted `searchindex.js` as a fast
   candidate pre-filter only. For a query the first-party core takes the
   OR-union of candidate folios (capped at **10**), retrieves those
   folios same-origin (cached), splits each into heading-delimited
   sections, scores the sections, and renders progressively. There is no
   second build-time index in this tranche; a precomputed section index
   is the documented scale upgrade, deferred until corpus size requires
   it. Zero network; `file://` degrades as disclosed below.
2. **One search, two surfaces.** The dialog and the full search page use
   the same query planner, candidate fetch, section scoring, highlighting
   and `.sd-res-*` decoration: a folio header row (file icon + page
   title), section rows (heading chain, highlighted snippet), and a
   grimoire chip (book icon + grimoire title) on every row. The full
   page is a first-party takeover of `search.html`; the engine's
   `searchtools.js` result rendering is removed from the page (the file
   stays in the vendored asset set per 0027, but no page loads it). A
   `<noscript>` block states that search needs JavaScript. `?q=` is the
   deep link; the full-results link in the dialog carries the typed
   query (`search.html?q=…`), and clearing the full-page field removes
   `?q=` from the URL.
3. **Semantics — the whole sentence first, every word visible.**
   - **Display words**: every typed word, in order, including repeated
     stopwords and numbers; used for the phrase and for highlighting.
   - **Scoring words**: unique content words (stopwords and pure numbers
     removed); if the query is stopwords only, they fall back as scoring
     words so the search still works.
   - **Phrase**: the typed sentence in order, punctuation-blind
     (word-boundary matched); an exact phrase hit adds a dominant
     **+1000** to the section score, so the closest sentence ranks first.
   - **Candidates**: OR-union over every scoring term (exact stem first,
     then a guarded prefix scan both directions for terms ≥3 chars);
     title terms weigh **3×** body terms; the last token is the only
     token allowed to match as a prefix; `-word` exclusions are honored.
   - **Section score**: phrase bonus + distinct-word coverage + capped
     term frequency + heading hits; a section with no scoring-word hit
     is not a row.
   - **Highlight**: every typed word is marked in the snippet (stopwords
     included), whole-word boundaries, last-token prefix-aware.
   - **Rows**: one row per matching heading-delimited section under its
     folio group; the page-title-only section is suppressed when it has
     no body (the group header already names it); structural `index`
     pages are excluded; max **8** folio groups, **6** rows per group.
   - **Snippet**: anchored on the phrase when present, otherwise on the
     longest scoring word; the heading itself is scored once and never
     echoed at the start of the body snippet.
4. **Dialog geometry and dismissal.** The dialog is centred in the
   browser window (horizontal and vertical, including mobile), compact
   until results arrive, then grows vertically to
   `max-height: min(78dvh, 720px)` with an internal scrolling body. It
   closes on Esc, backdrop click, and the new Tabler **x** header button
   (aria-label/title “Close search”). The footer keeps the keyboard bar
   and the full-results link.
5. **Panel clear is clear-only.** The panel search field is
   `type="text"` (the browser's native search clear is removed) with a
   Tabler **x** control that clears the value and refocuses the field;
   it never opens the dialog. The field still opens the dialog on click
   or submit.
6. **Heading weight 800, content only.** Article `h1`–`h6`, the search
   page title, and the general-index title use weight **800**. UI chrome
   (rail, panel, labels, result metadata) stays at its ruled 600; `h6`
   keeps the page ink.
7. **Two physical panel controls.** The **collapse** button lives beside
   the panel search field (panel header). The **expand** button is the
   top-left-most control in the top bar and appears only while the panel
   is off. Both use the ruled Tabler panel glyphs; the stroke keeps the
   chrome ink (no green accent), and hover/active feedback is preserved.
   State still persists per device (`localStorage`).
8. **Scrollspy includes the page title.** The rail's `href="#"` entry
   maps to the article `h1`, so the title is active at the top instead
   of leaving the rail blank. Measurement is direct on the (already
   frame-coalesced) scroll event — no rAF dependency; heading tops are
   recomputed each time; the last heading above the offset wins; at the
   exact bottom of the page the final heading is activated even if its
   section is shorter than the offset.
9. **Inline code deepened one step.** `--sd-code-inline-bg` moves from
   `#EAF1EB` to **`#D8E7DD`**; the ink stays `#2E5C43`. The AA pair is
   re-pinned in `test_theme_contrast.py`.
10. **The grimoire island is explicitly namespaced.** The `#sd-map`
    JSON is `{"books": {slug: {label, title}}}`, not the raw slug map.
    The script normalizes both shapes so an older artifact still renders
    chips; the build test JSON-parses the island.
11. **Link integrity is a build gate.** The theme regression test crawls
    every internal `href`/`src` in every artifact page and fails on a
    missing file, a directory (the dev-server “directory listing”
    symptom), or a path escaping the artifact. This is the permanent
    proof for the batch-#1 404 class, on top of the already-fixed
    `pathto(docname)` root cause (0031).
12. **The h2 staging finding.** `export_rst`/`export_myst` now accept
    `base_level: int = 0`. `sourcegen._page_body` calls them with
    `base_level=1` because it prepends the page title at level 1, so an
    authored body may legally start at `h2`. Standalone exports keep the
    0017 fail-loud default: a first heading above `h1` still raises. A
    body `h3` directly under the generated title still fails loud; a
    body `h2` followed by `h3` is valid and test-pinned.

## Implementation notes

- `static/scriptorium.js`: query planner (`planQuery`), OR-union
  candidates, cached page fetch, section extraction with heading chain,
  phrase-first scoring, all-word highlighting, phrase-anchored snippets,
  progressive render with a per-surface epoch, shared dialog/page
  renderer, centred dialog with Tabler x, clear-only panel field,
  split panel controls, title-aware scrollspy. The test seam
  `window.__sdSearch` exposes the pure core to Node.
- `static/scriptorium.css`: `#D8E7DD` inline token, weight 800 content
  headings, shared `.sd-res-*` surface (paper + chrome variants), centred
  dialog + capped internal scroll, split toggle/clear controls,
  responsive centring.
- `layout.html`: `{"books": …}` island, `sd-i-x` sprite symbol, clear
  button, collapse button beside the search field, expand button first
  in the top bar.
- `search.html`: first-party form + `#search-results`, `?q=` prefill,
  no-JS warning, engine result renderer and `#search-progress` gone.
- `sourcegen.py`: `base_level=1` for staged page bodies; the island
  already carries `book_categories`.
- Tests: Node semantic harness (plan, phrase rank, stopwords, prefix,
  highlights, snippet body); theme-build pins for the
  island, shared search surface, toggles, clear, weights, inline token,
  scrollspy title, and the link crawl; sourcegen test for h2 bodies;
  contrast test for the new inline pair. Suite **80 passed / 36 skipped**
  (`-W error`), ruff + `mypy --strict` clean.
- Preview #5: rebuilt inspection fixture served on `0.0.0.0:8321`;
  headless Chrome verified the query “Inside the furnace the berserker”
  → 7 folios / 12 sections, exact-phrase group first, all words marked
  (including “the”), centred dialog with internal scroll and query-
  carrying full link, clear-only X, split toggles, and scrollspy
  top/deep/bottom (`#` → `#anvil-chorus` → `#cinder-footnote`).

## Disclosures

- Full search on the static artifact requires JavaScript; the no-JS
  block is explicit. The engine index is still built (candidate
  pre-filter), so the artifact remains self-contained.
- `file://` previews cannot fetch sibling pages; results degrade to
  folio/heading links without snippets (same disclosure as 0031).
- Candidate/group/row caps are deliberate: 10 folios, 8 groups, 6 rows
  per group. They bound DOM work and keep the closest-sentence promise;
  a precomputed section index is the scale upgrade, not a semantic
  change.
- `searchtools.js` remains vendored in `_static` (0027 asset contract)
  although no page loads it. Removing it from the asset list would be an
  unapproved 0027 change; it is inert bytes until a later cleanup ruling.

## Amendments to earlier records

- **0027:** the “engine client JS is vendored” rule still holds for the
  asset set; the search *consumer* is now the first-party core. The
  engine's `searchindex.js` and `language_data.js` remain the index and
  language source; `searchtools.js` is retained but unloaded.
- **0028 §Search DOM contract:** the `searchtools.js`-driven search page
  contract is superseded. The page still provides `form` +
  `input[name="q"]` + `#search-results` (for our component and the
  `?q=` deep link), but no `#search-progress`, no engine result markup,
  and no `searchtools.js` tag. `role="main"` remains an accessibility
  landmark, not a search-summary hook.
- **0031:** ruling 2's engine-mirror mechanics and “engine `search.html`
  untouched” fallback are superseded by rulings 1–3 above; ruling 3's
  inline-code bg is superseded by `#D8E7DD`; ruling 4's weight 700 is
  superseded by 800; ruling 8's single top-bar toggle is superseded by
  the split collapse/expand controls; ruling 9's scrollspy is extended
  with the page-title entry and direct measurement.
