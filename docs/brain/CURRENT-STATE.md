# CURRENT-STATE

Last updated: 2026-10-28 / Ref: URL-durability phase 0036 pushed (`be5af83`), CI ×3 green

- **Phase:** **URL-durability phase (0036) pushed (`be5af83`), CI ×3
  green: owner-renamable
  public names, permanent aliases, tombstones, migration 0008, live
  regressions. Distribution and the dedicated SEO phase remain later.**
  Owner approved A1/B1/C1/D1/E1/F1 on 2026-10-28 and confirmed URL-scheme
  Option 1 (`/a/{public_slug}/`, `/latest/`, `/stable/`, `/b/{n}/`;
  `/a/` retained; numbered builds public). Public names are owner-only
  renamable via `PATCH /api/v1/athenaeums/{id}/public-slug`; old names
  become permanent `308` aliases after the current site's access check;
  deletion creates permanent tombstones; reversion to the same site's old
  alias is allowed; reserved/invalid names `422`, other-site/tombstone
  collisions `409`; no artifact rebuild. Migration `0008urldurability`
  backfills every existing `athenaeums.public_slug` into `public_names`.
  SEO is a separate later phase with per-Athenaeum editorial controls;
  canonical host/channel, robots/sitemap, structured data, and social
  metadata are not decided here. Distribution awaits Q-DIST-A…D.
  Serving phase (0035) remains pushed (`6169696`), gates/browser checks
  and CI ×3 green; M4-C3.5/M4-C4 remain pushed and green (`1add6c8`).
  M4-C1 (`2aed3ef`): decision 0026
  (per-Athenaeum site P1, manual trigger P2, subprocess sandbox P3,
  keep-all versions P4; reconciliation: staging keyed by grimoire id
  inside each build, artifact keyed by Athenaeum; design mandates:
  artifact security parity + structure-locked/skin-open) + migration
  0006 (`builds.build_number` per-Athenaeum counter, `athenaeum_id` FK,
  `grimoire_id` relaxed nullable, `ck_builds_site`,
  `uq_builds_athenaeum_number`). Edge rulings owner A/A/A (`7d14f3a`,
  0026 §Edge rulings): E1 empty athenaeum → 422; E2 empty book → skip +
  note; E3 one build per Athenaeum (409 while queued/running, C3
  enforces). M4-C2 (`3a15b52`, CI ×3): `app/sphinx/sourcegen.py` —
  pure deterministic staging: per-book dirs, `toctree` masters (RST,
  always), MyST-conditional `conf.py`, bodies direct from canonical
  TipTap, fail-loud `StagingError`; disclosed micro-defaults: `index-p`
  leaf mangle, toctree-title `«»` sanitize. M4-C3 (`c6c407d` + `fadef93`
  + `1e1637e`, CI ×3): `app/sphinx/runner.py` sandbox (whitelist env,
  RLIMIT cpu/as/fsize/core, 900 s, `sphinx -W -b html`),
  `app/sphinx/execute.py` shared executor (fresh engine/orderly
  disposal; queued→running→ok|failed), `app/worker/` celery (queue
  `scriptorium`, `CELERY_BROKER_URL` fail-loud), `app/routers/builds.py`
  POST owner-only (E1 422, E3 409, advisory-locked `max+1`) + GET
  member-visible; CI live suites prove E1/E3/numbering/artifact/
  failed-log + migration roundtrip vs library-era rows.
  **CI-discovered staging rulings** in 0026 (absolute `</docname>`
  refs, generated top sections, MyST fenced toctree, downgrade mirror,
  save-path exporter guarantee). Q-SERVE-A…E resolved by 0035; Q-DIST-A…D
  remain parked. Migrate head `0008urldurability`.
  **C3.5 code (this tranche):** Scriptorium's own theme shipped in
  `backend/app/sphinx/theme/scriptorium/` (`theme.conf` `inherit=none`
  — 9.1 mandates the explicit key; layout/page/search/genindex
  templates + `scriptorium.css` (tokens verbatim + 33 `--sd-adm-*`) +
  `scriptorium.js` copy script + custom `ScriptoriumStyle`), runner
  `_materialize` staging the theme + style module + engine assets
  (`searchtools/doctools/sphinx_highlight` **+ the two
  `.jinja` static templates** — with a parentless theme the builder
  never reaches basic's statics; unvendored artifact would 404
  `documentation_options.js`/`language_data.js`, silent under `-W`),
  sidebar tree via `html_context{'sidebar_categories'}` (list-typed
  html_context rejected by the engine), loader fetches category names.
  Tests +9 → **offline baseline `75 passed, 36 skipped`** (materialize
  units incl. fail-loud paths, offline-but-real sandboxed `-W` build
  asserting exact artifact `_static` inventory/search contract/
  custom-style spans, WCAG AA computed from the stylesheet, sidebar
  tree/labels/order). `ruff`/`mypy --strict` clean;
  `types-Pygments==2.21.0.20260819` added dev-only (typing stubs; no
  runtime dep, no allowlist). 0028 amended with the exact vendoring
  mechanics + exact AA outcome note.
   **0029 preview-feedback pass (2026-10-22, staged now):** owner
   reviewed preview #1 and ruled seven items (record
   `docs/decisions/0029-theme-preview-feedback.md`; 0028 pointer
   amended): ① header anchors = Tabler link glyph at every heading
   level (¶ hidden via CSS mask; quiet-until-hover accepted); ② search
   hits decorated — scope line **Category › Grimoire**
   (`#sd-map` island from `html_context{'book_categories'}`) + the
   heading chain read from the artifact's own pages, same-origin, no
   network (the themed highlight itself is engine-native:
   `span.highlighted` over the engine's own summary; scope-only on
   file:// previews, disclosed); ③ code blocks get a header bar (code
   icon + language name + always-visible copy — fixed the C3.5 copy
   bug: the button lived on a detached wrapper) + scrolling pane; ④
   pager = ruled green `--sd-accent-strong` Previous/Next (hover
   lift+shadow, active press; fill kept on hover to preserve the AA
   pair); ⑤ footer bar removed — Index centered under the sidebar
   search form, Search link gone, per-page credit block ("© Copyright
   by <librarian display name>. Last updated on <date>." / "Compiled
   by Scriptorium."; loader fetches `users.display` → `site_credit`;
   conf gains `html_last_updated_fmt = "%B %d, %Y"` — engine date is
   build-time; equal to per-page mtime here since staging rewrites all
   sources per build); ⑥ reading layout wide-left (`--sd-col-wide:
   896px` in a labeled addendum `:root` — consult `:root` verbatim) +
   sticky **On This Page** rail (`{{ toc }}` + scrollspy, hides
   <1200px — 740px measure superseded); ⑦ second preview =
   handcrafted inspection fixture (all 11 callouts, h1–h6 nested
   depth, full link inventory — hand-written post-materialization,
   never committed; fail-loud corpus discipline stands). Script
   ledger: `scriptorium.js` = copy + code chrome + search decoration +
   scrollspy. Suite **76 passed / 36 skipped** (`-W error` clean,
   ruff + mypy strict clean).
   **0030 typography pass (2026-10-23):** reading face swapped to
   **vendored Inter** (owner chose Option B + sans "Notion look";
   fetched from Google Fonts per their sourcing ruling): two variable
   latin woff2 files (upright 72.5 KB + italic 79.7 KB) under
   `theme/.../static/fonts/` + vendored OFL 1.1 text + NOTICE row;
   `@font-face` (`font-display: swap`, weight 100-900) and the ruled
   `--sd-font-body` override live in the 0029/0030 addendum `:root`
   (consult `:root` stays verbatim; `--sd-font-heading` follows);
   fallback = the ruled UI sans stack (RTD-faithful chain considered
   and dropped by the owner). Body + headings only — UI sans/mono/
   scale/AA unchanged. served `_static/fonts/` → zero network holds.
   0028 D4 (serif-leaning) superseded by this ruling; recorded 0030.
   **0032 third-feedback pass (2026-10-23/24, preview #5):** the search
   is now ONE first-party mechanism on both surfaces — engine
   `searchindex.js` as candidate pre-filter only, on-demand sectioning of
   up to 10 cached folios, phrase-first ranking (whole sentence +1000),
   all typed words highlighted (stopwords included), last-token prefix,
   OR-union candidates, 8 groups × 6 rows, progressive render; the full
   `search.html` is a first-party takeover (`?q=`, no-JS notice,
   `searchtools.js` unloaded) with the same `.sd-res-*` rows; dialog
   centred + internal scroll + Tabler x close; panel clear is clear-only;
   content headings 800; inline-code bg `#D8E7DD`; collapse beside the
   search field / expand top-bar far-left (chrome ink); scrollspy
   includes the page title and activates the final heading at the bottom;
   island is `{"books": …}`; the theme-build test crawls every internal
   link (missing/directory/escape fails). **Staging finding fixed:**
   `export_rst`/`export_myst` gained `base_level=0`; sourcegen passes 1
   because it prepends the page title, so authored h2 bodies are legal
   while standalone exports stay fail-loud. Suite **80 passed / 36
   skipped** (`-W error`), ruff + mypy strict clean; preview #5 rebuilt
   and served on `0.0.0.0:8321`.
  M3 was C1–C6 all green ×3 (typical refs: C6 `5b5dee1`, close-out
  `5f97463`).
  **Decision 0027 recorded (2026-10-21):** the theme is Scriptorium's
  **own, from scratch** — no builtin/third-party template inheritance,
  `theme.conf` no parent — while the Sphinx **engine** is fully
  inherited/utilized incl. engine-JS vendoring at build time
  and DOM contracts pinned to it. Third-party candidates
  (furo/rtd/alabaster-as-final) presented and rejected. **Decision 0028
  recorded (2026-10-22):** the design baseline is implementation-ready —
  consult tokens accepted (fixed dark-forest chrome + cream paper,
  `[data-theme]` reserved), Tabler inline-SVG sprite (16 icons), custom
  Pygments `Style`, **first-party copy script** (0027 JS clause
  amended: engine assets + one disclosed first-party `scriptorium.js`),
  zero asset-injecting extensions v1, 11-anchor per-type callout
  palette (`--sd-adm-<type>-{rule,bg,ink}`, body ink uniform
  `--sd-page-ink`), all-caps bold verdigris category labels (D15
  owner-revision), WCAG AA pair list (now test-pinned exactly),
  engine-JS vendoring mechanics verified (5 vendored incl. 2 `.jinja`
  renderer templates + engine-emitted the rest) and the search DOM
  contract pinned off the vendored
  `searchtools.js`. **0029 (2026-10-22):** all seven preview-feedback
  rulings approved (link-icon anchors, search decoration spec
  owner-amended, code chrome, green pager, footer removal + credit,
  wide reading + toc rail, inspection fixture); Tabler confirmed
  ("Tabler it is"), credit holder = librarian display name, date =
  engine last-updated. **0030 (2026-10-23):** typography — vendored
  Inter reading face (sans, "Notion look", Option B mechanics, Google
  Fonts source, OFL vendored + NOTICE; fallback = ruled UI sans stack;
  RTD chain dropped).
  **M4-C4 complete (2026-10-24):** isolated build venv
  (`packaging/scripts/build-venv.sh` + 27-pin engine lock), config
  example/queue keys, both units `Requires=redis`/`After=redis`,
  postinst artifacts/config seed/build-venv check, manual docutils-0.23
  probe (58 passed; pin stays 0.22.4), and the M4 report. Suite is
  87 passed / 36 skipped. Pushed as `1add6c8`, CI green ×3. M4
  implementation is complete. **Serving phase (0035) implemented
  (2026-10-25):** schema/API for `public_slug`/`is_public`/custom CSS +
  latest/stable pointers; FastAPI artifact routes; access cookie;
  manifest/CSP; custom-CSS sandbox; live + unit + theme regressions.
  **URL-durability phase (0036) implemented (2026-10-28):** owner
  public-name renames, permanent aliases/tombstones, migration 0008,
  auth-before-`308` serving, no rebuild. Next: dedicated SEO phase and
  Distribution (Q-DIST-A…D); sequencing not ruled.
- **Owner decisions:** 0018 (grimoire rename, per-user categories, auth
  semantics) → **amended by 0020 (2026-10-21):** native hierarchy — categories
  per-Athenaeum (Q-M3-9=A), `grimoires.athenaeum_id` NOT NULL (Q-M3-10=A),
  delete refuses 409 while grimoires remain (Q-M3-11=A), sharing stays
  grimoire-level (Q-M3-12=A), nested sidebar endpoint (Q-M3-13=A).
  Micro-defaults: per-owner slug uniqueness, migration backfills "Default"
  per user, athenaeum slug immutable (mirrors 0018 grimoire slugs),
  audit `athenaeum_*` + `grimoire_moved`. **0027 (2026-10-21):** own
  from-scratch theme + full engine inheritance
  (education-before-ruling; plan ratified before implementation).
  **0028 (2026-10-22):** theme design baseline — ①A icons, ②A Pygments
  style, ③B first-party copy script (0027 JS clause amended), ⑤ zero
  extensions v1, ⑥1 fixed scheme, ⑥2 no logo v1, ⑥3 icon breadth;
  exceptions: 11-anchor per-type callout palette (blue/violet added,
  uniform body ink), all-caps bold verdigris category labels (D15
  revision). All on the consult/gap-inventory basis. **0029 (2026-10-22)
  + 0030 (2026-10-23) + 0031 (2026-10-23) + 0032 (2026-10-23/24):**
  the four theme feedback passes — link-icon anchors, search
  decoration/dialog, code chrome, green pager, footer credit, wide
  reading + toc rail; vendored Inter; fluid width, hidden staged trees,
  first-leaf book rows, sticky collapsible panel, wine danger, chips,
  copy→check; then the unified first-party search, weight 800, split
  toggles, clear-only X, centred dialog, scrollspy title, link crawl and
  the h2 staging fix (0032 amends 0027/0028/0031). **0033 (2026-10-24):**
  Standing Rule 8 — Regression Integrity (No Collateral Breakage), the
  owner's project-wide directive that every change preserve all approved
  behavior with full gates, browser checks, and regression tests.
  **0034 (2026-10-24, accepted):** fourth feedback — panel placeholder
  only, code-language label fix with `Code` fallback, pager inside
  `.sd-reading-main`, plus the pre-paint collapsed panel fix so pager
  navigation never flashes the panel open. Preview #6 was approved;
  preview #7 is the browser-verified no-flash follow-up.
  **0035 (2026-10-24, accepted; implemented 2026-10-25):** serving —
  owner-published latest/stable pointers over immutable numbered builds
  (A2), private-default per-Athenaeum visibility with owner/member
  access (B3), FastAPI artifact serving (C1), global public
  slug + `/a/{public_slug}/{latest|stable|b/n}/` URLs (D1; now
  owner-renamable per 0036), strict
  manifest-derived CSP + bounded namespaced custom CSS (E2). Migration
  0007. URL-durability aliases/redirects were deferred at that point
  (implemented by 0036); distribution remains deferred.
  **0036 (2026-10-28, accepted; implemented):** URL durability A1/B1/C1/
  D1/E1/F1 — owner-renamable public name, permanent aliases/tombstones,
  single `public_names` namespace, `308` aliases after auth, path/query
  preservation, no rebuild, Option 1 URL shape retained; page-path
  aliases and SEO remain later phases.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/2 + Q-M3-1…8 + Q-002=B(0019) +
  Q-M3-9…13=A(0020) + Q-M3-16a–e=A(0025) + Q-M4-P1…P4 + E1–E3(0026) +
  theme ruling(0027) + design baseline(0028) + preview-feedback
  rulings(0029) + typography(0030) + second feedback batch(0031) +
  third feedback batch(0032) + Standing Rule 8(0033) +
  fourth feedback(0034) + serving(0035) + URL durability(0036);
  Rules 1–8. M0 locks; M1 green (2539391); M2 A–C green; M3 C1–C6 green
  ×3; M4 C1 `2aed3ef` + C2 `3a15b52` + C3 `1e1637e` green ×3; 0028
  record `556bbce` green ×3; C3.5 baseline `b15446f` green ×3 (0029 +
  0030 + 0031 + 0032; 80 passed / 36 skipped, ruff + mypy strict clean).
- **Serving work (pushed `6169696`, CI ×3):** 0035 schema/migration,
  serving modules/routers, auth access cookie, build manifest/custom CSS,
  tests, docs/brain. Local gates: full suite **147 passed / 1 deselected**
  (PG16 local; PG18 version test excluded locally) + unit/theme suites;
  ruff + format + `mypy --strict` clean; headless Chrome verified public
  and private serving, CSP (no violations), custom CSS, search dialog,
  placeholders, and panel persistence. All three CI workflows green.
- **URL-durability work (0036, this tranche):** `public_names` registry +
  migration 0008 (backfill current names, partial unique current index,
  FK `SET NULL` tombstones); owner-only public-slug rename endpoint with
  validation/reserved words/409 collisions/reversion/audit; create/delete
  registry hooks and namespace advisory lock; alias resolution in
  `site.py` with auth-before-`308`, suffix/query preservation, flattening,
  public `no-cache`/private no-store headers; publication response
  `public_aliases`; live tests for rename/alias/tombstone/reversion/
  collision/cache/audit and migration backfill. Local fresh PG16 suite
  **149 passed / 1 deselected** with Redis for auth and Redis-backed
  ratelimit tests (PG18 version test excluded locally); ruff/format/mypy/
  compileall clean. Headless Chrome followed an alias `308` to the
  canonical page and loaded its assets.
- **Last pushed:** `be5af83` — `feat(url): durable public names with
  aliases and tombstones` (29 files, +1235/−168), pushed `dev`; all
  three CI workflows green (lint-type-test incl. docs-brain, security,
  packaging). It sits on `9dbd8a0` — docs closeout for serving (CI ×3
  green). `6169696` — `feat(serving): publish and serve
  immutable Sphinx artifacts` (46 files, +2914/−105), pushed `dev`; all
  three CI workflows green (lint-type-test, security, packaging). It sits
  on `1add6c8` — `feat(m4-c4): package isolated build venv
  and docutils probe` (32 files, +645/−101), also green ×3. It sits on
  `2680738` (0034, 14 files, +410/−76), `cbe2b22` (Standing Rule 8, 12
  files, +238/−71), and the approved baseline `b15446f`
  (`feat(m4-c3.5): complete theme feedback passes 0029-0032`, 35 files,
  +3968/−275). 0034 is the owner-approved fourth batch plus the no-flash
  collapsed-panel follow-up (preview #7); C4 is the M4 packaging/probe
  closeout.
  The exact owner-approved preview #5 artifact is `b15446f`: 0029
  seven-ruling pass + 0030 vendored Inter + 0031 second batch + 0032
  unified first-party search (phrase-first, all-word highlight,
  full-page takeover), centred dialog + x close, clear-only panel field,
  weight 800, `#D8E7DD` inline code, split panel controls, scrollspy
  title, island contract fix, link-integrity crawl, and the h2
  `base_level` staging fix. **0034 is pushed and CI green ×3; preview
  #7 is browser-verified. M4-C4 is pushed as `1add6c8`, CI green ×3.**
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M3 + M4 implementation + serving + URL durability;
  `main` stays at release point (ff-only).
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests migrate to the current head (`0008urldurability`).
  Search on the static artifact requires JavaScript; `file://` previews
  degrade to folio/heading links without snippets; candidate/group/row
  caps are 10/8/6; a build-time section index is the documented scale
  upgrade (deferred, 0032); `searchtools.js` remains vendored but
  unloaded (0027 asset contract). Serving: public numbered builds are
  immutable-cached, so making a site private cannot recall copies already
  cached at those URLs (0035 disclosure); custom CSS has no at-rules
  (including `@media`), custom JS, or remote assets; public names are
  owner-renamable (0036), but page-level path aliases are deferred (B1),
  so `latest`/`stable` page paths can change after an editor rename while
  numbered builds keep their old paths. SEO canonical/sitemap/robots/
  structured/social policy is a dedicated later phase with per-Athenaeum
  editorial controls; distribution is not implemented.
