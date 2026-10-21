# HANDOFF

Last updated: 2026-10-21 / Ref: M4-C3 LANDED (1e1637e, CI ×3) — brain synced

## Was doing
M4-C3: runner + Celery + build endpoints — LANDED green ×3 on
`1e1637e` (record `c6c407d`, then `fadef93` pickling-secret fix +
`1e1637e` staging round-trip fixes). CI live suites prove: E1 422,
owner-only trigger, numbering 1→2, artifact on disk, E3 409,
member-visible GETs, failed run + crash log, and the migration
roundtrip against library-era rows. Micro-defaults disclosed in 0026
§C3 mechanics / §CI-discovered staging rulings.

## Blocked / open owner question
**Curated default theme base** (0026 mandate 2) — parked in
OPEN-QUESTIONS; MUST be presented with options before C4 packaging
presents the theme story. `alabaster` remains the placeholder.

## Next steps (in order)
1. **Owner question (Rule 4, present next):** curated default theme
   base (0026 mandate 2) — options + trade-offs before C4 packaging
   presents the theme story.
2. **M4-C4** — packaging (`packaging/` creates the isolated build venv,
   `SC_BUILD_PYTHON` pointed there; worker unit `After=redis`;
   `config.env` gains `CELERY_BROKER_URL` + `SC_*` build keys), the
   0017 docutils-0.23 probe mechanics, M4-complete report + brain sync.
4. Serving phase — resolve Q-SERVE-A…E first, then implement.
5. URL-durability phase after serving; Distribution-phase concepts
   (Q-DIST-A…D) presented before their implementation.

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
