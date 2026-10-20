# HANDOFF

Last updated: 2026-10-20 / M3 C1 staged with this sync (on `dev`, CI verify pending)

## Was doing
M3 commit C1: decision 0018 record, migration `0003_grimoires_categories`
(full projects→grimoires rename incl. column/constraint/index renames +
per-user `grimoire_categories` + `grimoires.category_id`), model renames
(`Grimoire`/`GrimoireCategory`, `grimoire_id` columns), `test_migration`
10 tables, docs (data-model.md, postgresql.md, changelog).

## Next steps (in order)
1. Commit `feat: grimoire rename + categories schema (0018)`, push,
   verify CI green ×3 (Rule 7).
2. C2 auth/session endpoints (login/refresh/logout; rotating refresh
   cookies; family store wired) + `test_auth_api.py` (live PG).
3. C3 categories + grimoires + memberships (+audit rows) endpoints.
4. C4 tree endpoints (atomic sibling reorder; slug invariants).
5. C5 document endpoints (expected_version→409, history append,
   import-from-source→422).

## Gotchas (carried)
- Migrate head now `0003grimoire`; live DB must migrate before C1 live tests.
- CI mypy MUST use `--config-file backend/pyproject.toml` (0018 ratified).
- docutils 0.22.4 inline markup never nests; heading levels sequential —
  encoded in 0017 + conversion.md.
- Keep per-step work small; write files one at a time (past derailments).
