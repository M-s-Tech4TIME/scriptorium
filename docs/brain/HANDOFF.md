# HANDOFF

Last updated: 2026-10-21 / C5 green (034db20) — C6 parked on Q-M3-16 sub-decisions

## Was doing
M3 C5: decision 0024 (folio documents) — LANDED green ×3 on `034db20`
(two live-path fix-ups recorded in the C5 changelog: eager_defaults for
the onupdate timestamp; `_run` now guarantees the awaited disposal even
on failing asserts). API surface: GET/PUT `/document` +
`/document/history` with expected_version→409, version+history append,
server-derived source cache, import→422, editor/owner saves.

## Next steps (in order)
1. **C6 is blocked on Q-M3-16a–e** (PARKED in OPEN-QUESTIONS per Rule 4):
   duplication slug source, member scope, history depth, cross-library
   copies, copy-of-copy. Present to owner; implement after ruling
   (decision 0025) → M3-complete report.
2. M4 next (gated Sphinx builds; docutils 0.23 gate per 0017; packaging
   `After=redis` systemd note); then dedicated serving + URL-durability
   phases.

## Gotchas (carried)
- Migrate head `0005foliochapter`; verify migration SQL against older
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
