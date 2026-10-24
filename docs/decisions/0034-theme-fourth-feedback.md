# Decision 0034 — theme, fourth feedback batch: panel placeholder, code-language label, pager column, no-flash panel state

Status: accepted · 2026-10-24 · Owner: alsechemist (feedback delivered
after approving the preview #5 baseline `b15446f`; preview #6 approved,
with one follow-up flash bug reported and fixed; preview #7 verified)

## Context

The owner approved preview #5 as the best Scriptorium UI so far and asked
for three targeted corrections, plus the project-wide Standing Rule 8
(recorded separately as decision 0033). Preview #6 implemented those
three and the owner approved them, but the review exposed one additional
behavior bug: with the sidebar collapsed, clicking the Previous/Next
pager made the panel flash expanded for one frame before collapsing
again. This batch is the first change executed under Rule 8: it verifies
the previously approved search, dialog, clear control, panel toggles,
scrollspy, weights, and inline-code behavior in addition to the fixes.

## Rulings

1. **Panel placeholder only.** The sidebar panel field's placeholder is
   the single word **“Search”**. The dialog keeps its descriptive
   **“Search the library”** placeholder; the full search page has no
   placeholder and is unchanged. The panel's `aria-label` remains
   “Search the library” for screen readers.
2. **Code-block language name.** The header must show the programming
   language next to the `</>` icon. Root cause: the Pygments lexer class
   lives on the **outer** `div.highlight-<lang>` wrapper, while the
   script ran on the inner `div.highlight`; `closest("[class*=highlight]")`
   matched the inner block itself, so the `highlight-<lang>` regex never
   saw the language and returned an empty label. The fix searches
   ancestors for `highlight-*`, parses the alias, and maps it to the
   friendly name. Blocks with no language or the Pygments `default`
   alias show **“Code”**; unknown aliases fall back to a title-cased
   label.
3. **Pager stays in the article column.** The Previous/Next pager must
   not run under the On-This-Page rail. Root cause: `.sd-pager` was a
   sibling of `.sd-reading`, so it spanned the full paper width and
   `margin-left: auto` pushed Next to the far right. The article and
   pager now share a `.sd-reading-main` first grid column; the rail
   remains the second column. Next ends at the article's right edge,
   never at the rail.
4. **Collapsed panel must stay collapsed through navigation.** With the
   sidebar collapsed, clicking Previous/Next must not paint the panel
   expanded for a frame. Root cause: the persisted `sd-panel-open` state
   was read by `scriptorium.js` at the end of `<body>`, after the browser
   had already painted the default expanded shell; the body script then
   collapsed it. The fix reads the stored state in a tiny inline `<head>`
   script and marks `<html>` with `sd-panel-pending-off` before the shell
   exists. CSS applies the collapsed grid/sidebar/expand state from that
   marker; the body script then swaps in the normal `.sd-panel-off` shell
   class and removes the marker. The first paint is collapsed; normal
   toggle animation and persistence are unchanged.
5. **Rule 8 applies.** The fixes are additive; the approved search
   mechanism, dialog geometry, clear-only control, panel state, and
   scrollspy behavior must remain intact. Any unavoidable behavior change
   would have required a separate owner ruling (none was needed).

## Implementation

- `layout.html`: panel `placeholder="Search"`; dialog untouched; inline
  `<head>` script applies the persisted collapsed marker before first
  paint.
- `scriptorium.js`: `languageFromClass()` pure helper; `languageName()`
  resolves the outer `highlight-*` ancestor; `default`/`none`/`text` and
  missing language → `Code`; the helper is exposed on the existing
  `window.__sdSearch` test seam for the Node test. `wirePanelToggle()`
  removes the pre-paint marker after applying `.sd-panel-off`.
- `page.html`: `.sd-reading-main` wraps the article + pager; the rail is
  its sibling.
- `scriptorium.css`: `.sd-reading-main { min-width: 0; }` so the first
  grid column cannot overflow; combined `html.sd-panel-pending-off` /
  `.sd-shell.sd-panel-off` rules make the pre-JS paint collapsed, with
  no transition on the marker path.
- Tests: Node assertions for Python/JavaScript/Bash/Code/no-class;
  theme-build pins for the panel placeholder, dialog placeholder, pager
  ancestry (`_PagerPlacement` HTML parser), the `.sd-reading-main` rule,
  the pre-paint marker before the shell, and the CSS/JS marker contract.
- Records: this decision, changelog, 0029 code-chrome correction,
  `docs/technology/sphinx.md` note, brain sync.

## Verification (preview #7)

- Artifact code headers (headless Chrome): Bash, JavaScript, Python next
  to the icon; no empty labels.
- Pager geometry at 1400×900: article right **1069**, Next right
  **1069**, rail left **1101**; Next is inside the article and clear of
  the rail. At 1000×800 and 800×900 the rail is hidden and Next still
  ends at the article edge; no horizontal overflow.
- Placeholders: panel **“Search”**, dialog **“Search the library”**.
- No-flash state (headless Chrome, stored `closed`): the first body
  script sees `html.sd-panel-pending-off` **before the shell exists**
  (`shellExists=false`); the final shell is `.sd-panel-off`, the marker
  is removed, the sidebar width is 0, and the expand control is visible.
  Stored `open` paints expanded with no marker. Toggle still persists
  `closed`/`open` and switches the shell state correctly.
- Regression smoke: search sentence → **7 folios / 12 sections**,
  exact-phrase group first, 88 marks; dialog `dx=0, dy=0`, 7 groups /
  12 rows, internal scroll, full link carries `?q=`; Escape closes;
  clear-only leaves the value empty and the dialog closed; collapse/
  expand and scrollspy (`#` → `#anvil-chorus` → `#cinder-footnote`) are
  unchanged.
- Gates: Node + theme-build tests pass; full suite **80 passed / 36
  skipped** (`pytest -W error`), ruff + `mypy --strict` clean.

## Disclosures

- Panel-only placeholder is the owner's explicit choice; the dialog's
  longer placeholder is intentionally retained.
- The pager wrapper changes DOM nesting only; no search or scrollspy
  selectors depend on the pager.
- `languageFromClass()` is a test-only seam (same pattern as the search
  core); production reads only the DOM.

## Status

Preview #6 was approved by the owner; preview #7 adds the no-flash panel
state fix and is browser-verified. This record, the changelog, and the
0034 code/tests are committed together with the already-committed Rule 8
docs (`cbe2b22`), then pushed and CI-verified green ×3.
