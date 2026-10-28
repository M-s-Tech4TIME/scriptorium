# 2026-10-28 — URL durability (0036)

Owner-approved A1/B1/C1/D1/E1/F1; URL-scheme Option 1 confirmed.

## Schema

- Migration `0008urldurability` adds `public_names`:
  - `slug` text primary key (single global namespace);
  - nullable `athenaeum_id` FK `ON DELETE SET NULL`;
  - `is_current`, `created_at`, `retired_at`;
  - partial unique index for one current name per live Athenaeum.
- Backfills every existing `athenaeums.public_slug` as its current row.
- Sites deleted before 0008 have no row to tombstone; post-0008 API
  deletion always leaves tombstones.
- Downgrade drops the registry (aliases created after 0008 are not
  recoverable on downgrade).

## API

- `PATCH /api/v1/athenaeums/{id}/public-slug` (`{public_slug}`), owner-only:
  - `[a-z0-9-]+`, 1–160, reserved `latest`/`stable`/`b`/`_static`/`api`
    → `422`;
  - another site's current/alias/tombstone → `409`;
  - same-site retired alias → allowed reversion;
  - same-name no-op; old name becomes permanent alias; no rebuild;
  - audit `athenaeum_public_slug_changed`.
- Creation inserts the current registry row; deletion retires all of the
  site's names and leaves permanent tombstones.
- `GET /athenaeums/{id}/publication` adds
  `public_aliases: [{slug, retired_at}]`.

## Serving

- `site.py` resolves current names and aliases through `public_names`.
- Aliases authorize the current Athenaeum before redirecting.
- Alias redirects: `308`, relative `Location`, suffix/query preserved,
  flatten to current canonical name; tombstones/unknown names `404`.
- Public alias: `Cache-Control: no-cache`; private alias:
  `private, no-store`, `Vary: Cookie`, `X-Robots-Tag: noindex, nofollow`.
- Canonical root/channel/numbered slash redirects remain `307`.

## Tests

- Live: rename, private auth-before-redirect, owner/member/outsider,
  public/private alias headers, root/channel/numbered/asset suffix
  preservation, query preservation, flattening, reversion, same-name
  no-op, reserved/invalid `422`, foreign `404`, current/alias/tombstone
  `409`, tombstone non-reuse, editor-rename independence, publication
  aliases, audit rows.
- Migration: 0008 backfill + upgrade/downgrade/upgrade round-trip.
- Local fresh PG16: 149 passed / 1 deselected (PG18 version test
  excluded locally; TCP Redis used for auth and ratelimit tests);
  ruff/format/mypy/compileall clean. Headless Chrome followed an alias
  `308` to the canonical page and loaded its assets. CI PG18
  verification pending closeout push.

## Docs

Decision 0036; amendments to 0035/0021/0026; architecture/API/data-model/
security/overview/codebase-map; brain/current-state/handoff/tasks/open
questions/decisions index/glossary; this changelog.
