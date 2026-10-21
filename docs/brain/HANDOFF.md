# HANDOFF

Last updated: 2026-10-21 / M3 complete pending C6 CI — C6 staged (0025)

## Was doing
M3 C6: decision 0025 (grimoire duplication) — owner ruled Q-M3-16a–e;
`POST /grimoires/{id}/duplicate` deep-copies grimoire + tree + head
documents (v1, no history clone), fresh owner-only roster, caller-slug
or auto-suffix, any owned target library, copy-of-copy allowed;
`test_duplicate_api.py` (2 live cases); docs + brain.

## Next steps (in order)
1. Commit C6, push, verify CI green ×3 (Rule 7).
2. **M3-complete report to the owner** (all tranches green, micro-default
   recap).
3. M4 builds (gated Sphinx builds; docutils 0.23 gate per 0017;
   packaging `After=redis` systemd note) → dedicated serving phase →
   dedicated URL-durability phase.

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
