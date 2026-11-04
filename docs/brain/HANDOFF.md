# HANDOFF

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040); Dependabot cleanup

## CI housekeeping (2026-11-04)

Owner approved removing the unused `docker` ecosystem from
`.github/dependabot.yml` (added in `9d645e3`). No Dockerfile or
Kubernetes manifest exists, so scheduled Dependabot Updates runs failed
with `dependency_file_not_found`. The change is config-only; see
`docs/changelog/2026-11-04-dependabot-cleanup.md`. CI results are
recorded in the closeout commit.

## Current tranche (2026-11-04): server move/first-run + built-in TLS 0040

Owner rulings Q-SM-A…E and Q-SM-G…M were accepted as recommended;
revised Q-SM-F (F-A1…F-L1) and ownership ruling O1 were accepted. The
binding record is `docs/decisions/0040-server-move-first-run.md`.

- **First run:** `scriptorium-admin setup` is a read-only preflight;
  `migrate` is explicit and PG18-only; `user create/list` provides the
  first account with a TTY prompt or `--password-stdin`, 12–1024
  characters, Argon2id, and no open registration.
- **Move:** CLI `backup export`/`restore` share the 0039 core; restore
  requires an existing importer, refuses a non-empty target unless
  `--force`, and uses strict public names (a live name or another owner's
  tombstone fails before writes). The API owner restore keeps 0039
  auto-suffix. `verify` is a read-only post-move gate for DB/head,
  names/pointers, artifacts/manifests/jail, media hashes, config, and TLS.
- **Config parity:** `backend/app/config.py` is the one loader for
  `/etc/scriptorium/config.env`; no shell evaluation, malformed lines
  fail loud, and a real environment variable (including empty) wins.
  Existing env readers were migrated.
- **TLS:** `backend/app/tls/` implements native HTTPS termination,
  local CA/leaf generation, SAN detection/normalization, import
  validation, renewal, history/rollback/prune, HSTS, a hardened
  ECDHE+AEAD context, and the HTTP→HTTPS `308` redirect. The web unit
  uses `TlsUvicornWorker` on 443; the redirect unit serves port 80.
  Proxy headers are disabled; `X-Forwarded-For` remains untrusted.
- **Ownership/packaging:** `postinst` creates the group/user/dirs,
  seeds config once, applies `scriptorium:scriptorium` recursively,
  forces `ca.key` back to `root:root 0600`, and enables the renewal
  timer. Units are sandboxed with read-only `/opt` and `/etc`;
  privileged binds use `CAP_NET_BIND_SERVICE`.
- **Dependencies:** added `cryptography==50.0.2` and
  `uvicorn-worker==0.4.0`, regenerated both backend locks, and added a
  local mypy stub for `uvicorn_worker` (no `py.typed`).
- **Tests:** new `test_config.py`, `test_tls.py`, `test_tls_redirect.py`,
  `test_cli.py`, and TLS packaging assertions. Local gates: backend
  **169 passed, 51 skipped** (`-W error`; live PG18/Redis unavailable),
  ruff/format/mypy clean; packaging **12 passed**; frontend
  typecheck/lint/format/19 Vitest/build/audit pass; docs validator
  passes; `pip-audit --strict` clean. Live CLI/backup tests run in CI.
- **Docs:** decision 0040, approved plan, `operations/tls.md`,
  `operations/server-move.md`, rewritten `operations/install.md`,
  architecture/threat/compatibility/onboarding/structure/roadmap/docs
  index/changelog, and new `docs/history/` (project history +
  environment-migration handoff).
- **Fixed during the gate:** `test_config.py` used
  `get_setting("SECRET_KEY")`, which was bypassed by the dummy
  `SECRET_KEY` set at import time in `test_auth_api.py`; the test now
  exercises `load_config()` directly. The first CI run then found a
  second isolation defect: live CLI tests mutated `os.environ` directly
  and CI's ambient `DATABASE_URL` leaked into config tests. CLI tests now
  use `monkeypatch.setenv`, and config tests clear the specific ambient
  keys they assert.
- **Closeout:** implementation `f7f6d06` was pushed to `dev`; the first
  CI run was red on the isolation defect above, fixed in `09850d6`. All
  three workflows are green on `09850d6`, and `main` is fast-forwarded to
  the final `dev` closeout commit so both branches are byte-identical.
  The live CI run is the coverage for the CLI/backup tests that skip in
  this local environment.
- **Known limits:** local live PG18/Redis is unavailable here (Docker
  socket denied), so live tests are CI-only; TypeScript ESLint remains
  blocked by `typescript-eslint`'s TS <6.1 peer range (`tsc --noEmit`
  is the type gate); no ACME, reverse proxy, HSTS preload, or automatic
  renewal of imported certificates; page aliases, M5, distribution, and
  SEO remain later phases.

## Previous tranche (2026-11-01): backup/restore 0039

Owner rulings A1/B3/C1/D1/E1 implemented; docs/brain closeout complete.
The first CI run found a build defect in the live round-trip test; fixed
in `55276ff` and CI ×3 green. Tranche pushed as `31ac99d` + `55276ff`.

- **Backend:** `app/backup/` (`manifest`, `archive`, `snapshot`, `export`,
  `restore`, `execute`, `tokens`), `app/routers/backups.py`, shared
  `app/serving/names.py`, migration `0010backup` (`public_names.owner_id`,
  `backup_jobs`). Editorial export streams a ZIP/`.tar.gz` with
  `X-Backup-SHA256`/`X-Backup-Size`; Full export is a `202` job. Restore
  validates the manifest, rows, FKs, cycles, payload inventory, hashes,
  and sizes before any DB write; it creates a fresh Athenaeum, maps every
  row to fresh UUIDs, preserves build numbers/pointers, rewrites media
  URLs, nulls unmatched identities, reclaims free/same-user-tombstoned
  public names, and stages/cleans files on failure. Full downloads use a
  single-use 15-minute HMAC token; archives are deleted after send/expiry.
- **Worker:** `app/worker/celery.py` (`-A app.worker` discovery),
  `include=["app.worker.tasks"]`, and `@shared_task` names for build +
  backup export/restore. Fixed three latent production-only defects (app
  resolution, task registration, build dispatch in `celery` mode);
  dispatch failure marks the job/build failed and returns `503`.
- **Frontend:** `BackupPanel` on the Athenaeum page (Editorial/Full,
  ZIP/`.tar.gz`, streamed download, Full job polling + single-use download,
  restore upload/job/result/warnings, cache invalidation), shared
  `authorizedFetch`, `lib/download.ts`, client tests.
- **Packaging:** `SC_BACKUP_DISPATCH`, `SC_BACKUP_ROOT`, commented
  `SC_BACKUP_*` overrides; `postinst` creates `backups/`.
- **Gates:** backend `141 passed, 48 skipped` locally; archive suite 23
  passed; live-DB backup suite runs in CI against PG18/Redis; ruff/format/
  mypy clean. Frontend typecheck, lint, format check, 19 Vitest tests,
  production build, and high-severity audit pass.
- **CI-discovered media-build fix:** the live round-trip's first build
  failed because `runner._materialize` required a `_static/media/` prefix
  while content stores canonical `/_static/media/...` URLs. Staging now
  strips the leading slash (Sphinx resolves `/` against the source dir)
  and still rejects traversal/backslash paths; tests cover canonical
  staging and a full offline Sphinx build with media. Fixed in `55276ff`.
- **Docs:** decision 0039 implementation note, changelog
  `2026-11-01-backup-restore.md`, API/data-model/overview/operations/
  security/celery, brain.
- **Known limits:** local live PG18/Redis unavailable (Docker socket
  denied), so the new live tests only run in CI. TypeScript ESLint remains
  blocked by typescript-eslint's TS `<6.1` peer range; `tsc --noEmit` is
  the type gate.
- **Next:** owner rulings on Q-SM-A…M, then implement the server-move/
  first-run phase; then page aliases, M5, and the SEO plan.

## Previous tranche (2026-10-31): editor/content completion 0038

Implemented and **pushed (`476dfff`)**; CI ×3 green. The live-PG18 run
completed 159 tests with no skips, covering media/history and migration
`0009media`.

- **Backend:** `GET /auth/me`; history detail + restore endpoints
  (`document_restored` audit, new version appended, media re-validated);
  `media_assets` (migration `0009media`), raw-body upload with magic-byte
  sniffing + 10 MiB streaming cap + atomic write, member-scoped list and
  authenticated content read; document saves reject external/foreign image
  refs; builds copy referenced media into `_static/media`; RST/MyST image
  round-trip.
- **Frontend:** first real app — Vite/React shell, memory-only token +
  refresh-cookie bootstrap, login/dashboard/Athenaeum/editor pages, lazy
  route chunks, TipTap surface, tree CRUD, history restore, source
  preview, single-file import, conflict reload/overwrite, unsaved-change
  warning, canonical media URL ↔ blob mapping.
- **Gates:** backend `115 passed, 44 skipped` locally, ruff/format/mypy
  clean; CI backend `159 passed` with no skips. Frontend typecheck, lint,
  format check, 16 Vitest tests, build, and high-severity audit gate pass.
  CI frontend job now runs typecheck, test, and build.
- **Docs:** decision 0038, changelog, API/data-model/conversion/frontend/
  overview/security/roadmap, brain.
- **Known limits:** live PG18/Redis unavailable locally (Docker socket
  denied), so media/history/migration tests only run in CI. TypeScript
  ESLint remains blocked by typescript-eslint's TS `<6.1` peer range;
  `tsc --noEmit` is the type gate.
- **Next:** backup/restore was the next phase and is now implemented
  (0039, this tranche). Server move/first-run provisioning, page aliases,
  M5, and the SEO plan remain later.

## Previous tranche (2026-10-30): technical-stack upgrade 0037

Owner-approved upgrade is implemented and pushed; no product behavior,
schema, URL, or SEO change.

- **Python 3.14.10 bundled** via python-build-standalone release
  `20261026` (x86_64 + aarch64 SHA-256 pins). `fetch-python.sh` extracts
  the runtime; `build-app-venv.sh` builds the runtime-only app venv from
  `backend/requirements.prod.lock`; `build-venv.sh` builds the engine-only
  venv from `packaging/build-requirements.lock`; `relocate-venv.sh`
  rewrites shebangs/pyvenv.cfg to the installed paths. The target host
  never runs pip.
- **Redis 8.10.2 bundled** via `build-redis.sh` (source SHA-256 pinned,
  core `redis-server` + `redis-cli`). New `scriptorium-redis.service`
  (`Type=notify`, `scriptorium` user, localhost, AOF); web/worker units
  require it. `nfpm.yaml` packages both runtimes + app/build venvs and
  drops distro `python3.12`/`redis` dependencies. `postinst` seeds
  `/etc/scriptorium/redis.conf` and verifies every runtime.
- **Backend pins:** FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1,
  Uvicorn 0.54.0, Gunicorn 26.2.0, SQLAlchemy 2.1.6, Alembic 1.20.1,
  asyncpg 0.32.0, Celery 5.6.3, redis-py 6.4.0, Sphinx 9.2.0, MyST 5.1.0;
  docutils remains 0.22.4. Ruff 0.17.3 findings were fixed (FastAPI
  dependencies converted to `Annotated[...]`; no blanket B008 ignore).
- **Frontend pins:** Node 26.13.0 LTS / npm 11.20.0, React 19.3.1,
  TypeScript 7.0.2, TipTap 3.32.1, React Router 8.5.1, TanStack Query
  5.105.0, RHF 7.91.0, Zod 4.6.7, Radix latest, Vite 8.3.5, Vitest
  5.0.5, ESLint 10.13.0, Prettier 3.9.10, Playwright 1.64.1, Testing
  Library 16.3.3, axe-core 4.14.0. Support matrix:
  `docs/technology/frontend.md`.
- **Gates:** backend `114 passed, 40 skipped`; ruff/format/mypy clean;
  `pip-audit` clean; frontend `npm ci` + lint + format check + audit
  clean (0 vulnerabilities). docutils-0.23 probe: 59 passed with Sphinx
  9.2.0; pin stays. Known scoped exception: typescript-eslint 8.72.1
  excludes TS 7, so ESLint covers JS/config only and `tsc --noEmit` is
  the type gate.
- **Package validation:** nfpm 2.48.0 built a 117 MB `.deb` from the
  bundled runtimes; extraction verified Python 3.14.10, app imports,
  build-engine imports, Redis 8.10.2, and `scriptorium-admin --help`.
  The runtime and both venvs ship without pip/bytecode.
- **Closeout:** pushed as `9d645e3`; lint-type-test, packaging, and
  security workflows all green.
- **Still pending:** M5 signed package pipeline (lintian/rpmlint,
  SBOM/provenance, clean-install matrix); SEO phase; distribution.

## Previous tranche (2026-10-28): URL durability 0036

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
- Pushed as `be5af83`; all three CI workflows green.

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
1. **Page aliases:** owner-approved later phase; plan/rulings first.
2. **M5:** signed package pipeline (lintian/rpmlint, SBOM/provenance,
   clean-install matrix) and fold the first-run/TLS runbooks into the
   admin guide.
3. **Dedicated SEO phase:** owner requested a structured, detailed plan
   in its own phase; every SEO feature/attribute must be user-controllable
   per Athenaeum in the editorial panel. Do not implement before the
   plan and owner rulings.
4. **Distribution phase:** present Q-DIST-A…D (credentials, delivery
   semantics, target roster, React shell) and wait; do not implement
   before owner approval.
5. **Junk-sweep before every gate:** re-read written files; grep the
   standing junk markers before committing.

## Gotchas (carried)
- **Shared config loader (0040):** `app/config.py` does no shell
  evaluation. A present-but-empty environment variable wins over the
  file (so `SECRET_KEY=` fails loud). Malformed `KEY=VALUE` lines raise
  `ConfigError`; do not add `source`/expansion semantics. Tests must
  call `load_config()` when asserting parse failures, because test
  modules set a dummy `SECRET_KEY` at import time.
- **TLS CA key:** the local CA private key is `root:root 0600` and the
  service cannot read it. `tls generate` needs root only for the default
  `/etc/scriptorium/tls`; tests use a non-default `SC_TLS_ROOT`
  unprivileged. `postinst` applies `scriptorium:scriptorium` then forces
  `ca.key` back to root.
- **TLS worker:** `TlsUvicornWorker` requires Gunicorn `--certfile` and
  `--keyfile` and refuses to run without them. It installs the hardened
  `ssl_context_factory` after the base Uvicorn config is created; keep
  proxy headers disabled (`--no-proxy-headers`). Do not add a plaintext
  app listener.
- **Redirect safety:** the port-80 app honors `Host` only when it
  matches an active certificate SAN; otherwise `SC_TLS_REDIRECT_HOST`, a
  certificate SAN, or `400`. Never reflect an arbitrary Host.
- **Strict move names:** CLI restore (`strict_names=True`) fails on a
  live name or another owner's tombstone; free/same-user-tombstoned
  names are claimable. `--force` bypasses only the empty-target guard.
  The API restore keeps 0039 auto-suffix — do not conflate the paths.
- **TLS versions:** version IDs include UTC microseconds + 8 hex chars;
  history ordering is deterministic. Prune protects the active version
  even if it is older than the newest `--keep`.
- **CLI privilege:** `scriptorium-admin` refuses any account other than
  root or `scriptorium`. `setup`/`verify` are read-only; `migrate` is
  explicit; `postinst` never migrates or issues certificates.
- **Live CLI tests:** `test_cli.py` live cases skip without
  `DATABASE_URL`; they run in CI against PG18/Redis. Do not claim a local
  skip is coverage.
- **Mypy/uvicorn-worker:** the package has no `py.typed`; the local stub
  in `backend/typings/` plus `mypy_path = "typings"` is the approved
  mechanism. Do not add a broad missing-imports ignore.
- **Sphinx 9.2 theme:** `theme.conf` MUST carry `inherit = none`
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
- Migrate head `0010backup`; verify migration SQL against older
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
- **Backup/restore (0039):** archives are untrusted; validate the whole
  manifest/inventory/hashes before any DB write. `public_names.owner_id`
  is the only way to distinguish a user's own tombstone from another
  user's — never reclaim a name without checking it. Restore maps every
  row to fresh UUIDs and rewrites media URLs in TipTap/source/history;
  artifact HTML stays untouched (`site_id` remains the old public slug).
  Build numbers/pointers are preserved; queued/running builds are omitted
  in Full restore. Full downloads are single-use (`UPDATE … WHERE
  downloaded_at IS NULL … RETURNING`) and expire in 15 minutes; files are
  unlinked after send/expiry. Editorial restore is synchronous `201`;
  Full restore is a `202` job. `SC_BACKUP_DISPATCH=celery` in production;
  `inline` in dev/CI. Celery must resolve `-A app.worker` via
  `app/worker/celery.py` and register tasks via `include`.
