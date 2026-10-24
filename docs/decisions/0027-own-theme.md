# 0027 — M4-C3.5: the Scriptorium theme (own, from scratch; full engine inheritance)

- **Status:** accepted
- **Decided:** 2026-10-21 (owner ruled the theme fork after an
  engine-capability education session — Rule 4 education-before-decision —
  and ratified the execution plan in the same session; re-confirmed
  immediately before implementation)
- **Scope:** the M4-C3.5 theme tranche (the curated default theme of
  0026 mandate 2). Serving-phase concerns — per-site brand injection,
  custom-CSS hook wiring, dark-mode presentation policy, URL shapes —
  are **not** in scope here and reuse 0026's phase boundary.
- **Amended 2026-10-23 by 0032** (search consumer): the vendored engine
  asset set is unchanged (`searchtools.js` is still copied per this
  record), but no artifact page loads it after the first-party search
  takeover. The engine's build-emitted `searchindex.js` and
  `language_data.js` remain the index/language source. The search-page
  DOM contract in ruling 4 is superseded by 0032's first-party form.

## Owner ruling

1. **The theme is Scriptorium's own, built from the ground up.** Every
   template and all CSS are written fresh. **No template inheritance
   from any Sphinx builtin theme** (`theme.conf` declares no parent —
   nothing from `basic` leaks in), and **no third-party theme ever**
   (furo / rtd-theme / alabaster-as-final were presented and rejected).
2. **Full engine inheritance and utilization — "each and every single
   thing of it."** The theme uses everything the Sphinx **engine**
   offers: the HTML builder, the cross-reference environment, toctree /
   prev-next / genindex data, client-side search generation and index
   (`searchindex.js`), and Pygments highlighting. What is *not* taken
   from the engine distribution: any of its bundled themes' templates
   or CSS — those are replaced by ours, one for one.
3. **Engine client JS is vendored at build time.** The four engine
   scripts (`searchtools.js`, `doctools.js`, `sphinx_highlight.js`,
   `language_data.js`) are copied from the installed pinned Sphinx into
   each build workspace during materialization — the same trusted
   origin as the compiler itself, never fetched from the network,
   never committed to the repo. Hermetic per Rule 2; consistent with
   0026 mandate 1 (no third-party scripts in artifacts).
4. **DOM contracts are pinned with the engine.** Our templates must
   provide the exact element ids/classes the engine's own JS expects
   (doctools hooks; the search-page renderer contract is superseded by
   0032). The vendored JS version and these contracts are bumped as one
   conscious, CI-tested sync event — search UI sagging under an engine
   bump is not possible silently.

## Mechanics (committed for the C3.5 tranche)

- Theme package: `backend/app/sphinx/theme/scriptorium/` —
  `theme.conf` (no parent), `layout.html`, `page.html`, `search.html`,
  `genindex.html`, `static/scriptorium.css`. All written against the
  builder context (`toctree()`, `prev`/`next`, `pathto()`, `hasdoc()`,
  `project`) with zero supported-from-basic templates.
- `sourcegen.py`: `THEME_BASE = "scriptorium"` and the staged
  `conf.py` gains `html_theme_path = ["theme"]` so every workspace is
  self-contained.
- `runner.py` `_materialize` copies the theme directory into the
  workspace and vendors the four engine JS files from the installed
  pinned Sphinx distribution (they ship inside the engine's own theme
  static dir; copying at build time keeps them build-local and
  uncommitted).
- **Implementation-time lock:** the exact search-page DOM ids/classes
  are read off the vendored `searchtools.js` during implementation and
  recorded in the C3.5 changelog — the designer-facing contract stays
  free, the wire contract is exact.
- **Regression pin:** an offline-but-real pipeline test (tiny mixed
  RST+MyST site through the actual runner) asserts `ok`, our CSS in the
  artifact, the search markup ids present, and `searchindex.js` built.

## v1 scope boundary

- Template surface: `layout.html`, `page.html`, `search.html`,
  `genindex.html` + one stylesheet. Engine-provided machinery
  (`searchindex.js`, Pygments CSS, static copying) inherited as-is.
- **Deferred to the serving phase** (0026 mandate 2 "skin open through
  the platform"): dark-mode presentation policy, per-site brand
  injection (accent/font/wordmark via theme options + CSS custom
  properties), custom-CSS hook wiring. The tokens are structried as CSS
  custom properties now so those hooks land without rework.
- UI specifics (palette, type, layout geometry) come from the owner's
  external design consult; the binding engineering floor for that
  consult was delivered in the owner's brief: no webfonts/CDN, system
  font stacks preferred, WCAG AA, reduced-motion respect, every value
  a token.

## Rejected alternatives (with the owner)

- **Third-party theme (furo / rtd-theme / alabaster-as-final):** less
  template risk, but violates the structure-locked mandate (someone
  else's structure), imports their DOM assumptions, and caps identity —
  rejected.
- **Inherit `basic` in `theme.conf`:** smallest diff, but keeps Sphinx
  templates inside the artifact and blurs "our theme" vs "their engine
  packaging" — the owner explicitly drew the boundary at the engine,
  not the theme; rejected.
- **Reimplement engine pieces (own search indexer/JS):** maximal
  control over JS provenance but rebuilds trusted, engine-tested
  machinery and breaks the inheritance mandate — rejected.

## Micro-defaults (disclosed, owner-vetoable)

- v1 ships a single light color scheme unless the design consult
  supplies a dark pair; the scheme is CSS custom properties either way.
- Vendored engine JS is copied verbatim (no re-minification, no
  fingerprinting); its provenance is the frozen stack's responsibility.
- The theme lives inside the backend package (not frontend static) so
  builds stay self-contained and server-side reproducible.
- Footer carries a plain attribution line ("Compiled by Scriptorium");
  exact wording follows the design consult.

## Status of the earlier placeholder

`alabaster` was a disclosed interim placeholder in C2/C3 `conf.py`
(0026 §C3 mechanics). 0027 supersedes it: `THEME_BASE = "scriptorium"`
from C3.5 onward. The OPEN-QUESTIONS park ("curated default theme
base") is resolved by this record — closed by owner ruling.
