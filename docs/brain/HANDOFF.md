# HANDOFF

Last updated: 2026-10-21 / M3 COMPLETE — C6 green (f3e7bc1) — brain synced

## Was doing
M3 C6: decision 0025 (grimoire duplication) — LANDED green ×3 on
`f3e7bc1` after two live-path fix-ups (missing owner Membership on the
copy; the copy's own v1 history trace — ruling-c clarified in 0025).
Q-M3-16a–e were ruled by the owner then implemented same-day.

## Next steps (in order)
1. **M3 is complete (C1–C6, all green ×3).** Deliver the M3-complete
   report to the owner.
2. M4 builds — gated Sphinx builds; docutils 0.23 gate per 0017;
   packaging `After=redis` systemd note; sources jail keyed by grimoire
   id (vetoable micro-default from the plan).
3. Dedicated phase: serving as a website (decisions pending: build
   granularity, visibility/publishing, serving mechanics, URL scheme).
4. Dedicated phase after that: URL durability after renames
   (aliases/redirects/immutable build identity).

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
