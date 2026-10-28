# 2026-10-28 — URL durability (0036)

## Scope

Owner-approved A1/B1/C1/D1/E1/F1 with URL-scheme Option 1 retained.
Site-level public names are owner-renamable; old names are permanent
aliases; deletion leaves permanent tombstones. Page-path aliases, SEO,
and distribution remain later phases.

## Implemented

- Migration `0008urldurability` + `PublicName` model: single global
  `public_names` namespace, partial unique current row per Athenaeum,
  nullable FK `SET NULL` tombstones, backfill of existing public slugs.
- Create/delete registry hooks and transaction-scoped namespace lock.
- Owner-only `PATCH /api/v1/athenaeums/{id}/public-slug`: validation,
  reserved words, current/alias/tombstone collisions, same-site
  reversion, audit, no rebuild.
- Serving alias resolution with auth-before-`308`, suffix/query
  preservation, flattening, public/private headers.
- Publication response `public_aliases`.
- Tests: live rename/alias/tombstone/reversion/collision/cache/audit,
  migration backfill + round-trip.
- Docs: decision 0036, amendments to 0035/0021/0026, architecture/API/
  data-model/security/overview/codebase-map/roadmap, changelog, brain.

## Verification

- Fresh local PG16: **149 passed / 1 deselected** (PG18 version test
  excluded locally; TCP Redis used for auth and ratelimit tests).
- `ruff`, `ruff format --check`, `mypy --strict`, `compileall`, docs
  validator clean.
- Headless Chrome followed an alias `308` to the canonical page and
  loaded its assets.
- Pushed as `be5af83`; all three CI workflows green (lint-type-test incl.
  docs-brain, security, packaging).

## Next

Dedicated SEO phase plan (per-Athenaeum editorial controls) and
distribution Q-DIST-A…D; sequencing not yet ruled.
