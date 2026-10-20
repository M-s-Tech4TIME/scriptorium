# HANDOFF

Last updated: 2026-10-20 / M3 C1 green (c26cd7e) + C2 staged with this sync

## Was doing
M3 C2: auth/session endpoints — `app/routers/auth.py` (login/refresh/
logout, rotating HttpOnly refresh cookie wired to the M2 family store),
`verify_dummy` enumeration guard, `test_auth_api.py` (5 live cases via
`httpx.ASGITransport`), docs (auth.md, changelog, OPEN-QUESTIONS Q-002).

## Next steps (in order)
1. Commit C2, push, verify CI green ×3 (Rule 7).
2. C3 categories + grimoires + memberships (+audit rows) endpoints
   (routers: grimoire_categories → 404-on-outsider rules live).
3. C4 tree endpoints (atomic sibling reorder; slug invariants).
4. C5 document endpoints (expected_version→409, history append,
   import-from-source→422).

## Gotchas (carried)
- Migrate head `0003grimoire`; **do NOT** rename columns on tables that
  never had them (C1's CI lesson: verify SQL against 0001 definitions).
- conftest now migrates to head ONCE when DATABASE_URL is set — new live
  test files sort before test_migration.py (C2's CI lesson); never rely
  on alphabetical ordering to migrate the schema.
- CI mypy MUST use `--config-file backend/pyproject.toml` (0018 ratified).
- starlette.testclient import deprecation-warns → use httpx.ASGITransport
  in tests (Rule 6 under -W error).
- docutils 0.22.4 fail-loud matrix = 0017 + conversion.md.
- Keep per-step work small; write files one at a time (past derailments).
