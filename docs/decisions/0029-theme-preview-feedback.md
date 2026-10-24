# Decision 0029 — C3.5 preview-feedback rulings (theme second pass)

Status: accepted · 2026-10-22 · Owner: alsechemist (preview feedback on the
M4-C3.5 browser artifact /tmp/opencode/theme-preview/out — all seven items
ruled in chat, confirmed "all approved as you recommended", amended with the
search spec the same day). **Amended 2026-10-23 by decision 0031** (second
feedback batch): the search-hit scope line is replaced by the grimoire
chip (0031 ②), the reading width is decapped (0031 ①), search dialogs land
(0031 ②) — see 0031 for the batch and keep this record for the base
pass' mechanisms. **Further amended by 0032:** the engine search
renderer (and therefore this record's hit-decoration mechanism) is
retired in favour of the first-party search; the other base-pass
rulings (anchors, code chrome, pager, footer/credit, reading layout)
stand.

## Rulings

1. **Header anchors:** the engine-emitted "¶" is replaced by a hyperlink
   icon on EVERY heading level (h1–h6, all hierarchy). Quiet-until-hover
   stays (owner accepted the recommended default; the reference showed the
   hover state). Icon = the pinned Tabler v3.36.0 "link" glyph, rendered
   as a `currentColor` CSS mask data-URI (same mechanism as the admonition
   icons); the ¶ text is hidden with a zero font-size, keeping the anchor
   functional; link purpose is given by the adjacent heading text (WCAG
   2.5.3 satisfied by context). **Icons stay Tabler** — the owner was told
   we already vendor Tabler and then ruled "Tabler it is"; a Lucide switch
   was declined. Sprite grew by one symbol: `code` (17 total).
2. **Search results (full spec):** every hit shows (a) the scope line
   **Category › Grimoire**, (b) the **heading/sub-heading chain** the
   match sits under, and (c) a **themed match with the matched words
   wrapped** (the image shows Read-the-Docs-like structured results).
   Mechanism (disclosed): (c) is **engine-native** — the vendored
   `searchtools.js` already retrieves the hit page from the artifact
   itself (same-origin, no network) and renders its `p.context`
   summary, over which `sphinx_highlight.js` wraps the query terms in
   `span.highlighted`, themed by the `.highlighted` token: the
   highlight deliverable is the engine's, not ours. The script adds
   (a)+(b): an `application/json` data island (`#sd-map`,
   blanket-page context, materialized by sourcegen) maps book slug →
   {label, title}; at query time the one first-party script reads the
   hit page the same way (same-origin fetch, cached per page, ids
   untouched), extracts the anchor's ancestor section chain, and
   stamps the engine's result rows (top 8) with the scope line and the
   `Page › Heading › Sub-heading` trail. On a plain file:// preview
   browsers block that retrieval → the scope line still renders
   (island), chain/summary degrade silently (the engine's summary
   fails the same way — mechanism symmetric with the engine it rides
   on). Engine contracts untouched.
3. **Code blocks:** header bar on every block — code icon + language name
   (from the engine's `highlight-<lang>` class; no language → icon only)
   and the copy button ALWAYS visible in the bar (the hover-only button
   was a C3.5 bug: the button was positioned inside a non-positioning
   parent — replaced by the header design). The code pane scrolls
   (`overflow: auto`, max-height 30rem). Language names mapped
   (`python→Python`, `javascript→JavaScript`, …, fallback title-cased).
   **0034 correction:** the label now reads the outer
   `div.highlight-<lang>` wrapper (the old inner-block lookup returned an
   empty string on every block); no-language/`default` blocks show
   `Code` instead of icon-only.
4. **Pager:** filled `--sd-accent-strong` green buttons (the ruled
   filled-control token), labels exactly **Previous / Next** (page titles
   removed); hover = lift + larger shadow (+ icon scale), active =
   press-down scale. AA: `on-accent` over `accent-strong` is the pinned
   ≥4.5 pair; the fill does NOT change on hover so the text pair stays.
5. **Footer bar removed** from layout. `Index` sits centered just below
   the sidebar search form (`.sd-side-links`); the `Search` link is gone
   (the sidebar form serves). The credit is an end-of-content block on
   EVERY page (Zeek-style, after the pager/topbar trail):
   "© Copyright by <holder>. Last updated on <date>." / "Compiled by
   Scriptorium." on the next line.
   - **Holder = the librarian's display name** (`users.display` via the
     Athenaeum's owner; loader fetches it → site_credit), owner-confirmed
     recommendation. Empty credit degrades to the platform line only.
   - **Last updated = engine `last_updated`** via conf
     `html_last_updated_fmt = "%B %d, %Y"` (format_date at build time).
     Owner-approved as "per-page last-updated"; engine fact: it is a
     build-time date — in Scriptorium's staging every build rewrites all
     sources fresh, so per-page mtime and build date are the same value;
   both approved options collapse to "date of this artifact".
6. **Reading layout:** article shifts to the left edge of the paper area
   and takes most of its width (`--sd-col-wide: 896px` — the consult's
   740px `--sd-col` is retained as a token but the reading column is
   wide now), plus a sticky **"On This Page" rail** (`--sd-toc-rail:
   252px`) rendering the engine's local `{{ toc }}` — authored heading
   hierarchy preserved — with a first-party scrollspy highlighting the
   section in view. Rail hides under 1200px (article then owns the
   full width).
7. **Inspection fixture:** the second preview is a hand-crafted demo
   workspace showing all 11 callout types, all heading levels h1–h6 with
   a nested chapter › sub-chapter › folio sidebar depth, and the full
   Sphinx/MyST link inventory (internal page refs, labeled/section refs,
   numbered refs, external URL, email, download, anonymous/term refs,
   MyST variants). It is an INSPECTION FIXTURE (handcrafted staged
   sources in /tmp, not committed, not the export path): the M2 pipeline
   still cannot emit callouts from TipTap today — styles stay idle per
   the fail-loud corpus discipline; if real books need callouts, that is
   a TipTap-schema ruling for the serving phase.

## Script responsibilities (0027 amendment ledger)

`scriptorium.js` (one file, disclosed, zero deps, zero network): ①
code-block chrome + copy, ② search-result decoration (scope line from
the island; heading chain via the same same-origin retrieval the
vendored engine itself performs — the themed match stays engine-native),
③ toc scrollspy, ④ nothing else. Engine assets/contracts untouched;
every decoration ADDS nodes to engine output.

## Effects

- `layout.html`: footer removed; `.sd-side-links` Index; `#sd-map` island; credit block; `code` sprite symbol.
- `page.html`: `.sd-reading` grid + `.sd-toc` rail + green pager.
- `scriptorium.css`: 0029 extensions (anchors, chrome, pager, credit,
  rail, hit styles); two `:root` blocks — the consult `:root` stays
  verbatim, the addendum block carries the two new layout tokens.
- `scriptorium.js` rewritten to the four responsibilities above.
- `sourcegen`: conf gains `html_last_updated_fmt`, context gains
  `book_categories` (slug → {label, title}) + `site_credit`.
- `loader`: returns the librarian's display name; `execute` passes it.
- Tests: artifact physiology asserts updated (footer absence, side
  links, island, credit, reading grid, rail, exact pager labels,
  last-updated line) + sourcegen island/credit asserts (+1 test).
