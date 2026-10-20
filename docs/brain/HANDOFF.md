# HANDOFF

Last updated: 2026-10-20 / C2 green (aee1872) + C2.5 (0019 limiter) staged

## Was doing
M3 C2.5: decision 0019 record (Q-002=B login rate limiting), `app/limiter.py`
(Redis fixed window, fail-closed), login-router wiring (check→429/503,
clear-on-success, audit row), `test_ratelimit_api.py` (4 live cases),
CI `redis:8.10.2` service, docs (redis.md, auth.md, changelog, brain).

## Next steps (in order)
1. Commit C2.5, push, verify CI green ×3 (Rule 7).
2. C3 grimoire_categories + grimoires + memberships endpoints (+audit rows)
   (`/api/v1/grimoire-categories`, `/api/v1/grimoires`, member management).
3. C4 tree endpoints (atomic sibling reorder; slug invariants).
4. C5 document endpoints (expected_version→409, history append,
   import-from-source→422).

## Gotchas (carried)
- Migrate head `0003grimoire`; verify migration SQL against 0001 definitions
  (C1 lesson: grimoires never had a project_id column).
- conftest migrates to head ONCE when DATABASE_URL is set; test files sort
  before test_migration.py — file order must not decide schema availability.
- One event loop per test: `db.reset_engine()`/`dispose_engine()` and
  `limiter.reset_client()` (conftest autouse) — cached clients never cross
  dead loops; engines must be disposed ON their owning loop (Rule 6).
- test_ratelimit flushes the Redis keyspace (tests own the CI DB /1).
- CI mypy MUST use `--config-file backend/pyproject.toml` (0018 ratified).
- starlette.testclient import warns → use httpx.ASGITransport (Rule 6).
- docutils 0.22.4 fail-loud matrix = 0017 + conversion.md.
- Keep per-step work small; write files one at a time (past derailments).
