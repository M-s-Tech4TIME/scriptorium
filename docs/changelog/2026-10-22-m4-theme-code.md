# 2026-10-22 — M4 C3.5 code: the Scriptorium theme shipped

The implementation tranche for the owner-ruled design baseline
(decision 0028, recorded earlier today): Scriptorium's own Sphinx theme
is now the staged build's engine — no builtin or third-party theme
bytes in any artifact.

## What changed

- **Theme package** (`backend/app/sphinx/theme/scriptorium/`):
  - `theme.conf` — `inherit = none` (discovered: Sphinx 9.1 requires
    the explicit setting; absence raises `ThemeError`), no display
    asset, no parent.
  - `layout.html` — the whole shell: 16-symbol inline Tabler sprite
    (stroke 1.75, MIT attribution comment), engine `css_tag`/`js_tag`
    helpers rendering the builder asset lists, recursive `sd_node`
    sidebar macro (books as `branch: "<slug>/"` rows, chapters
    collapsible `<details>` opened on the current path, folios leaf
    rows), CSS-only checkbox drawer (`#sd-drawer`), topbar +
    breadcrumbs, footer. Header-link ¶ anchors (engine-emitted) styled
    quiet-until-hover.
  - `page.html` — `role="main"` article + prev/next pager.
  - `search.html` — pinned contract: `input[name="q"]`,
    `#search-results`, `#search-progress`; `searchtools.js` +
    `language_data.js` tags; project-relative deferred
    `searchindex.js`.
  - `genindex.html` — jumpbox; first-link page name + `[N]` refs.
  - `static/scriptorium.css` — consult tokens verbatim (verified
    against `references/tokens.css`), 33 `--sd-adm-*` callout tokens,
    components, breakpoints, `prefers-reduced-motion`, paper-scoped
    focus ring (`--sd-page-link` verdigris is 2.3:1 on paper, so the
    ring handles focus substance).
  - `static/scriptorium.js` — the one disclosed first-party script
    (0027 JS clause as amended): idempotent ~40-line copy button.
  - `style.py` — `ScriptoriumStyle(Pygments Style)`: all token classes
    derived from the four consult syntax roles via `var(--sd-syn-*,
    #fallback)` values (verified: Pygments emits `var()` verbatim and
    inherits token groups); linenos `.special` yellow override lives in
    the stylesheet.
- **sourcegen**: `THEME_BASE = "scriptorium"` + `PYGMENTS_STYLE`
  dotted path, `html_theme_path=["theme"]`, `html_static_path=[]`,
  `pygments_style`, `exclude_patterns=["_build"]`, and the sidebar
  payload under `html_context = {'sidebar_categories': [...]}` —
  list-typed `html_context` is rejected by the engine's config
  validator (found by the real build), so the tree rides the
  dict-typed blanket-page context. Rows come from the same single
  `_emit_page` traversal that stages pages (`(docname, row)` returns);
  `_sidebar_rows` orders first-seen category labels with the unlabeled
  bucket last; dead `_emit_book` removed.
- **loader**: category `name` map fetched with the staging plan;
  `StagedBook.category_label` set.
- **runner**: `_materialize(workspace, plan, build_python)` — theme
  copytree → `workspace/theme/scriptorium`, style module →
  `workspace/scriptorium_style.py`, engine-asset vendoring
  (`doctools.js`, `searchtools.js`, `sphinx_highlight.js` +
  **`documentation_options.js.jinja` / `language_data.js.jinja`**)
  resolved from the BUILD interpreter's Sphinx via a subprocess probe
  (`_sphinx_static_dir`), fail loud (`RunnerConfigError`) on a missing
  asset. Implementation discovery: with `inherit = none` the builder
  never reaches the basic theme's statics, so without vendoring the
  two `.jinja` templates the artifact would reference and 404
  `documentation_options.js`/`language_data.js` — silent even under
  `-W`. Vendored templates are rendered by the builder from its own
  global context (the engine-emitted path, materialized from the
  pinned distro; zero network preserved). `run_build` passes
  `cfg.build_python`.
- **NOTICE**: Tabler icons v3.36.0 MIT attribution.
- **Tests** (+9 → 75 passed / 36 skipped, `pytest -W error` clean, zero
  warnings):
  - `test_theme_build.py` — materialization unit tests (theme + style
    module staged; vendored assets byte-identical to the pinned
    engine; fail-loud on a wrong/absent engine) and the
    offline-but-real integration: a full sandboxed `-W` build with the
    test interpreter as build python asserting the artifact
    physiology — exact `_static` inventory, `pygments.css` containing
    `var(--sd-syn-kw,#4FB39A)`, search DOM wiring, `role="main"`
    article, sidebar tree with the category label, myst/rst page mix,
    workspace cleanup, `build.log` in the artifact.
  - `test_theme_contrast.py` — WCAG AA computed from the stylesheet
    itself (WCAG 2.x relative luminance, `var()` indirections
    resolved): every text pair ≥ 4.5:1 (paper/chrome, category labels,
    filled controls on `accent-strong`, all 11 callout title-ink/tint
    pairs + uniform body ink + links over tints); rule anchors are
    decorative (WCAG 1.4.11 covers meaning-bearing graphics only —
    the title ink + hue carry the type), so no numeric floor is
    asserted for them.
  - 3 new sourcegen sidebar tests (tree structure, category grouping +
    unlabeled-last, E2-skipped books absent).
- **Dev dependency** (typing only, no runtime impact):
  `types-Pygments==2.21.0.20260819` added to `[project.optional-dependencies].dev`
  — mypy strict needed real stubs for the Pygments style subclass;
  same league as the existing dev tool pins. No pygments override
  allowlist was introduced.
- **Lint/type/format**: `ruff check` + `ruff format` clean, `mypy
  --strict` clean (50 files).

## 0029 preview-feedback pass (same day, second owner look)

The owner viewed the first browser preview and returned seven rulings —
all approved (search spec amended in chat; "Tabler it is" on the icon
set; librarian's display name as the copyright holder; engine last-updated
date). Implemented as decision **0029**:

- **Header anchors:** the engine ¶ replaced by a hyperlink icon at
  every heading level (Tabler `link`, `currentColor` CSS mask, ¶ hidden
  via zero font-size).
- **Search results:** full decoration — scope line
  **Category › Grimoire** (from the blanket-page `#sd-map` island),
  heading/sub-heading chain read from the artifact's own pages
  (same-origin, no network — the same retrieval the vendored engine
  already performs for its summary); the themed highlighted match is
  engine-native (`span.highlighted` themed by the `.highlighted`
  token); scope-only on file:// previews (browser-blocked retrieval,
  disclosed).
- **Code blocks:** header bar with code icon + language name and the
  always-visible copy button (also fixes the copy-button bug: the
  button was positioned inside a detached, never-inserted wrapper);
  scrolling pane (`overflow: auto`, max-height).
- **Pager:** ruled green `--sd-accent-strong` buttons, labels exactly
  Previous / Next, hover lift + shadow, active press.
- **Footer bar removed:** Index centered just below the sidebar search
  form; Search link gone (the form serves); per-page credit block
  ("© Copyright by <librarian>. Last updated on <date>." /
  "Compiled by Scriptorium.").
- **Reading layout:** wide-left article column (`--sd-col-wide: 896px`,
  consult `:root` kept verbatim; the two new layout tokens ride a
  labeled addendum `:root`) + sticky **On This Page** rail rendering
  `{{ toc }}` with a first-party scrollspy (rail hides <1200px).
- **sourcegen/loader/execute:** conf gains `html_last_updated_fmt`;
  context gains `book_categories` (slug → {label, title}) +
  `site_credit`; loader fetches the Athenaeum owner's `users.display`.
- **Tests:** physiology asserts updated (footer absence, side links,
  island, credit, reading grid, rail, pager labels) + the
  `book_categories` island test (76 passed / 36 skipped, `-W error`
  clean, ruff + mypy strict clean).

## Not in this tranche

Packaging (M4-C4), serving-phase hooks (brand injection, custom-CSS
hook, dark-mode policy per 0026 mandate 2), and any `docs/technology/`
addition for new deps — none added at runtime. Callout emission from
TipTap stays a serving-phase schema question (0029 ruling 7: the demo
fixture handcrafts staged sources; the fail-loud corpus discipline
stands).

## Next

M4-C4 packaging → 0017 docutils-0.23 probe → M4-complete report →
serving phase (Q-SERVE-A…E).
