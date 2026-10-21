# HANDOFF

Last updated: 2026-10-21 / C3.6 slug-rename staged (0021) — brain sync

## Was doing
M3 C3.6: decision 0021 (slugs renamable at every layer; amends 0018) —
`AthenaeumPatch`/`GrimoirePatch` gain `{slug?}` (allowlist/`null` → 422,
scoped collision → 409, metas record changes), two new live tests, docs.

## Next steps (in order)
1. Commit C3.6, push, verify CI green ×3 (Rule 7).
2. C3.7 folio/chapter rename: decision 0022, migration `0005`
   (kind `page→folio` + `category→chapter`, CHECK reuse `ck_nodes_kind`),
   models wording, glossary, docs — push, CI ×3.
3. C4 tree endpoints (decision 0023: D1=A delete-refusal incl. document
   check, D2=A owner-only, cycle guard, displacement reorder) —
   `test_tree_api.py`.
4. C5 document endpoints (`expected_version`→409, history append,
   import→422, D2 role mapping).
5. C6 grimoire duplication (deep copy; Q-M3-16) → M3 report → M4.

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
