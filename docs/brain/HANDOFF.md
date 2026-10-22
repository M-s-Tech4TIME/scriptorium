# HANDOFF

Last updated: 2026-10-22 / Ref: C3.5 code written + docs synced — commit/preview/push next

## Was doing
M4-C3.5 **code tranche complete, docs synced** (this staging): the
Scriptorium theme package shipped (`backend/app/sphinx/theme/
scriptorium/`: `theme.conf` `inherit = none`, four templates,
`scriptorium.css`, `scriptorium.js`, `style.py`), `sourcegen` wired
(`THEME_BASE`, `html_theme_path`, `pygments_style`, sidebar rows →
`html_context{'sidebar_categories'}`), loader fetches category labels,
runner `_materialize` stages theme + style module + engine assets and
fails loud, NOTICE + 0028 amendment + sphinx.md + changelog +
CURRENT-STATE. Two build-mechanics discoveries fixed en route (see
Gotchas): Sphinx 9.1 requires explicit `theme.inherit = none`, and with
a parentless theme the two `.jinja` static templates
(`documentation_options.js.jinja`/`language_data.js.jinja`) must be
vendored or the artifact 404s their rendered scripts (silent under
`-W`). Gates green locally: `75 passed, 36 skipped` (`-W error`, zero
warnings), `ruff check`/`format` clean, `mypy --strict` clean;
`types-Pygments==2.21.0.20260819` added dev-only (typing stubs for
mypy strict — reported to owner for visibility, same league as
existing dev pins). Junk sweep clean.

## Next steps (in order)
1. **C3.5 commit + preview + push:** owner offered a local browser
   preview of a built artifact (a probe build is materializable via
   `runner._materialize` + `sphinx -W -b html` with the dev venv as
   build python); commit
   (`feat(m4-c3.5): …` Conventional style, author
   `alsechemist <239932722+alsechemist@users.noreply.github.com>` +
   `Co-authored-by: OpenCode <opencode@local>`), push `dev`, verify CI
   green ×3 (`gh run list --branch dev`), fix-on-red if needed.
2. **M4-C4** — packaging (`packaging/` creates the isolated build venv,
   `SC_BUILD_PYTHON` pointed there; worker unit `After=redis`;
   `config.env` gains `CELERY_BROKER_URL` + `SC_*` build keys), the
   0017 docutils-0.23 probe mechanics, M4-complete report + brain sync.
3. **Junk-sweep before every gate:** re-read written files; grep the
   standing junk markers before committing.
4. Serving phase — resolve Q-SERVE-A…E first, then implement (theme
   brand-injection hooks + custom-CSS wiring land there, 0027;
   `[data-theme]` second scheme is its own later ruling, 0028).
5. URL-durability phase after serving; Distribution-phase concepts
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
- 0006: `ck_builds_site` (exactly one of grimoire_id / athenaeum_id);
  `Build` has a two-era key pattern — new code writes Athenaeum-keyed
  rows; `uq_builds_athenaeum_number` needs explicit max(build_number)+1
  per Athenaeum at trigger time (C3 will need `SELECT … FOR UPDATE`-style
  care, or serialize per library).
