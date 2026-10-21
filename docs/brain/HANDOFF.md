# HANDOFF

Last updated: 2026-10-21 / C5 documents staged (0024) — brain sync

## Was doing
M3 C5: decision 0024 (folio documents) — `routers/documents.py`
(GET/PUT `/document` + `/document/history`; `expected_version`→409,
version+history append, server-derived source cache, import→422,
editor/owner save rule), `test_document_api.py` (2 live cases), api.md
documents section, changelog.

## Next steps (in order)
1. Commit C5, push, verify CI green ×3 (Rule 7).
2. C6 grimoire duplication (deep copy; Q-M3-16) → M3-complete report.
3. M4 next (gated Sphinx builds; docutils 0.23 gate per 0017; packaging
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
