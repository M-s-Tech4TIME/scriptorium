# 0036 — URL durability: public-name renames, aliases, and tombstones

- **Status:** accepted and implemented
- **Decided:** 2026-10-28 (owner approved A1/B1/C1/D1/E1/F1 and confirmed
  URL-scheme Option 1)
- **Amends:** 0035 D1 (the public name is no longer immutable; the URL
  shape and all other 0035 rulings are unchanged)
- **Scope:** site-level public-name durability. Page-level path aliases,
  custom domains, SEO metadata/canonical policy, and distribution remain
  later phases.

## Owner rulings

| Fork | Ruling |
|---|---|
| A1 — public-name durability | The owner can rename an Athenaeum's public name without rebuilding. The old name becomes a permanent alias that redirects to the current name. Editor-slug renames remain independent and never move the public URL. |
| B1 — path scope | Page-level path aliases are deferred. Numbered builds preserve their old page paths; `latest`/`stable` page paths may change after an editor renames a chapter/folio. |
| C1 — registry and API | One `public_names` registry owns the single global namespace. Owner-only `PATCH /api/v1/athenaeums/{id}/public-slug`; renames are transactional, audited, and never rebuild artifacts. |
| D1 — redirect semantics | Aliases use `308` after the current site's access check, preserve path and query, use a relative `Location`, and flatten to the current canonical name. Public alias responses are `no-cache`; private ones are `private, no-store`, `Vary: Cookie`, `X-Robots-Tag: noindex, nofollow`. |
| E1 — tombstones | Deleting an Athenaeum permanently tombstones every name it held. Names are never reused by another site, even after deletion. |
| F1 — namespace and validation | A single namespace prevents canonical/alias collisions across owners. New names must match `[a-z0-9-]+`, are capped at 160 characters, and cannot be `latest`, `stable`, `b`, `_static`, or `api` (`422`). A name held by another site is `409`; a concurrent collision is also a clean `409`. |

## URL scheme (confirmed Option 1)

Keep the existing shape; `/a/` remains part of every public URL:

```
/a/{public_slug}/                  -> latest, else stable
/a/{public_slug}/latest/...        -> latest pointer
/a/{public_slug}/stable/...        -> stable pointer
/a/{public_slug}/b/{number}/...    -> immutable numbered build
```

Numbered builds stay public and remain the immutable build identity for
rollback, stable links, and future archiving. Build numbers are not
semantic versions; future version labels/aliases may layer on top.

## Registry and schema (migration 0008)

`public_names` is the authoritative namespace:

- `slug` — text primary key; one row per canonical name, alias, or
  tombstone.
- `athenaeum_id` — nullable FK to `athenaeums.id` with `ON DELETE SET
  NULL`. A live current/alias row points at its site; a tombstone has
  `NULL`.
- `is_current` — exactly one current row per live Athenaeum, enforced by a
  partial unique index on `(athenaeum_id) WHERE is_current AND
  athenaeum_id IS NOT NULL`.
- `created_at`, `retired_at` — timestamps; `retired_at` records when a
  name stopped being current.

Migration 0008 creates the table/indexes and backfills every existing
`athenaeums.public_slug` as its current row. No existing URL changes.
Downgrade drops the registry; aliases created after the migration are
therefore not recoverable on a downgrade.

`athenaeums.public_slug` remains the denormalized canonical value used by
serving and publication responses. It is updated atomically with the
registry in the same transaction. The registry's slug primary key plus a
transaction-scoped advisory lock serialize ordinary create/rename/delete
races; direct database conflicts still surface as `409`, never a `500`.

## Rename API

`PATCH /api/v1/athenaeums/{id}/public-slug` with
`{"public_slug": "new-name"}`.

- Owner-only; a foreign Athenaeum id is the uniform `404`.
- `[a-z0-9-]+`, 1–160 characters, not a reserved route word: otherwise
  `422`.
- A name held by another site (current, alias, or tombstone): `409`.
- Reusing one of the same site's own retired names is allowed (reversion).
  The previous current name becomes an alias.
- Same-name request is a no-op (no new alias, no audit row).
- Success updates the canonical column and registry, writes one
  `athenaeum_public_slug_changed` audit row, commits, and returns the
  Athenaeum body. No artifact is rewritten or rebuilt.
- `GET /api/v1/athenaeums/{id}/publication` includes
  `public_aliases: [{slug, retired_at}]` so the owner can see retired names.

Creation still allocates a globally unique name from the editor slug
(8-hex suffix on collision). New allocations also skip reserved route
words and tombstones. There is no create-time public-name override.

## Serving aliases

Resolution checks `public_names` by the requested first path segment:

- unknown or tombstoned name -> uniform `404`;
- current name -> serve normally;
- live alias -> authorize the **current** Athenaeum first, then
  `308` to `/a/{current}/...`.

The alias target preserves the suffix and query string, stays relative,
and resolves directly to the current canonical name (A -> B -> C means A
goes to C, not B). Private aliases never redirect before access succeeds,
so an outsider cannot use an old name to discover a private site. Canonical
slash/root redirects remain `307`; aliases are permanent `308`.

## Deletion and tombstones

`DELETE /api/v1/athenaeums/{id}` still refuses `409` while grimoires
remain. On an allowed delete, all registry rows for the site are retired
and then the FK sets `athenaeum_id` to `NULL`. The rows remain forever:
old URLs return `404`, and no new site can claim the name. A deletion
also retires any aliases the site had accumulated.

## Disclosures and limits

- **B1:** `latest`/`stable` page paths follow the current editor tree.
  Renaming a chapter/folio can change those page paths; old numbered
  builds keep their old paths. Page-level aliases are not implemented.
- **No rebuild:** old artifacts keep their build-time `site_id`,
  `data-sd-athenaeum`, custom CSS namespace, and manifest. The canonical
  URL changes, but the artifact content does not.
- **SEO duplication:** the same content can appear under `latest`,
  `stable`, numbered, and alias URLs. Canonical-host/channel policy,
  `noindex` decisions, sitemap/robots, structured data, and social
  metadata are deliberately deferred to the dedicated SEO phase. SEO
  features must be user-controllable per Athenaeum in the editorial panel;
  no SEO policy is decided here.
- **Migration scope:** 0008 can backfill only public slugs that still
  exist. An Athenaeum deleted before 0008 has no registry row, so its old
  name is not tombstoned; post-0008 API deletion always tombstones.
- **No custom domains:** a future dedicated docs origin could remove
  `/a/` without app-route collisions; that is not part of this phase.
- Public numbered builds are intentionally immutable-cached. If a site is
  later made private, already-cached copies at public numbered URLs are
  outside the server's control.
- Distribution remains deferred until Q-DIST-A…D approval; signed
  packages/app-venv assembly (M5) remain deferred.

## Verification

- Live PG16/CI PG18: rename, private-auth-before-redirect, owner/member
  alias access, outsider `404`, public alias headers, root/channel/
  numbered/asset suffix preservation, query preservation, alias
  flattening, reversion, same-name no-op, reserved/invalid `422`, foreign
  site `404`, current/alias/tombstone collisions `409`, tombstone
  non-reuse, editor-rename independence, publication aliases, and audit
  rows.
- Migration: 0008 backfill from an existing `public_slug`, plus
  upgrade/downgrade/upgrade round-trip.
- Static: `ruff`, `ruff format --check`, `mypy --strict`, `compileall`,
  `pytest -W error`; CI ×3 green after push.
