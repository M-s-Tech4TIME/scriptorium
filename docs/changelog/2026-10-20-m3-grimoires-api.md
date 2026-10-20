# 2026-10-20 — Categories, grimoires, members endpoints (M3 C3)

- Router tranche per decision 0018: `/api/v1/grimoire-categories` (own-rows
  CRUD + explicit-position reorder), `/api/v1/grimoires` (list/create/
  detail/patch/delete), `/api/v1/grimoires/{id}/members` (roster management).
- RBAC wiring: `require_membership` per request — outsiders uniform `404`,
  under-privileged members `403`; mutations owner-only except self-leave.
- Grimoire creation is atomic: grimoire row + `owner` membership + audit in
  one transaction; slug allowlist `[a-z0-9-]+` (422), dup slug (409), NULL
  category allowed (Q-M3-8), foreign category (404).
- Category delete flips its grimoires to Uncategorized (NULL) — Q-M3-7.
- Explicit-NULL PATCH clears `category_id` (pydantic `model_fields_set`
  distinguishes omission vs explicit null); `source_format` immutable
  (micro-default, owner-vetoable, documented).
- Member roles: editor/viewer only via API; owner role fixed (no transfer
  yet); owner self-removal blocked; unknown email 404, dup 409.
- Audit rows one-per-mutation via `app/audit.py` staged helper (same tx).
- New surface documented: `docs/architecture/api.md` (endpoint tables +
  conventions + micro-defaults).
- Tests: `test_grimoires_api.py` — 5 live cases covering the full matrix
  (category lifecycle incl. delete→uncategorized; slug/idor/audit;
  owner-only patches; member flows; delete cascades + membership-loss 404).
- Docs/brain synced; no schema change (C1 migration stands); offline suite
  45 passed / 19 skipped.
- CI fix-up: 422 constant renamed (`HTTP_422_UNPROCESSABLE_CONTENT`);
  category reorder is insert-displacement (position = 1-based index at
  patch time, siblings compacted in-tx); test payload UUIDs str()-ed;
  `_run` disposal in try/finally so mid-test failures still release loops.
