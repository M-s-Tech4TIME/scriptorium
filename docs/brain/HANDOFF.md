# HANDOFF

Last updated: 2026-10-21 / M4-C1 staged (decision 0026 + migration 0006)

## Was doing
M4-C1: decision 0026 (per-Athenaeum site builds — P1–P4, staging/
artifact reconciliation, design mandates; all owner-ruled) +
migration 0006 (build_number per-Athenaeum, athenaeum_id FK,
grimoire_id relaxed, ck_builds_site, uq_builds_athenaeum_number;
legacy rows keep the grimoire key and share one derived legacy
sequence). Q-SERVE-A…E + Q-DIST-A…D parked in OPEN-QUESTIONS.

## Next steps (in order)
1. **M4-C2 source generation** (`app/sphinx` package): TipTap →
   deterministic per-folio `.rst`/`.md` via the M2 exporters, chapter
   toctree assembly, one `conf.py` per Athenaeum (MyST enabled when any
   book is myst); pure functions → offline unit tests. Edge cases
   **RULED** (E1–E3, owner A/A/A 2026-10-21, recorded 0026 §Edge
   rulings): empty Athenaeum → 422; empty book → skip + note; one
   build per Athenaeum at a time (409 while queued/running — C3
   enforces).
2. **M4-C3 runner + Celery task** (`app/worker`): stage → limited
   subprocess (`sphinx -W`, RLIMIT, no network, minimal env) → artifact
   `/var/lib/scriptorium/artifacts/{athenaeum}/{build_number}/`; status
   queued→running→ok|failed; endpoints `POST /api/v1/athenaeums/{id}/
   builds` (owner-only), GET list/one (members); Sphinx 9.1.0 into the
   locked stack + `docs/technology/`; live tests.
3. **M4-C4** — packaging worker `After=redis` note; the 0017
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
