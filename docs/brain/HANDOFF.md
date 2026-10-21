# HANDOFF

Last updated: 2026-10-22 / Ref: 0028 recorded — C3.5 code tranche next

## Was doing
M4-C3.5 record chain: **decision 0028 committed** — the owner approved
the full design-baseline sheet (Tabler inline-sprite icons, custom
Pygments style, **first-party copy script amending 0027's JS clause**,
zero extensions v1, fixed scheme, no logo v1, icon breadth) plus two
ruled exceptions: an 11-anchor per-type callout palette
(`--sd-adm-<type>-{rule,bg,ink}`, blue/violet/teal/rust added, uniform
`--sd-page-ink` body ink) and all-caps bold verdigris category labels
(D15 owner-revision). Engine-asset mechanics verified against Sphinx
9.1.0 (3 vendored JS + builder-emitted `language_data.js` /
`documentation_options.js`); search DOM contract read off the vendored
`searchtools.js` and pinned. Consult gaps (missing reference HTMLs,
CDN icon loader, declared-inaccurate preview) inventoried and resolved
by the owner.

## Next steps (in order)
1. **M4-C3.5 code tranche** (0027 + 0028 are the full spec — no design
   decisions remain): theme package
   `backend/app/sphinx/theme/scriptorium/` (`theme.conf` no parent,
   `layout/page/search/genindex.html`, `static/scriptorium.css` from
   the consult tokens + `--sd-adm-*` 33 tokens, inline Tabler sprite in
   layout, first-party `static/scriptorium.js`, Pygments style module
   wired via conf `pygments_style`); `sourcegen.py`
   `THEME_BASE = "scriptorium"` + `html_theme_path = ["theme"]`;
   `runner.py` `_materialize` copies the theme dir into the workspace +
   vendors `searchtools/doctools/sphinx_highlight.js` from the pinned
   Sphinx (`language_data.js` is builder-emitted); templates honor the
   pinned search contract (`#search-results`, `#search-progress`,
   `input[name="q"]`, `role="main"`, `data-content_root`, script
   wiring, `Search.init()` self-runs); offline-but-real runner test
   (build ok, our CSS in artifact, search markup ids, `searchindex.js`,
   vendored engine JS present, `scriptorium.js` + CSS referenced) +
   sourcegen test updates (conf asserts) + AA contrast verification
   test; docs (sphinx.md theme section refresh) + changelog + brain;
   gates + push + CI ×3. Offer the owner a local browser preview of a
   built artifact before push.
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
