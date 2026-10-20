# HANDOFF

Last updated: 2026-10-20 / C2.5 green (a6c17bb) + C3 staged with this sync

## Was doing
M3 C3: `app/audit.py` helper + `routers/categories.py` +
`routers/grimoires.py` (incl. member management) + `tests/test_grimoires_api.py`
(5 live cases) + `docs/architecture/api.md` (new endpoint tables +
micro-defaults) + changelog + brain sync.

## Next steps (in order)
1. Commit C3, push, verify CI green ×3 (Rule 7).
2. C4 tree endpoints: GET `/grimoires/{id}/tree`, node create/move/
   rename/delete — atomic sibling reorder (Q-M3-4=A), slug integrity
   `[a-z0-9-]+`, per-sibling-set partial-unique slugs, category/page kinds.
3. C5 document endpoints: GET/PUT `/nodes/{node_id}/document` with
   `expected_version`→409, version+history append, import-from-source→422.

## Gotchas (carried)
- Migrate head `0003grimoire`; verify migration SQL against 0001 definitions.
- conftest migrates to head ONCE (DATABASE_URL set); one loop per test —
  always end test coroutines with `await app_teardown()`.
- `Membership` rows cascade with grimoires: after delete, member requests
  become 404 again (covered by tests).
- Explicit-NULL pattern: use `model_fields_set` when a PATCH field must
  distinguish omission vs null (grimoire category_id).
- starlette.testclient warns → httpx.ASGITransport; ratelimit tests flush
  the CI Redis DB (conftest REDIS_TEST_URL).
- Keep per-step work small; write files one at a time (past derailments).
