# HANDOFF

Last updated: 2026-10-21 / Ref: 0027 recorded, green ×3 (`52a2124`) — awaiting design tokens

## Was doing
M4-C3.5 record tranche: **decision 0027** committed — the owner ruled
the theme is Scriptorium's **own, from scratch** (no builtin/third-party
template inheritance; engine fully inherited incl. vendored engine JS
`searchtools/doctools/sphinx_highlight/language_data`, pinned DOM
contracts). OPEN-QUESTIONS theme park flipped to RESOLVED (Q-C3.5-A);
sphinx.md theme section replaced the alabaster placeholder text;
changelog `2026-10-21-m4-own-theme-record.md`.

## Blocked / waiting on owner input (not an open question — input, not decision)
Theme **implementation** (templates + CSS) waits for the owner's
external design-consult tokens (palette/type/layout per the brief
delivered to them; binding floor: no webfonts/CDN, WCAG AA, tokens as
CSS custom properties, system stacks). The code-side mechanics are
already committed in 0027 — implementation on token arrival.

## Next steps (in order)
1. **M4-C3.5 implementation** (mechanics locked in 0027): theme
   package `backend/app/sphinx/theme/scriptorium/` (`theme.conf` no
   parent, `layout/page/search/genindex.html`, `static/scriptorium.css`);
   `sourcegen.py` `THEME_BASE = "scriptorium"` + `html_theme_path =
   ["theme"]`; `runner.py` `_materialize` copies the theme dir into the
   workspace + vendors the four engine JS files from the installed
   pinned Sphinx; search DOM ids locked by reading vendored
   `searchtools.js`; offline-but-real runner test (build ok, our CSS in
   artifact, search markup ids, `searchindex.js`) + sourcegen test
   updates; docs (sphinx.md theme section refresh) + changelog + brain;
   gates + push + CI ×3.
2. **M4-C4** — packaging (`packaging/` creates the isolated build venv,
   `SC_BUILD_PYTHON` pointed there; worker unit `After=redis`;
   `config.env` gains `CELERY_BROKER_URL` + `SC_*` build keys), the
   0017 docutils-0.23 probe mechanics, M4-complete report + brain sync.
3. **Junk-sweep before every gate:** re-read written files; grep the
   standing junk markers before committing.
4. Serving phase — resolve Q-SERVE-A…E first, then implement (theme
   brand-injection hooks + custom-CSS wiring land there, 0027).
5. URL-durability phase after serving; Distribution-phase concepts
   (Q-DIST-A…D) presented before their implementation (incl. the React
   shell format).

## Gotchas (carried)
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
