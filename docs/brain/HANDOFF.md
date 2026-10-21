# HANDOFF

Last updated: 2026-10-21 / M4-C2 LANDED (3a15b52, CI ×3) — brain synced

## Was doing
M4-C2: deterministic sourcegen (`app/sphinx/sourcegen.py`) — LANDED
green ×3 on `3a15b52` (record `7d14f3a` first: edge rulings E1–E3
owner A/A/A). 14 offline tests; suite 59 passed, 33 skipped.
Micro-defaults disclosed: docname `index-p` mangle, toctree-title
`«»` sanitize, `alabaster` interim theme (curated theme = C3).

## Next steps (in order)
1. **M4-C3 runner + Celery task** (`app/worker`): load snapshots (same
   ordering as the nested sidebar), call `plan_site`, materialize into
   the per-build workspace, run `sphinx -W` inside the limited
   subprocess (`RLIMIT` CPU/time+memory+processes, no network, minimal
   env) → artifact
   `/var/lib/scriptorium/artifacts/{athenaeum}/{build_number}/`; status
   queued→running→ok|failed; endpoints `POST /api/v1/athenaeums/{id}/
   builds` (owner-only; E3: while queued/running → `409`), GET list/one
   (members); numbering `max(build_number)+1`; Sphinx 9.1.0 into the
   locked stack + `docs/technology/`; live tests (hardened `_run`).
2. **M4-C4** — packaging worker `After=redis` note; the 0017
   docutils-0.23 probe mechanics; M4-complete report + brain sync.
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
