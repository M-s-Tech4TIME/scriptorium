# 2026-10-22 — M4 C3.5 record: decision 0028, the theme design baseline

Docs-only record tranche (no code yet — the C3.5 code requires the
rulings, recorded first per record-first discipline).

## What changed

- **Decision 0028** (`docs/decisions/0028-theme-design-baseline.md`,
  status accepted): the owner approved the full Rule-4 decision sheet —
  all as recommended: **①A** Tabler icon subset as an *inline SVG
  sprite* (16 named icons, stroke 1.75/16px/`currentColor`, MIT pinned
  + attribution; zero CDN), **②A** custom Pygments `Style` subclass
  wired via `pygments_style` (all classes derived from the four consult
  roles), **③B** a **first-party copy script** (~40 lines,
  `scriptorium.js` in the theme static — amends 0027's JS clause to
  "engine assets + one disclosed first-party theme script";
  `sphinx-copybutton` rejected: third-party bytes in every artifact for
  30 lines of replacement), **⑤** zero asset-injecting Sphinx
  extensions in v1 (future: owner approval + pin + zero-network audit +
  corpus compatibility), **⑥1** single fixed scheme (dark-forest chrome
  + cream paper; D3 supersedes D2; `prefers-color-scheme` /
  `[data-theme]` reserved), **⑥2** no logo file — text-only
  "Scriptorium" wordmark posture standing (D17), **⑥3** icons across
  the whole artifact surface.
- **Ruled exception A — per-type admonition palette:** every type gets
  its own distinct anchor (owner ruled beyond the 4-hue proposal),
  blue (`note`), slate (`seealso`), teal (`hint`), violet
  (`important`), rust (`warning`) added; 11 anchors total with
  `--sd-adm-<type>-{rule,bg,ink}` tokens (33). Structure stays D13
  (3px rule + faint tint + square rule side); **body text is uniform
  `--sd-page-ink` in all types** (owner-confirmed); title + icon take
  the per-type ink; links stay `--sd-page-link`; code blocks unchanged.
  Consult deviations recorded: D13's two-color rule replaced; D1's
  "green-only chromatic voice" extended — *only inside admonitions*.
  Corpus caveat: the M2 pipeline cannot emit callouts today (verified
  by grep) — styles land idle per the fail-loud corpus discipline.
- **Ruled exception B — category labels:** all-caps, bold 600, ~0.75rem,
  letter-spacing ≈0.09em in verdigris (`--sd-link`, ≈7:1 on chrome) —
  revising consult D15's sentence-case faint (owner-approved
  deviation); uppercase via `text-transform`, stored titles untouched.
- **Consult inventory + gap resolution recorded:** the (incomplete)
  delivered references (`theme-reference.html` / `editor-reference.html`
  / `shared.css` never arrived) and the owner-declared-inaccurate
  preview HTML are documented; site layout extrapolates from the
  published-site PNG (structure) + preferred editor PNG + tokens
  (aesthetics); CDN-loaded icons in that preview become the inline
  sprite.
- **WCAG AA pair list** recorded (paper/chrome/filled-button/callout
  pairs with hand-checked ratios; the C3.5 test suite will compute and
  pin exact numbers, Rule 2).
- **Engine-JS vendoring mechanics verified against Sphinx 9.1.0:**
  three engine scripts vendored at materialization
  (`searchtools.js`, `doctools.js`, `sphinx_highlight.js` from the
  pinned install's `themes/basic/static`); `language_data.js` +
  stemmers are *build-emitted* by the search module (0027's "four
  scripts = 3 vendored + 1 builder-generated" refinement, verified by
  probe build); `documentation_options.js`, `searchindex.js`,
  `pygments.css`, `objects.inv` are builder outputs.
- **Search DOM contract pinned** (read off the vendored
  `searchtools.js`): `#search-results`, optional `#search-progress`,
  `input[name="q"]`, `role="main"` content wrapper, `<html
  data-content_root>` attribute, and our `search.html` wiring
  `searchindex.js` (deferred) + `searchtools.js` + `language_data.js`;
  `genindex.html` needs no engine JS. Contracts are bumped together
  with the engine per 0027.

## Not in this tranche

No code changed. `THEME_BASE` stays `alabaster` in the working tree
until the C3.5 implementation commit. The design baseline is now
implementation-complete: tokens, icon list, script set, palette table,
AA pairs, and DOM contracts.

## Next

C3.5 implementation: theme package (`theme.conf` no parent, templates +
`scriptorium.css` + sprite + `scriptorium.js` + Pygments style),
`THEME_BASE = "scriptorium"` + `html_theme_path`, runner theme copy +
engine-JS vendoring, offline-but-real regression test (build `ok`, our
CSS in artifact, search ids present, `searchindex.js`, AA pairs
computed) → gates + push + CI ×3 → M4-C4 packaging.
