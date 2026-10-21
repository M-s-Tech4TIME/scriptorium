# HANDOFF

Last updated: 2026-10-21 / C3.7 folio/chapter staged (0022) — brain sync

## Was doing
M3 C3.7: decision 0022 (folio + chapter vocabulary; single-membership
confirmation) — migration `0005` rewrites `nodes.kind` (CHECK dropped →
data → CHECK recreated, `page→folio`, `category→chapter`), models
docstrings, GLOSSARY, data-model, changelog.

## Next steps (in order)
1. Commit C3.7, push, verify CI green ×3 (Rule 7).
2. C4 tree endpoints (decision 0023: D1=A delete-refusal incl. document
   check, D2=A owner-only, cycle guard, displacement reorder) —
   `test_tree_api.py`.
3. C5 document endpoints (`expected_version`→409, history append,
   import→422, D2 role mapping).
4. C6 grimoire duplication (deep copy; Q-M3-16) → M3 report → M4.

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
