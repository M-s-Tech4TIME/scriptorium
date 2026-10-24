# HANDOFF

Last updated: 2026-10-24 / Ref: cbe2b22 Rule 8 + 0034 accepted/committed; push + CI next

## Was doing
M4-C3.5 **baseline committed and pushed**: the owner-approved preview #5
artifact is `b15446f` (`feat(m4-c3.5): complete theme feedback passes
0029-0032`, 35 files, +3968/−275). All three CI workflows are green
(lint-type-test, security, packaging). The owner then approved the
artifact and requested three fourth-feedback fixes plus Standing Rule 8:
panel placeholder only → "Search"; code-block language label (root cause:
the lexer class is on the outer `highlight-*` wrapper, but the script
matched the inner `highlight` block); pager Next must stay inside the
article column, not cross the On-This-Page rail. Rule 8 is approved as
written and committed as `cbe2b22`; the 0034 fixes are implemented.
Preview #6 was approved, but the owner found a one-frame expanded-panel
flash on pager navigation while collapsed. Root cause: the stored state
was applied at the end of `<body>`, after first paint. A tiny inline
`<head>` script now marks `<html>` with `sd-panel-pending-off` before the
shell exists; CSS paints the collapsed grid/sidebar/expand state, then
the body script swaps in `.sd-panel-off` and removes the marker. Preview
#7 is browser-verified and 0034 is committed. Push Rule 8 + 0034, then
verify CI green ×3.

M4-C3.5 **0032 third feedback batch (now committed in `b15446f`):** the
search is one first-party mechanism on both surfaces — engine
`searchindex.js` as candidate pre-filter only,
on-demand sectioning of up to 10 cached folios, phrase-first ranking
(whole typed sentence +1000), all typed words highlighted (stopwords
included), last-token prefix, OR-union candidates, 8 groups × 6 rows,
progressive render; `search.html` is a first-party takeover (`?q=`,
no-JS notice, `searchtools.js` unloaded) sharing the `.sd-res-*` rows;
the dialog is centred with internal scroll and a Tabler x close; the
panel clear is clear-only; content headings are 800; inline code is
`#D8E7DD`; collapse sits beside the search field and expand is the
top-bar far-left control (chrome ink); the scrollspy includes the
page-title entry and activates the final heading at the bottom; the
island is `{"books": …}`. The theme-build test crawls every internal
link (missing/directory/escape fails). **Staging finding fixed:**
`export_rst`/`export_myst` gained `base_level=0`; sourcegen passes 1
because it prepends the page title, so authored h2 bodies are legal
while standalone exports stay fail-loud. Suite **80 passed / 36
skipped** (`-W error`), ruff + `mypy --strict` clean; preview #5
rebuilt and served on `0.0.0.0:8321`; headless Chrome verified search,
dialog geometry, clear, toggles, and scrollspy.

M4-C3.5 **0031 second feedback batch complete (staged on the unpushed
0029 + 0030 work)**: all ten owner rulings applied — fluid reading
width (the `--sd-col-wide` cap deleted everywhere), RTD-style search
dialog on every page (panel field + `Ctrl+K`; engine index via shim;
hits grouped by folio with matched heading + highlighted snippet rows
and a grimoire chip on each row's bottom; ↑/↓/Enter/Esc bar; engine
`search.html` untouched as fallback — superseded by 0032), icy-green
inline-code +
download chips (AA tip family; download glyph CSS-mask), weight-700
headings, wine/plum danger + skull (error keeps vermilion), panel
rows → first content-bearing folio with `:hidden:` staged toctrees +
`"container": True`, sticky collapsible panel (persisted, top-bar
toggle, two `layout-sidebar` glyphs), scrollspy rewrite
(last-heading-above-offset; IntersectionObserver removed), copy→check
icon swap. **CI finding fixed in passing:** engine 9.1's
`pathto(docname, 1)` is RESOURCE mode — sidebar links were
suffix-less; now `pathto(docname)` (document form), pinned by tests.
At that point the suite was **78 passed / 36 skipped** (`-W error`),
ruff + `mypy --strict` clean. Records:
`docs/decisions/0031-theme-second-feedback.md` +
DECISIONS-INDEX + 0029 amendment pointer + sphinx.md contract block +
changelog `2026-10-23-m4-theme-second-feedback.md` + OPEN-QUESTIONS
Q-EDITOR-1 (editor language-suggestion combobox — recommendation
parked, not approved). Fixture rebuild: inspection library + a fourth
staging rung + console block, rebuilt and SERVING on `0.0.0.0:8321`
(14 pages; `lang 200`, deeper page reachable). Earlier (0029, still
uncommitted on top of unpushed `0f5fcc8`): link-icon anchors at every
heading level (¶ hidden; Tabler kept), search-hit decoration (grimoire
chip + heading chain — trimmed of the page-title dup per 0031,
same-origin; themed highlight is engine-native), code-block header
bars (language badge + persistent copy — fixed the copy bug: the
button was wired onto a detached wrapper and never inserted), ruled
green Previous/Next pager (hover lift + active press, AA pair
preserved), footer bar removed (Index centered under the sidebar
search form; per-page credit "© Copyright
by <librarian>. Last updated on <date>." / "Compiled by Scriptorium."
via `html_last_updated_fmt` + `site_credit` from `users.display`),
wide-left reading layout + sticky On-This-Page rail (`{{ toc }}` +
scrollspy, hides <1200px). Records 0029/0030 + 0028 pointer amended;
sphinx.md + changelogs + brain synced. The C3.5 code tranche itself is
committed as `0f5fcc8` (23 files, +2034/−142, unpushed); the 0029 +
0030 passes are the staged changeset on top.

## Next steps (in order)
1. **Push `dev`** with Rule 8 `cbe2b22` + 0034, verify CI green ×3
   (`gh run list --branch dev`), fix-on-red if needed.
2. **M4-C4** — packaging (`packaging/` creates the isolated build venv,
   `SC_BUILD_PYTHON` pointed there; worker unit `After=redis`;
   `config.env` gains `CELERY_BROKER_URL` + `SC_*` build keys), the
   0017 docutils-0.23 probe mechanics, M4-complete report + brain sync.
5. **Junk-sweep before every gate:** re-read written files; grep the
   standing junk markers before committing.
6. Serving phase — resolve Q-SERVE-A…E first, then implement (theme
   brand-injection hooks + custom-CSS wiring land there, 0027;
   `[data-theme]` second scheme is its own later ruling, 0028).
7. URL-durability phase after serving; Distribution-phase concepts
   (Q-DIST-A…D) presented before their implementation (incl. the React
   shell format).

## Gotchas (carried)
- **Sphinx 9.1 theme:** `theme.conf` MUST carry `inherit = none`
  explicitly (absence → `ThemeError`); with a parentless theme the
  builder only reaches YOUR staged theme statics — engine basic-theme
  statics are unreachable, so `.jinja` static templates must be
  vendored to be rendered (silent 404s otherwise, `-W` can't see
  runtime asset misses). `html_context` must be a DICT
  (list → config-validation warning → error under `-W`).
  `searchindex.js` lands at output ROOT (not `_static`) — reference it
  project-relative (`pathto('searchindex.js', 1)`).
- **Test interpreter = build python** in the offline-but-real runner
  test (same venv): vendored-byte assertions compare against the same
  engine distribution the build used; in production `SC_BUILD_PYTHON`
  points at the isolated build venv and vendoring follows it
  (`_sphinx_static_dir` subprocess probe).
- Migrate head `0006buildsite`; verify migration SQL against older
  definitions before push (C1 lesson). `ck_nodes_kind` is dropped before
  the kind UPDATE runs (values outside the CHECK are otherwise illegal).
  Downgrade re-adds `user_id` as a trailing column — harmless, but
  backed by backfill SQL; roundtrip is CI-tested.
- conftest migrates to head ONCE (DATABASE_URL set); one loop per test —
  always end test coroutines with `await app_teardown()`.
- `Membership` rows cascade with grimoires: after delete, member requests
  become 404 again (covered by tests).
- Explicit-NULL pattern: use `model_fields_set` when a PATCH field must
  distinguish omission vs null (grimoire category_id; athenaeum move uses
  presence + null→422 instead).
- starlette.testclient warns → httpx.ASGITransport; ratelimit tests flush
  the CI Redis DB (conftest REDIS_TEST_URL).
- Categories/grimoire category checks are athenaeum-scoped now: a category
  of another (even own) athenaeum → 404.
- Keep per-step work small; write files one at a time (past derailments).
- **Jinja island gotcha (0029):** `{{ x or {}|tojson }}` binds OR first —
  the dict leaks as a Python repr (single quotes), not JSON; set the
  value first (`{% set sd_map = … %}`). The engine's Jinja also renders
  the island with alphabetically sorted keys — assert order-independently.
  The 0032 contract is `{"books": {slug: {label, title}}}`; the script
  normalizes the legacy raw map.
- **Staging heading context (0032):** `export_rst`/`export_myst` default
  `base_level=0` for standalone exports; `sourcegen._page_body` passes
  `base_level=1` because it prepends the page title at h1. Do not relax
  the standalone default — a body h3 directly under the generated title
  must still fail loud.
- **Search (0032):** `searchindex.js` is only the candidate pre-filter;
  `language_data.js` must load once (it declares `const stopwords`);
  `searchtools.js` is vendored but no page loads it. Full search needs
  JavaScript; `file://` degrades snippets to links.
- **Headless Chrome scroll tests:** with `scroll-behavior: smooth`
  (no-preference) `scrollTo` does not update under virtual time; use
  `--force-prefers-reduced-motion`, and dispatch a synthetic `scroll`
  event because programmatic scroll does not emit one in this harness.
  The spy itself measures directly on scroll (no rAF).
- **Link integrity (0032):** the theme-build test resolves every
  artifact-local `href`/`src` to a FILE; a directory target is a failure
  (the old dev-server directory-listing symptom). `pathto(docname, 1)`
  is resource mode in 9.1 — use `pathto(docname)` for document links.
- 0006: `ck_builds_site` (exactly one of grimoire_id / athenaeum_id);
  `Build` has a two-era key pattern — new code writes Athenaeum-keyed
  rows; `uq_builds_athenaeum_number` needs explicit max(build_number)+1
  per Athenaeum at trigger time (C3 will need `SELECT … FOR UPDATE`-style
  care, or serialize per library).
