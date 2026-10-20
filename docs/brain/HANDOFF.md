# HANDOFF

Last updated: 2026-10-21 / C3.5 athenaeum layer staged with this sync (0020)

## Was doing
M3 C3.5 (decision 0020): migration `0004_athenaeums`, `Athenaeum` model,
`routers/athenaeums.py` (CRUD + delete-refusal + nested sidebar),
`categories.py` re-homed to athenaeum paths, `grimoires.py` scoping +
cross-Athenaeum move, `main.py` mount, `test_athenaeums_api.py` (4 live
cases) + `test_grimoires_api.py` rewrite (5 live cases), test_migration
EXPECTED_TABLES → 11, docs restructure, brain sync.

## Next steps (in order)
1. Commit C3.5 (`feat: athenaeum layer as native library hierarchy (0020)`),
   push, verify CI green ×3 (Rule 7).
2. C4 tree endpoints: GET `/grimoires/{id}/tree`, node create/move/
   rename/delete — atomic sibling reorder (Q-M3-4=A), slug integrity
   `[a-z0-9-]+`, per-sibling-set partial-unique slugs, category/page kinds.
3. C5 document endpoints: GET/PUT `/nodes/{node_id}/document` with
   `expected_version`→409, version+history append, import-from-source→422.
4. Then: M3 complete report; M4 next (gated Sphinx builds; docutils 0.23
   gate per 0017; packaging `After=redis` systemd note).

## Gotchas (carried)
- Migrate head `0004athenaeum`; verify migration SQL against 0001/0003
  definitions before push (C1 lesson). Downgrade re-adds `user_id` as a
  trailing column — harmless, but backed by backfill SQL; roundtrip is
  CI-tested.
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
