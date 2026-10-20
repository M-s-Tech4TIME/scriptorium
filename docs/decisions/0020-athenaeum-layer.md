# 0020 — Athenaeum layer: the native library hierarchy

- **Status:** accepted
- **Decided:** 2026-10-21 (owner)
- **Scope:** organizational model of Scriptorium; amends 0018 (Q-M3-6/7/8)

## Native hierarchy (owner framing)

Scriptorium is the center of managing, building, and serving documentation.
The canonical, ground-up structure is:

```
user ──owns──> Athenaeum(s) ──contains──> categories (sections)
                                            └── grimoires (books/projects,
                                                categorized or uncategorized)
```

An **Athenaeum** (owner's chosen name for "Library") is the complete
documentation project for one product/company of a user — multiple
products ⇒ multiple Athenaeums. Categories are **sections inside an
Athenaeum**, not user-global. This is the native model; 0018's per-user
categories are superseded.

## Decisions (owner, all option A)

- **Q-M3-9=A** Categories are per-Athenaeum: `grimoire_categories`
  drops `user_id`; `UNIQUE(athenaeum_id, name)`; ownership flows through
  the Athenaeum's owner.
- **Q-M3-10=A** `grimoires.athenaeum_id` NOT NULL direct FK — every
  grimoire lives in an Athenaeum (uncategorized ones included); category
  is optional *within* that Athenaeum.
- **Q-M3-11=A** Athenaeum delete refuses `409` while it holds grimoires —
  move or delete them first (no accidental destruction).
- **Q-M3-12=A** Sharing stays grimoire-level (memberships); Athenaeum-level
  sharing is a future decision.
- **Q-M3-13=A** Nested sidebar endpoint: `GET /api/v1/athenaeums/{id}/sidebar`
  returns categories → their grimoires + the uncategorized bucket in one
  call (matches the sidebar mental model).

## Micro-defaults (owner-approved with the set)

- Table `athenaeums`, model `Athenaeum`, paths `/api/v1/athenaeums`;
  fields: `id, owner_id (FK users CASCADE), slug, title, created_at`.
- Slug uniqueness **per owner**: partial-unique `(owner_id, slug)` — every
  user may own a slug `default`.
- Migration `0004` backfills one Athenaeum titled **"Default"** per user
  and re-points all existing categories/grimoires into it, then enforces
  NOT NULL. Old migrations stay immutable (append-only history).
- Grimoire PATCH gains a cross-Athenaeum **move** (owner of both ends).
- Audit rows: `athenaeum_created|patched|deleted`, `grimoire_moved`.
  Refused deletes write no audit row (nothing happened).
- Category endpoint access = owner of the Athenaeum (Q-M3-12: no sharing
  layer above grimoires yet).

## Test/CI plan

- Live-PG cases: athenaeum lifecycle (create/list/dup-slug-per-owner/
  rename), delete-refusal (409 + no audit), sidebar shape (categories +
  uncategorized), grimoire create requires owned athenaeum (422/404),
  cross-Athenaeum move, category flows under the new paths.
- Offline suite skips live cases (needs_db) as before.
