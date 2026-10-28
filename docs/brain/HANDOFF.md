# HANDOFF

Last updated: 2026-10-28 / Ref: URL-durability phase 0036 implemented (pending closeout push)

## Current tranche (2026-10-28): URL durability 0036

Implemented the owner-approved A1/B1/C1/D1/E1/F1 URL-durability phase
and kept URL-scheme Option 1 (`/a/{public_slug}/`, `/latest/`,
`/stable/`, `/b/{n}/`; `/a/` retained; numbered builds public).

- Migration `0008urldurability` creates `public_names` (`slug` PK,
  nullable `athenaeum_id` FK `SET NULL`, `is_current`, timestamps,
  partial unique current index) and backfills every existing
  `athenaeums.public_slug` as current.
- Owner-only `PATCH /api/v1/athenaeums/{id}/public-slug` validates
  `[a-z0-9-]+`/160/reserved words (`422`), rejects another site's
  current/alias/tombstone (`409`), allows reversion to the site's own
  retired name, retires the old row as a permanent alias, updates the
  canonical column atomically, audits `athenaeum_public_slug_changed`,
  and never rebuilds artifacts.
- Create/delete hooks populate/retire registry rows; deletion leaves
  permanent tombstones. Names are never reused.
- `site.py` resolves current names and aliases, authorizes the current
  site first, then `308`s to the canonical name with suffix/query
  preserved and aliases flattened. Public alias `no-cache`; private
  alias `private, no-store`, `Vary: Cookie`, `X-Robots-Tag`.
- `GET /athenaeums/{id}/publication` now exposes
  `public_aliases: [{slug, retired_at}]`.
- Tests: live rename/private-auth/owner/member/outsider/public headers/
  root-channel-numbered-asset suffix/query/flatten/reversion/no-op/
  reserved/invalid/foreign/collision/tombstone/non-reuse/audit;
  migration backfill + round-trip. Local fresh PG16 suite
  **149 passed / 1 deselected** with Redis for auth and Redis-backed
  ratelimit tests (PG18 version test excluded locally); ruff/format/mypy/
  compileall clean. Headless Chrome followed an alias `308` to the
  canonical page and loaded its assets.
- Docs: decision 0036, 0035/0021/0026 amendments, architecture/API/
  data-model/security/overview/codebase-map, changelog, brain.

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
#7 is browser-verified, 0034 is pushed as `2680738`, and all three CI
workflows are green. M4-C4 packaging/probe/report is complete:
isolated build venv + 27-pin engine lock, config example
and queue/build keys, both units `Requires=redis`/`After=redis`,
postinst artifacts/config seed/build-venv check, manual docutils-0.23
probe (58 passed; pin stays 0.22.4), M4 report, and packaging
regressions (suite 87 passed / 36 skipped). Pushed as `1add6c8`; all
three CI workflows are green. M4 implementation is complete.

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
(14 pages; `lang 200`, deeper page reachable). Earlier (0029):
link-icon anchors at every heading level (¶ hidden; Tabler kept), search-hit decoration (grimoire
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
sphinx.md + changelogs + brain synced. The entire C3.5 stack (0029–
0034) was committed/pushed as `b15446f` … `2680738` after owner
approval; M4-C4 is pushed as `1add6c8` with CI green ×3.

## Next steps (in order)
1. **Close out URL durability:** commit/push the 0036 implementation +
   docs, verify CI ×3, then update this handoff/CURRENT-STATE with the
   closeout SHA.
2. **Dedicated SEO phase:** owner requested a structured, detailed plan
   in its own phase; every SEO feature/attribute must be user-controllable
   per Athenaeum in the editorial panel. Do not implement before the
   plan and owner rulings. Canonical host/channel, robots/sitemap,
   structured data, and social metadata are still undecided.
3. **Distribution phase:** present Q-DIST-A…D (credentials, delivery
   semantics, target roster, React shell) and wait; do not implement
   before owner approval. Sequencing (recommended URL durability → SEO →
   distribution) is not yet ruled.
4. **Junk-sweep before every gate:** re-read written files; grep the
   standing junk markers before committing.

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
- Migrate head `0008urldurability`; verify migration SQL against older
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
- Serving: a build is publishable/servable only if `status='ok'` AND its
  artifact has a valid `manifest.json`; the manifest is the CSP hash
  source. The theme must never reintroduce inline `style=`/event
  handlers/`<style>` blocks (build fails). `artifact_dir` checks both the
  artifact path and resolved `html/` against `SC_ARTIFACT_ROOT`; keep
  that jail when adding export/serving paths. Numbered URLs require
  `published_at`; unpublish clears pointers only. Private serving uses
  the `/a` access cookie; API routes keep bearer. Public numbered builds
  are immutable-cached (privacy caveat in 0035).
- **URL durability (0036):** `public_names` is the single global
  namespace; canonical, alias, and tombstone rows all occupy it, so never
  check only `athenaeums.public_slug`. Create/rename/delete take the
  transaction-scoped `SDNS` advisory lock; the slug PK/partial unique
  index is still the hard guard. Aliases authorize the **current**
  Athenaeum before `308`; tombstones (`athenaeum_id NULL`) are `404`.
  Reversion to the site's own retired alias is allowed; another site's
  alias/tombstone is `409`. No rebuild on rename: old artifacts keep
  build-time `site_id`/`data-sd-athenaeum`/manifest. Page-level path
  aliases are deferred (B1), so `latest`/`stable` page paths can change
  after editor renames; numbered builds keep old paths. SEO canonical/
  robots/sitemap/structured/social policy is a separate later phase.
