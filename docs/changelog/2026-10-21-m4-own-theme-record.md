# 2026-10-21 — M4 C3.5 record: decision 0027, the Scriptorium theme ruling

Docs-only record tranche (no code yet). The theme ruling is now
committed **before implementation** per the record-first discipline.

## What changed

- **Decision 0027** (`docs/decisions/0027-own-theme.md`, status
  accepted): the owner ruled — after an engine-capability education
  session — that the curated default theme (0026 mandate 2) is
  **Scriptorium's own, built from the ground up**: every template and
  all CSS fresh, `theme.conf` declares **no parent** (no `basic`
  inheritance), third-party themes rejected (furo / rtd /
  alabaster-as-final). The Sphinx **engine** is fully inherited and
  utilized — "each and every single thing of it": builder,
  environment, toctree/prev-next/genindex data, `searchindex.js`
  client search, Pygments highlighting.
- **Engine JS vendoring** recorded: `searchtools.js`, `doctools.js`,
  `sphinx_highlight.js`, `language_data.js` are copied from the
  installed pinned Sphinx into each build workspace at materialization
  time — same trusted origin as the compiler, never committed, never
  network-fetched (hermetic; 0026 mandate 1 consistent).
- **DOM contracts pinned with the engine:** theme templates must
  provide the exact ids/classes the vendored engine JS expects
  (search page per `searchtools.js`); the contracts and the vendored
  JS are bumped as one conscious, CI-tested sync event.
- **C3.5 mechanics** committed in 0027: theme package
  `backend/app/sphinx/theme/scriptorium/` (`theme.conf` + `layout` +
  `page` + `search` + `genindex` + `static/scriptorium.css`),
  `sourcegen.THEME_BASE = "scriptorium"` + `html_theme_path`,
  runner materialization copies the theme + vendors the engine JS,
  and an offline-but-real runner test pins the regression contract.
- **Rejected alternatives recorded with trade-offs:** third-party
  theme (violates structure-locked), `basic` inheritance (blurs the
  engine/theme boundary the owner drew at the engine), reimplementing
  engine pieces (breaks the inheritance mandate).
- **v1 scope boundary:** template surface = one layout/page/search/
  genindex + one stylesheet; dark-mode policy, per-site brand
  injection, custom-CSS hook wiring → serving phase (0026 mandate 2).
- **OPEN-QUESTIONS flip:** "curated default theme base" (the parked
  owner question; ID as Q-C3.5-A) → **RESOLVED by owner ruling**.
  alabaster stays only as the import-time placeholder until C3.5
  code lands.
- **Design intake in flight:** the owner is consulting an external
  design partner; a full self-contained brief (artifact structure,
  browser-template contracts, engineering floor, token checklist with
  defaults) was delivered for the consult. Theme implementation
  (templates + CSS) starts when the consult's palette/type/layout
  tokens arrive; code-side wiring (theme package, THEME_BASE flip,
  runner vendoring, tests) proceeds in the same tranche.

## Not in this tranche

No code changed. `THEME_BASE` stays `alabaster` in the working tree
until the C3.5 implementation commit (revealed then, tests updated
with it).

## Next

C3.5 implementation on the design tokens' arrival → gates + CI ×3 →
M4-C4 packaging.
