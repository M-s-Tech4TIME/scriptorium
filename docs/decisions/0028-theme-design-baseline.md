# 0028 — M4-C3.5 design baseline: consult tokens, icons, callout palette, syntax style, copy button

- **Status:** accepted
- **Decided:** 2026-10-22 (owner approved the full Rule-4 decision sheet
  in conversation — ①A ②A ③B ⑤, ⑥1–⑥3 — plus two ruled exceptions
  (below), then confirmed the finalized exception specs and the
  uniform body-ink rule); **amended the same day by decision 0029**
  (`0029-theme-preview-feedback.md`): preview-feedback rulings —
  header anchors swap to a hyperlink icon, search-result decoration,
  code-block chrome, green Previous/Next pager, footer-bar removal +
  per-page credit, wide reading layout + On-This-Page rail. 0029
  elaborates these rulings and supersedes ONLY the 740px article
  measure (wide `--sd-col-wide` reading column); the token system,
  palette, icon set (Tabler, + the `code` symbol), copy-script clause
  and AA floor all stand as ruled here. **Amended 2026-10-23 by 0032**:
  the `searchtools.js`-driven search-page contract below is superseded
  by the first-party full-search takeover; `searchtools.js` remains
  vendored per 0027 but no page loads it. The 0032 record is the current
  search contract.
- **Scope:** the M4-C3.5 implementation mechanics of the theme
  (0027)*—*the design layer. Serving-phase concerns (brand injection,
  custom-CSS wiring, dark-scheme policy) remain out of scope per 0026
  mandate 2 / 0027.
- **Protocol:** nothing fell back silently to brief defaults — every
  consult gap and every open point was surfaced to the owner before
  any default was used (the owner's standing rule: consult before
  falling back, never self-answer).

## Owner rulings (the decision sheet, as approved)

1. **①A — Icons: Tabler inline-SVG subset, vendored as an inline
   sprite.** Feather-subset and hand-drawn sets were presented and
   rejected (catalog per type-callout variety / originality cost).
   Zero-network rule is met by construction: icons are `<symbol>` sprite
   markup inlined in `layout.html` and referenced with `<use>` — no
   CDN, no icon font, no webfont. Tabler is MIT; at implementation the
   vendored paths are pinned to a specific Tabler release, the license
   is verified (Rule 5), and an attribution comment in the sprite block
   + NOTICE update carry the MIT notice. Icon grammar: stroke 1.75,
   round caps, 16px (14px chevrons), `currentColor`. Shipped set
   (16): `book`, `file-text`, `chevron-right`, `chevron-down`,
   `search`, `copy`, `alert-triangle`, `alert-octagon`, `bulb`,
   `info-circle`, `bookmarks`, `flag`, `message-circle`, `arrow-left`,
   `arrow-right`, `eye`.
2. **②A — Syntax colors: a custom Pygments `Style` subclass** mapped
   onto the palette (`pygments_style` wired in the staged `conf.py`;
   exact registration mechanism realized and CI-tested in the C3.5
   regression). All Pygments classes derive from the four consult roles
   (`--sd-syn-kw` verdigris, `--sd-syn-str` brass, `--sd-syn-com` faint
   italic, `--sd-syn-fn` muted blue; numbers take the string role;
   everything else `--sd-code-text`). Builtin style + handwritten
   overrides (double bookkeeping) and closest-builtin (palette mismatch)
   were rejected.
3. **③B — Copy button: first-party support script** (~40 small lines:
   copy control per `div.highlight` block, `navigator.clipboard` with a
   non-secure-context fallback to `execCommand`, brief "copied" flash
   state, focusable, `aria-label`). This **amends 0027's JS clause**:
   the "engine assets or nothing" rule becomes *engine assets + one
   disclosed first-party theme script* (`scriptorium.js`, committed
   inside the theme's `static/`). Pinned/sphinx-copybutton was
   presented and rejected: it puts third-party JS bytes into every
   artifact for ~30 lines of first-party replacement, and its default
   look needs CSS overrides anyway.
4. **⑤ — Extensions policy:** v1 installs **zero** Sphinx extensions
   that inject assets or behavior (`myst_parser` is not one of these —
   it is the source-format parser of the frozen engine stack for MyST
   books, pre-approved by 0003/0026). Future extensions require owner
   approval + version pin + zero-network audit + corpus-compatibility
   check (does the corpus even emit the markup the extension targets?).
   Parked as documented-N/A-unless-corpus-grows: `sphinx-design`, tabs,
   `viewcode`, mathjax.
5. **⑥1 — Single fixed scheme in v1:** dark-forest chrome + cream
   paper page (consult D3 supersedes the brief's D2 "both schemes").
   `prefers-color-scheme` and a `[data-theme]` hook stay reserved for a
   later phase — the fixed scheme is a token-only change away.
6. **⑥2 — Logo:** none in v1. Text-only "Scriptorium" wordmark
   positioning stands (consult D17): artifact top bar carries the
   library (Athenaeum) title; the wordmark appears as "Compiled by
   Scriptorium" in the footer; `--sd-wordmark` + per-library brand
   option later (serving phase) can replace it.
7. **⑥3 — Icon breadth:** the icon set is used across the whole
   artifact surface (sidebar tree, callouts, search, copy, prev/next) —
   not only the sidebar tree.

## Ruled exception A — per-type admonition palette (one distinct anchor each)

The owner chose the deviation option (consult D13's two-color rule is
replaced) and ruled further: **every admonition type gets its own
specific color**, with blue and violet introduced. Structure per callout
(consult D13 base): 3px left rule + faint tint + square corners on the
rule side; title in UI sans 600. Each type carries its own
`--sd-adm-<type>-{rule,bg,ink}` tokens (33 total); the shared
`.admonition` rules consume the three local tokens, each
`.admonition.<type>` sets them.

| Type | Anchor | Rule | Tint bg | Title/icon ink |
|---|---|---|---|---|
| `note` | blue (new) | `#4E7FA8` | `#E9EEF4` | `#274B66` |
| `seealso` | slate (new) | `#7C8FA0` | `#EDEFF1` | `#43525C` |
| `tip` | `--sd-ok` family | `#6BA87F` | `#EAF1EB` | `#2E5C43` |
| `hint` | teal (new) | `#45A0A8` | `#E7F1F1` | `#1F6B72` |
| `important` | violet (new) | `#8A67AD` | `#F1ECF6` | `#5A3E7E` |
| `attention` | `--sd-page-note` brass | `#C9A961` | `#F1EFDF` | `#6B5B1F` |
| `caution` | `--sd-warn` amber | `#D0A24A` | `#F4EEDD` | `#6F5013` |
| `warning` | rust (new) | `#C2763F` | `#F5EDE4` | `#6E4020` |
| `danger` | deep red (new value) | `#A63E36` | `#F3E7E6` | `#6B241F` |
| `error` | `--sd-err` red | `#B5524A` | `#F3E8E7` | `#6F2A25` |
| generic `admonition` | `--sd-ink-faint` | `#7E9486` | `#EFF1EF` | `#4A544E` |

Text rules inside a callout (owner-confirmed):

- **Body text is uniform in all 11 types:** `--sd-page-ink` `#14201A`
  (≈15:1 on every tint) — author prose stays neutral; the type is
  carried by rule + tint + title.
- **Title text + icon take the per-type `-ink`**; the bright rule
  anchor is decorative.
- Links inside callouts use `--sd-page-link`; inline code and code
  blocks keep their standard treatments (dark block), unaffected by the
  tint.
- New hues are muted to the palette's value range (anchors L≈40–55%, no
  neon) so blue/violet/rust read as the archive's own colors.

Consult deviations carried by this ruling (owner-approved):

- D13's "note → `--sd-note` brass / warning → `--sd-err`" two-color
  scheme is replaced by the per-type table above.
- D1's "green is the only chromatic voice; brass/amber only on
  callouts" is extended — **the chromatic expansion happens only inside
  admonitions**; the rest of the surface keeps its restraint.

Corpus caveat (disclosed, verified by grep): the M2 TipTap pipeline
cannot emit admonition callouts today, so the callout styles live idle
until the corpus can produce them. The fail-loud matrix
(`docs/technology/conversion.md`) is unchanged; any future emitting
support follows the extensions/corpus policy above.

## Ruled exception B — category labels: highlighted all-caps bold

The owner revised consult D15's "small faint sentence case": in the
artifact sidebar, category labels render **uppercase, bold (600), ~
0.75rem, letter-spacing ≈0.09em** in the verdigris `--sd-link`
(≈7:1 on the chrome bg — AA). Uppercase is applied via
`text-transform` — stored titles are untouched. (The all-caps
"GRIMOIRES" seen in the preferred editor screenshot now legitimately
matches the artifact voice; a full-ink variant was presented and
declined — verdigris is the ruled value.)

Consult deviation carried: D15 (sentence-case faint) → all-caps bold
verdigris, owner-approved.

## Consult inventory (source of truth)

The owner's external design consult landed in workspace `references/`
(seven files, all seen and inventoried): the ruling text D1–D17 fully
answered (`scriptorium-design-spec.md`), the `--sd-*` token sheet
(`tokens.css`), the preferred-editor aesthetic screenshots, the closest
HTML mock (`scriptorium_ui_green_linear.html`), the published-site
structure reference PNG. Gaps resolved by the owner:

- The spec's cited `theme-reference.html` / `editor-reference.html` /
  `shared.css` never arrived; no accurate published-site HTML mock
  exists. The site layout is extrapolated from the published-site PNG
  (structure) + preferred editor PNG + tokens (aesthetics).
- `scriptorium_site_and_editor_preview.html` was **declared inaccurate
  by the owner** — structure reference only via the published-site PNG,
  never aesthetics.
- That preview loads Tabler icons from a CDN — replacing it with the
  inline sprite above; the zero-network artifact audit stays intact.

## WCAG AA verified token pairs (Rule 2 — test-pinned in C3.5)

The C3.5 test suite computes relative-luminance contrast for every
fg/bg pair it asserts and requires ≥ 4.5:1 for text pairs (hand-checked
now at ≈ values; the test pins exact numbers):

- Paper page: `--sd-page-ink`/`--sd-page` ≈ 15.3;
  `--sd-page-faint`/page ≈ 4.8; `--sd-page-link`/page ≈ 5.8.
- Dark chrome: `--sd-ink`/`--sd-bg` ≈ 15.1; `--sd-ink-muted`/chrome ≈ 9.0;
  `--sd-ink-faint`/chrome ≈ 5.5; `--sd-link`/chrome ≈ 7.0.
- Filled buttons carry text only on `--sd-accent-strong`
  (`--sd-on-accent` on it ≈ 4.6 — AA). `--sd-accent` itself (≈3.8 with
  white text) is used for rules/bars/fills **without normal text**.
- All 11 callout title-ink/tint pairs ≥ 5.3 (hand-checked ≈ 6.4–9.2
  range); body ink over each tint ≈ 15.
- Reduced-motion respect is carried verbatim from the consult tokens
  (`prefers-reduced-motion` block) plus the AA focus ring.
- **C3.5 note (2026-10-22):** exact ratios are test-pinned in
  `tests/test_theme_contrast.py` (computes WCAG 2.x luminance from the
  stylesheet itself): every text pair ≥ 4.5:1 asserted
  (paper/chrome/callout titles+body+links/on-accent over
  accent-strong). The 3px rule anchors are decorative — WCAG 1.4.11
  covers meaning-bearing graphics only (the title ink + hue carry the
  type), and several owned anchors are deliberately quiet on their
  tint, so no numeric floor is asserted for rules. `--sd-on-accent` on
  plain `--sd-accent` is 3.8:1 — only valid for large/decorative use;
  normal text sits on `--sd-accent-strong`.

## Engine-JS vendoring — exact mechanics (verified against Sphinx 9.1.0)

0027's "four engine scripts vendored from the pinned engine" realizes as
three vendored + one build-emitted (verified by inspecting the
pinned distribution and a probe build), and the C3.5 implementation
discovered the exact shape needed by an `inherit = none` theme:

- **Vendored at materialization** (copied from
  `sphinx/themes/basic/static/` inside the installed pinned Sphinx —
  resolved through `SC_BUILD_PYTHON` so they come from the SAME
  distribution the builder runs on — into each staged workspace's
  staged theme `static/`, never committed, never fetched):
  `searchtools.js`, `doctools.js`, `sphinx_highlight.js`, **plus the
  two static templates `documentation_options.js.jinja` and
  `language_data.js.jinja`** — C3.5 refinement: with no parent chain
  the builder never reaches the basic theme's own statics, so without
  these the artifact would reference two scripts it 404s (silent even
  under `-W`). Vendoring the `.jinja` templates makes the builder
  render them from its own global context — the engine-emitted path,
  just materialized from the pinned distro.
- **Build-emitted by the engine itself (same trusted origin):**
  stemmer JS (`base-stemmer.js`, `english-stemmer.js`),
  `searchindex.js`, `pygments.css`, `objects.inv`. The rendered
  `documentation_options.js` (which supplies `DOCUMENTATION_OPTIONS`)
  is the engine rendering of the vendored template.
- The engine auto-scripts (`doctools.js`, `sphinx_highlight.js`,
  `documentation_options.js`) reach pages via the builder's asset
  injection; our templates render the provided asset lists with our own
  tags (`css_tag`/`js_tag`) — no hand-copied engine script tags.

## Search contract (current; the engine-renderer contract was retired by 0032)

The original contract below was read off the vendored `searchtools.js`
and pinned the engine's page-level renderer. **0032 retired that
renderer**: the search page and the dialog now share the first-party
core in `scriptorium.js`, and no page loads `searchtools.js`.

- Search page (`search.html`): a first-party
  `form.sd-searchpage-form action="" method="get"` with
  `input[name="q"]` (prefilled from `?q=`), a `#search-results` live
  region, and a `<noscript>` JavaScript-required notice. No
  `#search-progress` node and no `searchtools.js` tag.
- Script wiring: `language_data.js` in the head (classic script, so its
  `stopwords`/stemmer bindings exist before the body-end core), the
  build-emitted `searchindex.js` project-relative + deferred as the
  candidate pre-filter, and `scriptorium.js` as the one search core.
- Article pages carry `role="main"` as an accessibility landmark. The
  first-party core fetches the artifact's own pages and extracts
  heading-delimited sections; it does **not** use the engine's
  `DOCUMENTATION_OPTIONS.SHOW_SEARCH_SUMMARY` path.
- `<html data-content_root="#">` still comes from the builder context;
  the first-party script uses it for artifact-relative retrieval.
- The dialog and full page share `.sd-res-*` markup: folio header row,
  section rows (heading chain + highlighted snippet), grimoire chip.
  Keyboard: ↑/↓/Enter in the dialog, Esc/backdrop/Tabler x close;
  `Ctrl+K` opens. Engine shortcut flags stay off.
- `genindex.html` is plain HTML (no extra engine JS required).
- The historical `Search.renderItem` (`li.kind-*`) styling contract is
  gone with the renderer; `searchtools.js` stays in `_static` only
  because 0027's vendored-asset list has not been reopened.

## v1 scope boundary (unchanged from 0027, now design-complete)

Template surface: `layout.html`, `page.html`, `search.html`,
`genindex.html`, plus the stylesheet, the Tabler sprite inline in
layout, and the first-party `scriptorium.js`. Brand hooks
(accent/font/wordmark) + custom-CSS wiring + dark-mode policy → serving
phase. Category grouping in the sidebar is visual grouping only
(order-only; the tree is book → chapter → folio).

## Rejected alternatives (with the owner, this record)

- **Pinned `sphinx-copybutton` (③A):** mature UX, but third-party JS/
  CSS in every artifact + 0027 amendment with a bigger blast radius than
  one small first-party script; its default look needs overrides anyway.
- **Feather icons (①B):** matches the spec's wording but lacks
  bulb-style/per-type callout variety.
- **Builtin Pygments style + CSS overrides (②B/C):** double
  bookkeeping or palette mismatch.
- **Full-ink category labels (⑥4-variant B):** loudest reading; verdigris
  ruled instead.

## Consequences

- The C3.5 implementation is fully specified: tokens, icon list, script
  set, palette table, AA pair list, DOM contracts. Implementation needs
  no further design decisions — only fixes caught by tests/gates.
- Any future palette addition is a token-only change; expanding the
  fixed scheme to a second scheme is a new owner ruling.
- 0027 remains in force (structure-locked, engine-owned, vendored JS);
  its JS clause is amended by the ③B ruling above (one disclosed
  first-party script).
